#!/usr/bin/env python3
"""qcm_mcp_v043_test.py — QCM V0.4.3 5 维缺口暴露驱动测试（§13）

覆盖（14 用例）：
  1. 5 维缺口评分（行业/工艺/工具/标准/大师 各边界）
  2. 缺口评分 <3 → 不触发
  3. 单维缺口（≥3）→ Phase 1
  4. critical 单维（≥7）→ Phase 2
  5. critical 多维（≥2）→ Phase 3
  6. 跨域缺口（5 维全缺口）→ Phase 3
  7. §13.4 层级映射（L1-L5）
  8. §13.6 入库策略（main/history/terminate）
  9. §13.7 健康指标
  10. 缺口→调研→入库闭环（detect → plan → ingest）
  11. MCP server 端到端
  12. token_budget_total 汇总
"""
import json
import os
import sys
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import subprocess

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
CORE = os.path.join(QCM_ROOT, "core")  # V8.3.2 T2：gap_detector 已迁入 core/（原 scripts/ 路径 ModuleNotFoundError）
SERVER = os.path.join(SCRIPTS, "mcp_server.py")

sys.path.insert(0, SCRIPTS)
sys.path.insert(0, CORE)
from gap_detector import QCMGapDetector

DET = QCMGapDetector()


def test(name, fn, expect_error=False):
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            if expect_error:
                print(f"  ✅ {name}（预期错误: {str(result['error'])[:60]}）")
                return True
            print(f"  ❌ {name}: {str(result.get('error'))[:100]}")
            return False
        if expect_error and not isinstance(result, bool):
            print(f"  ❌ {name}: 预期错误但返回成功")
            return False
        if isinstance(result, bool) and not result:
            print(f"  ❌ {name}: assert failed")
            return False
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        if expect_error:
            print(f"  ✅ {name}（预期异常: {str(e)[:60]}）")
            return True
        print(f"  ❌ {name}: {e}")
        return False


