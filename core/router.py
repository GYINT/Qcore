#!/usr/bin/env python3
"""qcm_router.py — QCM 场景路由（action-orders §14 · 词库归一化）

意图 5 × 领域 8 双维路由：
  - 词库单一真源：references/keyword.yaml（静态 + 热词 + 歧义 + 同义词）
  - 协议规则：action-orders §14（路由流程/置信度/矩阵/形态）
  - 动态热词：keyword.yaml level=hot（§11 生命周期）
  - 降级：hotword_level 标注（L0 完整 / L3[no-external-source]）
  - 深层实时：need_research 标记 + suggest_research 接口（置信度门控）

用法：
  from router import route
  result = route("CNC 镗孔椭圆 0.002mm 怎么办")
"""
import os
from paths import KEYWORD_YAML, ENTITIES_YAML, REF_CONFIG
import re
from typing import Dict, List, Optional

# ============ 词库加载（单一真源 · keyword.yaml） ============
KEYWORD_PATH = os.environ.get(
    "QCM_KEYWORDS", str(KEYWORD_YAML))

INTENT_KEYWORDS: Dict[str, List[str]] = {}
DOMAIN_KEYWORDS: Dict[str, List[str]] = {}
AMBIGUOUS_TERMS: List[str] = []
OPTIMIZE_VERBS: List[str] = []
SYNONYM_MAP: Dict[str, str] = {}  # 同义词 → 主词
_load_state = {"loaded": False, "level": "L0", "capacity_warn": []}

# ============ 路由阈值配置（V8.4 · router.yaml 外置 · 缺失用默认值兜底） ============
DEFAULT_THRESHOLDS = {
    "high_score_base": 0.8, "high_score_step": 0.05, "high_score_cap": 0.99,
    "low_score_base": 0.5, "low_score_step": 0.1, "fallback": 0.2,
    "score_high": 3, "score_low": 1, "clarify": 0.3,
}
THRESHOLDS = dict(DEFAULT_THRESHOLDS)
ROUTER_CFG_PATH = os.environ.get("QCM_ROUTER_CFG", str(REF_CONFIG / "router.yaml"))
_threshold_loaded = False


def load_thresholds() -> dict:
    """加载路由阈值配置（router.yaml · 配置驱动 §14.4）

    缺失/解析失败 → 内置默认值（防御性降级，等价现状）。
    """
    global _threshold_loaded
    if _threshold_loaded:
        return THRESHOLDS
    _threshold_loaded = True
    if not os.path.exists(ROUTER_CFG_PATH):
        return THRESHOLDS
    try:
        import yaml
        data = yaml.safe_load(open(ROUTER_CFG_PATH, encoding="utf-8")) or {}
        for k, v in (data.get("thresholds") or {}).items():
            if k in THRESHOLDS and isinstance(v, (int, float)):
                THRESHOLDS[k] = v
    except Exception:
        pass  # 配置失败 → 默认值
    return THRESHOLDS

# ============ 实体索引加载（V8.4 P1 · entities.yaml） ============
ENTITIES: List[Dict] = []
ENTITY_PATH = os.environ.get("QCM_ENTITIES", str(ENTITIES_YAML))
_entity_loaded = False


def load_entities() -> List[Dict]:
    """加载实体索引（entities.yaml · 标准/大师 等）

    返回实体列表；缺失时返回空列表（实体为可选增强，不影响基础路由）。
    """
    global _entity_loaded
    if _entity_loaded:
        return ENTITIES
    _entity_loaded = True
    if not os.path.exists(ENTITY_PATH):
        return ENTITIES
    try:
        import yaml
        data = yaml.safe_load(open(ENTITY_PATH, encoding="utf-8")) or {}
        ENTITIES.extend(data.get("entities", []))
    except Exception:
        pass  # 实体层失败不影响路由（防御性降级）
    return ENTITIES


