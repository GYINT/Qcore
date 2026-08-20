# -*- coding: utf-8 -*-
"""QCM 歧义消解器（V8.4 P1 · 第 25 轮评估落地）

三级链（AI 语义消解 → Infoseek 语境兜底 → 规则兜底）：
  路径 A · llm_router 语义消解（主 · 置信 ≥0.7 采用）
  路径 B · Infoseek 语境兜底（A 失效时 · 当前 Infoseek 无语义意图能力 → 跳过/预留）
  规则兜底 · 优化动词 → ② · 否则默认①（双路失效零崩溃 · 现状等价）

动态自适应（回灌学习）：
  消解置信 ≥0.8 → 写案例 disambiguation_cases.yaml
  → 同词同特征模式 ≥3 次 → 固化（下次直接查表免 AI 调用）

零回归设计：无 LLM Key / 失败 → 落规则兜底（与现状 _resolve_ambiguity 等价）
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
CASES_YAML = ROOT / "references" / "config" / "disambiguation_cases.yaml"

# 固化阈值（同歧义词 + 同特征词 ≥3 次 → 固化为规则）
FIX_THRESHOLD = 3
# 采用阈值（AI 消解置信 ≥0.7 才覆盖规则）
ACCEPT_CONFIDENCE = 0.7
# 回灌阈值（≥0.8 写案例）
LEARN_CONFIDENCE = 0.8

# 意图全集（消解候选）
INTENTS = ("①危机处置", "②流程优化", "③评估审计", "④知识学习", "⑤知识沉淀", "⑥质量文化")

# 强危机信号（V8.4 修复：明确危机表达 → 规则直接① · 防 AI 过度介入覆盖正确判定）
CRISIS_SIGNALS = (
    "跌破", "超标", "骤降", "飙升", "拒收", "客诉", "投诉", "召回",
    "报废", "失效", "虚焊", "断裂", "裂纹", "停线", "停机", "恶化",
    "复发", "退货", "异常", "客户退", "不良率飙升",
)


def _load_cases() -> dict:
    """加载已固化案例（扁平：word → [(feature, intent, count)]）"""
    try:
        import yaml
        if CASES_YAML.exists():
            data = yaml.safe_load(CASES_YAML.read_text(encoding="utf-8")) or {}
            return data.get("cases", {}) or {}
    except Exception:
        pass
    return {}


def _load_optimize_verbs() -> list:
    """从词库加载优化动词（单一真源）"""
    try:
        import yaml
        kw_path = ROOT / "references" / "config" / "keyword.yaml"
        data = yaml.safe_load(kw_path.read_text(encoding="utf-8"))
        return [k["word"] for k in data.get("keywords", [])
                if k.get("role") == "optimize_verb"]
    except Exception:
        return ["提升", "改善", "提高", "优化", "缩短", "降低"]


def _rule_fallback(query: str) -> Dict:
    """规则兜底：优化动词 → ② · 否则默认①（现状等价）"""
    verbs = _load_optimize_verbs()
    if any(v in query for v in verbs):
        return {"intent": "②流程优化", "confidence": 0.5, "source": "rule"}
    return {"intent": "①危机处置", "confidence": 0.5, "source": "rule"}


def _feature_of(query: str, word: str) -> str:
    """提取歧义词的语境特征（前后 6 字 · 用于模式固化匹配）"""
    idx = query.find(word)
    if idx < 0:
        return ""
    return query[max(0, idx - 6): idx + len(word) + 6]


def _ai_resolve(query: str, word: str) -> Optional[Dict]:
    """路径 A · LLM 语义消解（无 Key/失败 → None → 落兜底）"""
    try:
        sys_path = os.path.join(ROOT, "scripts")
        import sys
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        from llm_router import LLMRouter
        router = LLMRouter()
        result = router.call(
            prompt=(
                f"【质量场景意图判定】用户输入：{query}\n"
                f"输入中包含质量歧义术语「{word}」，请判定用户意图属于哪一类：\n"
                f"①危机处置（质量事故/超标/客诉/紧急）②流程优化（改善/提升/优化）\n"
                f"③评估审计 ④知识学习 ⑤知识沉淀 ⑥质量文化\n"
                f"严格输出 JSON：{{\"intent\": \"②流程优化\", \"confidence\": 0.85}}\n"
                f"只输出 JSON，不要其它文字。"
            ),
            task="general",
            max_tokens=100,
        )
        if result.get("mode") != "real":
            return None
        text = result.get("text", "")
        m = __import__("re").search(r"\{.*\}", text, __import__("re").S)
        if not m:
            return None
        data = json.loads(m.group(0))
        intent = data.get("intent", "")
        conf = float(data.get("confidence", 0))
        if intent not in INTENTS:
            return None
        return {"intent": intent, "confidence": conf, "source": "ai"}
    except Exception:
        return None


def _check_fixed(query: str, word: str) -> Optional[Dict]:
    """查已固化案例（免 AI 调用 · 动态自适应缓存）"""
    cases = _load_cases()
    entries = cases.get(word, [])
    if not entries:
        return None
    feature = _feature_of(query, word)
    for e in entries:
        if e.get("count", 0) >= FIX_THRESHOLD and e.get("feature", "") and \
           e["feature"] in query:
            return {"intent": e["intent"], "confidence": 0.75, "source": "fixed"}
        # 无特征词的歧义词：词级累计（如"良率"累计 3 次以上归②）
        if e.get("count", 0) >= FIX_THRESHOLD and not e.get("feature", ""):
            return {"intent": e["intent"], "confidence": 0.7, "source": "fixed"}
    return None


def _learn(query: str, word: str, result: Dict) -> None:
    """回灌学习：高置信消解结果写案例（模式累计 → 固化）"""
    if result.get("source") != "ai" or result.get("confidence", 0) < LEARN_CONFIDENCE:
        return
    try:
        import yaml
        data = {}
        if CASES_YAML.exists():
            data = yaml.safe_load(CASES_YAML.read_text(encoding="utf-8")) or {}
        cases = data.setdefault("cases", {})
        entries = cases.setdefault(word, [])
        feature = _feature_of(query, word)
        # 特征词模式匹配（有特征按特征累计，无特征按词级累计）
        for e in entries:
            if e.get("feature", "") == feature and e.get("intent") == result["intent"]:
                e["count"] = e.get("count", 0) + 1
                e["last_ts"] = time.strftime("%Y-%m-%d %H:%M")
                break
        else:
            entries.append({
                "feature": feature, "intent": result["intent"],
                "confidence": round(result.get("confidence", 0), 2),
                "count": 1, "last_ts": time.strftime("%Y-%m-%d %H:%M"),
            })
        # 容量治理（每词最多 10 条）
        if len(entries) > 10:
            entries.sort(key=lambda e: -e.get("count", 0))
            del entries[10:]
        CASES_YAML.parent.mkdir(parents=True, exist_ok=True)
        CASES_YAML.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception:
        pass


def resolve(query: str, ambiguous_word: str) -> Dict:
    """歧义消解主入口（四级链）

    Args:
        query: 用户输入（已归一化）
        ambiguous_word: 命中的歧义词（良率/cpk/spc/ppm/直通率等）
    Returns:
        {"intent": "②流程优化", "confidence": 0.85, "source": "ai|fixed|rule"}

    V8.4 修复（Key 真实激活后）：强信号前置——明确危机/优化信号先用规则，
    AI 只处理边界场景（无强信号的歧义）· 防止 AI 覆盖规则的正确判定。
    """
    # 0. 强危机信号 → ①（不调 AI · 快且稳 · 黄金用例护栏）
    if any(s in query for s in CRISIS_SIGNALS):
        return {"intent": "①危机处置", "confidence": 0.75, "source": "rule"}
    # 0.5 优化动词 → ②（规则优先）
    if any(v in query for v in _load_optimize_verbs()):
        return {"intent": "②流程优化", "confidence": 0.75, "source": "rule"}

    # 1. 已固化案例（免调用 · 动态自适应缓存）
    fixed = _check_fixed(query, ambiguous_word)
    if fixed:
        return fixed

    # 2. 路径 A · AI 语义消解（边界场景：无强信号歧义）
    ai = _ai_resolve(query, ambiguous_word)
    if ai and ai.get("confidence", 0) >= ACCEPT_CONFIDENCE:
        _learn(query, ambiguous_word, ai)
        return ai

    # 3. 路径 B · Infoseek 语境兜底
    #    （当前 Infoseek 无语义意图能力 · 预留扩展点 · 直接落规则）
    # TODO(V8.5): Infoseek research 快速语境 → 意图映射

    # 3. 规则兜底（双路失效零崩溃 · 现状等价）
    return _rule_fallback(query)


# ============ 独立运行（观测） ============
def main():
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    query = args[0] if args else "良率太低了怎么改善"
    # 提取歧义词（从词库）
    import yaml
    kw_path = ROOT / "references" / "config" / "keyword.yaml"
    data = yaml.safe_load(kw_path.read_text(encoding="utf-8"))
    amb_words = [k["word"] for k in data.get("keywords", []) if k.get("role") == "ambiguous"]
    word = next((w for w in amb_words if w in query), amb_words[0] if amb_words else "良率")
    r = resolve(query, word)
    print(f"歧义消解: {query[:20]} · 词「{word}」 → intent={r['intent']} conf={r['confidence']} source={r['source']}")


if __name__ == "__main__":
    main()
