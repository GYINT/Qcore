# QCM MCP Server v0.1 测试脚本
"""
测试 QCM MCP Server 6 工具：
1. initialize / tools/list / tools/call
2. Bearer Token 认证
3. 错误处理
"""
import subprocess
import json
import os
import time
import sys

QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(QCM_ROOT, "scripts/mcp_server.py")

# 服务器期望的固定 Token（用于 auth 测试）
SERVER_EXPECTED_TOKEN = "expected-test-token-abc123"

def call_mcp(method, params=None, token=None):
    """调用 MCP server 单个方法"""
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    if token:
        if "params" not in request:
            request["params"] = {}
        request["params"]["__token__"] = token

    # auth 测试需要同时设置 QCM_AUTH_TOKEN（固定值，与请求 token 区分）
    test_env = {**os.environ, "QCM_REQUIRE_TOKEN": "1" if token else "0"}
    if token:
        test_env["QCM_AUTH_TOKEN"] = SERVER_EXPECTED_TOKEN

    proc = subprocess.Popen(
        ["python3", SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=test_env,
    )

    line = json.dumps(request, ensure_ascii=False)
    proc.stdin.write(line + "\n")
    proc.stdin.flush()
    proc.stdin.close()

    response = proc.stdout.readline().strip()
    proc.wait(timeout=5)

    if not response:
        stderr = proc.stderr.read()
        return {"error": "no response", "stderr": stderr}
    return json.loads(response)


def test(name, fn, expect_error=False):
    """测试包装"""
    try:
        result = fn()
        if "error" in result:
            if expect_error:
                print(f"  ✅ {name}（预期错误: {result['error'].get('code')}）")
                return True
            print(f"  ❌ {name}: {result.get('error')}")
            return False
        if expect_error:
            print(f"  ❌ {name}: 预期错误但返回成功")
            return False
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def run_all_tests():
    """运行全部 6 工具 + 协议测试"""
    print("=" * 70)
    print(f"QCM MCP Server v0.1 测试（{SERVER}）")
    print("=" * 70)

    passed = 0
    total = 0

    # === 协议测试 ===
    print("\n[协议层]")
    total += 1
    if test("initialize", lambda: call_mcp("initialize")):
        passed += 1
    total += 1
    if test("tools/list", lambda: call_mcp("tools/list")):
        passed += 1
    total += 1
    if test("ping", lambda: call_mcp("ping")):
        passed += 1

    # === 工具 1: qcm_research ===
    print("\n[工具 1: qcm_research]")
    total += 1
    if test("research · T2 焊接虚焊", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_research", "arguments": {"query": "焊接虚焊客诉复发怎么破", "level_hint": "T2"}}
    )):
        passed += 1
    total += 1
    if test("research · T4 完整", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_research", "arguments": {"query": "汽车焊接工艺参数优化", "level_hint": "T4"}}
    )):
        passed += 1

    # === 工具 2: qcm_score_source ===
    print("\n[工具 2: qcm_score_source]")
    total += 1
    if test("score · ISO 来源", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_score_source", "arguments": {
            "url": "https://iso.org/standard-42001",
            "content": "AI 治理标准 · 2023 年发布",
            "domain": "AI 治理"
        }}
    )):
        passed += 1
    total += 1
    if test("score · 普通博客", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_score_source", "arguments": {
            "url": "https://example-blog.com/post",
            "content": "AI 治理入门",
            "domain": "AI 治理"
        }}
    )):
        passed += 1

    # === 工具 3: qcm_decide ===
    print("\n[工具 3: qcm_decide]")
    total += 1
    if test("decide · 紧急", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_decide", "arguments": {
            "problem_text": "焊接虚焊客诉复发",
            "urgency": "紧急"
        }}
    )):
        passed += 1
    total += 1
    if test("decide · 例行", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_decide", "arguments": {
            "problem_text": "工艺参数 DOE 优化",
            "urgency": "例行"
        }}
    )):
        passed += 1

    # === 工具 4: qcm_solve_problem ===
    print("\n[工具 4: qcm_solve_problem]")
    total += 1
    if test("solve · 完整 5 段", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_solve_problem", "arguments": {
            "problem_dict": {"query": "尺寸波动大", "level": "T2", "layer": "L2"}
        }}
    )):
        passed += 1

    # === 工具 5: qcm_audit ===
    print("\n[工具 5: qcm_audit]")
    total += 1
    if test("audit · 完整决策", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_audit", "arguments": {
            "decision_output": {
                "query": "test",
                "level": "T2",
                "layer": "L2",
                "tools_used": ["A01 SPC"],
                "protocol_reference": "action-orders.md §3"
            }
        }}
    )):
        passed += 1
    total += 1
    if test("audit · 字段缺失", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_audit", "arguments": {
            "decision_output": {"query": "test"}
        }}
    )):
        passed += 1

    # === 工具 6: qcm_validate ===
    print("\n[工具 6: qcm_validate]")
    total += 1
    if test("validate · case-application", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_validate", "arguments": {
            "output_text": "行动要项：围堵变异\n事态导航：T2→L2\n危机沟通：D=3 P3\n行动措施：A01 SPC\n双归零：技术归零 + 管理归零",
            "form": "case-application"
        }}
    )):
        passed += 1
    total += 1
    if test("validate · quick-response", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_validate", "arguments": {
            "output_text": "D=3 立即围堵 责任人：张三 上报路径：班组长 工具：A01",
            "form": "quick-response"
        }}
    )):
        passed += 1

    # === 错误处理 ===
    print("\n[错误处理]")
    total += 1
    if test("unknown method", lambda: call_mcp("unknown_method"), expect_error=True):
        passed += 1
    total += 1
    if test("unknown tool", lambda: call_mcp(
        "tools/call", {"name": "unknown_tool", "arguments": {}}
    ), expect_error=True):
        passed += 1

    # === 认证测试 ===
    print("\n[Bearer Token 认证]")
    total += 1
    if test("auth · 错误 Token", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_decide", "arguments": {"problem_text": "test"}},
        token="wrong-token-12345"
    ), expect_error=True):
        passed += 1
    total += 1
    if test("auth · 正确 Token", lambda: call_mcp(
        "tools/call",
        {"name": "qcm_decide", "arguments": {"problem_text": "test"}},
        token=SERVER_EXPECTED_TOKEN
    )):
        passed += 1

    print("\n" + "=" * 70)
    print(f"测试结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ QCM MCP Server v0.1 全部测试通过")
    else:
        print(f"❌ {total - passed} 个测试失败")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)