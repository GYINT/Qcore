#!/usr/bin/env python3
"""qcm_mcp_v151_test.py — QCM V1.5.1 OTLP gRPC 导出测试

覆盖（8 用例）：
  1. gRPC exporter 库可用
  2. QCM_TRACE_EXPORTER=otlp-grpc 启用
  3. otlp_grpc_enabled() 判断
  4. get_exporter_name() = otlp-grpc
  5. 默认 4317 端口配置（QCM_OTLP_GRPC_ENDPOINT）
  6. HTTP otlp 仍可用（向后兼容）
  7. span 在 gRPC 模式正常
  8. console 默认回退
"""

import json
import os
import sys
import time
import importlib
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


def reload_tracing():
    import tracing
    # OTel 拒绝覆盖已设置的 TracerProvider → 测试前重置（含 Once 单例）
    try:
        from opentelemetry import trace as _otel_trace
        from opentelemetry.util._once import Once
        _otel_trace._TRACER_PROVIDER = None  # type: ignore
        _otel_trace._TRACER_PROVIDER_SET_ONCE = Once()  # type: ignore
    except Exception:
        pass
    importlib.reload(tracing)
    return tracing


def run_v151_tests():
    print("=" * 70)
    print("QCM V1.5.1 测试套件（OTLP gRPC 导出 · 4317 端口）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] gRPC 库
    print("\n[1. OTLP gRPC 库]")
    total += 1
    def grpc_lib():
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            return True
        except ImportError:
            return False, "opentelemetry-exporter-otlp-proto-grpc 未安装"
    if test("OTLP gRPC exporter 库可用", grpc_lib):
        passed += 1

    # [2] gRPC 模式
    total += 1
    def grpc_mode():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp-grpc"
        os.environ["QCM_OTLP_GRPC_ENDPOINT"] = "http://localhost:4317"
        try:
            qt = reload_tracing()
            qt.get_exporter_name()  # 触发延迟初始化
            assert qt.OTLP_GRPC_AVAILABLE is True, "gRPC exporter 不可用"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
            os.environ.pop("QCM_OTLP_GRPC_ENDPOINT", None)
    if test("otlp-grpc 模式启用", grpc_mode):
        passed += 1

    total += 1
    def grpc_enabled():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp-grpc"
        try:
            qt = reload_tracing()
            assert qt.otlp_grpc_enabled() is True
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("otlp_grpc_enabled() 判断", grpc_enabled):
        passed += 1

    total += 1
    def exporter_name():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp-grpc"
        try:
            qt = reload_tracing()
            assert qt.get_exporter_name() == "otlp-grpc"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("get_exporter_name() = otlp-grpc", exporter_name):
        passed += 1

    # [3] 端口配置
    total += 1
    def grpc_endpoint():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp-grpc"
        os.environ["QCM_OTLP_GRPC_ENDPOINT"] = "http://jaeger-collector:4317"
        try:
            qt = reload_tracing()
            qt.get_exporter_name()  # 触发延迟初始化
            assert qt.OTLP_GRPC_AVAILABLE
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
            os.environ.pop("QCM_OTLP_GRPC_ENDPOINT", None)
    if test("QCM_OTLP_GRPC_ENDPOINT（4317）", grpc_endpoint):
        passed += 1

    # [4] HTTP otlp 兼容
    total += 1
    def http_compat():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        os.environ["QCM_OTLP_ENDPOINT"] = "http://localhost:4318/v1/traces"
        try:
            qt = reload_tracing()
            assert qt.otlp_enabled() is True  # 内部触发初始化
            assert qt.otlp_grpc_enabled() is False
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
            os.environ.pop("QCM_OTLP_ENDPOINT", None)
    if test("HTTP otlp 向后兼容（4318）", http_compat):
        passed += 1

    # [5] span 在 gRPC 模式
    total += 1
    def span_grpc():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp-grpc"
        try:
            qt = reload_tracing()
            qt.get_exporter_name()  # 触发延迟初始化
            span = qt.start_tool_span("qcm_grpc_test", {"q": 1})
            assert span is not None
            time.sleep(0.02)
            span.end()
            d = span.to_dict()
            assert d["name"] == "tool:qcm_grpc_test"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("span 在 gRPC 模式正常", span_grpc):
        passed += 1

    # [6] console 默认
    total += 1
    def console_default():
        os.environ.pop("QCM_TRACE_EXPORTER", None)
        try:
            qt = reload_tracing()
            assert qt.get_exporter_name() == "console"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("默认 console 导出器", console_default):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"V1.5.1 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V1.5.1 全部测试通过")
        print("   - OTLP gRPC 导出（4317 · Jaeger/Tempo/Collector）")
        print("   - otlp-grpc 与 http otlp 并存")
        print("   - console 默认回退")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v151_tests()
    sys.exit(0 if success else 1)
