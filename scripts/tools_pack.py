#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools_pack.py — QCM MCP 工具实现包（P2-9 从 mcp_server 拆出）

承载 9 个 MCP 工具实现（research/score_source/decide/solve_problem/audit/validate/
attribution/attribution_phase/gap_detect）+ 公共依赖（corpus 加载 / LLM Router）。

依赖方向：mcp_server → tools_pack（单向）。mcp_server 导入 TOOL_DEFS 注册工具。
"""
import os
import re
import sys
from typing import Any, Dict, List, Optional

# 版本常量（与 mcp_server.py 同步）
PROTOCOL_VERSION = "V8.0+"

# ============ 路径常量（与 mcp_server 一致） ============
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REFERENCES = os.path.join(QCM_ROOT, "references")
OUTPUTS = os.path.join(QCM_ROOT, "outputs")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============ LLM Router ============
try:
    from llm_router import LLMRouter
    LLM_ROUTER = LLMRouter()
    LLM_AVAILABLE = True
except Exception:
    LLM_ROUTER = None
    LLM_AVAILABLE = False

# ============ Corpus 加载（SQLite Cache） ============
def load_corpus() -> Dict[str, str]:
    """读取 QCM 全量文件（references + outputs）· SQLite Cache"""
    if os.environ.get("QCM_CACHE_DISABLE", "0") == "1":
        return _load_corpus_direct()
    try:
        from corpus_cache import CorpusCache
        cache = CorpusCache(REFERENCES)
        if not cache.is_built():
            cache.build()
        else:
            cache.incremental_update()
        return cache.get_all_files()
    except Exception:
        return _load_corpus_direct()

def _load_corpus_direct() -> Dict[str, str]:
    """直接读取（fallback）"""
    corpus = {}
    for d in [REFERENCES, OUTPUTS]:
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if fname.endswith(".md") and not fname.endswith(".deprecated"):
                fpath = os.path.join(d, fname)
                try:
                    corpus[fname] = open(fpath, encoding="utf-8").read()
                except Exception:
                    pass
    return corpus

# ============ 本地注册器（收集到 TOOL_DEFS · mcp_server 再注册） ============
TOOL_DEFS: List[Dict[str, Any]] = []

def register_tool(name: str, description: str, input_schema: Dict[str, Any]):
    """本地收集装饰器：向 TOOL_DEFS 追加定义（mcp_server 统一注册）"""
    def decorator(func):
        TOOL_DEFS.append({
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": func,
        })
        return func
    return decorator

# ============ 工具实现（从 mcp_server 迁移 · 自动生成） ============
@register_tool(
    name="qcm_research",
    description="端到端质量调研（T1-T4 → L1-L4 → 4 形态输出）",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "用户问题/场景描述"},
            "level_hint": {"type": "string", "enum": ["T1", "T2", "T3", "T4"], "description": "输入深度"},
            "context": {"type": "object", "description": "行业/工艺/危机等级等"},
        },
        "required": ["query"],
    },
)
def qcm_research(query: str, level_hint: Optional[str] = None, context: Optional[Dict] = None) -> Dict[str, Any]:
    """端到端调研 · 接入 LLM Router"""
    # T-L 路由（规则保持）
    if level_hint is None:
        n = len(query)
        level_hint = "T1" if n < 50 else ("T2" if n < 150 else ("T3" if n < 400 else "T4"))
    layer_map = {"T1": "L1", "T2": "L2", "T3": "L3", "T4": "L4"}
    layer = layer_map.get(level_hint, "L2")

    # 工具匹配（规则保持）
    tools_used = []
    corpus = load_corpus()
    tools_md = corpus.get("tools.md", "")
    query_lower = query.lower()
    for m in re.finditer(r"^## ([A-F]\d+)\. (.+)$", tools_md, re.M):
        num, name = m.group(1), m.group(2).strip()
        first_kw = re.split(r"[\s（(]", name)[0].lower()
        if first_kw and first_kw in query_lower:
            tools_used.append(f"{num} {name[:30]}")
            if len(tools_used) >= 5:
                break

    # LLM 增强输出
    if LLM_AVAILABLE and LLM_ROUTER:
        system_prompt = """你是 QCM + 质量管控专家。按 action-orders.md 协议给出 5 段式输出：
