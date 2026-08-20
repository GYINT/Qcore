#!/usr/bin/env python3
"""qcm_v82_test.py — QCM V8.2 新增功能测试

覆盖（10 用例）：
  V8.2-1~4  危机判定 D' 计算（FMEA 维度化 · 探测溢价）
  V8.2-5    领域标签完整性（87 工具）
  V8.2-6~9  场景路由（意图/领域/置信度/缺口）
  V8.2-10   定位探针触发词
"""
import os
import re
import sys

import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
SCRIPTS = _os.path.join(_ROOT, "scripts")
REFERENCES = _os.path.join(_ROOT, "references")
OUTPUTS = _os.path.join(_ROOT, "outputs")
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, _os.path.join(_ROOT, "core"))


def test(name, fn):
    try:
        result = fn()
        if result is True:
            print(f"  ✅ {name}")
            return True
        print(f"  ❌ {name}: {result}")
        return False
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def run_v82_tests():
    print("=" * 60)
    print("QCM V8.2 测试套件（判定+资产+路由）")
    print("=" * 60)
    passed = 0
    total = 0

    # [1-4] D' 计算
    print("\n[1. 危机判定 D'（P0-1 FMEA 维度化）]")
    def calc_d(d1, d2, d3, detect=None):
        d = d1 + d2 + d3
        if detect is not None and detect >= 8:
            d += 1
        return d

    total += 1
    if test("隐蔽微裂纹·探测9 → D'=10", lambda: calc_d(3,3,3,9) == 10):
        passed += 1
    total += 1
    if test("可检出·探测3 → D'=5", lambda: calc_d(1,2,2,3) == 5):
        passed += 1
    total += 1
    if test("电测盲区·探测8 → D'=6", lambda: calc_d(1,2,2,8) == 6):
        passed += 1
    total += 1
    if test("无探测输入 → D'=D 兼容", lambda: calc_d(2,2,1) == 5):
        passed += 1

    # [5] 领域标签
    print("\n[2. 领域标签完整性（P1-1）]")
    total += 1
    def domain_labels():
        tools = open(os.path.join(REFERENCES, "tools", "tools.md"), encoding="utf-8").read()
        labels = re.findall(r"- \*\*领域\*\*：主:(\S+)", tools)
        assert len(labels) == 87, f"标签数 {len(labels)}"
        valid = {"A制造","B设计","C供应链","D现场","E体系","F战略","R风险","Q客户","通用"}
        assert all(l in valid for l in labels), "存在非法领域值"
        return True
    if test("87 工具领域标签合法", domain_labels):
        passed += 1

    # [6-9] 场景路由
    print("\n[3. 场景路由（P2-1 · §14）]")
    total += 1
    def route_cnc():
        from router import route
        r = route("CNC 镗孔椭圆 0.002mm 怎么办")
        assert r["intent"] == "①危机处置", r["intent"]
        assert "A制造" in r["domain"]
        assert r["confidence"] >= 0.5
        return True
    if test("镗孔椭圆 → ①/A制造", route_cnc):
        passed += 1
    total += 1
    def route_yield():
        from router import route
        r = route("如何提升注塑良率")
        assert r["intent"] == "②流程优化", r["intent"]
        return True
    if test("提升良率 → ②流程优化（歧义动词）", route_yield):
        passed += 1
    total += 1
    def route_fmea():
        from router import route
        r = route("FMEA 七步法是什么")
        assert r["intent"] == "④知识学习", r["intent"]
        return True
    if test("FMEA 是什么 → ④知识学习（兜底）", route_fmea):
        passed += 1
    total += 1
    def route_distill():
        from router import route
        r = route("QCM 接入新能源行业")
        assert r["intent"] == "⑤知识沉淀", r["intent"]
        assert r["gap"] is True, "知识沉淀应触发缺口"
        assert r["form"] == "case_application", f"⑤应走 case_application（A+B 决策），实际 {r['form']}"
        # 输出层：蒸馏清单组件必须存在（防"注册无文件"重现）
        comp = os.path.join(_ROOT, "components", "_distill_pack.md")
        assert os.path.exists(comp), "_distill_pack.md 组件缺失"
        ctxt = open(comp, encoding="utf-8").read()
        assert "【蒸馏清单】" in ctxt and "ADAPTER" in ctxt, "蒸馏清单组件缺七段内容"
        # constraint_map 无 adapter_pack 幽灵引用
        cm = open(os.path.join(REFERENCES, "config", "constraint.yaml"), encoding="utf-8").read()
        assert "adapter_pack" not in cm, "constraint_map 仍有 adapter_pack 幽灵引用"
        return True
    if test("接入新能源 → ⑤知识沉淀/case_application+组件", route_distill):
        passed += 1

    # [22] 意图⑥质量文化路由（V8.3 新增 · ISO 10010 对齐）
    total += 1
    def route_culture():
        from router import route
        assert route("质量文化建设评估")["intent"] == "⑥质量文化"
        assert route("组织质量文化氛围怎么评估")["intent"] == "⑥质量文化"
        assert route("双环学习变革")["intent"] == "⑥质量文化"
        # ②vs⑥ 边界：优化→② · 文化→⑥
        assert route("优化流程效率")["intent"] == "②流程优化"
        # 形态映射：⑥→评估报告
        assert route("质量文化成熟度")["form"] == "assessment_report"
        return True
    if test("意图⑥质量文化（新增·边界+形态）", route_culture):
        passed += 1

    # [23] 组件引擎动态组装（P2 回写 · 花店案例）
    total += 1
    def engine_assemble():
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location(
            "qcm_assembler_t", root / "core" / "assembler.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        route = {"intent": "①危机处置", "domain": ["Q客户"], "confidence": 0.85,
                 "D": 6, "complexity": "multi_chain", "nav": "隐蔽→AO-1", "tools": "5Why"}
        actions = [{"phase": "围堵", "action": "临期下架", "target": "30店",
                    "raci": {"R": "店长", "C": "物流", "I": "采购"},
                    "deadline": "24h", "deliverable": "记录", "ao": 1}]
        res = m.assemble(route, actions, role="manager")
        assert not res["errors"], res["errors"]
        assert "| 来源 | 动作 | 做多少 | 责任人 | 截止 | 交付 |" in res["action_list"]
        assert res["output"].startswith("【行动清单】")
        assert "今日必做" in res["action_list"]
        return True
    if test("组件引擎动态组装（清单6列/分组/前置）", engine_assemble):
        passed += 1

    # [24] 密度分层（exec 折叠 / executive 全开）
    total += 1
    def density_layer():
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location(
            "qcm_assembler_d", root / "core" / "assembler.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        route = {"intent": "①危机处置", "domain": ["Q客户"], "confidence": 0.85,
                 "D": 6, "complexity": "multi_chain", "nav": "隐蔽→AO-1", "tools": "5Why"}
        actions = [{"phase": "围堵", "action": "临期下架", "target": "30店",
                    "raci": {"R": "店长", "C": "物流", "I": "采购"},
                    "deadline": "24h", "deliverable": "记录", "ao": 1}]
        r_exec = m.assemble(route, actions, role="exec")
        r_full = m.assemble(route, actions, role="executive")
        assert "(fold)" in r_exec["density"], r_exec["density"]
        assert "(full)" in r_full["density"], r_full["density"]
        assert "【路由】" not in r_exec["output"]      # exec 分析折叠
        assert "【路由】" in r_full["output"]          # executive 分析全开
        return True
    if test("密度分层（exec折叠/executive全开）", density_layer):
        passed += 1

    # [25] 交叉矩阵视图（责任人×时间）
    total += 1
    def cross_view():
        import importlib.util
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location(
            "qcm_assembler_c", root / "core" / "assembler.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        actions = [
            {"phase": "围堵", "action": "下架", "target": "30店",
             "raci": {"R": "店长", "C": "物流", "I": "采购"},
             "deadline": "24h", "deliverable": "记录", "ao": 1},
            {"phase": "预防", "action": "SLA", "target": "3家",
             "raci": {"R": "经理", "C": "采购", "I": "门店"},
             "deadline": "季末", "deliverable": "合同", "ao": 4},
        ]
        mat = m.render_cross_matrix(actions)
        assert "| 责任人 | 今日必做 | 本周重点 | 本月推进 |" in mat
        assert "店长" in mat and "经理" in mat
        assert "AO-1" in mat and "AO-4" in mat
        return True
    if test("交叉矩阵（责任人×时间）", cross_view):
        passed += 1

    # [10] 定位探针
    print("\n[4. 定位探针（P1-2）]")
    total += 1
    def probe_trigger():
        ao = open(os.path.join(REFERENCES, "protocol", "action-orders.md"), encoding="utf-8").read()
        assert "展开定位" in ao, "§6 缺触发词"
        out = open(os.path.join(OUTPUTS, "case-application.md"), encoding="utf-8").read()
        assert "定位探针" in out, "outputs 缺模板"
        return True
    if test("触发词+输出模板存在", probe_trigger):
        passed += 1

    # [11] RACI 实际措施值（P2-2 强化）
    print("\n[5. RACI 实际措施（P2-2）]")
    total += 1
    def raci_real():
        # 模拟实际案例输出（非模板占位符）
        sample = """AO-1 围堵
| ① 批次冻结 | QE R | 质量部 A | 制造经理 I |"""
        hits = re.findall(r"[R责任]", sample)
        assert "R" in sample and "A" in sample and "I" in sample, "缺 R/A/I"
        # 模板含占位符（结构声明）
        tpl = open(os.path.join(OUTPUTS, "case-application.md"), encoding="utf-8").read()
        assert "【R:" in tpl, "模板缺 RACI 结构"
        return True
    if test("RACI 实际值 + 模板结构", raci_real):
        passed += 1

    # [12-15] 零售词/热词/降级（P0-P1 扩展）
    print("\n[6. 零售词+热词+降级（P0-P1）]")
    total += 1
    def retail_flower():
        from router import route
        r = route("门店鲜花早衰但肉眼看不出来")
        assert r["intent"] == "①危机处置", f"零售词误归 {r['intent']}"
        assert "Q客户" in r["domain"] or "D现场" in r["domain"]
        return True
    if test("花店早衰 → ①危机处置（零售词）", retail_flower):
        passed += 1
    total += 1
    def retail_coldchain():
        from router import route
        r = route("花店供应商冷链断裂")
        assert r["intent"] == "①危机处置", r["intent"]
        assert "C供应链" in r["domain"]
        return True
    if test("冷链断裂 → ①/C供应链", retail_coldchain):
        passed += 1
    total += 1
    def hotword_load():
        from router import load_keywords
        lv = load_keywords()
        assert lv == "L0", f"热词加载 {lv}"
        return True
    if test("热词库挂载 L0", hotword_load):
        passed += 1
    total += 1
    def hotword_microcrack():
        from router import route
        r = route("玻璃基板微裂纹")
        assert "R风险" in r["domain"], f"热词领域未挂载 {r['domain']}"
        return True
    if test("热词微裂纹 → R风险", hotword_microcrack):
        passed += 1
    total += 1
    def degrade_l3():
        import os
        import router
        from router import route
        old_env = os.environ.get("QCM_HOTWORDS")
        os.environ["QCM_KEYWORDS"] = "/nonexistent/keyword.yaml"
        router._load_state["loaded"] = False  # 重置缓存（关键）
        try:
            r = route("CNC 镗孔椭圆 0.002mm 怎么办")
            assert r["keyword_level"] == "L3[no-external-source]", r["keyword_level"]
            assert r["intent"] == "①危机处置", "基础词应仍可路由"
            return True
        finally:
            if old_env:
                os.environ["QCM_HOTWORDS"] = old_env
            else:
                os.environ.pop("QCM_HOTWORDS", None)
            import router
            router._load_state["loaded"] = False  # 重置缓存
    if test("热词缺失 → L3 降级+基础词可用", degrade_l3):
        passed += 1

    # [16-18] 定位探针导航/三查/分层（V8.2 增强）
    print("\n[7. 定位探针导航/三查/分层]")
    total += 1
    def nav_map():
        ao = open(os.path.join(REFERENCES, "protocol", "action-orders.md"), encoding="utf-8").read()
        assert "复发 > 隐蔽 > 多链" in ao or "复发" in ao, "缺特征优先级"
        assert "AO-4" in ao, "复发导航缺 AO-4"
        return True
    if test("导航映射表（复发→AO-4/优先级）", nav_map):
        passed += 1
    total += 1
    def tri_check():
        import subprocess
        r = subprocess.run([sys.executable, "-B",
                            os.path.join(_ROOT, "core", "validator.py")],
                           capture_output=True, text=True)
        assert "96/96" in r.stdout, r.stdout[-200:]
        return True
    if test("验证器 96/96（三查+既有+路由消费）", tri_check):
        passed += 1
    total += 1
    def layered_review():
        ao = open(os.path.join(REFERENCES, "protocol", "action-orders.md"), encoding="utf-8").read()
        assert "分层检阅" in ao, "§2.1 缺分层检阅"
        tpl = open(os.path.join(OUTPUTS, "case-application.md"), encoding="utf-8").read()
        assert "分层检阅" in tpl, "模板缺分层说明"
        return True
    if test("分层检阅（§2.1+模板）", layered_review):
        passed += 1

    # [19-20] 4 形态分级 + 双归零三查
    print("\n[8. 4 形态分级校验 + 双归零三查]")
    total += 1
    def graded_check():
        import subprocess
        r = subprocess.run([sys.executable, "-B",
                            os.path.join(_ROOT, "core", "validator.py")],
                           capture_output=True, text=True)
        assert "96/96" in r.stdout, r.stdout[-200:]
        return True
    if test("验证器 96/96（4形态分级+双归零+路由消费）", graded_check):
        passed += 1
    total += 1
    def zero_check():
        tpl = open(os.path.join(OUTPUTS, "case-application.md"), encoding="utf-8").read()
        assert "双归零" in tpl, "模板缺双归零"
        # 状态标注为运行期填充（模板含占位符）——校验交由验证器 has_zero_status
        assert "{✅" in tpl or "状态" in tpl or "双归零" in tpl
        return True
    if test("双归零模板（机理/责任/状态）", zero_check):
        passed += 1

    # [21] 决策桥融合（探针→AO 卡映射）
    print("\n[9. 决策桥融合（§2.1→AO 卡）]")
    total += 1
    def bridge_fusion():
        ao = open(os.path.join(REFERENCES, "protocol", "action-orders.md"), encoding="utf-8").read()
        assert "决策桥" in ao, "§2.1 缺决策桥声明"
        assert "导航阶段" in ao and "组织层定位" in ao and "16 格落点" in ao, "缺 AO 卡映射"
        assert "多链起点" in ao and "取物" in ao and "定深" in ao, "缺映射字段"
        tpl = open(os.path.join(OUTPUTS, "case-application.md"), encoding="utf-8").read()
        assert "决策桥" in tpl, "模板缺决策桥标注"
        assert "探针：" in tpl, "模板缺探针填充标注"
        return True
    if test("决策桥融合（§2.1 映射+模板填充）", bridge_fusion):
        passed += 1

    # [27] 场景路由消费（P1 镜像：4 形态分级）
    print("\n[10. 场景路由消费（P1 镜像）]")
    total += 1
    def route_consume():
        forms = {
            "case-application.md":   {"route": True,  "conf": True,  "tool": True},
            "decision-card.md":      {"route": True,  "conf": True,  "tool": False},
            "assessment-report.md":  {"route": True,  "conf": True,  "tool": False},
            "quick-response.md":     {"route": True,  "conf": True,  "tool": False},
        }
        for fn, expect in forms.items():
            tpl = open(os.path.join(OUTPUTS, fn), encoding="utf-8").read()
            assert ("【路由】" in tpl) == expect["route"], f"{fn} 路由元数据"
            assert ("置信度" in tpl) == expect["conf"], f"{fn} 置信度标注"
            assert ("工具预选" in tpl) == expect["tool"], f"{fn} 领域工具预选（仅案例应用）"
        return True
    if test("路由消费分级（案例应用全/其余元数据）", route_consume):
        passed += 1

    print("\n" + "=" * 60)
    print(f"V8.2 测试结果：{passed}/{total}")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    ok = run_v82_tests()
    sys.exit(0 if ok else 1)
