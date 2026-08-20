#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM Key 全生命周期管理（V8.4 T1 · 对齐 Infoseek core/key_manager.py 已验证模式）

KeyRecord 四态：ACTIVE → DEGRADED → CIRCUIT_OPEN（熔断冷却）→ EXHAUSTED（配额耗尽）
功能：register/get/report_success/report_failure/report_quota/health/reset
持久化：references/key_state.json（Key 健康状态 · 熔断冷却跨进程有效）
熔断：连续失败达阈值 → CIRCUIT_OPEN（60s 冷却）→ 冷却后恢复 ACTIVE

设计对齐（参考 infoseek/core/key_manager.py）：
  - KeyRecord schema：provider/env_name/status/fail_count/circuit_open_until/quota_used/quota_limit
  - 反馈驱动：调用方成功 → report_success 重置；失败 → report_failure 递增 + 熔断
  - 配额感知：429/额度响应 → report_quota → EXHAUSTED 主动降级
"""
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env_file() -> None:
    """轻量 .env 加载（V8.4 批次 B · 无 python-dotenv 依赖）

    读取 QCM_ROOT/.env（KEY=value 行 · # 注释 · 不覆盖已存在的环境变量）
    → Key 配置持久化，免每次会话手动 export
    """
    try:
        env_path = ROOT / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass
STATE_PATH = ROOT / "references" / "key_state.json"

# 状态常量
S_ACTIVE = "ACTIVE"
S_DEGRADED = "DEGRADED"
S_CIRCUIT_OPEN = "CIRCUIT_OPEN"
S_EXHAUSTED = "EXHAUSTED"
VALID_STATES = {S_ACTIVE, S_DEGRADED, S_CIRCUIT_OPEN, S_EXHAUSTED}

# 熔断/阈值参数（环境可调）
CIRCUIT_COOLDOWN = float(os.environ.get("QCM_KEY_CIRCUIT_COOLDOWN", "60"))   # 熔断冷却秒数
MAX_FAILS = int(os.environ.get("QCM_KEY_MAX_FAILS", "3"))                     # 连续失败熔断阈值


class KeyRecord:
    """单个 Key 的健康状态记录"""

    def __init__(self, provider: str, env_name: str = "", key: str = "",
                 quota_limit: int = 0):
        self.provider = provider
        self.env_name = env_name
        self.key = key
        self.status = S_ACTIVE
        self.fail_count = 0
        self.circuit_open_until = 0.0
        self.quota_used = 0
        self.quota_limit = quota_limit
        self.last_success = ""
        self.last_failure = ""

    def to_dict(self) -> dict:
        return {
            "provider": self.provider, "env_name": self.env_name,
            "status": self.status, "fail_count": self.fail_count,
            "circuit_open_until": self.circuit_open_until,
            "quota_used": self.quota_used, "quota_limit": self.quota_limit,
            "last_success": self.last_success, "last_failure": self.last_failure,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KeyRecord":
        r = cls(d.get("provider", ""), d.get("env_name", ""), d.get("key", ""))
        r.status = d.get("status", S_ACTIVE)
        r.fail_count = d.get("fail_count", 0)
        r.circuit_open_until = d.get("circuit_open_until", 0.0)
        r.quota_used = d.get("quota_used", 0)
        r.quota_limit = d.get("quota_limit", 0)
        r.last_success = d.get("last_success", "")
        r.last_failure = d.get("last_failure", "")
        return r


class KeyManager:
    """Key 全生命周期管理器（单例 · 持久化到 key_state.json）"""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, state_path: str = ""):
        self.state_path = Path(state_path) if state_path else STATE_PATH
        self._records: dict = {}
        _load_env_file()  # V8.4 批次 B：.env 加载（Key 配置持久化）
        self._load()

    @classmethod
    def instance(cls) -> "KeyManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = KeyManager()
        return cls._instance

    # ── 持久化 ──
    def _load(self) -> None:
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                for prov, d in data.items():
                    self._records[prov] = KeyRecord.from_dict(d)
        except Exception:
            pass

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(
                json.dumps({p: r.to_dict() for p, r in self._records.items()},
                           ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass

    # ── 注册/查询 ──
    def register(self, provider: str, env_name: str = "", quota_limit: int = 0) -> KeyRecord:
        key = os.environ.get(env_name, "") if env_name else ""
        with self._lock:
            r = self._records.get(provider)
            if r is None:
                r = KeyRecord(provider, env_name, key, quota_limit)
                self._records[provider] = r
            else:
                r.env_name = env_name or r.env_name
                r.key = key or r.key
                if quota_limit:
                    r.quota_limit = quota_limit
            self._save()
            return r

    def get(self, provider: str) -> KeyRecord:
        """获取记录（调用前检查熔断/配额状态）"""
        r = self._records.get(provider)
        if r is None:
            r = KeyRecord(provider, "")
            self._records[provider] = r
        now = time.time()
        # 熔断冷却到期 → 恢复 ACTIVE（探测期）
        if r.status == S_CIRCUIT_OPEN and now >= r.circuit_open_until:
            r.status = S_ACTIVE
            r.fail_count = 0
            self._save()
        return r

    def is_usable(self, provider: str) -> bool:
        """是否可用（非熔断/非耗尽）"""
        r = self.get(provider)
        return r.status in (S_ACTIVE, S_DEGRADED)

    def get_usable_providers(self, providers: list) -> list:
        """过滤出可用 provider（按传入顺序 · 跳过熔断/耗尽）"""
        return [p for p in providers if self.is_usable(p)]

    # ── 反馈驱动 ──
    def report_success(self, provider: str) -> None:
        with self._lock:
            r = self.get(provider)
            r.status = S_ACTIVE
            r.fail_count = 0
            r.circuit_open_until = 0.0
            r.last_success = datetime.now().isoformat(timespec="minutes")
            self._save()

    def report_failure(self, provider: str) -> None:
        with self._lock:
            r = self.get(provider)
            r.fail_count += 1
            r.last_failure = datetime.now().isoformat(timespec="minutes")
            if r.fail_count >= MAX_FAILS:
                r.status = S_CIRCUIT_OPEN
                r.circuit_open_until = time.time() + CIRCUIT_COOLDOWN
            elif r.fail_count >= 1:
                r.status = S_DEGRADED
            self._save()

    def report_quota(self, provider: str, used: int = 0, limit: int = 0) -> None:
        """配额反馈（429/额度响应 → EXHAUSTED 主动降级）"""
        with self._lock:
            r = self.get(provider)
            if used:
                r.quota_used = used
            if limit:
                r.quota_limit = limit
            if r.quota_limit and r.quota_used >= r.quota_limit:
                r.status = S_EXHAUSTED
                r.last_failure = datetime.now().isoformat(timespec="minutes")
            self._save()

    def reset(self, provider: str = "") -> None:
        """重置健康状态（provider 空 = 全部）"""
        with self._lock:
            if provider:
                if provider in self._records:
                    self._records[provider] = KeyRecord(provider)
            else:
                self._records = {}
            self._save()

    # ── 健康报告 ──
    def health(self) -> list:
        return [r.to_dict() for r in sorted(self._records.values(),
                                            key=lambda r: r.provider)]

    def stats(self) -> dict:
        recs = self.health()
        return {
            "total": len(recs),
            "active": sum(1 for r in recs if r["status"] == S_ACTIVE),
            "degraded": sum(1 for r in recs if r["status"] == S_DEGRADED),
            "circuit_open": sum(1 for r in recs if r["status"] == S_CIRCUIT_OPEN),
            "exhausted": sum(1 for r in recs if r["status"] == S_EXHAUSTED),
        }


def main():
    import sys
    km = KeyManager.instance()
    args = sys.argv[1:]
    if not args or args[0] == "list":
        print("QCM Key 健康状态：")
        for r in km.health():
            mark = {"ACTIVE": "✅", "DEGRADED": "⚠️", "CIRCUIT_OPEN": "🔴", "EXHAUSTED": "⛔"}.get(r["status"], "?")
            print(f"  {mark} {r['provider']:<18} {r['status']:<12} fail={r['fail_count']} "
                  f"quota={r['quota_used']}/{r['quota_limit'] or '∞'}")
        s = km.stats()
        print(f"\n  统计: {s['total']} 个 Key（ACTIVE {s['active']} · DEGRADED {s['degraded']} · 熔断 {s['circuit_open']} · 耗尽 {s['exhausted']}）")
        return 0
    if args[0] == "reset":
        km.reset(args[1] if len(args) > 1 else "")
        print("✅ Key 状态已重置")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