1. 行动要项（围堵/消除/纠正/预防）
2. 事态导航（时间线 + 决策点）
3. 危机沟通（ITIL P1-P4）
4. 行动措施（具体步骤 + 责任人）
5. 双归零（技术归零 + 管理归零）
要求：专业、严谨、有数据支撑、引用大师观点。"""

        llm_result = LLM_ROUTER.call(
            prompt=f"问题：{query}\n层级：{layer}\n工具：{', '.join(tools_used[:5]) if tools_used else '默认'}",
            task="research",
            system=system_prompt,
            max_tokens=600,
            temperature=0.3,
        )
        output_md = llm_result["text"]
        confidence = 0.92 if llm_result["mode"] == "real" else 0.75
        llm_meta = {
            "provider": llm_result["provider"],
            "mode": llm_result["mode"],
            "duration_s": llm_result["duration_s"],
        }
    else:
        # fallback（无 LLM Router 时）
        output_md = f"""# QCM 调研输出（{layer}）

## 行动要项
- 围堵遏制（24h）：立即排查 `{query[:40]}...` 主因
- 消除阶段（1-2 周）：落地 PDCA + 8D D1-D4

## 事态导航
- 输入深度：{level_hint}
- 决策层级：{layer}
- 工具落格：{', '.join(tools_used[:5]) if tools_used else 'SPC/FMEA/8D 默认'}

## 危机沟通
- D 总分估算：基于 query 长度 {len(query)} 推断 = 3
- ITIL P：P3 Medium

## 行动措施
- T1：5 字段快响
- T2：13 字段标准应答
- T3：17 字段深度分析
- T4：22 字段完整输入

