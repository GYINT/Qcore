#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 词源同类语义检测器（V8.4 候选 · 词源管理执行引擎 #0）

功能：扫描 keyword.yaml，自动检测 5 类"同类语义"关系，输出审计报告：
  ① 近拼易混对（编辑距离 ≤1）        —— 疑似同义/错拼/易混淆
  ② 同根跨意图（子串包含 + 意图不同） —— 语义漂移风险（同一词根分属不同意图）
  ③ 上下位关系（子串包含 + 同意图）   —— 可归族的父子词
  ④ 互补指标（专业词典规则）         —— 良率/不良率 等互补量纲
  ⑤ 已归一化覆盖检查                —— SYNONYM_MAP 是否覆盖上述关系

用法：
  python3 scripts/semantic_audit.py            # 输出审计报告（markdown + 控制台摘要）
  python3 scripts/semantic_audit.py --check    # CI 模式：仅输出严重警告计数（退出码）
  python3 scripts/semantic_audit.py --report   # 生成报告文件 outputs/semantic-audit.md

设计原则（对齐 §11/§14）：
  - 词库单一真源：只读 keyword.yaml，不修改
  - 输出防御性：每对关系带 confidence + 建议动作，供人工确认（不自动改词）
  - 渐进增强：可作为热词生命周期执行器的输入（V8.4 #1）
