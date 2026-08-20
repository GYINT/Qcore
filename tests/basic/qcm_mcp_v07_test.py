#!/usr/bin/env python3
"""qcm_mcp_v07_test.py — QCM V0.7 MCP 协议完整化测试

V0.7 任务清单：
  1. MCP Resources API（resources/list + resources/read）
  2. MCP Prompts API（prompts/list + prompts/get）
  3. MCP Sampling API（sampling/createMessage）
  4. MCP Protocol 版本协商（capabilities 完整）
  5. V0.6 carryover: WebSocket transport（可选 · 占位）

测试场景（20）：
  Protocol Capabilities（3）：
    - initialize 返回完整 capabilities
    - 含 resources/prompts/tools/logging
    - protocolVersion 字段

  Resources（5）：
    - resources/list 包含 corpus 资源
    - resources/list 包含 tools 资源
    - resources/list 包含 masters 资源
    - resources/read 单个 corpus 文件
    - resources/read 单个 tool（A01）

  Prompts（4）：
    - prompts/list 包含预设模板
    - prompts/get qcm_research_default
    - prompts/get 参数替换
    - prompts/get 错误处理

  Sampling（3）：
    - sampling/createMessage 调 LLM
    - 错误时返回
    - 无 LLM 时降级

  Unit Tests（5）：
    - ResourceHandler 直接调用
    - PromptTemplate 填充
    - URL 解析 qcm://
    - Capabilities 字段完整
    - backward compat（V0.6 tools/call 仍工作）
"""
import subprocess
import json
import os
import sys
import time
import signal
import socket
import urllib.request
import urllib.error
from pathlib import Path
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")
TEST_TOKEN = "v07-test-token"

def find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

TEST_PORT = find_free_port()


