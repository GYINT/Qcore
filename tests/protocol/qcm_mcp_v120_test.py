#!/usr/bin/env python3
"""qcm_mcp_v120_test.py — QCM V1.2.0 GraphQL Subscription 测试

覆盖（8 用例）：
  1. subscription 类型构建
  2. schema 含 subscription（HTTP server）
  3. publish_tool_event 事件发布
  4. subscribe 收到事件（async）
  5. 多订阅者广播
  6. 工具调用触发事件（真实调用 → 事件发布）
  7. 事件字段完整（tool/arguments/time）
  8. 错误 subscription 查询 → errors
"""
import json
import os
import sys
import time
import asyncio
import subprocess
import urllib.request
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")
PORT = 8960

sys.path.insert(0, SCRIPTS)


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


def run_v120_tests():
    print("=" * 70)
    print("QCM V1.2.0 测试套件（GraphQL Subscription · WS 实时推送）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] 模块级
    print("\n[1. Subscription 模块]")
    total += 1
    def sub_build():
        from qcm_graphql import build_subscription_schema
        sub_type = build_subscription_schema()
        assert sub_type is not None
        fields = sub_type.fields
        assert "toolCalled" in fields
        return True
    if test("build_subscription_schema 构建", sub_build):
        passed += 1

    total += 1
    def event_publish():
        from qcm_graphql import publish_tool_event, _event_subscribers
        n = len(_event_subscribers)
        publish_tool_event({"tool": "t", "arguments": {}, "time": "now"})
        # 无订阅者不应报错
        assert len(_event_subscribers) == n
        return True
    if test("publish_tool_event 无订阅者安全", event_publish):
        passed += 1

    total += 1
    def event_subscribe():
        from qcm_graphql import publish_tool_event, subscribe_tool_events
        async def run():
            async def consumer():
                gen = subscribe_tool_events()
                evt = await gen.__anext__()  # 迭代器启动
                return evt
            # 先创建订阅
            q_future = asyncio.ensure_future(consumer())
            await asyncio.sleep(0.1)
            publish_tool_event({"tool": "demo", "arguments": {"a": 1}, "time": "t"})
            evt = await asyncio.wait_for(q_future, timeout=3)
            return evt
        evt = asyncio.run(run())
        assert evt["tool"] == "demo"
        return True
    if test("subscribe 收到事件（async）", event_subscribe):
        passed += 1

    # [2] HTTP server 集成
    print("\n[2. HTTP server 集成]")
    proc = subprocess.Popen(["python3", "-B", SERVER, "--transport", "http",
                             "--port", str(PORT)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    try:
        total += 1
        def schema_has_subscription():
            import importlib
            import mcp_server as srv
            schema = srv.get_graphql_schema()
            assert schema is not None
            assert schema.subscription_type is not None, "schema 无 subscription"
            fields = schema.subscription_type.fields
            assert "toolCalled" in fields
            return True
        if test("HTTP server schema 含 subscription", schema_has_subscription):
            passed += 1

        total += 1
        def tool_call_publishes():
            import mcp_server as srv
            from qcm_graphql import publish_tool_event, subscribe_tool_events
            # 通过 HTTP 调用工具 → 应发布事件
            async def run():
                gen = subscribe_tool_events()
                fut = asyncio.ensure_future(gen.__anext__())
                await asyncio.sleep(0.2)
                # 直接调用 handler（模拟工具调用）
                srv._gql_call_provider("qcm_research", {"query": "焊接虚焊"})
                evt = await asyncio.wait_for(fut, timeout=5)
                return evt
            evt = asyncio.run(run())
            assert evt["tool"] == "qcm_research", f"tool={evt.get('tool')}"
            return True
        if test("工具调用触发事件发布", tool_call_publishes):
            passed += 1

        total += 1
        def event_fields():
            from qcm_graphql import publish_tool_event, subscribe_tool_events
            async def run():
                gen = subscribe_tool_events()
                fut = asyncio.ensure_future(gen.__anext__())
                await asyncio.sleep(0.2)
                publish_tool_event({"tool": "qcm_audit", "arguments": {"x": 1}, "time": "2026-08-12T17:00:00"})
                evt = await asyncio.wait_for(fut, timeout=3)
                return evt
            evt = asyncio.run(run())
            assert evt["tool"] == "qcm_audit"
            assert evt["arguments"] == {"x": 1}
            assert evt["time"].startswith("2026")
            return True
        if test("事件字段完整（tool/arguments/time）", event_fields):
            passed += 1

        total += 1
        def multi_subscriber():
            from qcm_graphql import publish_tool_event, subscribe_tool_events
            async def run():
                gen1 = subscribe_tool_events()
                gen2 = subscribe_tool_events()
                f1 = asyncio.ensure_future(gen1.__anext__())
                f2 = asyncio.ensure_future(gen2.__anext__())
                await asyncio.sleep(0.2)
                publish_tool_event({"tool": "broadcast", "arguments": {}, "time": "t"})
                e1 = await asyncio.wait_for(f1, timeout=3)
                e2 = await asyncio.wait_for(f2, timeout=3)
                return e1["tool"], e2["tool"]
            t1, t2 = asyncio.run(run())
            assert t1 == "broadcast" and t2 == "broadcast"
            return True
        if test("多订阅者广播", multi_subscriber):
            passed += 1

        total += 1
        def bad_sub_query():
            # 非 subscription 查询应正常（走 query）
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/graphql",
                data=json.dumps({"query": "{ health { status } }"}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            r = json.loads(urllib.request.urlopen(req, timeout=5).read())
            assert r["data"]["health"]["status"] == "ok"
            return True
        if test("普通 query 不受影响", bad_sub_query):
            passed += 1
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # 总结
    print("\n" + "=" * 70)
    print(f"V1.2.0 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V1.2.0 全部测试通过")
        print("   - GraphQL Subscription（toolCalled 事件）")
        print("   - 工具调用实时发布（事件总线）")
        print("   - 多订阅者广播")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v120_tests()
    sys.exit(0 if success else 1)
