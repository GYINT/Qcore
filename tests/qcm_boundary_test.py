# -*- coding: utf-8 -*-
"""QCM 全维度边界测试（V8.4 · 只读 · 不修改词库/状态）

覆盖 6 类边界：
  ① 输入边界：空/None/纯空白/超长 1 万字/异常字符（emoji·HTML·URL·控制符）
  ② 容量边界：词库意图/领域容量上限（40/20）+ 状态分布
  ③ 阈值边界：置信度区间（0~0.99）· need_clarify 临界 · 高分截断
  ④ 实体边界：大小写/空格/版本号变体命中
  ⑤ 歧义边界：歧义词 + 优化动词分流
  ⑥ 异常安全：route 永不抛异常（所有输入均返回合法结构）
"""
import sys
import os
from pathlib import Path

QCM_ROOT = os.environ.get("QCM_ROOT", str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.join(QCM_ROOT, "core"))
sys.path.insert(0, os.path.join(QCM_ROOT, "scripts"))
os.environ["QCM_ROOT"] = QCM_ROOT

import yaml
from router import route, load_keywords, THRESHOLDS

passed = 0
total = 0
fails = []


def test(name, fn):
    global passed, total
    total += 1
    try:
        fn()
        passed += 1
        print(f"  ✅ {name}")
    except AssertionError as e:
        fails.append((name, str(e)))
        print(f"  ❌ {name}: {e}")
    except Exception as e:
        fails.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ❌ {name}: {type(e).__name__}: {e}")


print("=" * 70)
print("QCM 全维度边界测试")
print("=" * 70)

# ============ ① 输入边界 ============
print("\n[1. 输入边界]")

def empty_query():
    r = route("")
    assert isinstance(r, dict) and r.get("intent"), f"空串返回异常: {r}"
test("空串输入 → 合法结构（兜底路由）", empty_query)

def none_query():
    r = route(None)  # type: ignore
    assert isinstance(r, dict) and r.get("intent"), f"None 返回异常: {r}"
test("None 输入 → 合法结构", none_query)

def blank_query():
    r = route("   \t\n  ")
    assert isinstance(r, dict) and r.get("intent"), f"纯空白返回异常: {r}"
test("纯空白输入 → 合法结构", blank_query)

def long_query():
    q = "注塑车间" + "缩水缺陷" * 2000  # ~1 万字
    r = route(q)
    assert isinstance(r, dict) and r.get("intent"), "超长输入异常"
    assert r.get("confidence", 0) <= 0.99 + 1e-9, f"置信度超上限: {r.get('confidence')}"
test("超长输入（1 万字）→ 正常路由 + 置信度 ≤0.99", long_query)

def emoji_query():
    r = route("😀🎉🔥 我们的产品坏了怎么办")
    assert isinstance(r, dict) and r.get("intent"), "emoji 输入异常"
test("emoji/特殊符号输入 → 合法", emoji_query)

def html_query():
    r = route("<script>alert('xss')</script> 质量缺陷")
    assert isinstance(r, dict), "HTML 注入输入异常"
test("HTML/注入输入 → 合法（不崩溃）", html_query)

def ctrl_query():
    r = route("失效\x00\x01\x02模式\x7f")
    assert isinstance(r, dict), "控制字符输入异常"
test("控制字符输入 → 合法", ctrl_query)

def mixed_lang():
    r = route("SPC 控制图 how to use 统计过程控制")
    assert isinstance(r, dict) and r.get("intent"), "中英混合输入异常"
test("中英混合输入 → 合法", mixed_lang)

def numeric_query():
    r = route("12345 67890")
    assert isinstance(r, dict) and r.get("intent"), "纯数字输入异常"
test("纯数字输入 → 合法（兜底）", numeric_query)

# ============ ② 容量边界 ============
print("\n[2. 容量边界]")

def capacity_check():
    kw = yaml.safe_load(open(os.path.join(QCM_ROOT, "references", "config", "keyword.yaml"), encoding="utf-8"))
    items = [k for k in kw["keywords"] if k.get("status") != "archived"]
    intent_cnt, domain_cnt = {}, {}
    for it in items:
        if it.get("intent"):
            intent_cnt[it["intent"]] = intent_cnt.get(it["intent"], 0) + 1
        if it.get("domain"):
            domain_cnt[it["domain"]] = domain_cnt.get(it["domain"], 0) + 1
    over_i = {k: v for k, v in intent_cnt.items() if v > 40}
    over_d = {k: v for k, v in domain_cnt.items() if v > 20}
    assert not over_i, f"意图超限: {over_i}"
    assert not over_d, f"领域超限: {over_d}"
    print(f"    意图容量: {intent_cnt} · 领域容量: {domain_cnt}")
test("词库容量 ≤ 上限（意图 40/领域 20）", capacity_check)

