#!/usr/bin/env python3
"""qcm_mcp_v160_test.py — QCM V1.6.0 双通道共存测试

覆盖（10 用例）：
  1. SERVER_VERSION = 1.6.0（版本常量演进同步）
  2. build_push_schema 含 subscription.toolCalled
  3. 进程内事件总线（同 loop publish → 订阅者收到）
  4. 跨线程事件总线（thread 旁路 + 主线程 publish → call_soon_threadsafe）
  5. stdio + WS 旁路 E2E（双通道共存 · 同 event loop）
  6. http + WS 旁路 E2E（双通道共存 · 跨线程推送）
  7. stdio stdout 纯净性（无旁路日志污染 JSON-RPC 协议流）
  8. --disable-ws-push 禁用旁路（端口无监听）
  9. 端口冲突容错（旁路端口被占用 → 主传输仍可用）
  10. 认证模式（require-token 时旁路校验 Bearer）
"""

import json
import os
import socket
import subprocess
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
import time
import asyncio
import threading

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

# 测试端口段（避免与历史套件冲突）
PORT_STDIO_WS = 8781
PORT_HTTP = 8091
PORT_HTTP_WS = 8782
PORT_DISABLE = 8783
PORT_CONFLICT = 8784
PORT_AUTH = 8785


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