## 双归零
- 技术归零：变异消除 + 流程锁定
- 管理归零：体系审核 + 责任追溯
"""
        confidence = 0.78 if tools_used else 0.55
        llm_meta = {"provider": "v0.1-rule", "mode": "fallback"}

    return {
        "version": f"QCM {PROTOCOL_VERSION} V8.3.0",
        "form": "case-application",
        "layer": layer,
        "input_level": level_hint,
        "tools_used": tools_used,
        "output_markdown": output_md,
        "confidence": confidence,
        "llm_meta": llm_meta,
        "protocol_reference": "action-orders.md §1-§7",
    }


# ---------- Tool 2: qcm_score_source ----------
@register_tool(
    name="qcm_score_source",
    description="5 维评分（主题30% + 可信40% + 时效20% + 完整10%）",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "content": {"type": "string"},
            "domain": {"type": "string", "description": "行业/工艺/工具域"},
        },
        "required": ["url", "content"],
    },
)
def qcm_score_source(url: str, content: str, domain: Optional[str] = None) -> Dict[str, Any]:
    """5 维评分（规则版）"""
    # 主题一致性（domain 命中关键词）
    domain_score = 60.0
    if domain:
        domain_kws = ["汽车", "电子", "航空", "医疗", "SPC", "FMEA", "8D", "DMAIC"]
        if any(k in domain for k in domain_kws):
            domain_score = 85.0

    # 来源可信度（基于 URL 域名）
    trusted_domains = ["iso.org", "asq.org", "aiag.org", "vda-qmc.de", "iattf.com", "as9100"]
    url_score = 30.0
    for td in trusted_domains:
        if td in url.lower():
            url_score = 95.0
            break
    if "github.com" in url.lower():
        url_score = max(url_score, 70.0)
    if "wikipedia.org" in url.lower():
        url_score = max(url_score, 60.0)

    # 时效性
    freshness = 70.0  # 默认 30-90 天 ×0.9
    # 完整度
    completeness = min(100.0, len(content) / 50.0)

    score = (
        domain_score * 0.30
        + url_score * 0.40
        + freshness * 0.20
        + completeness * 0.10
    )

    tier = 4
    if score >= 80: tier = 1
    elif score >= 65: tier = 2
    elif score >= 50: tier = 3

    gate = "核心自动采集" if score >= 70 else ("需确认" if score >= 40 else "过滤")

    return {
        "score": round(score, 1),
        "tier": tier,
        "gate": gate,
        "breakdown": {
            "主题一致性": round(domain_score, 1),
            "来源可信度": round(url_score, 1),
            "时效性": round(freshness, 1),
            "完整度": round(completeness, 1),
        },
        "domain": domain or "未指定",
        "url": url,
    }


# ---------- Tool 3: qcm_decide ----------
@register_tool(
    name="qcm_decide",
    description="T-L 路由决策（T1-T4 → L1-L4 + 工具 + 大师）",
    input_schema={
        "type": "object",
        "properties": {
            "problem_text": {"type": "string"},
            "urgency": {"type": "string", "enum": ["紧急", "重要", "常规", "例行"]},
        },
        "required": ["problem_text"],
    },
)
def qcm_decide(problem_text: str, urgency: Optional[str] = None) -> Dict[str, Any]:
    """T-L 路由决策（规则版）"""
    # 紧急度 → T 层映射
    urgency_t = {"紧急": "T1", "重要": "T2", "常规": "T3", "例行": "T4"}
    level = urgency_t.get(urgency or "常规", "T2")
    layer_map = {"T1": "L1", "T2": "L2", "T3": "L3", "T4": "L4"}
    layer = layer_map[level]

    # 工具匹配（关键词）
    corpus = load_corpus()
    tools_md = corpus.get("tools.md", "")
    matched = []
    for m in re.finditer(r"^## ([A-F]\d+)\. (.+)$", tools_md, re.M):
        num, name = m.group(1), m.group(2).strip()
        first_kw = re.split(r"[\s（(]", name)[0]
        if first_kw and first_kw in problem_text:
            matched.append(num)
            if len(matched) >= 3:
                break

    # 默认工具集
    if not matched:
        if "变异" in problem_text or "波动" in problem_text:
            matched = ["A01", "F01", "F03"]
        elif "客诉" in problem_text or "投诉" in problem_text:
            matched = ["F01", "F07", "D23"]
        elif "焊接" in problem_text:
            matched = ["A01", "B01", "F01"]
        else:
            matched = ["A01", "B01", "F01"]

    return {
        "level": level,
        "layer": layer,
        "tools": matched,
        "masters": ["戴明", "克劳士比"],
        "rationale": f"urgency={urgency} → {level} → {layer}（围堵/消除/纠正/预防 主维度）",
        "protocol_reference": "action-orders.md §3 决策路由",
    }


# ---------- Tool 4: qcm_solve_problem ----------
@register_tool(
    name="qcm_solve_problem",
    description="5 段式输出 + 双归零判据（行动/导航/沟通/措施/双归零）",
    input_schema={
        "type": "object",
        "properties": {
            "problem_dict": {"type": "object", "description": "T-L 全字段输入"},
            "context": {"type": "object"},
        },
        "required": ["problem_dict"],
    },
)
def qcm_solve_problem(problem_dict: Dict, context: Optional[Dict] = None) -> Dict[str, Any]:
    """5 段式输出（规则版）"""
    pd = problem_dict
    query = pd.get("query", "未知问题")
    return {
        "form": "case-application",
        "version": f"QCM {PROTOCOL_VERSION}",
        "five_section_output": {
            "1_行动要项": f"围堵（24h）：{query[:60]} 立即遏制",
            "2_事态导航": f"输入={pd.get('level', 'T2')} 决策层级={pd.get('layer', 'L2')}",
            "3_危机沟通": "D 总分=3 / ITIL P3 Medium",
            "4_行动措施": "T1-T4 输入框架 + 5 段式 + 双归零",
            "5_双归零": "技术归零 + 管理归零（系统链 + 责任追溯）",
        },
        "protocol_reference": "action-orders.md §6 围堵消除",
    }


# ---------- Tool 5: qcm_audit ----------
@register_tool(
    name="qcm_audit",
    description="字段校验 + 引用追溯 + 五维风险评估",
    input_schema={
        "type": "object",
        "properties": {
            "decision_output": {"type": "object"},
        },
        "required": ["decision_output"],
    },
)
def qcm_audit(decision_output: Dict) -> Dict[str, Any]:
    """审计决策输出（规则版）"""
    warnings = []
    errors = []
    suggestions = []

    # 字段校验
    required = ["query", "level", "layer", "tools_used"]
    for r in required:
        if r not in decision_output:
            errors.append(f"必填字段缺失: {r}")

    # 引用追溯
    if "protocol_reference" not in decision_output:
        warnings.append("protocol_reference 缺失")

    # 五维风险
    risk_dimensions = {
        "覆盖": 95 if "tools_used" in decision_output else 60,
        "有效性": 88,
        "可追溯": 92 if "protocol_reference" in decision_output else 65,
        "可重复": 85,
        "可持续": 80,
    }
    avg_score = sum(risk_dimensions.values()) / 5

    if avg_score < 80:
        suggestions.append("补充数据来源 + 案例引用")

    return {
        "audit_score": round(avg_score, 1),
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "suggestions": suggestions,
        "risk_dimensions": risk_dimensions,
        "protocol_reference": "action-orders.md §12 五维风险",
    }


# ---------- Tool 6: qcm_validate ----------
@register_tool(
    name="qcm_validate",
    description="4 形态 × 10 项 = 40 检查矩阵",
    input_schema={
        "type": "object",
        "properties": {
            "output_text": {"type": "string"},
            "form": {"type": "string", "enum": ["case-application", "decision-card", "assessment-report", "quick-response"]},
        },
        "required": ["output_text", "form"],
    },
)
def qcm_validate(output_text: str, form: str) -> Dict[str, Any]:
    """4 形态合规校验（规则版 · 10 项 × 4 = 40 检查）"""
    checks = []

    if form == "case-application":
        items = [
            ("5 段式完整", all(s in output_text for s in ["行动要项", "事态导航", "危机沟通", "行动措施", "双归零"])),
            ("数据说话", "数据" in output_text or "实测" in output_text or "评分" in output_text),
            ("双归零判据", "归零" in output_text or "复发" in output_text),
            ("工具编号", bool(re.search(r"[A-F]\d{2}", output_text))),
            ("大师引用", any(m in output_text for m in ["戴明", "朱兰", "克劳士比", "石川", "田口"])),
            ("三链闭环", "发生链" in output_text or "流出链" in output_text or "系统链" in output_text),
            ("治理层级", any(g in output_text for g in ["工序级", "现场级", "车间级", "部门级", "公司级"])),
            ("标准引用", any(s in output_text for s in ["ISO", "IATF", "AS", "VDA", "AIAG"])),
            ("危机等级", "P1" in output_text or "P2" in output_text or "P3" in output_text or "P4" in output_text or "D" in output_text),
            ("可追溯", "action-orders" in output_text or "cases" in output_text or "§" in output_text),
        ]
    elif form == "decision-card":
        items = [
            ("3 行精简", len(output_text.split("\n")) <= 5),
            ("工具明确", bool(re.search(r"[A-F]\d{2}", output_text))),
            ("责任清晰", "责任" in output_text or "责任人" in output_text),
            ("数据支撑", any(c.isdigit() for c in output_text)),
            ("风险标识", "风险" in output_text or "D" in output_text),
            ("治理层级", any(g in output_text for g in ["工序级", "现场级", "车间级", "部门级", "公司级"])),
            ("24h 围堵", "24" in output_text or "围堵" in output_text),
            ("可执行", "做" in output_text or "执行" in output_text or "启动" in output_text),
            ("标准引用", any(s in output_text for s in ["ISO", "IATF", "AS", "VDA"])),
            ("合规", "合规" in output_text or "通过" in output_text),
        ]
    elif form == "assessment-report":
        items = [
            ("4 层 × 25 分", "25 分" in output_text or "100" in output_text),
            ("趋势分析", "趋势" in output_text or "环比" in output_text),
            ("根因分析", "根因" in output_text),
            ("治理水平", "治理" in output_text),
            ("标准对齐", any(s in output_text for s in ["ISO", "IATF", "AS", "VDA"])),
            ("文化评估", "文化" in output_text),
            ("可持续", "可持续" in output_text or "持续" in output_text),
            ("可对比", "对比" in output_text or "基线" in output_text),
            ("数据源", "来源" in output_text or "数据" in output_text),
            ("可审计", "audit" in output_text.lower() or "审计" in output_text),
        ]
    else:  # quick-response
        items = [
            ("30 秒判定", len(output_text) < 200),
            ("D 总分", "D" in output_text or "总分" in output_text),
            ("应急动作", "应急" in output_text or "立即" in output_text),
            ("责任人", "责任" in output_text or "人" in output_text),
            ("上报路径", "上报" in output_text or "路径" in output_text),
            ("复盘", "复盘" in output_text),
            ("预防", "预防" in output_text),
            ("工具", bool(re.search(r"[A-F]\d{2}", output_text))),
            ("标准", any(s in output_text for s in ["ISO", "IATF", "AS"])),
            ("合规", "合规" in output_text or "通过" in output_text),
        ]

    passed = sum(1 for _, ok in items if ok)
    failed = [name for name, ok in items if not ok]

    return {
        "form": form,
        "checks_passed": passed,
        "checks_total": len(items),
        "score": round(passed / len(items) * 100, 1),
        "failures": failed,
        "protocol_reference": "outputs/ 4 形态 × 10 项 = 40 检查",
    }


# ---------- Tool 7: qcm_attribution（§8 归因 + §8.5 三级降级）----------
try:
    from infoseek_bridge import qcm_attribution as _bridge_attribution
    from infoseek_bridge import qcm_attribution_phase as _bridge_phase
    from gap_detector import QCMGapDetector
    INFOSEEK_BRIDGE_AVAILABLE = True
except ImportError:
    INFOSEEK_BRIDGE_AVAILABLE = False
    _bridge_attribution = None
    _bridge_phase = None

_GAP_DETECTOR = QCMGapDetector() if 'QCMGapDetector' in dir() else None


@register_tool(
    name="qcm_attribution",
    description="QCM-Infoseek 归因（§8 协议 · 5 维触发 ≥2 → 调研 → 4 形态路由）· Infoseek 未安装时三级降级（L1 本地/L2 Web/L3 协议）",
    input_schema={
        "type": "object",
        "properties": {
            "unparsed_query": {"type": "string", "description": "用户原始问题/场景描述"},
            "qcm_failure_dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "5 维触发信号：行业/危机类型/工具/标准/大师（'ok' 或失败描述）",
            },
            "industry_hint": {"type": "string", "description": "行业提示（可选）"},
            "mds_fields": {"type": "object", "description": "MDS 输入字段（可选）"},
        },
        "required": ["unparsed_query", "qcm_failure_dimensions"],
    },
)
def qcm_attribution(unparsed_query: str, qcm_failure_dimensions: List[str],
                    industry_hint: Optional[str] = None,
                    mds_fields: Optional[Dict] = None) -> Dict[str, Any]:
    """§8 QCM-Infoseek 归因协议 + §8.5 三级降级"""
    if not INFOSEEK_BRIDGE_AVAILABLE:
        # 桥接模块缺失（异常环境）→ 本地兜底
        from infoseek_bridge import qcm_attribution
        return qcm_attribution(unparsed_query, qcm_failure_dimensions,
                               industry_hint, mds_fields)
    return _bridge_attribution(unparsed_query, qcm_failure_dimensions,
                               industry_hint, mds_fields)


# ---------- Tool 8: qcm_attribution_phase（§13.3 3 阶段混合策略）----------
@register_tool(
    name="qcm_attribution_phase",
    description="QCM-Infoseek 3 阶段混合策略（§13.3）· Phase 1 浅层锚点 / Phase 2 research_v3 / Phase 3 research_stream 流式",
    input_schema={
        "type": "object",
        "properties": {
            "unparsed_query": {"type": "string", "description": "用户原始问题"},
            "qcm_failure_dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "5 维触发信号（'ok' 或失败描述）",
            },
            "phase": {"type": "integer", "enum": [1, 2, 3], "description": "指定阶段（默认自动判断）"},
            "user_explicit": {"type": "boolean", "default": False, "description": "用户显式深度调研"},
            "industry_hint": {"type": "string", "description": "行业提示"},
        },
        "required": ["unparsed_query", "qcm_failure_dimensions"],
    },
)
def qcm_attribution_phase(unparsed_query: str, qcm_failure_dimensions: List[str],
                          phase: Optional[int] = None,
                          user_explicit: bool = False,
                          industry_hint: Optional[str] = None) -> Dict[str, Any]:
    """§13.3 混合策略 3 阶段触发"""
    if not INFOSEEK_BRIDGE_AVAILABLE:
        from infoseek_bridge import qcm_attribution_phase
        return qcm_attribution_phase(unparsed_query, qcm_failure_dimensions,
                                     phase, user_explicit, industry_hint)
    return _bridge_phase(unparsed_query, qcm_failure_dimensions,
                         phase, user_explicit, industry_hint)


# ---------- Tool 9: qcm_gap_detect（§13 缺口暴露驱动）----------
@register_tool(
    name="qcm_gap_detect",
    description="QCM 5 维缺口暴露驱动（§13）· 行业/工艺/工具/标准/大师缺口评分 + 触发计划 + 层级映射",
    input_schema={
        "type": "object",
        "properties": {
            "case": {
                "type": "object",
                "description": "案例：{industry, process, tools[], standards[], masters[]}",
            },
        },
        "required": ["case"],
    },
)
def qcm_gap_detect(case: Dict[str, Any]) -> Dict[str, Any]:
    """§13 5 维缺口检测 + 触发计划 + 层级映射"""
    if _GAP_DETECTOR is None:
        from gap_detector import QCMGapDetector
        det = QCMGapDetector()
    else:
        det = _GAP_DETECTOR
    scores = det.detect(case)
    plan = det.trigger_plan(scores)
    return {
        "gap_scores": scores,
        "trigger_plan": plan,
        "protocol_reference": "action-orders.md §13",
    }


# ============ JSON-RPC 协议处理 ============

# ============ 工具注册辅助（mcp_server 调用） ============
def register_all(target_registry: Dict[str, Dict[str, Any]]):
    """把 TOOL_DEFS 注册进目标注册表（mcp_server.TOOL_REGISTRY）"""
    for d in TOOL_DEFS:
        target_registry[d["name"]] = d
    return len(TOOL_DEFS)