def match_entities(text: str) -> List[Dict]:
    """实体匹配：实体名/别名命中 → 返回命中的实体（含 type/domain/intent）

    V8.4 A3 修复：函数自包含——text 统一小写（此前依赖 route 预先 lower，
    外部直接调用大写 text 恒不匹配）。
    """
    if not load_entities():
        return []
    text_low = text.lower()
    hits = []
    for e in ENTITIES:
        names = [e.get("name", "")] + list(e.get("aliases", []))
        for n in names:
            if n and n.lower() in text_low:
                hits.append(e)
                break
    return hits


def load_keywords() -> str:
    """加载归一化词库（keyword.yaml · 单一真源）

    返回降级等级：
      L0 = 词库加载完整（静态 + 热词）
      L3 = 词库缺失（[no-external-source] · 内置最小词表兜底）
    """
    if _load_state["loaded"]:
        return _load_state["level"]

    path = os.environ.get("QCM_KEYWORDS", KEYWORD_PATH)
    if not os.path.exists(path):
        # L3 降级：内置最小词表（制造业核心 · 防路由完全失效）
        _load_state["level"] = "L3[no-external-source]"
        # 降级保底词表（词库文件缺失时的最小可用集 · 高频基础词）
        INTENT_KEYWORDS.update({"①危机处置": ["失效", "缺陷", "客诉", "裂纹", "椭圆", "超差", "异常"],
                                "②流程优化": ["优化", "改善", "提升"],
                                "③评估审计": ["评估", "审核"],
                                "④知识学习": ["什么是", "是什么", "标准"],
                                "⑤知识沉淀": ["新行业", "适配"]})
        DOMAIN_KEYWORDS.update({"A制造": ["工艺", "参数", "工序"],
                                "B设计": ["设计", "开发"],
                                "C供应链": ["供应商", "采购"],
                                "Q客户": ["客户", "客诉"]})
        _load_state["loaded"] = True
        return _load_state["level"]

    try:
        import yaml
        data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    except Exception:
        _load_state["level"] = "L3[no-external-source]"
        _load_state["loaded"] = True
        return _load_state["level"]

    for item in data.get("keywords", []):
        word = str(item.get("word", "")).lower()
        if not word:
            continue
        # V8.4 P5：archived 词退出活跃路由（§11.2 生命周期语义 · 归档=不参与路由但保留记录）
        if item.get("status") == "archived":
            continue
        is_base = item.get("level", "base") == "base"
        if item.get("intent"):
            kws = INTENT_KEYWORDS.setdefault(item["intent"], [])
            kws.append(word)
            if is_base:
                _load_state.setdefault("_base_intent_count", {}).setdefault(item["intent"], 0)
                _load_state["_base_intent_count"][item["intent"]] += 1
        if item.get("domain"):
            kws = DOMAIN_KEYWORDS.setdefault(item["domain"], [])
            kws.append(word)
            if is_base:
                _load_state.setdefault("_base_domain_count", {}).setdefault(item["domain"], 0)
                _load_state["_base_domain_count"][item["domain"]] += 1
        if item.get("role") == "ambiguous":
            AMBIGUOUS_TERMS.append(word)
        elif item.get("role") == "optimize_verb":
            OPTIMIZE_VERBS.append(word)
        # V8.4 字典归一化级 1（渐进式）：词条 aliases 变体 → 并入意图/领域词表（命中变体=命中主词）
        # 与实体层 aliases 模式对齐（统一词条模型 · 变体全覆盖 · aliases 不占 base 容量）
        for alias in item.get("aliases") or []:
            a = str(alias).lower()
            if not a or a == word:
                continue
            if item.get("intent"):
                INTENT_KEYWORDS.setdefault(item["intent"], []).append(a)
            if item.get("domain"):
                DOMAIN_KEYWORDS.setdefault(item["domain"], []).append(a)

    # 同义词归一化（P1-2）：副词 → 主词
    for main, alts in (data.get("synonyms") or {}).items():
        for a in alts:
            SYNONYM_MAP[str(a).lower()] = str(main).lower()

    # 容量约束检查（P1-2）：静态层（base）每意图 ≤40 词 / 每领域 ≤20 词
    # 热词层（hot）由 §11 生命周期天然管理，不占容量
    for intent, cnt in _load_state.get("_base_intent_count", {}).items():
        if cnt > 40:
            _load_state["capacity_warn"].append(f"{intent}: 静态 {cnt} 词超限(40)")
    for domain, cnt in _load_state.get("_base_domain_count", {}).items():
        if cnt > 20:
            _load_state["capacity_warn"].append(f"{domain}: 静态 {cnt} 词超限(20)")

    _load_state["level"] = "L0"
    _load_state["loaded"] = True
    return _load_state["level"]


