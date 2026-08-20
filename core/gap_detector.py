#!/usr/bin/env python3
"""qcm_gap_detector.py — QCM 5 维缺口暴露驱动（§13 协议）

功能：
  1. 5 维缺口检测（行业/工艺/工具/标准/大师 · 评分 0-10）
  2. 触发规则（§13.2：阈值 ≥3 触发 · 单维/多维/跨域）
  3. 5 维层级映射（§13.4：L1 行业 → L5 大师 · Token 预算）
  4. 入库策略（§13.6：≥70 main / 40-69 history / <40 终止）
  5. 健康指标（§13.7：缺口暴露率/闭合率/入库率/学习率）

用法：
  from gap_detector import QCMGapDetector
  detector = QCMGapDetector()
  scores = detector.detect(case_dict)
  plan = detector.trigger_plan(scores)
"""
import os
from pathlib import Path  # V8.4：corpus rglob 递归
from paths import REFERENCES
import re
import json
import time
from typing import Dict, Any, List, Optional

# ============ 5 维层级映射（§13.4）============
PHASE_MAPPING = {
    # QCM 颗粒度 → Infoseek 调研层级 → 调研深度 → Token 预算 → 工具
    "L1_行业":   {"depth": 1, "token_budget": 3000, "tools": ["search_anchors"]},
    "L2_工艺":   {"depth": 2, "token_budget": 2000, "tools": ["search_anchors", "fetch_content"]},
    "L3_工具":   {"depth": 2, "token_budget": 2000, "tools": ["score_source"]},
    "L4_方法论": {"depth": 3, "token_budget": 3000, "tools": ["research", "conflict_detection"]},
    "L5_大师":   {"depth": 3, "token_budget": 2000, "tools": ["research", "entity_profile"]},
}

# 缺口维度
DIMENSIONS = ["行业", "工艺", "工具", "标准", "大师"]