"""
import sys
import json
import itertools
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
from paths import KEYWORD_YAML as KEYWORD  # V8.4 路径归一
REPORT = ROOT / "outputs" / "semantic-audit.md"
SEMANTIC_CFG = ROOT / "references" / "config" / "semantic.yaml"

# ============ 检测词典（V8.4 词源解耦级 2 · semantic.yaml 外置） ============
def _load_semantic_cfg() -> dict:
    """加载语义检测配置（semantic.yaml · 缺失/失败用内置默认兜底）"""
    defaults = {
        "complementary_pairs": [
            ("良率", "不良率"), ("合格率", "不合格率"), ("直通率", "废品率"),
            ("一次合格率", "一次不良率"), ("准时交付率", "延误率"),
        ],
        "confirmed_pairs": [
            ("损耗", "损耗率"), ("良率", "不良率"), ("微裂纹", "裂纹"),
            ("不合格", "不合格率"),
        ],
        "params": {"confusable_edit_dist": 1, "same_root_len_diff": 3,
                   "min_word_len": 3, "coverage_warn_pct": 10},
    }
    if not SEMANTIC_CFG.exists():
        return defaults
    try:
        import yaml
        data = yaml.safe_load(SEMANTIC_CFG.read_text(encoding="utf-8")) or {}
        cfg = dict(defaults)
        if data.get("complementary_pairs"):
            cfg["complementary_pairs"] = [tuple(p) for p in data["complementary_pairs"]]
        if data.get("confirmed_pairs"):
            cfg["confirmed_pairs"] = [tuple(p) for p in data["confirmed_pairs"]]
        if data.get("params"):
            cfg["params"].update({k: v for k, v in data["params"].items() if k in cfg["params"]})
        return cfg
    except Exception:
        return defaults


_CFG = _load_semantic_cfg()
COMPLEMENTARY = _CFG["complementary_pairs"]
CONFIRMED_PAIRS = {tuple(p) for p in _CFG["confirmed_pairs"]}
P = _CFG["params"]  # confusable_edit_dist / same_root_len_diff / min_word_len / coverage_warn_pct

# 忽略的近拼对（语义本就不同但正常共存 · 避免噪音）
IGNORE_PAIRS = set()


def load_words():
    """加载词库 → [(word, intent, domain, role, level, status)]"""
    try:
        import yaml
        data = yaml.safe_load(KEYWORD.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"❌ 无法加载 keyword.yaml: {e}")
        sys.exit(2)
    items = []
    for k in data.get("keywords", []):
        items.append({
            "word": str(k.get("word", "")).lower(),
            "intent": k.get("intent"),
            "domain": k.get("domain"),
            "role": k.get("role"),
            "level": k.get("level", "base"),
            "status": k.get("status", "new"),
        })
    syn_groups = data.get("synonyms", {})
    return items, syn_groups


def edit_dist(a: str, b: str) -> int:
    """字符级编辑距离（汉字按单字符）"""
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def detect_confusable(items):
    """① 近拼易混对：编辑距离 ≤1 且较长词 ≥3 字符"""
    out = []
    words = sorted({it["word"] for it in items})
    by_word = {it["word"]: it for it in items}
    for a, b in itertools.combinations(words, 2):
        if (a, b) in IGNORE_PAIRS or (b, a) in IGNORE_PAIRS:
            continue
        if max(len(a), len(b)) < P['min_word_len']:
            continue
        d = edit_dist(a, b)
        if d <= P['confusable_edit_dist']:
            ia, ib = by_word[a], by_word[b]
            same_sem = (ia["intent"] == ib["intent"] and ia["domain"] == ib["domain"]
                        and ia["intent"] is not None)
            out.append({
                "type": "近拼易混",
                "pair": (a, b), "dist": d,
                "same_sem": same_sem,
                "a": {"intent": ia["intent"], "domain": ia["domain"], "level": ia["level"]},
                "b": {"intent": ib["intent"], "domain": ib["domain"], "level": ib["level"]},
                "confidence": 0.9 if same_sem else 0.6,
                "suggestion": "疑似同义，建议并入 SYNONYM_MAP" if same_sem
                              else "近拼但语义可能不同，标注易混淆对（人工确认）",
            })
    return out


def detect_same_root_cross_intent(items):
    """② 同根跨意图：长词包含短词词根，且 intent 不同 → 语义漂移风险"""
    out = []
    by_word = {it["word"]: it for it in items}
    words = sorted(by_word)
    for a, b in itertools.combinations(words, 2):
        short, long = (a, b) if len(a) <= len(b) else (b, a)
        if len(short) < 2 or short == long:
            continue
        if short in long and len(long) - len(short) <= P['same_root_len_diff']:
            ia, ib = by_word[short], by_word[long]
            if ia["intent"] and ib["intent"] and ia["intent"] != ib["intent"]:
                out.append({
                    "type": "同根跨意图",
                    "pair": (short, long),
                    "a": {"intent": ia["intent"], "domain": ia["domain"]},
                    "b": {"intent": ib["intent"], "domain": ib["domain"]},
                    "confidence": 0.85,
                    "suggestion": f"同一词根分属 {ia['intent']}/{ib['intent']}，确认语义是否漂移",
                })
    return out


def detect_hyponym(items):
    """③ 上下位关系：长词包含短词词根，intent/domain 相同 → 可归族"""
    out = []
    by_word = {it["word"]: it for it in items}
    words = sorted(by_word)
    for a, b in itertools.combinations(words, 2):
        short, long = (a, b) if len(a) <= len(b) else (b, a)
        if len(short) < 2 or short == long:
            continue
        if short in long and len(long) - len(short) <= P['same_root_len_diff']:
            ia, ib = by_word[short], by_word[long]
            if (ia["intent"] and ib["intent"] and ia["intent"] == ib["intent"]
                    and ia["domain"] == ib["domain"]):
                out.append({
                    "type": "上下位",
                    "pair": (short, long),
                    "a": {"intent": ia["intent"], "domain": ia["domain"], "level": ia["level"]},
                    "b": {"intent": ib["intent"], "domain": ib["domain"], "level": ib["level"]},
                    "confidence": 0.8,
                    "suggestion": f"{long} 是 {short} 的子类，可归为同词族（热词升级时确认）",
                })
    return out


def detect_complementary(items, syn_groups):
    """④ 互补指标：内置词典匹配，检查是否已归一化"""
    out = []
    by_word = {it["word"]: it for it in items}
    known = set()
    for main, alts in syn_groups.items():
        known.update([main] + list(alts))
    for a, b in COMPLEMENTARY:
        ia, ib = by_word.get(a), by_word.get(b)
        if not ia or not ib:
            continue
        out.append({
            "type": "互补指标",
            "pair": (a, b),
            "a": {"intent": ia["intent"]},
            "b": {"intent": ib["intent"]},
            "normalized": (a in known and b in known),
            "confidence": 0.95,
            "suggestion": "互补量纲已同族" if (a in known and b in known)
                          else "互补指标未归一化，建议同族管理（如路由歧义联动）",
        })
    return out


def detect_synonym_gap(items, syn_groups):
    """⑤ 已归一化覆盖检查：SYNONYM_MAP 词数 vs 词库（覆盖率）"""
    known = set()
    for main, alts in syn_groups.items():
        known.update([main] + list(alts))
    total = len(items)
    covered = len(known & {it["word"] for it in items})
    return {
        "type": "归一化覆盖",
        "syn_groups": len(syn_groups),
        "covered_words": covered,
        "total_words": total,
        "coverage": round(covered / max(total, 1) * 100, 1),
        "suggestion": "覆盖率低，建议以检测结果补全 SYNONYM_MAP" if covered / max(total, 1) * 100 < P["coverage_warn_pct"]
                      else "覆盖率可接受",
    }


def run_audit():
    items, syn_groups = load_words()
    results = []
    results += detect_confusable(items)
    results += detect_same_root_cross_intent(items)
    results += detect_hyponym(items)
    results += detect_complementary(items, syn_groups)
    cov = detect_synonym_gap(items, syn_groups)
    return results, cov


def gen_report(results, cov) -> str:
    lines = [
        "# QCM 词源同类语义检测报告",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 依据：references/config/keyword.yaml ｜ 工具：scripts/semantic_audit.py",
        f"> 说明：全部检测结果为**候选**，供人工确认后决定是否归一化/标注；本工具只读不改。",
        "",
        "## 一、归一化覆盖",
        "",
        f"- SYNONYM_MAP 同义词组：**{cov['syn_groups']}** 组",
        f"- 已归一化词覆盖：**{cov['covered_words']}/{cov['total_words']}**（{cov['coverage']}%）",
        f"- {cov['suggestion']}",
        "",
        f"## 二、检测结果（共 {len(results)} 条关系）",
        "",
    ]
    by_type = {}
    for r in results:
        by_type.setdefault(r["type"], []).append(r)
    for tname, rs in by_type.items():
        lines.append(f"### {tname}（{len(rs)} 条）")
        lines.append("")
        lines.append("| 词对 | 归属（意图/领域） | 置信度 | 建议 |")
        lines.append("|------|------------------|--------|------|")
        for r in rs:
            a, b = r["pair"]
            ia = r["a"].get("intent") or "-"
            ib = r["b"].get("intent") or "-"
            lines.append(f"| {a} ~ {b} | {ia}/{ib} | {r['confidence']} | {r['suggestion']} |")
        lines.append("")
    return "\n".join(lines)


def main():
    results, cov = run_audit()
    # 严重项：排除已人工确认合理分流的对
    severe = [r for r in results
              if r["type"] in ("同根跨意图", "互补指标")
              and not r.get("normalized", False)
              and tuple(r["pair"]) not in CONFIRMED_PAIRS]

    if "--report" in sys.argv:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(gen_report(results, cov), encoding="utf-8")
        print(f"📄 报告已生成：{REPORT}")

    print(f"QCM 词源同类语义检测（{len(results)} 条关系 · 归一化覆盖 {cov['coverage']}%）")
    for r in results[:25]:
        a, b = r["pair"]
        mark = "🔴" if r["type"] in ("同根跨意图", "互补指标") and not r.get("normalized", False) else "🟡"
        print(f"  {mark} [{r['type']}] {a} ~ {b}（conf={r['confidence']}）{r['suggestion']}")
    if len(results) > 25:
        print(f"  … 其余 {len(results) - 25} 条见报告")

    if "--check" in sys.argv:
        print(f"\n严重警告（同根跨意图/未归一化互补）：{len(severe)} 项")
        return 1 if severe else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
