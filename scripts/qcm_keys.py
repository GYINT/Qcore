#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM Key 管理 CLI（V8.4 T5 + 批次 B · 对齐 infoseek_keys_cli）

用法：
  python3 scripts/qcm_keys.py list              # Key 健康状态列表
  python3 scripts/qcm_keys.py health            # 健康统计（同上）
  python3 scripts/qcm_keys.py register <provider> [env_name] [quota_limit]
  python3 scripts/qcm_keys.py reset [provider]  # 重置健康状态（空=全部）
  python3 scripts/qcm_keys.py fail <provider> [n]   # 模拟 n 次失败（测试熔断）
  python3 scripts/qcm_keys.py rotate <provider> [env_name]  # 轮换 Key（重置健康+重读 env）
  python3 scripts/qcm_keys.py probe [provider]  # 失效探测（真实最小调用验证 · 空=全部）
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from key_manager import KeyManager  # noqa: E402


def main():
    km = KeyManager.instance()
    args = sys.argv[1:]
    if not args or args[0] in ("list", "health"):
        for r in km.health():
            mark = {"ACTIVE": "✅", "DEGRADED": "⚠️", "CIRCUIT_OPEN": "🔴", "EXHAUSTED": "⛔"}.get(r["status"], "?")
            print(f"  {mark} {r['provider']:<18} {r['status']:<12} fail={r['fail_count']} "
                  f"quota={r['quota_used']}/{r['quota_limit'] or '∞'} env={r['env_name']}")
        s = km.stats()
        print(f"\n  统计: {s['total']} 个 Key（ACTIVE {s['active']} · DEGRADED {s['degraded']} · 熔断 {s['circuit_open']} · 耗尽 {s['exhausted']}）")
        return 0

    if args[0] == "register" and len(args) >= 2:
        env = args[2] if len(args) > 2 else ""
        quota = int(args[3]) if len(args) > 3 and args[3].isdigit() else 0
        km.register(args[1], env, quota)
        print(f"✅ 已注册 {args[1]}（env={env or 'auto'} · quota_limit={quota or '∞'}）")
        return 0

    if args[0] == "reset":
        km.reset(args[1] if len(args) > 1 else "")
        print("✅ Key 状态已重置")
        return 0

    if args[0] == "fail" and len(args) >= 2:
        n = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        for _ in range(n):
            km.report_failure(args[1])
        print(f"ℹ️  {args[1]} 已记录 {n} 次失败（状态: {km.get(args[1]).status}）")
        return 0

    if args[0] == "rotate" and len(args) >= 2:
        """轮换 Key（V8.4 批次 B）：重置健康状态 + 重新读取 env（支持更换新 key）"""
        env = args[2] if len(args) > 2 else ""
        km.register(args[1], env)  # 重读 env key
        km.reset(args[1])          # 清熔断/配额/失败计数
        r = km.get(args[1])
        has = bool(os.environ.get(r.env_name) if r.env_name else "")
        print(f"✅ 已轮换 {args[1]}（env={r.env_name or 'auto'} · key 存在: {has} · 状态: {r.status}）")
        return 0

    if args[0] == "probe":
        """失效探测（V8.4 批次 B）：真实最小调用验证 Key 有效性"""
        from llm_router import LLMRouter
        router = LLMRouter(mode="real")
        targets = [args[1]] if len(args) > 1 else [r["provider"] for r in km.health() if r["env_name"]]
        ok, fail = 0, 0
        for name in targets:
            r = km.get(name)
            if not r or not r.env_name or not os.environ.get(r.env_name):
                print(f"  ⏭  {name:<12} 无 key（env={r.env_name if r else '-'}）")
                continue
            try:
                res = router.call("回复 OK", max_tokens=5, prefer_provider=name)
                if res.get("mode") == "real":
                    km.report_success(name)
                    ok += 1
                    print(f"  ✅ {name:<12} 有效（真实调用 {res.get('duration_s', 0):.1f}s）")
                else:
                    print(f"  ⚠️  {name:<12} 未走真实路径（mode={res.get('mode')}）")
            except Exception as e:
                km.report_failure(name)
                fail += 1
                print(f"  ❌ {name:<12} 失效: {type(e).__name__}: {str(e)[:60]}")
        print(f"\n  探测结果: 有效 {ok} · 失效 {fail} · 共 {len(targets)}")
        return 1 if fail else 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
