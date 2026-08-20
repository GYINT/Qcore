#!/usr/bin/env python3
"""qcm_mcp_v140_test.py — QCM V1.4.0 GraphQL Subscription over WS 测试

覆盖（10 用例）：
  1. WS server 启动（--transport ws 双协议）
  2. connection_init → connection_ack
  3. GraphQL subscription（toolCalled 实时推送）
  4. 订阅事件 → 工具调用触发（跨协议）
  5. GraphQL query over WS（next + complete）
  6. JSON-RPC tools/list over WS（MCP 兼容）
  7. JSON-RPC tools/call over WS
  8. ping → pong
  9. 无效查询 → error 消息
  10. 认证（require-token）
"""

import json
import os
import sys
import time
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import asyncio
import subprocess
import websockets

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")
PORT = 8978


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


def start_server(port, require_token=False, token=None):
    # 测试隔离：移除 LLM key（工具走 mock 快路径 · 避免 real LLM 慢导致超时）
    env = {**os.environ}
    for k in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
              "DASHSCOPE_API_KEY", "SCNET_API_KEY", "OLLAMA_KEY",
              "AZURE_OPENAI_API_KEY", "LM_STUDIO_KEY"]:
        env.pop(k, None)
    cmd = ["python3", "-B", SERVER, "--transport", "ws", "--port", str(port)]
    if require_token:
        cmd += ["--require-token", "--token", token or "ws-token-123"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    time.sleep(4)
    return proc


async def recv_until(ws, predicate, timeout=6, max_msgs=8):
    msgs = []
    deadline = time.time() + timeout
    while time.time() < deadline and len(msgs) < max_msgs:
        try:
            remaining = max(0.1, deadline - time.time())
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
            msgs.append(msg)
            if predicate(msg):
                break
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
            break
    return msgs


def run_v140_tests():
    print("=" * 70)
    print("QCM V1.4.0 测试套件（GraphQL Subscription over WS）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1-9] 无认证 server
    proc = start_server(PORT)
    try:
        print("\n[1. WS 双协议基础]")
        total += 1
        def ws_ack():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"type": "connection_init"}))
                    msgs = await recv_until(ws, lambda m: m.get("type") == "connection_ack")
                    return msgs[0]["type"] if msgs else None
            assert asyncio.run(run()) == "connection_ack"
            return True
        if test("connection_init → connection_ack", ws_ack):
            passed += 1

        total += 1
        def ws_subscription():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"type": "subscribe", "id": "s1",
                        "payload": {"query": "subscription { toolCalled { tool } }"}}))
                    await asyncio.sleep(0.5)
                    # 通过 JSON-RPC 调工具触发事件
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "qcm_research", "arguments": {"query": "虚焊"}}}))
                    msgs = await recv_until(ws,
                        lambda m: m.get("type") == "next" and m.get("id") == "s1", timeout=8, max_msgs=10)
                    subs = [m for m in msgs if m.get("type") == "next" and m.get("id") == "s1"]
                    if not subs:
                        return False, f"no subscription event: {msgs}"
                    return subs[0]["payload"]["data"]["toolCalled"]["tool"]
            tool = asyncio.run(run())
            assert tool == "qcm_research", f"tool={tool}"
            return True
        if test("subscription 实时推送（工具调用触发）", ws_subscription):
            passed += 1

        total += 1
        def ws_query():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"type": "subscribe", "id": "q1",
                        "payload": {"query": "{ health { status } }"}}))
                    msgs = await recv_until(ws, lambda m: m.get("type") == "complete")
                    types = [m.get("type") for m in msgs]
                    return "next" in types and "complete" in types
            assert asyncio.run(run()) is True
            return True
        if test("GraphQL query over WS（next + complete）", ws_query):
            passed += 1

        total += 1
        def ws_jsonrpc_list():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}))
                    msgs = await recv_until(ws, lambda m: m.get("jsonrpc") == "2.0" and m.get("id") == 1)
                    if not msgs:
                        return 0
                    return len(msgs[0].get("result", {}).get("tools", []))
            n = asyncio.run(run())
            assert n >= 9, f"tools={n}"
            return True
        if test("JSON-RPC tools/list over WS（≥9）", ws_jsonrpc_list):
            passed += 1

        total += 1
        def ws_jsonrpc_call():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                        "params": {"name": "qcm_research", "arguments": {"query": "焊接"}}}))
                    msgs = await recv_until(ws, lambda m: m.get("jsonrpc") == "2.0" and m.get("id") == 2)
                    return bool(msgs and "result" in msgs[0])
            assert asyncio.run(run()) is True
            return True
        if test("JSON-RPC tools/call over WS", ws_jsonrpc_call):
            passed += 1

        total += 1
        def ws_ping():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"type": "ping"}))
                    msgs = await recv_until(ws, lambda m: m.get("type") == "pong")
                    return msgs[0]["type"] if msgs else None
            assert asyncio.run(run()) == "pong"
            return True
        if test("ping → pong", ws_ping):
            passed += 1

        total += 1
        def ws_bad_query():
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT}") as ws:
                    await ws.send(json.dumps({"type": "subscribe", "id": "b1",
                        "payload": {"query": "{ noSuchField }"}}))
                    msgs = await recv_until(ws, lambda m: m.get("type") == "error")
                    return any(m.get("type") == "error" for m in msgs)
            assert asyncio.run(run()) is True
            return True
        if test("无效查询 → error 消息", ws_bad_query):
            passed += 1
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # [10] 认证
    print("\n[2. WS 认证]")
    proc_auth = start_server(PORT + 1, require_token=True, token="ws-token-123")
    try:
        total += 1
        def ws_auth_reject():
            async def run():
                try:
                    async with websockets.connect(
                            f"ws://127.0.0.1:{PORT + 1}",
                            additional_headers={"Authorization": "Bearer wrong"},
                            open_timeout=3) as ws:
                        await ws.send(json.dumps({"type": "connection_init"}))
                        msgs = await recv_until(ws, lambda m: m.get("type") == "connection_error", timeout=3)
                        return "connection_error" in [m.get("type") for m in msgs] if msgs else True
                except Exception:
                    return True  # 连接被拒/关闭也算拒绝
            return asyncio.run(run())
        if test("无效 token 拒绝（connection_error/关闭）", ws_auth_reject):
            passed += 1

        total += 1
        def ws_auth_accept():
            async def run():
                async with websockets.connect(
                        f"ws://127.0.0.1:{PORT + 1}",
                        additional_headers={"Authorization": "Bearer ws-token-123"},
                        open_timeout=3) as ws:
                    await ws.send(json.dumps({"type": "connection_init"}))
                    msgs = await recv_until(ws, lambda m: m.get("type") == "connection_ack", timeout=3)
                    return "connection_ack" in [m.get("type") for m in msgs] if msgs else False
            return asyncio.run(run())
        if test("有效 token 通过（connection_ack）", ws_auth_accept):
            passed += 1
    finally:
        proc_auth.terminate()
        proc_auth.wait(timeout=5)

    # 总结
    print("\n" + "=" * 70)
    print(f"V1.4.0 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V1.4.0 全部测试通过")
        print("   - graphql-ws 协议（subscription 实时推送）")
        print("   - JSON-RPC + GraphQL 双协议 WS")
        print("   - 认证 + ping/pong + 错误处理")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v140_tests()
    sys.exit(0 if success else 1)
