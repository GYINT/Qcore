#!/usr/bin/env python3
"""qcm_mcp_v042_test.py — QCM V0.4.2 3 阶段混合策略测试（§13.3）

覆盖（12 用例）：
  1. Phase 1 自动触发（浅层锚点 · 深度 1 · ~3000 Token）
  2. Phase 1 无缺口不触发
  3. Phase 2 自动升级（≥3 失败）
  4. Phase 2 critical 维度触发
  5. Phase 3 用户显式触发
  6. Phase 3 双 critical 自动升级
  7. Phase 3 streaming 7 步 yield
  8. Phase 1 渠道框架（search_anchors 返回渠道）
  9. Phase 2 降级（Infoseek 不可用 → L1/L3）
  10. Phase 3 降级（Infoseek 不可用 → error + 本地）
  11. MCP server 端到端（tools/call qcm_attribution_phase）
  12. token_estimate 预算校验
"""
import json
import os
import sys
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import subprocess
from pathlib import Path

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")

sys.path.insert(0, SCRIPTS)
import infoseek_bridge as bridge


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


def call_mcp(method, params=None, timeout_s=30):
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


def run_v042_tests():
    print("=" * 70)
    print("QCM MCP Server V0.4.2 测试套件（3 阶段混合策略 · §13.3）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] Phase 1 自动触发
    print("\n[1. Phase 1 自动触发]")
    total += 1
    def phase1_auto():
        r = bridge.qcm_attribution_phase(
            "汽车焊接虚焊", ["汽车行业", "ok", "ok", "ok", "工具缺失"])
        assert r["phase"] == 1, f"unexpected phase: {r['phase']}"
        assert r["token_estimate"] == 3000
        assert "anchors" in r
        return True
    if test("Phase 1 自动（1 失败 → 浅层）", phase1_auto):
        passed += 1

    # [2] Phase 1 不触发（全 ok）
    total += 1
    def phase1_no_trigger():
        r = bridge.qcm_attribution_phase("焊接虚焊", ["ok", "ok", "ok", "ok", "ok"])
        assert r["phase"] == 1  # 无失败也走 Phase 1（浅层锚点）
        return True
    if test("Phase 1 无失败仍浅层", phase1_no_trigger):
        passed += 1

    # [3] Phase 2 自动升级
    print("\n[2. Phase 2 自动升级]")
    total += 1
    def phase2_upgrade():
        r = bridge.qcm_attribution_phase(
            "半导体封装金线键合虚焊", ["半导体行业新工艺", "ok", "工具缺失", "标准缺失", "ok"])
        assert r["phase"] == 2, f"unexpected phase: {r['phase']}"
        assert r["token_estimate"] == 2500
        assert r["degradation_path"] == "L0_infoseek"
        return True
    if test("Phase 2 自动（≥3 失败 → research_v3）", phase2_upgrade):
        passed += 1

    # [4] Phase 2 critical 触发
    total += 1
    def phase2_critical():
        r = bridge.qcm_attribution_phase(
            "汽车焊接虚焊客诉",
            [{"dim": "行业", "severity": "critical"}, "ok", "ok", "ok", "ok"])
        assert r["phase"] == 2, f"unexpected: {r['phase']}"
        return True
    if test("Phase 2 critical 维度自动", phase2_critical):
        passed += 1

    # [5] Phase 3 用户显式
    print("\n[3. Phase 3 深度调研]")
    total += 1
    def phase3_explicit():
        r = bridge.qcm_attribution_phase(
            "量子芯片封装工艺失效深度调研",
            ["量子芯片行业", "ok", "工具缺失", "标准缺失", "ok"],
            user_explicit=True)
        assert r["phase"] == 3, f"unexpected: {r['phase']}"
        assert r["streaming"] is True
        assert r["step_count"] == 7
        return True
    if test("Phase 3 用户显式 → streaming 7 步", phase3_explicit):
        passed += 1

    # [6] Phase 3 双 critical
    total += 1
    def phase3_double_critical():
        r = bridge.qcm_attribution_phase(
            "船舶推进系统振动异常",
            [{"dim": "行业", "severity": "critical"},
             {"dim": "工具", "severity": "critical"},
             "ok", "ok", "ok"])
        assert r["phase"] == 3, f"unexpected: {r['phase']}"
        return True
    if test("Phase 3 双 critical 自动升级", phase3_double_critical):
        passed += 1

    # [7] Phase 3 streaming 7 步
    total += 1
    def phase3_steps():
        r = bridge.qcm_attribution_phase(
            "光伏钙钛矿封装工艺退化",
            ["光伏行业", "ok", "工具缺失", "ok", "ok"], user_explicit=True)
        assert r["step_count"] == 7, f"steps != 7: {r.get('step_count')}"
        return True
    if test("Phase 3 7 步 yield 完整", phase3_steps):
        passed += 1

    # [8] Phase 1 渠道框架
    print("\n[4. Phase 1 渠道框架]")
    total += 1
    def phase1_channels():
        r = bridge.qcm_attribution_phase(
            "新型电池工艺", ["电池行业", "ok", "ok", "ok", "ok"])
        anchors = r.get("anchors", [])
        # search_anchors 返回渠道框架或真实锚点
        assert isinstance(anchors, list)
        return True
    if test("Phase 1 返回锚点列表（渠道框架兼容）", phase1_channels):
        passed += 1

    # [9] Phase 2 降级
    print("\n[5. 降级路径]")
    total += 1
    def phase2_degrade():
        saved = bridge.INFOSEEK_SERVER
        bridge.INFOSEEK_SERVER = "/nonexistent/infoseek_mcp_server.py"
        try:
            r = bridge.qcm_attribution_phase(
                "汽车焊接虚焊", ["汽车行业", "ok", "工具缺失", "ok", "ok"])
            assert r["degradation_path"] in ("L1_local", "L3_protocol"), \
                f"unexpected: {r['degradation_path']}"
            return True
        finally:
            bridge.INFOSEEK_SERVER = saved
            bridge.clear_probe_cache()
    if test("Phase 2 Infoseek 不可用 → 降级", phase2_degrade):
        passed += 1

    # [10] Phase 3 降级
    total += 1
    def phase3_degrade():
        saved = bridge.INFOSEEK_SERVER
        bridge.INFOSEEK_SERVER = "/nonexistent/infoseek_mcp_server.py"
        try:
            r = bridge.qcm_attribution_phase(
                "量子芯片封装", ["量子芯片行业", "ok", "工具缺失", "ok", "ok"],
                user_explicit=True)
            assert r["streaming"] is False
            assert r["infoseek_status"] == "not_installed"
            return True
        finally:
            bridge.INFOSEEK_SERVER = saved
            bridge.clear_probe_cache()
    if test("Phase 3 Infoseek 不可用 → graceful 降级", phase3_degrade):
        passed += 1

    # [11] MCP server 端到端
    print("\n[6. MCP server 端到端]")
    total += 1
    def mcp_e2e():
        r = call_mcp("tools/call", {
            "name": "qcm_attribution_phase",
            "arguments": {
                "unparsed_query": "半导体封装虚焊",
                "qcm_failure_dimensions": ["半导体行业", "ok", "工具缺失", "ok", "ok"],
            },
        })
        assert "result" in r, f"no result: {r}"
        assert r["result"]["phase"] in (1, 2, 3)
        return True
    if test("MCP tools/call → qcm_attribution_phase", mcp_e2e):
        passed += 1

    # [12] token 预算
    print("\n[7. Token 预算]")
    total += 1
    def token_budget():
        r1 = bridge.qcm_attribution_phase("A", ["x", "ok", "ok", "ok", "ok"])
        r2 = bridge.qcm_attribution_phase(
            "B", ["x", "ok", "y", "z", "ok"])
        r3 = bridge.qcm_attribution_phase(
            "C", ["x", "ok", "y", "z", "ok"], user_explicit=True)
        assert r1["token_estimate"] == 3000
        assert r2["token_estimate"] == 2500
        assert r3["token_estimate"] == 2500
        return True
    if test("token_estimate 分级（3000/2500/2500）", token_budget):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"V0.4.2 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM MCP Server V0.4.2 全部测试通过")
        print("   - §13.3 3 阶段混合策略：Phase 1/2/3")
        print("   - Phase 3 streaming 7 步 yield")
        print("   - 降级路径完整（L1/L3）")
        print("   - token 预算分级")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    try:
        success = run_v042_tests()
    finally:
        bridge.clear_probe_cache()
    sys.exit(0 if success else 1)
