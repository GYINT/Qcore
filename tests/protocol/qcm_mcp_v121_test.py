#!/usr/bin/env python3
"""qcm_mcp_v121_test.py — QCM V1.2.1 OpenTelemetry 追踪测试

覆盖（8 用例）：
  1. qcm_tracing 模块导入
  2. tracing_enabled 默认开启
  3. start_tool_span 创建 span（轻量）
  4. span 属性（tool.name + arguments）
  5. span.end 记录 duration
  6. record_exception 标记 ERROR
  7. QCM_TRACING=0 关闭追踪
  8. 工具调用集成（_gql_call_provider 产生 span）
"""

import json
import os
import sys
import time

QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(QCM_ROOT, "scripts")
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


def run_v121_tests():
    print("=" * 70)
    print("QCM V1.2.1 测试套件（OpenTelemetry 分布式追踪）")
    print("=" * 70)

    passed = 0
    total = 0

    from tracing import (Span, start_tool_span, tracing_enabled,
                             get_tracer, OTEL_AVAILABLE)

    # [1] 模块
    print("\n[1. 追踪模块]")
    total += 1
    def module_import():
        assert hasattr(start_tool_span, "__call__")
        assert hasattr(tracing_enabled, "__call__")
        return True
    if test("qcm_tracing 模块导入", module_import):
        passed += 1

    total += 1
    def enabled_default():
        os.environ.pop("QCM_TRACING", None)
        assert tracing_enabled() is True
        return True
    if test("tracing_enabled 默认开启", enabled_default):
        passed += 1

    # [2] span 功能
    print("\n[2. Span 功能]")
    total += 1
    def span_create():
        span = start_tool_span("qcm_test", {"query": "x"})
        assert span is not None
        return True
    if test("start_tool_span 创建 span", span_create):
        passed += 1

    total += 1
    def span_attrs():
        span = start_tool_span("qcm_research", {"query": "焊接"})
        d = span.to_dict()
        assert d["name"] == "tool:qcm_research", f"name={d['name']}"
        assert "tool.name" in d["attributes"]
        assert "tool.arguments" in d["attributes"]
        assert "焊接" in d["attributes"]["tool.arguments"]
        return True
    if test("span 属性（name + arguments）", span_attrs):
        passed += 1

    total += 1
    def span_duration():
        span = start_tool_span("qcm_slow")
        time.sleep(0.05)
        span.end()
        d = span.to_dict()
        assert d["duration_ms"] is not None
        assert d["duration_ms"] >= 40, f"duration={d['duration_ms']}"
        return True
    if test("span.end 记录 duration", span_duration):
        passed += 1

    total += 1
    def span_error():
        span = start_tool_span("qcm_err")
        try:
            raise ValueError("测试错误")
        except ValueError as e:
            span.record_exception(e)
        span.end()
        d = span.to_dict()
        assert d["status"] == "ERROR"
        assert len(d["events"]) >= 1
        assert "exception" in d["events"][0]["name"]
        return True
    if test("record_exception 标记 ERROR", span_error):
        passed += 1

    total += 1
    def tracing_off():
        os.environ["QCM_TRACING"] = "0"
        try:
            assert tracing_enabled() is False
            span = start_tool_span("qcm_disabled")
            assert span is None, "关闭时不应创建 span"
            return True
        finally:
            os.environ.pop("QCM_TRACING", None)
    if test("QCM_TRACING=0 关闭追踪", tracing_off):
        passed += 1

    # [3] 集成
    print("\n[3. 工具调用集成]")
    total += 1
    def integration():
        import mcp_server as srv
        # 通过 GraphQL provider 调用 → 应创建 span（不报错）
        r = srv._gql_call_provider("qcm_research", {"query": "汽车焊接虚焊"})
        assert "version" in r
        return True
    if test("工具调用集成（span 不干扰）", integration):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"V1.2.1 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V1.2.1 全部测试通过")
        print("   - OpenTelemetry span（工具调用追踪）")
        print("   - 属性/耗时/异常记录")
        print("   - 开关控制（QCM_TRACING）")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v121_tests()
    sys.exit(0 if success else 1)