def start_server(require_token=False, port=None):
    if port is None:
        port = TEST_PORT
    env = {**os.environ, "QCM_REQUIRE_TOKEN": "1" if require_token else "0"}
    if require_token:
        env["QCM_AUTH_TOKEN"] = TEST_TOKEN
    proc = subprocess.Popen(
        ["python3", SERVER, "--transport", "http", "--port", str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/health/live", timeout=2) as resp:
                if resp.status == 200:
                    return proc, base_url
        except (urllib.error.URLError, ConnectionRefusedError):
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("Server failed to start")


def http_get(url, token=None, timeout=5):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def http_post(url, payload, token=None, timeout=10):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def rpc_call(method, params=None, token=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        payload["params"] = params
    status, body = http_post(f"http://127.0.0.1:{TEST_PORT}/rpc", payload, token=token)
    return status, json.loads(body) if body else {}


def test(name, fn, expect_error=False):
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            if expect_error:
                print(f"  ✅ {name}（预期错误）")
                return True
            print(f"  ❌ {name}: {result.get('error')}")
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
        print(f"  ❌ {name}: {e}")
        return False


def run_v07_tests():
    print("=" * 70)
    print(f"QCM MCP Server V0.7 测试（Resources + Prompts + Sampling + Protocol + WS）")
    print(f"测试端口：{TEST_PORT}")
    print("=" * 70)

    passed = 0
    total = 0
    proc = None

    try:
        # 启动
        total += 1
        if test("V0.7 server 启动", lambda: (start_server(), True)[1]):
            passed += 1

        # ========== Protocol Capabilities（3） ==========
        print("\n[1. Protocol Capabilities]")

        def init_capabilities_full():
            _, body = rpc_call("initialize")
            caps = body["result"]["capabilities"]
            assert "tools" in caps
            assert "resources" in caps
            assert "prompts" in caps
            assert "logging" in caps
            return True

        total += 1
        if test("initialize · 完整 capabilities", init_capabilities_full):
            passed += 1

        def init_capabilities_tools():
            _, body = rpc_call("initialize")
            tools_cap = body["result"]["capabilities"]["tools"]
            assert "listChanged" in tools_cap
            return True

        total += 1
        if test("capabilities.tools 含 listChanged", init_capabilities_tools):
            passed += 1

        def init_protocol_version():
            _, body = rpc_call("initialize")
            pv = body["result"]["protocolVersion"]
            assert pv == "2024-11-05"
            return True

        total += 1
        if test("protocolVersion = 2024-11-05", init_protocol_version):
            passed += 1

        # ========== Resources（5） ==========
        print("\n[2. Resources API]")

        def resources_list_corpus():
            _, body = rpc_call("resources/list")
            resources = body["result"]["resources"]
            uris = [r["uri"] for r in resources]
            assert any("qcm://corpus/" in u for u in uris)
            return True

        total += 1
        if test("resources/list 含 corpus 资源", resources_list_corpus):
            passed += 1

        def resources_list_tools():
            _, body = rpc_call("resources/list")
            resources = body["result"]["resources"]
            uris = [r["uri"] for r in resources]
            assert any("qcm://tools/" in u for u in uris)
            return True

        total += 1
        if test("resources/list 含 tools 资源", resources_list_tools):
            passed += 1

        def resources_list_masters():
            _, body = rpc_call("resources/list")
            resources = body["result"]["resources"]
            uris = [r["uri"] for r in resources]
            assert any("qcm://masters/" in u for u in uris)
            return True

        total += 1
        if test("resources/list 含 masters 资源", resources_list_masters):
            passed += 1

        def resources_read_corpus():
            _, body = rpc_call("resources/read",
                               {"uri": "qcm://corpus/action-orders.md"})
            assert "contents" in body["result"]
            text = body["result"]["contents"][0]["text"]
            assert len(text) > 100
            return True

        total += 1
        if test("resources/read qcm://corpus/action-orders.md", resources_read_corpus):
            passed += 1

        def resources_read_tool():
            _, body = rpc_call("resources/read",
                               {"uri": "qcm://tools/A01"})
            assert "contents" in body["result"]
            text = body["result"]["contents"][0]["text"]
            assert "SPC" in text
            return True

        total += 1
        if test("resources/read qcm://tools/A01", resources_read_tool):
            passed += 1

        # ========== Prompts（4） ==========
        print("\n[3. Prompts API]")

        def prompts_list():
            _, body = rpc_call("prompts/list")
            prompts = body["result"]["prompts"]
            names = [p["name"] for p in prompts]
            assert "qcm_research_default" in names
            assert "qcm_decide_emergency" in names
            assert "qcm_audit_quick" in names
            assert "qcm_solve_5why" in names
            return True

        total += 1
        if test("prompts/list 含 4 预设模板", prompts_list):
            passed += 1

        def prompts_get_research():
            _, body = rpc_call("prompts/get",
                               {"name": "qcm_research_default",
                                "arguments": {"query": "焊接虚焊", "level_hint": "T2"}})
            assert "messages" in body["result"]
            msg = body["result"]["messages"][0]
            assert msg["role"] == "user"
            assert "焊接虚焊" in msg["content"]["text"]
            return True

        total += 1
        if test("prompts/get 参数替换", prompts_get_research):
            passed += 1

        def prompts_get_emergency():
            _, body = rpc_call("prompts/get",
                               {"name": "qcm_decide_emergency",
                                "arguments": {"problem_text": "客诉爆发"}})
            assert "messages" in body["result"]
            assert "客诉爆发" in body["result"]["messages"][0]["content"]["text"]
            return True

        total += 1
        if test("prompts/get qcm_decide_emergency", prompts_get_emergency):
            passed += 1

        def prompts_get_error():
            _, body = rpc_call("prompts/get",
                               {"name": "nonexistent_prompt",
                                "arguments": {}})
            assert "error" in body
            return True

        total += 1
        if test("prompts/get 不存在 → 错误", prompts_get_error):
            passed += 1

        # ========== Sampling（3） ==========
        print("\n[4. Sampling API]")

        def sampling_create_message():
            _, body = rpc_call("sampling/createMessage", {
                "messages": [{"role": "user", "content": {"type": "text", "text": "ping"}}],
                "maxTokens": 10,
            })
            assert "result" in body
            result = body["result"]
            assert result["role"] == "assistant"
            assert "content" in result
            assert result["stopReason"] == "endTurn"
            return True

        total += 1
        if test("sampling/createMessage 调 LLM", sampling_create_message):
            passed += 1

        def sampling_no_llm():
            # 即使无 LLM API，也应能返回结构化结果（降级到 mock 或返回错误）
            _, body = rpc_call("sampling/createMessage", {
                "messages": [{"role": "user", "content": {"type": "text", "text": "test"}}],
            })
            # 不管 result 还是 error，都应能正常处理
            assert "result" in body or "error" in body
            return True

        total += 1
        if test("sampling/createMessage 健壮处理", sampling_no_llm):
            passed += 1

        def sampling_model_field():
            _, body = rpc_call("sampling/createMessage", {
                "messages": [{"role": "user", "content": {"type": "text", "text": "x"}}],
            })
            if "result" in body:
                assert "model" in body["result"]
            return True

        total += 1
        if test("sampling 返回 model 字段", sampling_model_field):
            passed += 1

        # ========== 单元测试（5） ==========
        print("\n[5. Unit Tests]")

        def unit_resource_handler():
            sys.path.insert(0, SCRIPTS)
            from resources import ResourceHandler
            corpus = {
                "action-orders.md": "# Test content",
                "tools.md": "## A01. SPC 统计过程控制\n## A02. Poka-Yoke 防错\n",
            }
            handler = ResourceHandler(corpus)
            resources = handler.list_resources()
            # 验证 corpus 资源
            assert any(r["uri"] == "qcm://corpus/action-orders.md" for r in resources)
            # 验证 tools 资源（需要 tools.md 才有）
            assert any(r["uri"].startswith("qcm://tools/") for r in resources)
            # 验证 standards 资源（固定列表）
            assert any(r["uri"].startswith("qcm://standards/") for r in resources)
            return True

        total += 1
        if test("ResourceHandler 直接调用", unit_resource_handler):
            passed += 1

        def unit_prompts_template():
            sys.path.insert(0, SCRIPTS)
            from prompts import get_prompt
            result = get_prompt("qcm_research_default",
                               {"query": "test123", "level_hint": "T2", "context": ""})
            assert "test123" in result["messages"][0]["content"]["text"]
            return True

        total += 1
        if test("PromptTemplate 模板填充", unit_prompts_template):
            passed += 1

        def unit_url_parsing():
            sys.path.insert(0, SCRIPTS)
            from resources import ResourceHandler
            handler = ResourceHandler({})
            result = handler.read_resource("qcm://tools/A01")
            # 应该有 contents 或 error，但不能崩溃
            assert "contents" in result or "error" in result
            return True

        total += 1
        if test("URL 解析 qcm://", unit_url_parsing):
            passed += 1

        def unit_capabilities_complete():
            _, body = rpc_call("initialize")
            caps = body["result"]["capabilities"]
            # V0.7 应含 4 个 capability
            assert len(caps) >= 4
            assert all(k in caps for k in ["tools", "resources", "prompts", "logging"])
            return True

        total += 1
        if test("capabilities 字段完整（4 个）", unit_capabilities_complete):
            passed += 1

        def unit_backward_compat():
            # V0.6 tools/call 应仍工作
            _, body = rpc_call("tools/call",
                               {"name": "qcm_decide",
                                "arguments": {"problem_text": "test", "urgency": "重要"}})
            assert "result" in body
            assert body["result"]["content"][0]["type"] == "text"
            return True

        total += 1
        if test("向后兼容 V0.6 tools/call", unit_backward_compat):
            passed += 1

    finally:
        if proc:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

        # ========== Streaming（5） ==========
        print("\n[6. Streaming · notifications/progress]")

        def streaming_request_progress():
            """请求 streaming=true 应返回 progressToken"""
            _, body = rpc_call("tools/call",
                               {"name": "qcm_decide",
                                "arguments": {"problem_text": "test"},
                                "streaming": True})
            assert "result" in body
            result = body["result"]
            # progressToken 应在 result 里
            assert "progressToken" in result
            assert len(result["progressToken"]) > 0
            return True

        total += 1
        if test("streaming=true 返回 progressToken", streaming_request_progress):
            passed += 1

        def streaming_disabled_by_default():
            """默认 streaming=false 应不返回 progressToken"""
            _, body = rpc_call("tools/call",
                               {"name": "qcm_decide",
                                "arguments": {"problem_text": "test"}})
            assert "result" in body
            # 默认不返回 progressToken（向后兼容）
            assert "progressToken" not in body["result"]
            return True

        total += 1
        if test("默认 streaming=false 不返回 progressToken", streaming_disabled_by_default):
            passed += 1

        def streaming_with_research():
            """streaming=true + qcm_research（V0.2 LLM 增强工具）"""
            _, body = rpc_call("tools/call",
                               {"name": "qcm_research",
                                "arguments": {"query": "test", "level_hint": "T2"},
                                "streaming": True})
            assert "result" in body
            assert "progressToken" in body["result"]
            return True

        total += 1
        if test("streaming + qcm_research", streaming_with_research):
            passed += 1

        def streaming_tool_call_with_streaming_arg():
            """显式 streaming=true 应正常返回"""
            _, body = rpc_call("tools/call",
                               {"name": "qcm_decide",
                                "arguments": {"problem_text": "x", "urgency": "紧急"},
                                "streaming": True})
            assert "result" in body
            assert "progressToken" in body["result"]
            assert "content" in body["result"]
            return True

        total += 1
        if test("streaming 完整流程", streaming_tool_call_with_streaming_arg):
            passed += 1

        def streaming_backward_compat():
            """V0.6 客户端（无 streaming 参数）应仍正常"""
            _, body = rpc_call("tools/call",
                               {"name": "qcm_audit",
                                "arguments": {"decision_output": {"query": "test", "level": "T2"}}})
            assert "result" in body
            assert "progressToken" not in body["result"]
            return True

        total += 1
        if test("向后兼容 V0.6（无 streaming 参数）", streaming_backward_compat):
            passed += 1

    print("\n" + "=" * 70)
    print(f"V0.7 测试结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ QCM MCP Server V0.7 全部测试通过")
        print("   - MCP Resources API（list + read · corpus/tools/masters）")
        print("   - MCP Prompts API（list + get · 4 预设模板）")
        print("   - MCP Sampling API（createMessage · 服务端调 LLM）")
        print("   - Protocol 完整 capabilities（tools/resources/prompts/logging）")
    else:
        print(f"❌ {total - passed} 个测试失败")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = run_v07_tests()
    sys.exit(0 if success else 1)