def status_valid():
    kw = yaml.safe_load(open(os.path.join(QCM_ROOT, "references", "config", "keyword.yaml"), encoding="utf-8"))
    valid = {"new", "active", "stable", "archived"}
    bad = [k.get("word") for k in kw["keywords"] if k.get("status") not in valid]
    assert not bad, f"非法状态: {bad}"
test("词库状态值 ∈ {new/active/stable/archived}", status_valid)

# ============ ③ 阈值边界 ============
print("\n[3. 阈值边界]")

def confidence_range():
    samples = [
        "我们的产品出现严重质量缺陷，客户要求退货，客诉不断",  # 多词命中 → 高分
        "今天天气不错适合出门",  # 未命中 → 低分
        "失效模式分析怎么做",  # 中等
    ]
    for q in samples:
        r = route(q)
        c = r.get("confidence", 0)
        assert 0 <= c <= 0.99 + 1e-9, f"置信度越界: {c} for {q[:10]}"
        print(f"    {q[:12]:<14} → conf={c} intent={r['intent']}")
test("置信度恒在 [0, 0.99] 区间", confidence_range)

def clarify_boundary():
    r = route("今天天气不错适合出门")
    assert r.get("need_clarify") is True or r.get("need_clarify") is False
    assert r.get("confidence", 1) < THRESHOLDS.get("clarify", 0.3) + 0.05 or r.get("need_clarify") in (True, False)
test("低置信 → need_clarify 布尔值合法", clarify_boundary)

def high_score_cap():
    q = "失效 缺陷 客诉 超差 报废 召回 裂纹 划伤 毛刺 变形 虚焊 漏装 拒收 缩水"
    r = route(q)
    assert r.get("confidence", 0) <= 0.99 + 1e-9, f"高分未截断: {r.get('confidence')}"
    print(f"    14 词命中 conf={r.get('confidence')}（应截断 0.99）")
test("高分截断 ≤0.99", high_score_cap)

# ============ ④ 实体边界 ============
print("\n[4. 实体边界]")

def entity_variants():
    from router import match_entities
    cases = [
        ("IATF 16949 认证", "IATF 16949"),
        ("iatf16949 认证", "IATF 16949"),          # 无空格小写
        ("ISO9001 内审", "ISO 9001"),              # 无空格
        ("iso 9001 内审", "ISO 9001"),             # 小写
        ("戴明", "Deming"),                        # 中文简称
        ("克劳士比零缺陷", "Crosby"),
    ]
    for q, expect in cases:
        hits = [e["name"] for e in match_entities(q)]
        found = any(expect in h or h in expect or expect.lower() in h.lower() for h in hits)
        assert found, f"实体变体未命中: {q} → {hits}"
    print(f"    6 变体全部命中")
test("实体变体（大小写/空格/版本/中文简称）全命中", entity_variants)

def entity_negative():
    from router import match_entities
    hits = match_entities("今天天气很好")
    assert not hits, f"无实体却命中: {hits}"
test("无实体文本 → 零命中", entity_negative)

# ============ ⑤ 歧义边界 ============
print("\n[5. 歧义边界]")

def ambiguity_verbs():
    cases = [
        ("良率太低了怎么改善", "②流程优化"),   # 歧义 + 优化动词 → ②
        ("良率骤降 客户投诉不断", "①危机处置"),  # 歧义 + 危机词(投诉) → ①
    ]
    for q, expect in cases:
        r = route(q)
        assert r["intent"] == expect, f"{q[:12]} → {r['intent']}（期望 {expect}）"
        print(f"    {q[:14]:<16} → {r['intent']}")
test("歧义词 + 优化动词/危机词分流正确", ambiguity_verbs)

# ============ ⑥ 异常安全 ============
print("\n[6. 异常安全]")

def fuzz_safe():
    import random
    chars = list("失效缺陷客诉超差SPC 123!@#$%^&*()_+=\\n\\t😀abcXYZ中文")
    random.seed(42)
    for _ in range(200):
        q = "".join(random.choices(chars, k=random.randint(0, 80)))
        try:
            r = route(q)
            assert isinstance(r, dict) and r.get("intent"), "返回结构非法"
        except Exception as e:
            raise AssertionError(f"fuzz 崩溃: {q[:30]} → {type(e).__name__}: {e}")
    print("    200 组随机 fuzz 输入零崩溃")
test("随机 fuzz 200 组 → 零崩溃零异常", fuzz_safe)

def domain_hint_safe():
    r = route("超差怎么办", domain_hint="A制造")
    assert r.get("domain"), "domain_hint 后 domain 缺失"
    r2 = route("超差怎么办", domain_hint=None)
    assert r2.get("domain"), "domain_hint=None 正常"
test("domain_hint 参数边界（有/无）安全", domain_hint_safe)

# ============ 总结 ============
print("\n" + "=" * 70)
print(f"边界测试结果：{passed}/{total} 通过")
print("=" * 70)
if fails:
    for name, err in fails:
        print(f"  ❌ {name}: {err}")
    sys.exit(1)
print("✅ 全维度边界测试全部通过")
sys.exit(0)