def _normalize(text: str) -> str:
    """同义词归一化（匹配前文本归一）· V8.4 边界加固：None/非 str 安全"""
    if not isinstance(text, str):
        text = str(text or "")
    t = text.lower()
    for alt, main in SYNONYM_MAP.items():
        if alt and alt in t:
            t = t.replace(alt, main)
    return t


def _count_hits(text: str, keywords: List[str]) -> int:
    """统计特征词命中数（词库已归一化）"""
    return sum(1 for kw in keywords if kw and kw in text)


def _resolve_ambiguity(text: str, current_intent: str, word: str = "") -> str:
    """歧义消解（V8.4 P2 · 三级链：AI 语义消解 → Infoseek → 规则兜底）

    仅歧义词触发（调用方已确认 text 含 AMBIGUOUS_TERMS）。
    无 LLM Key / 消解失败 → 规则兜底（优化动词→② · 否则默认① · 与旧行为等价零回归）。
    """
    if word:
        try:
            from ambiguity_resolver import resolve
            r = resolve(text, word)
            if r.get("source") in ("ai", "fixed") and r.get("confidence", 0) >= 0.7:
                return r["intent"]
        except Exception:
            pass  # 消解器异常 → 规则兜底
    if any(v in text for v in OPTIMIZE_VERBS):
        return "②流程优化"
    return current_intent


# ============ 形态映射（§14.6） ============
FORM_MAP = {
    "①危机处置": "case_application",
    "②流程优化": "case_application",  # 借用 5 段式（改善适配）
    "③评估审计": "assessment_report",
    "④知识学习": "quick_response",
    "⑤知识沉淀": "case_application",  # A+B 决策：蒸馏清单走案例应用（原 adapter_pack 幽灵形态退役）
    "⑥质量文化": "assessment_report",
}


