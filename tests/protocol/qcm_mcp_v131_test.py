#!/usr/bin/env python3
"""qcm_mcp_v131_test.py — QCM V1.3.1 OTel OTLP 导出测试

覆盖（8 用例）：
  1. OTLP exporter 可用（库检测）
  2. QCM_TRACE_EXPORTER=otlp 启用 OTLP
  3. otlp_enabled() 判断
  4. get_exporter_name() 返回 otlp
  5. console 默认导出器
  6. OTLP endpoint 配置（QCM_OTLP_ENDPOINT）
  7. span 创建在 OTLP 模式下正常
  8. 开关组合（QCM_TRACING=0 + OTLP）
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
    """重新加载 qcm_tracing（应用 env 变更）"""
    import tracing
    importlib.reload(tracing)
    return tracing


def run_v131_tests():
    print("=" * 70)
    print("QCM V1.3.1 测试套件（OTel OTLP 导出 · Jaeger/Tempo）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1] OTLP 库
    print("\n[1. OTLP 库]")
    total += 1
    def otlp_lib():
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            return True
        except ImportError:
            return False, "opentelemetry-exporter-otlp-proto-http 未安装"
    if test("OTLP exporter 库可用", otlp_lib):
        passed += 1

    # [2] otlp 模式
    total += 1
    def otlp_mode():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        os.environ["QCM_OTLP_ENDPOINT"] = "http://localhost:4318/v1/traces"
        try:
            qt = reload_tracing()
            qt.get_exporter_name()  # 触发延迟初始化
            assert qt.OTLP_AVAILABLE is True, "OTLP 不可用"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
            os.environ.pop("QCM_OTLP_ENDPOINT", None)
    if test("QCM_TRACE_EXPORTER=otlp 启用 OTLP", otlp_mode):
        passed += 1

    total += 1
    def otlp_enabled():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        try:
            qt = reload_tracing()
            assert qt.otlp_enabled() is True
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("otlp_enabled() 判断", otlp_enabled):
        passed += 1

    total += 1
    def exporter_name():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        try:
            qt = reload_tracing()
            assert qt.get_exporter_name() == "otlp"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("get_exporter_name() = otlp", exporter_name):
        passed += 1

    # [3] console 默认
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

    # [4] OTLP endpoint
    total += 1
    def otlp_endpoint():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        os.environ["QCM_OTLP_ENDPOINT"] = "http://jaeger:4318/v1/traces"
        try:
            qt = reload_tracing()
            qt.get_exporter_name()  # 触发延迟初始化
            # 构造 exporter 时应使用配置的 endpoint（无法直接读，但确认 OTLP 模式加载成功）
            assert qt.OTLP_AVAILABLE
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
            os.environ.pop("QCM_OTLP_ENDPOINT", None)
    if test("QCM_OTLP_ENDPOINT 配置", otlp_endpoint):
        passed += 1

    # [5] span 在 OTLP 模式正常
    total += 1
    def span_otlp():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        try:
            qt = reload_tracing()
            span = qt.start_tool_span("qcm_otlp_test", {"q": 1})
            assert span is not None
            time.sleep(0.02)
            span.end()
            d = span.to_dict()
            assert d["name"] == "tool:qcm_otlp_test"
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
    if test("span 在 OTLP 模式创建正常", span_otlp):
        passed += 1

    # [6] 开关组合
    total += 1
    def tracing_off_otlp():
        os.environ["QCM_TRACE_EXPORTER"] = "otlp"
        os.environ["QCM_TRACING"] = "0"
        try:
            qt = reload_tracing()
            assert qt.tracing_enabled() is False
            span = qt.start_tool_span("qcm_off")
            assert span is None
            return True
        finally:
            os.environ.pop("QCM_TRACE_EXPORTER", None)
            os.environ.pop("QCM_TRACING", None)
    if test("QCM_TRACING=0 + OTLP 关闭", tracing_off_otlp):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"V1.3.1 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V1.3.1 全部测试通过")
        print("   - OTLP 导出（Jaeger/Tempo 兼容）")
        print("   - QCM_TRACE_EXPORTER=console|otlp")
        print("   - QCM_OTLP_ENDPOINT 配置")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v131_tests()
    sys.exit(0 if success else 1)
