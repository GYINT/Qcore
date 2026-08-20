#!/usr/bin/env python3
"""qcm_audit_aggregator.py — 跨设备审计聚合器（ELK 适配）

功能：
  1. 收集多设备 audit.log（JSON Lines）
  2. 聚合统计（按 device/user/tool/status）
  3. ELK 适配（输出 Elasticsearch bulk 格式）
  4. 导出聚合报告

用法：
  python3 qcm_audit_aggregator.py collect /path/to/audit_logs/     # 收集 + 统计
  python3 qcm_audit_aggregator.py elk /path/to/logs/ --out bulk.ndjson # 输出 ES bulk
  python3 qcm_audit_aggregator.py report /path/to/logs/           # 聚合报告
"""
import os
import sys
import json
import glob
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional


class AuditAggregator:
    """跨设备审计日志聚合器"""

    def __init__(self):
        self.records: List[Dict] = []
        self.sources: List[str] = []

    # ============ 收集 ============
    def collect(self, log_dirs: List[str], pattern: str = "audit.log") -> int:
        """从多个目录收集 audit.log（JSON Lines）"""
        count = 0
        for d in log_dirs:
            if os.path.isdir(d):
                for f in glob.glob(os.path.join(d, "**", pattern), recursive=True):
                    self.sources.append(f)
                    count += self._parse_file(f)
        return count

    def _parse_file(self, path: str) -> int:
        n = 0
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        rec["_source_file"] = path
                        self.records.append(rec)
                        n += 1
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
        return n

    # ============ 聚合统计 ============
    def stats(self) -> Dict[str, Any]:
        """聚合统计（按维度）"""
        if not self.records:
            return {"total": 0}

        by_device = Counter(r.get("device_id", "unknown") for r in self.records)
        by_user = Counter(r.get("user_id", "anonymous") for r in self.records)
        by_tool = Counter(r.get("tool", "unknown") for r in self.records)
        by_status = Counter(r.get("status", 0) for r in self.records)
        by_method = Counter(r.get("method", "unknown") for r in self.records)

        # 时间范围
        times = [r.get("time", "") for r in self.records if r.get("time")]
        times.sort()

        return {
            "total": len(self.records),
            "sources": len(self.sources),
            "time_range": (times[0], times[-1]) if times else (None, None),
            "by_device": dict(by_device.most_common()),
            "by_user": dict(by_user.most_common()),
            "by_tool": dict(by_tool.most_common(15)),
            "by_status": dict(by_status.most_common()),
            "by_method": dict(by_method.most_common()),
        }

    # ============ ELK 适配 ============
    def to_elk_bulk(self, index: str = "infoseek-audit") -> str:
        """输出 Elasticsearch bulk 格式（ELK 导入）

        NDJSON：action 行 + source 行交替
        """
        lines = []
        for i, rec in enumerate(self.records):
            # 去掉 _source_file（本地字段，不导入 ES）
            doc = {k: v for k, v in rec.items() if not k.startswith("_")}
            action = {"index": {"_index": index, "_id": f"{i}-{rec.get('time', '')}"}}
            lines.append(json.dumps(action, ensure_ascii=False))
            lines.append(json.dumps(doc, ensure_ascii=False))
        return "\n".join(lines) + ("\n" if lines else "")

    def elk_index_mapping(self) -> Dict[str, Any]:
        """Elasticsearch index mapping（时间序列友好）"""
        return {
            "mappings": {
                "properties": {
                    "time": {"type": "date"},
                    "method": {"type": "keyword"},
                    "tool": {"type": "keyword"},
                    "client_ip": {"type": "ip"},
                    "status": {"type": "integer"},
                    "user_id": {"type": "keyword"},
                    "device_id": {"type": "keyword"},
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
        }

    # ============ 报告 ============
    def report(self) -> str:
        """生成聚合报告（Markdown）"""
        s = self.stats()
        if s["total"] == 0:
            return "# 审计聚合报告\n\n无记录"
        lines = [
            "# 跨设备审计聚合报告",
            "",
            f"- **总记录**：{s['total']}",
            f"- **日志源**：{s['sources']} 个文件",
            f"- **时间范围**：{s['time_range'][0]} → {s['time_range'][1]}",
            "",
            "## 按设备",
            "",
            "| 设备 | 记录数 |",
            "|------|--------|",
        ]
        for dev, cnt in s["by_device"].items():
            lines.append(f"| {dev} | {cnt} |")
        lines += ["", "## 按用户", "", "| 用户 | 记录数 |", "|------|--------|"]
        for u, cnt in s["by_user"].items():
            lines.append(f"| {u} | {cnt} |")
        lines += ["", "## 按工具 Top15", "", "| 工具 | 记录数 |", "|------|--------|"]
        for t, cnt in s["by_tool"].items():
            lines.append(f"| {t} | {cnt} |")
        lines += ["", "## 按状态码", ""]
        for st, cnt in s["by_status"].items():
            lines.append(f"- **{st}**：{cnt}")
        return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    log_dir = sys.argv[2]
    agg = AuditAggregator()

    if cmd == "collect":
        count = agg.collect([log_dir])
        print(f"收集 {count} 条记录（{len(agg.sources)} 个日志文件）")
        print(json.dumps(agg.stats(), ensure_ascii=False, indent=2))

    elif cmd == "elk":
        agg.collect([log_dir])
        out = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--out" else "audit_bulk.ndjson"
        bulk = agg.to_elk_bulk()
        with open(out, "w", encoding="utf-8") as f:
            f.write(bulk)
        print(f"ELK bulk 已导出：{out}（{len(agg.records)} 条）")

    elif cmd == "report":
        agg.collect([log_dir])
        print(agg.report())

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