def route(query: str, domain_hint: Optional[str] = None) -> Dict:
    """场景路由主入口

    Args:
        query: 用户输入
        domain_hint: 可选领域提示
    Returns:
        {'intent', 'domain', 'confidence', 'form', 'gap',
         'need_clarify', 'keyword_level', 'need_research', 'capacity_warn'}
    """
    keyword_level = load_keywords()
    text = _normalize(query)

    # ① 意图快速路由（归一化词库）
    scores = {intent: _count_hits(text, kws) for intent, kws in INTENT_KEYWORDS.items()}
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    # 歧义处理（V8.4 P2：三级链消解 · 无 Key 自动落规则等价旧行为）
    # BUG FIX（V8.3.1）：仅当歧义词实际归②时才重算 best_score；
    # 否则保留①的原始得分，避免 best_score=0 误触发"未命中→④知识学习"兜底。
    if best_intent == "①危机处置" and any(a in text for a in AMBIGUOUS_TERMS):
        amb_word = next((a for a in AMBIGUOUS_TERMS if a in text), "")
        resolved = _resolve_ambiguity(text, best_intent, amb_word)
        if resolved != best_intent:
            best_intent = resolved
            best_score = _count_hits(text, INTENT_KEYWORDS.get("②流程优化", []))

    # 无任何命中 → 兜底知识学习 + 深层实时标记（P2-3）
    need_research = False
    if best_score == 0:
        best_intent = "④知识学习"
        best_score = 1
        need_research = True  # 未命中 → 建议调研（触发门槛由调用方统计）
        # V8.4 闭环 Step 1：观测环——未命中词频次落盘（同词≥3 次触发调研信号）
        try:
            from hit_tracker import record_miss
            known = set()
            for kws in INTENT_KEYWORDS.values():
                known.update(kws)
            for kws in DOMAIN_KEYWORDS.values():
                known.update(kws)
            for e in load_entities():
                known.add(e.get("name", ""))
                known.update(e.get("aliases", []))
            record_miss(text, known)
        except Exception:
            pass  # 观测环失败不影响路由（防御性降级）

    # ② 置信度（V8.4 配置驱动 · router.yaml thresholds · 缺省等价内置默认）
    th = load_thresholds()
    if best_score >= th["score_high"]:
        confidence = min(th["high_score_base"] + th["high_score_step"] * (best_score - th["score_high"]),
                         th["high_score_cap"])
    elif best_score >= th["score_low"]:
        confidence = th["low_score_base"] + th["low_score_step"] * best_score
    else:
        confidence = th["fallback"]

    # ③ 领域次路由（归一化词库）
    domains = []
    for domain, kws in DOMAIN_KEYWORDS.items():
        if _count_hits(text, kws) > 0:
            domains.append(domain)
    if domain_hint:
        for domain in DOMAIN_KEYWORDS:
            if domain_hint.lower() in domain.lower():
                if domain not in domains:
                    domains.append(domain)
    if not domains:
        domains = ["通用"]

    # ④ 形态映射
    form = FORM_MAP[best_intent]

    # ⑤ 缺口联动
    gap = domains == ["通用"] or best_intent == "⑤知识沉淀"

    # ⑥ 实体匹配（V8.4 P1：标准/大师等实体命中 → 附加信号 + 领域增强）
    entities = match_entities(text)
    if entities:
        for e in entities:
            ed = e.get("domain")
            if ed and ed != "通用" and ed not in domains:
                domains.append(ed)
        if domains:
            gap = gap and len(entities) == 0  # 实体命中视为已覆盖，缓解缺口误判

    return {
        "intent": best_intent,
        "domain": domains[:2],
        "confidence": round(confidence, 2),
        "form": form,
        "gap": gap,
        "need_clarify": confidence < th["clarify"],
        "keyword_level": keyword_level,
        "need_research": need_research,
        "entities": [{"name": e["name"], "type": e["type"], "intent": e.get("intent")} for e in entities],
        "capacity_warn": _load_state["capacity_warn"],
    }


def suggest_research(query: str, hit_count: int = 3) -> Dict:
    """深层实时调研建议接口（P2-3 · 置信度门控）

    调用方统计未命中词频次，达到触发门槛后调用：
      - 输出调研建议词（query 整体 + 候选）
      - 门控：调研结果置信度 ≥70 才入库（§8.4）
      - 未达标词仅本次路由有效（不入库）
    """
    return {
        "suggest": query,
        "trigger": f"同词未命中 {hit_count} 次（门槛 ≥3）",
        "gate": "调研结果置信度 ≥70 才可入 keyword.yaml（§8.4）",
        "level": "deep_realtime",
    }


if __name__ == "__main__":
    demos = [
        "CNC 镗孔椭圆 0.002mm 怎么办",
        "如何提升注塑良率",
        "供应商质量体系评估",
        "FMEA 七步法是什么",
        "QCM 接入新能源行业",
        "IPQC 如何控制裂纹",
        "花店情人节玫瑰大量枯萎客诉怎么办",
        "门店鲜花早衰但肉眼看不出来",
        "玻璃基板微裂纹",
        "鲜花冷柜停摆客诉",
    ]
    print("词库等级:", load_keywords(), "容量警告:", _load_state["capacity_warn"] or "无")
    for d in demos:
        r = route(d)
        print(f"{d[:22]:<24} → {r['intent']} {r['domain']} conf={r['confidence']} "
              f"research={r['need_research']}")
