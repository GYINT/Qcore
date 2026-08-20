#!/usr/bin/env python3
"""qcm_mcp_v03_test.py — QCM V0.3 HTTP/SSE + /health + audit.log + K8s 测试

V0.1 (qcm_mcp_test.py): 18 测试 · stdio
V0.2 (qcm_mcp_v02_test.py): 17 测试 · LLM Router 框架
V0.2.1 (qcm_mcp_v021_test.py): 11 测试 · 真实 DeepSeek API
V0.3 (本文件): 13 测试 · HTTP/SSE + /health + audit + K8s

测试场景：
  1. HTTP server 启动/停止（2）：subprocess 启动 · 优雅关闭
  2. /health 端点（3）：overview · live · ready
  3. JSON-RPC over HTTP（4）：initialize · tools/list · tools/call · 错误处理
  4. Bearer Token 认证（2）：正确 · 错误
  5. audit.log（2）：写入 · JSON Lines 格式
"""
import subprocess
import json
import os
import sys
import time
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import signal
import socket
import urllib.request
import urllib.error
import tempfile
from pathlib import Path

# 路径
SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")
TEST_TOKEN = "v03-test-token-abc123"

# 找可用端口
def find_free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


TEST_PORT = find_free_port()
TEST_PORT_AUTH = find_free_port()  # auth server 用不同端口
TEST_AUDIT_DIR = "/tmp/qcm-mcp-audit-v03-test"


