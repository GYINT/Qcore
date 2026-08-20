#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 词源观测环 · 未命中词统计（V8.4 动态自适应闭环 Step 1）

功能：route() 未命中（need_research）时记录未命中词频次 → 同词 ≥3 次触发调研建议
     （补齐 suggest_research 缺失的"调用方统计" · §11.2/§13 热词发现闭环驱动信号）

用法：
  from hit_tracker import record_miss, top_misses, suggest_research, reset
  record_miss("船舶螺旋桨空蚀")     # 未命中词落盘
  top_misses(threshold=3)          # 达阈值词（待调研）
  suggest_research(word)           # 触发调研建议（置信度门控）
  reset(word)                      # 入库/确认后重置计数

设计：
  - 数据：references/hit_stats.json（词 → {count, first_seen, last_seen}）
  - 提取：query 中 2-4 字中文窗口 + ≥3 字母英文词（与词库匹配后取未命中片段）
  - 容量：单词计数上限 99 · 词典上限 500（防膨胀）
  - 防御：文件读写异常静默降级（观测环失败不影响路由）
"""
import json
import os
import re
import sys
import threading
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
HIT_STATS = ROOT / "references" / "hit_stats.json"

MISS_THRESHOLD = 3      # 同词未命中 ≥3 次 → 触发调研
MAX_WORD_COUNT = 99     # 单词计数上限
MAX_ENTRIES = 500       # 词典上限
_lock = threading.Lock()


def _load() -> dict:
    try:
        if HIT_STATS.exists():
            return json.loads(HIT_STATS.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(data: dict) -> None:
    try:
        HIT_STATS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def extract_miss_words(query: str, known_words: set = None) -> list:
    """从未命中 query 提取候选词（整句 + 有意义中文短语 + 英文词）

    V8.4 优化：废弃 4 字全滑窗（产生"蚀机理分"类碎词）；
    改为整句候选 + 中文 run 前缀/后缀 6 字段（语义完整可调研）。
    """
    import re
    candidates = set()
    q = query.strip()
    if q:
        candidates.add(q[:40])  # 整句（≤40 字 · 调研输入语义完整）
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", q):
        if len(run) <= 6:
            candidates.add(run)          # 短串整串
        else:
            candidates.add(run[:6])      # 长串前缀 6 字
            candidates.add(run[-6:])     # 长串后缀 6 字
    # 英文词 ≥3 字母
    candidates.update(w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", q))
    # 排除已知词（已命中词库/实体 → 无需调研）
    if known_words:
        candidates = {c for c in candidates if c.lower() not in known_words}
    return sorted(candidates)


def record_miss(query: str, known_words: set = None) -> list:
    """记录未命中词频次（返回本次新增/递增的词）"""
    words = extract_miss_words(query, known_words)
    if not words:
        return []
    with _lock:
        data = _load()
        now = datetime.now().isoformat(timespec="minutes")
        bumped = []
        for w in words[:8]:  # 单次最多 8 词
            e = data.setdefault(w, {"count": 0, "first_seen": now, "last_seen": now})
            e["count"] = min(e["count"] + 1, MAX_WORD_COUNT)
            e["last_seen"] = now
            if e["count"] >= MISS_THRESHOLD:
                bumped.append(w)
        # 容量治理：超限淘汰最旧
        if len(data) > MAX_ENTRIES:
            for k in sorted(data, key=lambda k: data[k].get("last_seen", ""))[:len(data) - MAX_ENTRIES]:
                data.pop(k, None)
        _save(data)
        return bumped


def top_misses(threshold: int = MISS_THRESHOLD) -> list:
    """达阈值未命中词（待调研候选）· V8.4 防御：跳过非 dict 条目（防损坏文件崩溃）"""
    data = _load()
    return sorted(
        [{"word": w, "count": e["count"], "last_seen": e.get("last_seen", "")}
         for w, e in data.items() if isinstance(e, dict) and e.get("count", 0) >= threshold],
        key=lambda x: -x["count"],
    )


def suggest_research(word: str = None, hit_count: int = MISS_THRESHOLD) -> dict:
    """触发调研建议（suggest_research 补齐实现 · 置信度门控 ≥70 才入库）"""
    if word:
        return {
            "suggest": word,
            "trigger": f"同词未命中 ≥{hit_count} 次（当前统计命中阈值）",
            "gate": "调研结果置信度 ≥70 才可入 keyword.yaml/entities.yaml（§8.4）",
            "level": "deep_realtime",
        }
    misses = top_misses(hit_count)
    return {
        "suggest": [m["word"] for m in misses],
        "trigger": f"{len(misses)} 个词达到未命中阈值 {hit_count}",
        "gate": "调研结果置信度 ≥70 才可入 keyword.yaml/entities.yaml（§8.4）",
        "level": "deep_realtime",
    }


def reset(word: str) -> None:
    """入库/确认后重置计数"""
    with _lock:
        data = _load()
        if word in data:
            data.pop(word)
            _save(data)


def stats() -> dict:
    """观测摘要（供 /metrics 与闭环报告）"""
    data = _load()
    return {
        "total_tracked": len(data),
        "above_threshold": len(top_misses()),
        "threshold": MISS_THRESHOLD,
    }


def main():
    if "--stats" in sys.argv:
        s = stats()
        print(f"未命中词观测：跟踪 {s['total_tracked']} 词 · 达阈值 {s['above_threshold']}（≥{s['threshold']}）")
        for m in top_misses()[:10]:
            print(f"  🔍 {m['word']}（{m['count']} 次 · 最近 {m['last_seen'][:16]}）")
        return 0
    if len(sys.argv) >= 3 and sys.argv[1] == "--record":
        bumped = record_miss(sys.argv[2])
        print(f"已记录：{sys.argv[2]} → 达阈值词: {bumped}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