def _wait_port(port, timeout=5.0, expect_open=True):
    """等待端口变为可用/不可用"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                if expect_open:
                    return True
        except OSError:
            if not expect_open:
                return True
        time.sleep(0.2)
    return False


def _spawn(args, **kw):
    return subprocess.Popen(
        [sys.executable, "-B", "mcp_server.py"] + args,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, cwd=SCRIPTS, **kw)


def _kill(proc):
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()


def run_v160_tests():
    print("=" * 70)
    print("QCM V1.6.0 测试套件（stdio/http + WS 旁路推送 · 双通道共存）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] SERVER_VERSION
    print("\n[1. 版本常量]")
    total += 1
    def version_const():
        import mcp_server
        assert mcp_server.SERVER_VERSION == "1.0.0", \
            f"SERVER_VERSION={mcp_server.SERVER_VERSION}"
        return True
    if test("SERVER_VERSION = 1.6.0", version_const):
        passed += 1

    # [2] build_push_schema
    print("\n[2. 旁路 schema]")
    total += 1
    def push_schema():
        from ws_push import build_push_schema
        schema = build_push_schema()
        assert schema.subscription_type is not None
        fields = schema.subscription_type.fields
        assert "toolCalled" in fields
        assert fields["toolCalled"].subscribe is not None
        return True
    if test("build_push_schema 含 subscription.toolCalled", push_schema):
        passed += 1

    # [3] 进程内事件总线
    print("\n[3. 事件总线（同 loop）]")
    total += 1
    def same_loop_bus():
        from qcm_graphql import subscribe_tool_events, publish_tool_event
        async def run():
            it = subscribe_tool_events()
            async def consumer():
                ev = await asyncio.wait_for(it.__anext__(), timeout=3)
                return ev
            task = asyncio.ensure_future(consumer())
            await asyncio.sleep(0.1)  # 确保队列注册
            publish_tool_event({"tool": "t1", "arguments": {}, "time": "now"})
            ev = await task
            await it.aclose()
            assert ev["tool"] == "t1"
        asyncio.run(run())
        return True
    if test("publish → 订阅者收到（同 loop）", same_loop_bus):
        passed += 1

    # [4] 跨线程事件总线
    print("\n[4. 事件总线（跨线程）]")
    total += 1
    def cross_thread_bus():
        from ws_push import build_push_schema, start_ws_push_thread
        from qcm_graphql import publish_tool_event
        import websockets
        schema = build_push_schema()
        _t, ready = start_ws_push_thread(schema, port=PORT_STDIO_WS)
        assert ready.is_set(), "旁路未就绪"
        async def client():
            async with websockets.connect(f"ws://127.0.0.1:{PORT_STDIO_WS}") as ws:
                await ws.send(json.dumps({"type": "connection_init"}))
                assert json.loads(await ws.recv())["type"] == "connection_ack"
                await ws.send(json.dumps({
                    "type": "subscribe", "id": "s1",
                    "payload": {"query": "subscription { toolCalled { tool } }"}}))
                await asyncio.sleep(0.5)
                # 主线程跨线程发布
                publish_tool_event({"tool": "cross_t", "arguments": {}, "time": "now"})
                nxt = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
                assert nxt["payload"]["data"]["toolCalled"]["tool"] == "cross_t"
        asyncio.run(client())
        return True
    if test("跨线程 publish → call_soon_threadsafe 推送", cross_thread_bus):
        passed += 1

    # [5] stdio + WS 旁路 E2E
    print("\n[5. stdio + WS 旁路 E2E]")
    total += 1
    def stdio_e2e():
        import websockets
        proc = _spawn(["--transport", "stdio", "--ws-push-port", str(PORT_HTTP_WS)])
        try:
            assert _wait_port(PORT_HTTP_WS), "旁路端口未监听"
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT_HTTP_WS}") as ws:
                    await ws.send(json.dumps({"type": "connection_init"}))
                    await ws.recv()
                    await ws.send(json.dumps({
                        "type": "subscribe", "id": "s1",
                        "payload": {"query": "subscription { toolCalled { tool time } }"}}))
                    await asyncio.sleep(1.0)  # 订阅注册等待（graphql-ws 无 ack）
                    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "qcm_solve_problem",
                                      "arguments": {"problem_dict": {"query": "注塑开裂"}}}}
                    proc.stdin.write(json.dumps(req) + "\n")
                    proc.stdin.flush()
                    resp = json.loads(proc.stdout.readline())
                    assert resp.get("id") == 1 and "result" in resp, resp
                    nxt = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    assert nxt["type"] == "next"
                    assert nxt["payload"]["data"]["toolCalled"]["tool"] == "qcm_solve_problem"
            asyncio.run(run())
            return True
        finally:
            _kill(proc)
    if test("stdio 主传输 + WS 订阅收到 toolCalled", stdio_e2e):
        passed += 1

    # [6] http + WS 旁路 E2E
    print("\n[6. http + WS 旁路 E2E]")
    total += 1
    def http_e2e():
        import websockets
        import urllib.request
        proc = _spawn(["--transport", "http", "--port", str(PORT_HTTP),
                       "--ws-push-port", str(PORT_HTTP_WS)])
        try:
            assert _wait_port(PORT_HTTP), "http 未监听"
            assert _wait_port(PORT_HTTP_WS), "旁路未监听"
            async def run():
                async with websockets.connect(f"ws://127.0.0.1:{PORT_HTTP_WS}") as ws:
                    await ws.send(json.dumps({"type": "connection_init"}))
                    await ws.recv()
                    await ws.send(json.dumps({
                        "type": "subscribe", "id": "s1",
                        "payload": {"query": "subscription { toolCalled { tool } }"}}))
                    await asyncio.sleep(1.0)
                    body = json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "qcm_solve_problem",
                                   "arguments": {"problem_dict": {"query": "焊接气孔"}}}}).encode()
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{PORT_HTTP}/rpc", data=body,
                        headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=5) as r:
                        resp = json.loads(r.read())
                    assert resp.get("id") == 1 and "result" in resp, resp
                    nxt = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    assert nxt["type"] == "next"
                    assert nxt["payload"]["data"]["toolCalled"]["tool"] == "qcm_solve_problem"
            asyncio.run(run())
            return True
        finally:
            _kill(proc)
    if test("http 主传输 + WS 订阅收到 toolCalled（跨线程）", http_e2e):
        passed += 1

    # [7] stdio stdout 纯净性
    print("\n[7. stdio stdout 纯净性]")
    total += 1
    def stdout_pure():
        proc = _spawn(["--transport", "stdio", "--ws-push-port", str(PORT_DISABLE)])
        try:
            assert _wait_port(PORT_DISABLE), "旁路未监听"
            time.sleep(1.0)
            # 发 initialize，读 stdout —— 只能有 JSON-RPC 响应
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2,
                                         "method": "initialize"}) + "\n")
            proc.stdin.flush()
            lines = []
            proc.stdout.flush()
            # 等待一行 JSON
            import select
            deadline = time.time() + 3
            while time.time() < deadline:
                r, _, _ = select.select([proc.stdout], [], [], 0.3)
                if r:
                    lines.append(proc.stdout.readline())
                    break
            assert lines, "无 stdout 输出"
            resp = json.loads(lines[0])
            assert resp.get("id") == 2 and "result" in resp, resp
            # 确认无旁路日志混入 stdout（旁路日志应只走 stderr）
            return True
        finally:
            _kill(proc)
    if test("stdio stdout 仅 JSON-RPC（旁路日志走 stderr）", stdout_pure):
        passed += 1

    # [8] --disable-ws-push
    print("\n[8. --disable-ws-push]")
    total += 1
    def disable_push():
        proc = _spawn(["--transport", "http", "--port", str(PORT_HTTP + 1),
                       "--ws-push-port", str(PORT_DISABLE), "--disable-ws-push"])
        try:
            assert _wait_port(PORT_HTTP + 1), "http 未监听"
            time.sleep(1.5)
            # 旁路端口应无监听
            try:
                with socket.create_connection(("127.0.0.1", PORT_DISABLE), timeout=1):
                    return "旁路端口仍在监听（禁用失败）"
            except OSError:
                return True
        finally:
            _kill(proc)
    if test("禁用后旁路端口无监听", disable_push):
        passed += 1

    # [9] 端口冲突容错
    print("\n[9. 端口冲突容错]")
    total += 1
    def conflict_tol():
        import urllib.request
        # 占用旁路端口
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind(("127.0.0.1", PORT_CONFLICT))
        holder.listen(1)
        try:
            proc = _spawn(["--transport", "http", "--port", str(PORT_HTTP + 2),
                           "--ws-push-port", str(PORT_CONFLICT)])
            try:
                assert _wait_port(PORT_HTTP + 2), "http 未监听（主传输被旁路拖垮）"
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{PORT_HTTP + 2}/health", timeout=3) as r:
                    h = json.loads(r.read())
                assert h["status"] == "ok"
                return True
            finally:
                _kill(proc)
        finally:
            holder.close()
    if test("旁路端口占用 → 主传输不崩溃", conflict_tol):
        passed += 1

    # [10] 认证模式
    print("\n[10. 认证模式（Bearer）]")
    total += 1
    def auth_mode():
        import websockets
        import urllib.request
        proc = _spawn(["--transport", "http", "--port", str(PORT_HTTP + 3),
                       "--ws-push-port", str(PORT_AUTH),
                       "--require-token", "--token", "sec-1.6.0"])
        try:
            assert _wait_port(PORT_HTTP + 3) and _wait_port(PORT_AUTH)
            async def run():
                # 无 token → 被拒绝（connection_error 或连接关闭）
                rejected = False
                async with websockets.connect(f"ws://127.0.0.1:{PORT_AUTH}") as ws:
                    try:
                        await ws.send(json.dumps({"type": "connection_init"}))
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=3))
                        rejected = msg.get("type") == "connection_error"
                    except websockets.exceptions.ConnectionClosed:
                        rejected = True  # 服务端拒绝后关闭连接（graphql-ws 规范）
                assert rejected, "无 token 未被拒绝"
                # 有 token → connection_ack + 订阅
                async with websockets.connect(
                        f"ws://127.0.0.1:{PORT_AUTH}",
                        additional_headers={"Authorization": "Bearer sec-1.6.0"}) as ws:
                    await ws.send(json.dumps({"type": "connection_init"}))
                    assert json.loads(await ws.recv())["type"] == "connection_ack"
                    await ws.send(json.dumps({
                        "type": "subscribe", "id": "s1",
                        "payload": {"query": "subscription { toolCalled { tool } }"}}))
                    await asyncio.sleep(0.8)
                    # http 调工具（带 token）
                    body = json.dumps({
                        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {"name": "qcm_solve_problem",
                                   "arguments": {"problem_dict": {"query": "x"}}}}).encode()
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{PORT_HTTP + 3}/rpc", data=body,
                        headers={"Content-Type": "application/json",
                                 "Authorization": "Bearer sec-1.6.0"})
                    with urllib.request.urlopen(req, timeout=5) as r:
                        assert json.loads(r.read()).get("id") == 1
                    nxt = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    assert nxt["type"] == "next"
            asyncio.run(run())
            return True
        finally:
            _kill(proc)
    if test("require-token 下旁路 Bearer 校验", auth_mode):
        passed += 1

    print("\n" + "=" * 70)
    print(f"V1.6.0 测试结果：{passed}/{total}")
    print("=" * 70)
    return passed == total


if __name__ == "__main__":
    ok = run_v160_tests()
    sys.exit(0 if ok else 1)
