# -*- coding: utf-8 -*-
"""QCM 歧义消解测试（V8.4 P4 · 三级链 + 回灌闭环）

覆盖：
  ① 规则兜底等价（无 Key · 优化动词→② / 默认→①）
  ② AI 路径消解（mock 高置信 → 采用）
  ③ 回灌学习闭环（3 次学习 → 固化 → 免调用）
  ④ router 集成（route 歧义分流正确）
  ⑤ 指标采集（qcm_ambiguity_*）
"""
import sys
import os
import yaml
from pathlib import Path

QCM_ROOT = os.environ.get("QCM_ROOT", str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.join(QCM_ROOT, "core"))
sys.path.insert(0, os.path.join(QCM_ROOT, "scripts"))
os.environ["QCM_ROOT"] = QCM_ROOT

from ambiguity_resolver import resolve, _check_fixed, CASES_YAML, FIX_THRESHOLD
import ambiguity_resolver as ar

# 确定性基线：默认 mock 无 AI（模拟无 Key · 与 CI 无 Key 行为一致）
_ORIG_AI = ar._ai_resolve
ar._ai_resolve = lambda q, w: None

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


print("=" * 70)
print("QCM 歧义消解测试（三级链 + 回灌闭环）")
print("=" * 70)

# ① 规则兜底等价
print("\n[1. 规则兜底（无 Key · 零回归）]")

def rule_fallback():
    r = resolve("良率太低了怎么改善", "良率")
    assert r["intent"] == "②流程优化" and r["source"] == "rule", r
    r2 = resolve("良率骤降 客户投诉", "良率")
    assert r2["intent"] == "①危机处置" and r2["source"] == "rule", r2
test("无 Key → 规则兜底（优化动词→② / 默认→①）", rule_fallback)

def rule_fallback_spc():
    r = resolve("spc 控制图怎么做", "spc")
    assert r["source"] == "rule", r  # 无优化动词 → 默认①（现状行为）
test("spc 无优化动词 → 规则默认①", rule_fallback_spc)

# ② AI 路径
print("\n[2. AI 语义消解（mock 高置信）]")

def ai_resolve():
    import ambiguity_resolver as ar
    orig = ar._ai_resolve
    # 隔离：AI 高置信用例会触发回灌写盘，备份/恢复防止污染固化案例（测试间状态隔离）
    existed = CASES_YAML.exists()
    backup = CASES_YAML.read_text(encoding="utf-8") if existed else None
    ar._ai_resolve = lambda q, w: {"intent": "④知识学习", "confidence": 0.9, "source": "ai"}
    try:
        r = resolve("spc 控制图怎么做", "spc")
        assert r["intent"] == "④知识学习" and r["source"] == "ai", r
    finally:
        ar._ai_resolve = orig
        if existed:
            CASES_YAML.write_text(backup, encoding="utf-8")
        else:
            CASES_YAML.write_text(yaml.safe_dump({"cases": {}}, allow_unicode=True), encoding="utf-8")
test("AI 高置信(0.9) → 覆盖规则（④知识学习）", ai_resolve)

def ai_low_conf_ignored():
    import ambiguity_resolver as ar
    orig = ar._ai_resolve
    ar._ai_resolve = lambda q, w: {"intent": "④知识学习", "confidence": 0.4, "source": "ai"}
    try:
        r = resolve("良率太低了怎么改善", "良率")
        assert r["source"] == "rule", r  # 低置信 → 不采用
    finally:
        ar._ai_resolve = orig
test("AI 低置信(0.4) → 不采用落规则", ai_low_conf_ignored)

# ③ 回灌闭环
print("\n[3. 回灌学习闭环]")

def learn_loop():
    import ambiguity_resolver as ar
    orig = ar._ai_resolve
    ar._ai_resolve = lambda q, w: {"intent": "②流程优化", "confidence": 0.9, "source": "ai"}
    existed = CASES_YAML.exists()
    backup = CASES_YAML.read_text(encoding="utf-8") if existed else None
    # 清理：写空 cases（沙箱禁用 unlink）
    CASES_YAML.parent.mkdir(parents=True, exist_ok=True)
    CASES_YAML.write_text(yaml.safe_dump({"cases": {}}, allow_unicode=True), encoding="utf-8")
    try:
        q = "良率为什么一直很低"  # 无强信号（无危机词/无优化动词）→ AI 路径
        for _ in range(FIX_THRESHOLD):
            resolve(q, "良率")
        fixed = _check_fixed(q, "良率")
        assert fixed and fixed["source"] == "fixed", f"固化未生效: {fixed}"
        # 免调用验证
        calls = []
        ar._ai_resolve = lambda q, w: calls.append(1) or {"intent": "②流程优化", "confidence": 0.9, "source": "ai"}
        r = resolve(q, "良率")
        assert r["source"] == "fixed" and len(calls) == 0, f"固化后仍调 AI: {r}"
    finally:
        ar._ai_resolve = orig
        if existed:
            CASES_YAML.write_text(backup, encoding="utf-8")
        else:
            CASES_YAML.write_text(yaml.safe_dump({"cases": {}}, allow_unicode=True), encoding="utf-8")
test("3 次学习 → 固化命中 → 免 AI 调用", learn_loop)

# ④ router 集成
print("\n[4. router 集成]")

def router_route():
    from router import route
    cases = [
        ("良率太低了怎么改善", "②流程优化"),
        ("良率骤降 客户投诉不断", "①危机处置"),
    ]
    for q, expect in cases:
        r = route(q)
        assert r["intent"] == expect, f"{q} → {r['intent']}（期望 {expect}）"
test("route 歧义分流正确（②优化 / ①危机）", router_route)

def strong_signal():
    """V8.4 修复护栏：明确危机信号 → 规则①（防 AI 过度介入覆盖）"""
    from router import route
    cases = [
        ("冲压尺寸 Cpk 跌破 1.33", "①危机处置"),       # 跌破 = 强危机信号
        ("喷涂色差超标，良率只有 60%", "①危机处置"),    # 超标 = 强危机信号
    ]
    for q, expect in cases:
        r = route(q)
        assert r["intent"] == expect, f"强信号失败: {q} → {r['intent']}（期望 {expect}）"
test("强危机信号（跌破/超标）→ ① 规则护栏", strong_signal)

# ⑤ 指标
print("\n[5. 指标采集]")

def metrics_ok():
    from metrics import record_keyword_health, metrics
    record_keyword_health()
    out = metrics.export()
    assert "qcm_ambiguity_terms" in out, "缺少 qcm_ambiguity_terms 指标"
    assert "qcm_ambiguity_fixed_cases" in out, "缺少 fixed_cases 指标"
test("qcm_ambiguity_* 指标可采集", metrics_ok)

# 总结
print("\n" + "=" * 70)
print(f"歧义消解测试结果：{passed}/{total} 通过")
print("=" * 70)
if fails:
    for name, err in fails:
        print(f"  ❌ {name}: {err}")
    sys.exit(1)
print("✅ 歧义消解测试全部通过")
sys.exit(0)