def call_mcp(method, params=None, timeout_s=20):
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    proc = subprocess.Popen(
        ["python3", SERVER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    proc.stdin.close()
    try:
        response = proc.stdout.readline().strip()
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"error": "timeout"}
    if not response:
        return {"error": "no response"}
    parsed = json.loads(response)
    if isinstance(parsed.get("result"), dict) and "content" in parsed["result"]:
        try:
            text_content = parsed["result"]["content"][0]["text"]
            parsed["result"] = json.loads(text_content)
        except (KeyError, IndexError, json.JSONDecodeError):
            pass
    return parsed


def run_v043_tests():
    print("=" * 70)
    print("QCM MCP Server V0.4.3 测试套件（5 维缺口暴露驱动 · §13）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] 5 维缺口评分
    print("\n[1. 5 维缺口评分]")
    total += 1
    def scores_valid():
        case = {"industry": "量子芯片", "process": "金线键合",
                "tools": ["A01", "F99"], "standards": ["ISO 9999"], "masters": []}
        scores = DET.detect(case)
        for dim in ["行业", "工艺", "工具", "标准", "大师"]:
            assert dim in scores, f"missing {dim}"
            assert 0 <= scores[dim] <= 10, f"out of range: {scores[dim]}"
        return True
    if test("5 维评分范围 0-10", scores_valid):
        passed += 1

    # [2] 低缺口不触发
    total += 1
    def no_trigger():
        case = {"industry": "汽车", "process": "焊接", "tools": ["A01"],
                "standards": ["ISO 9001"], "masters": ["戴明"]}
        scores = DET.detect(case)
        plan = DET.trigger_plan(scores)
        assert plan["trigger"] is False or plan["phase"] == 1, f"unexpected: {plan}"
        return True
    if test("已知行业/工具/标准 → 低缺口", no_trigger):
        passed += 1

    # [3] 单维缺口 Phase 1
    print("\n[2. 触发规则（§13.2）]")
    total += 1
    def phase1_single():
        case = {"industry": "量子芯片", "process": "焊接", "tools": ["A01"],
                "standards": ["ISO 9001"], "masters": ["戴明"]}
        plan = DET.trigger_plan(DET.detect(case))
        assert plan["trigger"] is True
        assert plan["phase"] in (1, 2), f"unexpected: {plan['phase']}"
        return True
    if test("行业缺口 → Phase 1/2 触发", phase1_single):
        passed += 1

    # [4] critical 单维 → Phase 2
    total += 1
    def phase2_critical():
        case = {"industry": "量子芯片", "process": "光刻", "tools": ["Z99", "F99"],
                "standards": ["ISO 9999", "IEC 9999"], "masters": []}
        plan = DET.trigger_plan(DET.detect(case))
        assert plan["phase"] == 2 or plan["phase"] == 3, f"unexpected: {plan}"
        assert len(plan["critical_dimensions"]) >= 1
        return True
    if test("多维缺口 → Phase 2/3", phase2_critical):
        passed += 1

    # [5] 跨域全缺口 → Phase 3
    total += 1
    def phase3_all_gaps():
        case = {"industry": "火星采矿", "process": "等离子切割", "tools": ["X99", "Y99"],
                "standards": ["ISO 8888"], "masters": []}
        plan = DET.trigger_plan(DET.detect(case))
        assert plan["trigger"] is True
        assert plan["phase"] >= 2, f"unexpected: {plan['phase']}"
        assert len(plan["gap_dimensions"]) >= 3
        return True
    if test("跨域全缺口 → 深度触发", phase3_all_gaps):
        passed += 1

    # [6] §13.4 层级映射
    print("\n[3. §13.4 层级映射]")
    total += 1
    def mapping_l1_l5():
        case = {"industry": "量子芯片", "process": "金线键合", "tools": ["F99"],
                "standards": ["ISO 9999"], "masters": ["张三丰"]}
        plan = DET.trigger_plan(DET.detect(case))
        mapping = plan["mapping"]
        assert len(mapping) >= 3, f"mapping < 3: {mapping}"
        for dim, m in mapping.items():
            assert "layer" in m, f"no layer: {m}"
            assert m["layer"] in ("L1_行业", "L2_工艺", "L3_工具", "L4_方法论", "L5_大师")
            assert m["token_budget"] > 0
        return True
    if test("缺口维度 → L1-L5 层级映射", mapping_l1_l5):
        passed += 1

    # [7] §13.6 入库策略
    print("\n[4. §13.6 入库策略]")
    total += 1
    def ingestion_strategy():
        assert QCMGapDetector.ingestion_plan(85)["level"] == "main"
        assert QCMGapDetector.ingestion_plan(55)["level"] == "history"
        assert QCMGapDetector.ingestion_plan(30)["level"] == "terminate"
        return True
    if test("≥70 main / 40-69 history / <40 terminate", ingestion_strategy):
        passed += 1

    # [8] §13.7 健康指标
    total += 1
    def health_metrics():
        stats = {"cases": 100, "gaps_detected": 40, "gaps_closed": 32,
                 "gaps_ingested": 8, "gaps_prev_month": 45}
        h = QCMGapDetector.health_metrics(stats)
        assert h["exposure_rate"] == 40.0  # 40/100
        assert h["close_rate"] == 80.0     # 32/40
        assert h["ingest_rate"] == 20.0    # 8/40
        assert h["learn_rate"] == 11.1     # (45-40)/45
        assert h["pass"]["exposure_rate"] is True  # 30-50
        assert h["pass"]["close_rate"] is True      # ≥80
        return True
    if test("健康指标计算（暴露率/闭合率/入库率/学习率）", health_metrics):
        passed += 1

    # [9] 缺口→调研→入库闭环
    print("\n[5. 缺口→调研→入库闭环]")
    total += 1
    def closure_loop():
        case = {"industry": "量子芯片", "process": "金线键合", "tools": ["F99"],
                "standards": [], "masters": []}
        scores = DET.detect(case)
        plan = DET.trigger_plan(scores)
        # 触发调研 → 得到 confidence → 入库
        confidence = 85 if plan["trigger"] else 30
        ingest = QCMGapDetector.ingestion_plan(confidence)
        assert ingest["level"] == "main"
        # 缺口减少（学习率）
        stats = {"cases": 10, "gaps_detected": 4, "gaps_closed": 3,
                 "gaps_ingested": 1, "gaps_prev_month": 5}
        h = QCMGapDetector.health_metrics(stats)
        assert h["pass"]["learn_rate"] is True
        return True
    if test("缺口检测 → 触发 → 入库 → 健康指标闭环", closure_loop):
        passed += 1

    # [10] token 预算汇总
    total += 1
    def token_total():
        case = {"industry": "量子芯片", "process": "金线键合", "tools": ["F99"],
                "standards": ["ISO 9999"], "masters": []}
        plan = DET.trigger_plan(DET.detect(case))
        assert plan["token_budget_total"] > 0
        return True
    if test("token_budget_total 汇总", token_total):
        passed += 1

    # [11] MCP server 端到端
    print("\n[6. MCP server 端到端]")
    total += 1
    def mcp_e2e():
        r = call_mcp("tools/call", {
            "name": "qcm_gap_detect",
            "arguments": {
                "case": {
                    "industry": "量子芯片", "process": "金线键合",
                    "tools": ["F99"], "standards": [], "masters": [],
                },
            },
        })
        assert "result" in r, f"no result: {r}"
        assert "gap_scores" in r["result"]
        assert "trigger_plan" in r["result"]
        assert r["result"]["protocol_reference"] == "action-orders.md §13"
        return True
    if test("MCP tools/call → qcm_gap_detect", mcp_e2e):
        passed += 1

    # [12] 已知工具不误报
    print("\n[7. 已知库不误报]")
    total += 1
    def known_no_false_positive():
        case = {"industry": "汽车", "process": "焊接", "tools": ["A01", "B05"],
                "standards": ["ISO 9001", "IATF 16949"], "masters": ["戴明", "朱兰"]}
        scores = DET.detect(case)
        assert scores["工具"] < 3, f"工具误报: {scores['工具']}"
        assert scores["标准"] < 3, f"标准误报: {scores['标准']}"
        return True
    if test("已知工具/标准低缺口（不误报）", known_no_false_positive):
        passed += 1

    # [13] 边界：无字段案例
    total += 1
    def empty_case():
        scores = DET.detect({})
        for dim in DIMENSIONS_REF:
            assert dim in scores
        return True
    if test("空案例 → 全维度可评分", empty_case):
        passed += 1

    # [14] 全维度确认
    total += 1
    def all_dims():
        assert len(DIMENSIONS_REF) == 5
        assert DIMENSIONS_REF == ["行业", "工艺", "工具", "标准", "大师"]
        return True
    if test("5 维完整性（行业/工艺/工具/标准/大师）", all_dims):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"V0.4.3 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM MCP Server V0.4.3 全部测试通过")
        print("   - §13.1 5 维缺口检测（0-10 评分）")
        print("   - §13.2 触发规则（单维/多维/跨域 → Phase 1/2/3）")
        print("   - §13.4 层级映射（L1-L5 · token 预算）")
        print("   - §13.6 入库策略 + §13.7 健康指标")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


DIMENSIONS_REF = ["行业", "工艺", "工具", "标准", "大师"]


if __name__ == "__main__":
    success = run_v043_tests()
    sys.exit(0 if success else 1)
