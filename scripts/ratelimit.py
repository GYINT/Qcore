#!/usr/bin/env python3
"""qcm_ratelimit.py — QCM MCP Server Rate Limiter

Token Bucket 算法实现：
  - Per-IP 限流（100 req/min）
  - Per-Token 限流（1000 req/hour）
  - Global 限流（10000 req/min，防雪崩）

存储：内存 LRU cache（避免重启丢失关键数据）
返回：True（允许）+ Retry-After（秒）/ False（拒绝）

用法：
  from ratelimit import RateLimiter
  limiter = RateLimiter(per_ip=100, per_token=1000, global_limit=10000)
  ok, retry_after = limiter.check(client_ip="1.2.3.4", token="xxx")
"""
import time
import threading
from collections import deque
from typing import Tuple, Optional, Dict


class TokenBucket:
    """单 key 的 token bucket（滑动窗口）"""

    def __init__(self, limit: int, window_s: float):
        self.limit = limit
        self.window_s = window_s
        self.timestamps: deque = deque()
        self._lock = threading.Lock()

    def try_acquire(self) -> Tuple[bool, float]:
        """尝试获取 1 个 token

        Returns:
            (allowed, retry_after_seconds)
        """
        with self._lock:
            now = time.time()
            # 清理过期时间戳
            while self.timestamps and self.timestamps[0] < now - self.window_s:
                self.timestamps.popleft()

            if len(self.timestamps) < self.limit:
                self.timestamps.append(now)
                return True, 0.0
            else:
                # 最早的时间戳 + window_s 是下一次可用时刻
                oldest = self.timestamps[0]
                retry_after = oldest + self.window_s - now
                return False, max(0.1, retry_after)

    def get_usage(self) -> Tuple[int, int]:
        """返回 (当前计数, 限额)"""
        with self._lock:
            now = time.time()
            while self.timestamps and self.timestamps[0] < now - self.window_s:
                self.timestamps.popleft()
            return len(self.timestamps), self.limit


class RateLimiter:
    """多层 rate limiter（global + per-IP + per-token）"""

    def __init__(self,
                 per_ip: int = 100,
                 per_ip_window_s: float = 60.0,
                 per_token: int = 1000,
                 per_token_window_s: float = 3600.0,
                 global_limit: int = 10000,
                 global_window_s: float = 60.0,
                 max_keys: int = 10000):
        self.per_ip = per_ip
        self.per_ip_window_s = per_ip_window_s
        self.per_token = per_token
        self.per_token_window_s = per_token_window_s
        self.global_limit = global_limit
        self.global_window_s = global_window_s

        self._buckets: Dict[str, TokenBucket] = {}
        self._global_bucket = TokenBucket(global_limit, global_window_s)
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def _get_bucket(self, key: str, limit: int, window_s: float) -> TokenBucket:
        """懒加载 bucket + LRU 清理"""
        with self._lock:
            if key not in self._buckets:
                # LRU：超过 max_keys 时清理最旧的
                if len(self._buckets) >= self._max_keys:
                    # 简单清理：删除前 100 个（按字典插入顺序）
                    keys_to_remove = list(self._buckets.keys())[:100]
                    for k in keys_to_remove:
                        del self._buckets[k]
                self._buckets[key] = TokenBucket(limit, window_s)
            return self._buckets[key]

    def check(self, client_ip: str, token: Optional[str] = None) -> Tuple[bool, float]:
        """检查是否允许请求

        Args:
            client_ip: 客户端 IP（用于 per-IP 限流）
            token: 认证 token（用于 per-token 限流，可选）

        Returns:
            (allowed, retry_after_seconds)
            allowed=False 时 retry_after 是最少等待秒数
        """
        # 1. Global 限流
        global_ok, global_retry = self._global_bucket.try_acquire()
        if not global_ok:
            return False, global_retry

        # 2. Per-IP 限流
        if client_ip:
            ip_bucket = self._get_bucket(f"ip:{client_ip}", self.per_ip, self.per_ip_window_s)
            ip_ok, ip_retry = ip_bucket.try_acquire()
            if not ip_ok:
                return False, ip_retry

        # 3. Per-Token 限流
        if token:
            token_bucket = self._get_bucket(f"token:{token}", self.per_token, self.per_token_window_s)
            token_ok, token_retry = token_bucket.try_acquire()
            if not token_ok:
                return False, token_retry

        return True, 0.0

    def get_stats(self) -> dict:
        """获取限流状态"""
        return {
            "global": {
                "current": self._global_bucket.get_usage()[0],
                "limit": self.global_limit,
                "window_s": self.global_window_s,
            },
            "per_ip": {
                "limit": self.per_ip,
                "window_s": self.per_ip_window_s,
                "active_keys": sum(1 for k in self._buckets if k.startswith("ip:")),
            },
            "per_token": {
                "limit": self.per_token,
                "window_s": self.per_token_window_s,
                "active_keys": sum(1 for k in self._buckets if k.startswith("token:")),
            },
            "total_buckets": len(self._buckets),
        }


# 全局实例（可被 config 覆盖）
rate_limiter = RateLimiter()


if __name__ == "__main__":
    # Demo
    limiter = RateLimiter(per_ip=5, per_ip_window_s=10)

    print("=== Per-IP 限流测试（5 req / 10s）===")
    for i in range(8):
        ok, retry = limiter.check(client_ip="1.2.3.4")
        icon = "✅" if ok else "❌"
        print(f"  {icon} 请求 {i+1}: allowed={ok} retry_after={retry:.2f}s")

    print()
    print("=== /stats 输出 ===")
    import json
    print(json.dumps(limiter.get_stats(), ensure_ascii=False, indent=2))