def start_server(require_token=False, custom_audit_dir=None, port=None):
    """启动 MCP server (HTTP mode) · 返回 (proc, base_url)"""
    if port is None:
        port = TEST_PORT if not require_token else TEST_PORT_AUTH
    env = {**os.environ, "QCM_REQUIRE_TOKEN": "1" if require_token else "0"}
    if require_token:
        env["QCM_AUTH_TOKEN"] = TEST_TOKEN
    if custom_audit_dir:
        env["QCM_AUDIT_DIR"] = custom_audit_dir

    proc = subprocess.Popen(
        ["python3", SERVER, "--transport", "http", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # 等待 server 启动
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
    """HTTP GET"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200]}


def http_post(url, payload, token=None, timeout=10):
    """HTTP POST JSON-RPC"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body[:200]}


def test(name, fn, expect_error=False):
    """测试包装"""
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            if expect_error:
                print(f"  ✅ {name}（预期错误: {result.get('status', '?')}）")
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


def run_v03_tests():
    """运行 V0.3 测试套件"""
    print("=" * 70)
    print(f"QCM MCP Server V0.3 测试（HTTP/SSE + /health + audit.log + K8s）")
    print(f"测试端口：{TEST_PORT}")
    print("=" * 70)

    passed = 0
    total = 0
    proc = None

    try:
        # ========== 1. HTTP server 启动/停止 ==========
        print("\n[1. HTTP server 启动/停止]")

        def start_ok():
            global proc
            proc, base_url = start_server()
            return True

        total += 1
        if test("HTTP server 启动", start_ok):
            passed += 1

        def is_listening():
            # 连接并验证
            status, body = http_get(f"http://127.0.0.1:{TEST_PORT}/health/live")
            return status == 200 and body.get("status") == "alive"

        total += 1
        if test("HTTP server 监听", is_listening):
            passed += 1

        # ========== 2. /health 端点 ==========
        print("\n[2. /health 端点]")

        def health_overview():
            status, body = http_get(f"http://127.0.0.1:{TEST_PORT}/health")
            assert status == 200
            assert body.get("status") == "ok"
            assert body.get("tools_count") >= 6  # V0.3=6 · V0.4.1=7（+qcm_attribution）
            assert "stdio" in body.get("transports", [])
            return True

        total += 1
        if test("/health · overview", health_overview):
            passed += 1

        def health_live():
            status, body = http_get(f"http://127.0.0.1:{TEST_PORT}/health/live")
            assert status == 200
            assert body.get("status") == "alive"
            assert "uptime_s" in body
            return True

        total += 1
        if test("/health/live · K8s liveness", health_live):
            passed += 1

        def health_ready():
            status, body = http_get(f"http://127.0.0.1:{TEST_PORT}/health/ready")
            assert status == 200, f"status={status}, body={body}"
            assert body.get("status") in ("ready", "degraded")
            assert "corpus_files" in body
            assert "llm" in body
            return True

        total += 1
        if test("/health/ready · K8s readiness", health_ready):
            passed += 1

        # ========== 3. JSON-RPC over HTTP ==========
        print("\n[3. JSON-RPC over HTTP]")

        def rpc_initialize():
            payload = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
            status, body = http_post(f"http://127.0.0.1:{TEST_PORT}/rpc", payload)
            assert status == 200
            assert body["result"]["serverInfo"]["name"] == "qcm-mcp-server"
            return True

        total += 1
        if test("POST /rpc · initialize", rpc_initialize):
            passed += 1

        def rpc_tools_list():
            payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            status, body = http_post(f"http://127.0.0.1:{TEST_PORT}/messages", payload)
            assert status == 200
            assert len(body["result"]["tools"]) >= 6  # V0.3=6 · V0.4.1=7（+qcm_attribution）
            tool_names = [t["name"] for t in body["result"]["tools"]]
            assert "qcm_research" in tool_names
            assert "qcm_decide" in tool_names
            return True

        total += 1
        if test("POST /messages · tools/list", rpc_tools_list):
            passed += 1

        def rpc_tools_call():
            payload = {
                "jsonrpc": "2.0", "id": 3, "method": "tools/call",
                "params": {
                    "name": "qcm_decide",
                    "arguments": {"problem_text": "焊接虚焊客诉复发", "urgency": "紧急"}
                }
            }
            status, body = http_post(f"http://127.0.0.1:{TEST_PORT}/rpc", payload)
            assert status == 200
            assert body["result"]["content"][0]["type"] == "text"
            inner = json.loads(body["result"]["content"][0]["text"])
            assert inner["layer"] == "L1"
            return True

        total += 1
        if test("POST /rpc · tools/call", rpc_tools_call):
            passed += 1

        def rpc_error():
            payload = {"jsonrpc": "2.0", "id": 99, "method": "unknown/method"}
            status, body = http_post(f"http://127.0.0.1:{TEST_PORT}/rpc", payload)
            assert status == 200  # JSON-RPC 错误仍返回 200
            assert "error" in body
            assert body["error"]["code"] == -32601
            return True

        total += 1
        if test("JSON-RPC 错误处理", rpc_error):
            passed += 1

        def rpc_404():
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(f"http://127.0.0.1:{TEST_PORT}/notfound",
                                          method="POST",
                                          data=b'{}',
                                          headers={"Content-Type": "application/json"}),
                    timeout=3
                ) as resp:
                    return resp.status == 404
            except urllib.error.HTTPError as e:
                return e.code == 404

        total += 1
        if test("404 unknown path", rpc_404):
            passed += 1

        # ========== 4. Bearer Token 认证 ==========
        print("\n[4. Bearer Token 认证]")

        def start_with_auth():
            global proc
            proc, _ = start_server(require_token=True, port=TEST_PORT_AUTH)
            return True

        total += 1
        if test("启动带 auth 的 server", start_with_auth):
            passed += 1

        def auth_correct():
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            status, body = http_post(f"http://127.0.0.1:{TEST_PORT_AUTH}/rpc", payload, token=TEST_TOKEN)
            assert status == 200
            return True

        total += 1
        if test("正确 Token 访问", auth_correct):
            passed += 1

        def auth_wrong():
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
            status, body = http_post(f"http://127.0.0.1:{TEST_PORT_AUTH}/rpc", payload, token="wrong-token")
            assert status == 401, f"expected 401, got {status}: {body}"
            return True

        total += 1
        if test("错误 Token 拒绝（401）", auth_wrong):
            passed += 1

        # ========== 5. audit.log ==========
        print("\n[5. audit.log]")

        def audit_written():
            # 触发一次调用
            payload = {
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "qcm_decide", "arguments": {"problem_text": "test", "urgency": "重要"}}
            }
            http_post(f"http://127.0.0.1:{TEST_PORT_AUTH}/rpc", payload, token=TEST_TOKEN)

            # 检查 audit log 文件
            today = time.strftime("%Y-%m-%d")
            log_dir = os.environ.get("QCM_AUDIT_DIR", "/tmp/qcm-mcp-audit")
            log_file = os.path.join(log_dir, f"audit-{today}.log")

            # 等待写入
            for _ in range(10):
                if os.path.exists(log_file):
                    break
                time.sleep(0.1)

            assert os.path.exists(log_file), f"audit log not created: {log_file}"
            content = open(log_file, encoding="utf-8").read()
            lines = [l for l in content.strip().split("\n") if l]
            assert len(lines) > 0, "no audit entries"

            # JSON Lines 格式校验 - 查找 tools/call 条目（可能不是最后一条）
            call_entries = [l for l in lines if '"method": "tools/call"' in l]
            assert len(call_entries) > 0, f"no tools/call entry in {len(lines)} lines"
            entry = json.loads(call_entries[-1])
            assert "ts" in entry
            assert "method" in entry
            assert entry["method"] == "tools/call"
            return True

        total += 1
        if test("audit.log 写入 + JSON Lines", audit_written):
            passed += 1

    finally:
        # 清理
        if proc:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print(f"V0.3 测试结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ QCM MCP Server V0.3 全部测试通过")
        print("   - HTTP/SSE server 启动 + 监听")
        print("   - /health · /health/live · /health/ready (K8s probes)")
        print("   - POST /rpc + /messages · JSON-RPC 2.0")
        print("   - Bearer Token 认证（401）")
        print("   - audit.log JSON Lines 审计")
    else:
        print(f"❌ {total - passed} 个测试失败")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = run_v03_tests()
    sys.exit(0 if success else 1)