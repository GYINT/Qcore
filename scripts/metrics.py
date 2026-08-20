#!/usr/bin/env python3
"""qcm_metrics.py — QCM MCP Server Metrics Collector

Prometheus 文本格式输出 + 内存环形 buffer

Metrics 类型：
  Counter   - 单调递增计数（requests_total, errors_total）
  Gauge     - 任意值（active_sessions, corpus_files）
  Histogram - 分布统计（duration_seconds，使用指数桶）
  Summary   - 摘要统计（quantile-based）

用法：
  from metrics import metrics
  metrics.inc("requests_total", labels={"method": "tools/call", "tool": "qcm_research"})
  metrics.observe("duration_seconds", 0.234, labels={"tool": "qcm_research"})
  metrics.set("active_sessions", 5)
  text = metrics.export() # Prometheus 文本格式
"""
import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class MetricsCollector:
    """Prometheus 兼容的 Metrics 收集器"""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._gauges: Dict[Tuple[str, ...], float] = {}
        self._histograms: Dict[Tuple[str, ...], List[float]] = defaultdict(list)
        self._summaries: Dict[Tuple[str, ...], List[float]] = defaultdict(list)
        self._start_time = time.time()

    def _make_key(self, name: str, labels: Optional[dict] = None) -> Tuple[str, ...]:
        """生成 (name, k1, v1, k2, v2, ...) 形式的 key"""
        if not labels:
            return (name,)
        items = []
        for k, v in sorted(labels.items()):
            items.append(k)
            items.append(str(v))
        return (name,) + tuple(items)

    def inc(self, name: str, value: float = 1.0, labels: Optional[dict] = None):
        """Counter 自增"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def set(self, name: str, value: float, labels: Optional[dict] = None):
        """Gauge 设置值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Optional[dict] = None):
        """Histogram 记录观测值"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            # 限制 buffer 大小（最近 1000 个观测值）
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

    def export(self) -> str:
        """导出 Prometheus 文本格式"""
        with self._lock:
            lines = []

            # HELP/TYPE 元信息
            declared = set()
            for key in list(self._counters.keys()) + list(self._gauges.keys()) + list(self._histograms.keys()):
                name = key[0]
                if name not in declared:
                    lines.append(f"# HELP {name} QCM MCP metric")
                    if name in self._counters:
                        lines.append(f"# TYPE {name} counter")
                    elif name in self._gauges:
                        lines.append(f"# TYPE {name} gauge")
                    elif name in self._histograms:
                        lines.append(f"# TYPE {name} histogram")
                    declared.add(name)

            # Counter 输出
            for key, value in sorted(self._counters.items()):
                lines.append(self._format_line(key, value))

            # Gauge 输出
            for key, value in sorted(self._gauges.items()):
                lines.append(self._format_line(key, value))

            # Histogram 输出（buckets）
            for key, observations in sorted(self._histograms.items()):
                name = key[0]
                # 解析 labels（key 格式：name, k1, v1, k2, v2, ...）
                labels = {}
                for i in range(1, len(key), 2):
                    if i + 1 < len(key):
                        labels[key[i]] = key[i+1]
                # 指数桶
                buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                for b in buckets:
                    count = sum(1 for v in observations if v <= b)
                    bucket_labels = dict(labels)
                    bucket_labels["le"] = str(b)
                    lines.append(self._format_line_with_labels(f"{name}_bucket", bucket_labels, count))
                # +Inf
                inf_labels = dict(labels)
                inf_labels["le"] = "+Inf"
                lines.append(self._format_line_with_labels(f"{name}_bucket", inf_labels, len(observations)))
                # _count / _sum
                lines.append(self._format_line_with_labels(f"{name}_count", labels, len(observations)))
                lines.append(self._format_line_with_labels(f"{name}_sum", labels, sum(observations)))

            # 系统指标
            lines.append(f"# HELP qcm_uptime_seconds QCM MCP server uptime")
            lines.append(f"# TYPE qcm_uptime_seconds gauge")
            lines.append(f"qcm_uptime_seconds {time.time() - self._start_time:.1f}")

            return "\n".join(lines)

    def _format_line(self, key: Tuple[str, ...], value: float) -> str:
        """格式化单行 metric"""
        name = key[0]
        label_items = key[1:]
        if label_items:
            label_dict = {}
            for i in range(0, len(label_items), 2):
                if i + 1 < len(label_items):
                    label_dict[label_items[i]] = label_items[i+1]
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(label_dict.items()))
            return f"{name}{{{label_str}}} {value}"
        return f"{name} {value}"

    def _format_line_with_labels(self, name: str, labels: dict, value: float) -> str:
        """格式化单行 metric（直接用 labels dict）"""
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}} {value}"
        return f"{name} {value}"

    def get_summary(self) -> dict:
        """获取摘要（用于 /stats API）"""
        with self._lock:
            return {
                "uptime_s": round(time.time() - self._start_time, 1),
                "counters": {self._key_to_str(k): v for k, v in self._counters.items()},
                "gauges": {self._key_to_str(k): v for k, v in self._gauges.items()},
                "histogram_buckets": {self._key_to_str(k): len(v) for k, v in self._histograms.items()},
            }

    def _key_to_str(self, key: Tuple[str, ...]) -> str:
        name = key[0]
        label_items = key[1:]
        if not label_items:
            return name
        parts = []
        for i in range(0, len(label_items), 2):
            parts.append(f"{label_items[i]}={label_items[i+1]}")
        return f"{name}{{{','.join(parts)}}}"


# 全局实例
metrics = MetricsCollector()


# ============ 预定义指标辅助函数 ============

def record_request(method: str, tool: str = "-", status: str = "ok", duration_s: float = 0.0):
    """记录 HTTP 请求"""
    labels = {"method": method, "tool": tool, "status": status}
    metrics.inc("qcm_requests_total", 1, labels)
    metrics.observe("qcm_request_duration_seconds", duration_s, {"tool": tool})


def record_llm_call(provider: str, mode: str, duration_s: float = 0.0, success: bool = True):
    """记录 LLM 调用"""
    status = "success" if success else "fail"
    labels = {"provider": provider, "mode": mode, "status": status}
    metrics.inc("qcm_llm_calls_total", 1, labels)
    if duration_s > 0:
        metrics.observe("qcm_llm_call_duration_seconds", duration_s, {"provider": provider})


def record_tool_call(tool: str, duration_s: float = 0.0, success: bool = True):
    """记录工具调用"""
    status = "ok" if success else "error"
    labels = {"tool": tool, "status": status}
    metrics.inc("qcm_tool_calls_total", 1, labels)
    if duration_s > 0:
        metrics.observe("qcm_tool_call_duration_seconds", duration_s, {"tool": tool})


def record_error(error_type: str):
    """记录错误"""
    metrics.inc("qcm_errors_total", 1, {"type": error_type})


# ============ 词源健康指标（V8.4 闭环 Step 1 · §11.5） ============
def record_keyword_health():
    """采集词源健康指标到 metrics（读 keyword/entities/hit_stats · 纯本地）

    指标：qcm_keyword_total / qcm_keyword_by_status / qcm_keyword_intent_capacity
          qcm_entity_total / qcm_hit_misses_above_threshold
    """
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    try:
        import yaml
        from paths import KEYWORD_YAML, ENTITIES_YAML  # V8.4 路径归一
        kw = yaml.safe_load(KEYWORD_YAML.read_text(encoding="utf-8")) or {}
        ent = yaml.safe_load(ENTITIES_YAML.read_text(encoding="utf-8")) or {}
        items = kw.get("keywords", [])
    except Exception:
        items, ent = [], {}

    metrics.set("qcm_keyword_total", len(items))
    by_status = {}
    intent_cnt = {}
    for it in items:
        st = it.get("status", "new")
        by_status[st] = by_status.get(st, 0) + 1
        if it.get("intent") and it.get("status") != "archived":
            intent_cnt[it["intent"]] = intent_cnt.get(it["intent"], 0) + 1
    for st, cnt in by_status.items():
        metrics.set("qcm_keyword_by_status", cnt, {"status": st})
    for intent, cnt in intent_cnt.items():
        metrics.set("qcm_keyword_intent_capacity", cnt, {"intent": intent})

    metrics.set("qcm_entity_total", len(ent.get("entities", [])))

    try:
        hits = json.loads((root / "references" / "hit_stats.json").read_text(encoding="utf-8")) if (root / "references" / "hit_stats.json").exists() else {}
        above = sum(1 for e in hits.values() if e.get("count", 0) >= 3)
    except Exception:
        above = 0
    metrics.set("qcm_hit_misses_above_threshold", above)

    # V8.4 P4 · 歧义消解指标（读 disambiguation_cases.yaml · 纯本地）
    try:
        import yaml
        cases_path = root / "references" / "config" / "disambiguation_cases.yaml"
        cdata = yaml.safe_load(cases_path.read_text(encoding="utf-8")) if cases_path.exists() else {}
        cases = cdata.get("cases", {}) or {}
        metrics.set("qcm_ambiguity_terms", len(cases))
        metrics.set("qcm_ambiguity_fixed_cases", sum(
            1 for entries in cases.values() for e in entries if e.get("count", 0) >= 3))
    except Exception:
        metrics.set("qcm_ambiguity_terms", 0)
        metrics.set("qcm_ambiguity_fixed_cases", 0)


if __name__ == "__main__":
    # Demo
    metrics.inc("qcm_requests_total", 5, {"method": "tools/call", "tool": "qcm_research"})
    metrics.observe("qcm_request_duration_seconds", 0.234, {"tool": "qcm_research"})
    metrics.observe("qcm_request_duration_seconds", 1.234, {"tool": "qcm_decide"})
    metrics.set("qcm_active_sessions", 3)

    print("=== Prometheus 文本格式输出 ===")
    print(metrics.export())
    print()
    print("=== /stats JSON 摘要 ===")
    import json
    print(json.dumps(metrics.get_summary(), ensure_ascii=False, indent=2))