class QCMGapDetector:
    """5 维缺口检测器（§13.1）"""

    def __init__(self, references_dir: Optional[str] = None):
        self.references_dir = references_dir or os.environ.get(
            "QCM_REFERENCES", str(REFERENCES))
        self._corpus_text = None
        self._known_industries = None

    # ============ corpus 加载 ============
    def _load_corpus(self) -> str:
        """加载 references 全部文本（缓存 · 递归子目录）

        V8.4 修复：V8.3.1 重组后知识库移入 12 子目录，os.listdir 顶层扫描
        → corpus 为空 → 已知工具/标准/大师全判缺口（满分误报）。
        改用 rglob 递归（与 infoseek_bridge._search_local_corpus 同源缺陷一并治理）。
        """
        if self._corpus_text is not None:
            return self._corpus_text
        text = []
        ref = Path(self.references_dir) if self.references_dir else None
        if ref and ref.is_dir():
            for fpath in sorted(ref.rglob("*.md")):
                if ".deprecated" in fpath.name:
                    continue
                try:
                    with open(fpath, encoding="utf-8", errors="ignore") as f:
                        text.append(f.read())
                except Exception:
                    pass
        self._corpus_text = "\n".join(text)
        return self._corpus_text

    def _known_industry_set(self) -> set:
        """从 corpus 提取已知行业（§13.1 行业缺口判据）"""
        if self._known_industries is not None:
            return self._known_industries
        corpus = self._load_corpus()
        industries = set()
        for kw in ["汽车", "半导体", "电子", "电池", "光伏", "船舶", "航空",
                   "医药", "食品", "化工", "机械", "纺织", "钢铁", "家电"]:
            if kw in corpus:
                industries.add(kw)
        self._known_industries = industries
        return industries

    # ============ 5 维缺口评分（0-10）============
    def detect(self, case: Dict[str, Any]) -> Dict[str, float]:
        """§13.1 5 维缺口检测

        Args:
            case: {"industry": str, "process": str, "tools": [str],
                   "standards": [str], "masters": [str], "query": str}
        """
        corpus = self._load_corpus()
        scores = {
            "行业": self._industry_gap(case, corpus),
            "工艺": self._process_gap(case, corpus),
            "工具": self._tool_gap(case, corpus),
            "标准": self._standard_gap(case, corpus),
            "大师": self._master_gap(case, corpus),
        }
        return scores

    def _industry_gap(self, case: Dict, corpus: str) -> float:
        """行业缺口：行业不在已知行业集 → 高分"""
        industry = case.get("industry", "")
        if not industry:
            return 8.0  # 未指明行业 → 高缺口
        known = self._known_industry_set()
        if industry in known:
            return 1.0
        # 模糊匹配：行业关键词是否出现在 corpus
        hits = sum(1 for kw in known if kw in industry or industry in kw)
        return 4.0 if hits > 0 else 7.0

    def _process_gap(self, case: Dict, corpus: str) -> float:
        """工艺缺口：工艺关键词在 corpus 出现次数"""
        process = case.get("process", "")
        if not process:
            return 6.0
        # 中文工艺名 2 字即有效（len 按字符计）
        hits = corpus.count(process) if len(process) >= 2 else 0
        if hits >= 10:
            return 1.0
        if hits >= 3:
            return 3.0
        if hits >= 1:
            return 5.0
        return 7.0

    def _tool_gap(self, case: Dict, corpus: str) -> float:
        """工具缺口：case 声明的工具是否都在工具库"""
        tools = case.get("tools", [])
        if not tools:
            return 5.0  # 未声明工具 → 中缺口
        # 检查工具编号 A01-F10 或工具名
        missing = 0
        for t in tools:
            if isinstance(t, str) and t:
                if re.match(r"^[A-F]\d{2}$", t):
                    # 工具编号需在 corpus 中出现
                    if t not in corpus:
                        missing += 1
                elif t not in corpus:
                    missing += 1
        if missing == 0:
            return 0.0
        return min(10.0, 3.0 + missing * 2.0)

    def _standard_gap(self, case: Dict, corpus: str) -> float:
        """标准缺口：声明的标准是否在标准库"""
        standards = case.get("standards", [])
        if not standards:
            return 6.0  # 未声明标准 → 中高缺口
        missing = sum(1 for s in standards if s and s not in corpus)
        if missing == 0:
            return 0.0
        return min(10.0, 3.0 + missing * 2.0)

    def _master_gap(self, case: Dict, corpus: str) -> float:
        """大师缺口：大师视角是否被覆盖"""
        masters = case.get("masters", [])
        if not masters:
            return 5.0
        missing = sum(1 for m in masters if m and m not in corpus)
        if missing == 0:
            return 0.0
        return min(10.0, 2.0 + missing * 2.5)

    # ============ 触发规则（§13.2）============
    def trigger_plan(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """§13.2 触发规则 + §13.4 层级映射

        Returns:
            {
                "trigger": bool,
                "phase": 1|2|3,
                "reason": str,
                "gap_dimensions": [str], # 缺口维度（≥3）
                "critical_dimensions": [str], # 关键缺口（≥7）
                "mapping": {"L1_行业": {...}, ...}, # §13.4 层级映射
                "token_budget_total": int,
            }
        """
        max_score = max(scores.values()) if scores else 0
        gap_dims = [d for d, s in scores.items() if s >= 3]
        critical_dims = [d for d, s in scores.items() if s >= 7]

        # 触发判断
        if max_score < 3:
            trigger, phase, reason = False, 0, "all_gaps_below_threshold"
        elif max_score >= 9 or len(critical_dims) >= 2:
            trigger, phase, reason = True, 3, "critical_multi_dim"
        elif max_score >= 7 or len(critical_dims) >= 1:
            trigger, phase, reason = True, 2, "critical_or_3plus"
        else:
            trigger, phase, reason = True, 1, "threshold_3"

        # §13.4 层级映射：按缺口维度选择对应层级
        mapping = {}
        for dim in gap_dims:
            layer = {
                "行业": "L1_行业", "工艺": "L2_工艺",
                "工具": "L3_工具", "标准": "L4_方法论",
                "大师": "L5_大师",
            }.get(dim, "L3_工具")
            mapping[dim] = {**PHASE_MAPPING[layer], "layer": layer}

        token_total = sum(m["token_budget"] for m in mapping.values())

        return {
            "trigger": trigger,
            "phase": phase,
            "reason": reason,
            "gap_dimensions": gap_dims,
            "critical_dimensions": critical_dims,
            "mapping": mapping,
            "token_budget_total": token_total,
        }

    # ============ 入库策略（§13.6）============
    @staticmethod
    def ingestion_plan(confidence: float) -> Dict[str, Any]:
        """§13.6 入库策略"""
        if confidence >= 70:
            return {"level": "main", "manual_review": False, "action": "写入主库"}
        if confidence >= 40:
            return {"level": "history", "manual_review": True, "action": "归因历史"}
        return {"level": "terminate", "manual_review": False, "action": "终止不引用"}

    # ============ 健康指标（§13.7）============
    @staticmethod
    def health_metrics(stats: Dict[str, int]) -> Dict[str, Any]:
        """§13.7 健康指标

        stats: {"cases": int, "gaps_detected": int, "gaps_closed": int,
                "gaps_ingested": int, "gaps_prev_month": int}
        """
        cases = max(stats.get("cases", 0), 1)
        gaps = stats.get("gaps_detected", 0)
        closed = stats.get("gaps_closed", 0)
        ingested = stats.get("gaps_ingested", 0)
        prev = stats.get("gaps_prev_month", gaps)

        exposure_rate = gaps / cases * 100
        close_rate = closed / max(gaps, 1) * 100
        ingest_rate = ingested / max(gaps, 1) * 100
        learn_rate = (prev - gaps) / max(prev, 1) * 100 if prev > gaps else 0.0

        return {
            "exposure_rate": round(exposure_rate, 1),
            "close_rate": round(close_rate, 1),
            "ingest_rate": round(ingest_rate, 1),
            "learn_rate": round(learn_rate, 1),
            "targets": {
                "exposure_rate": "30-50%",
                "close_rate": "≥80%",
                "ingest_rate": "≥10%",
                "learn_rate": "≥5%/月",
            },
            "pass": {
                "exposure_rate": 30 <= exposure_rate <= 50,
                "close_rate": close_rate >= 80,
                "ingest_rate": ingest_rate >= 10,
                "learn_rate": learn_rate >= 5,
            },
        }


if __name__ == "__main__":
    # CLI 调试
    import sys
    det = QCMGapDetector()
    case = {
        "industry": "量子芯片",
        "process": "金线键合",
        "tools": ["A01", "F99"],  # F99 不存在 → 缺口
        "standards": ["ISO 9999"],  # 不存在 → 缺口
        "masters": [],
    }
    scores = det.detect(case)
    print("5 维缺口评分:", json.dumps(scores, ensure_ascii=False))
    plan = det.trigger_plan(scores)
    print("触发计划:", json.dumps(plan, ensure_ascii=False, indent=2))
