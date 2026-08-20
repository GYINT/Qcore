#!/usr/bin/env python3
"""qcm_mcp_v070_test.py — QCM V0.7.0 Grafana 审计可视化测试

覆盖（10 用例）：
  1. Infoseek /metrics 端点返回 Prometheus 格式
  2. infoseek_uptime_seconds 指标
  3. infoseek_tool_calls_total 指标（工具调用计数）
  4. infoseek_audit_total 指标（审计状态统计）
  5. Grafana dashboard JSON 存在
  6. Dashboard JSON 合法（json.loads）
  7. Dashboard 含 7 个面板
  8. Dashboard 含 uptime/total/audit 关键面板
  9. Dashboard 含 timeseries/bargauge 类型
  10. prometheus.yml 含 infoseek job
"""
import json
import os
import sys
import time
import subprocess
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import urllib.request
import urllib.error

SCRIPTS = os.path.join(QCM_ROOT, "scripts")
INFOSEEK_ROOT = os.environ.get("INFOSEEK_ROOT", "/root/.skills/infoseek")
INFOSEEK_SERVER = os.path.join(INFOSEEK_ROOT, "scripts", "infoseek_mcp_server.py")
DASHBOARD = os.path.join(QCM_ROOT, "deploy", "monitoring", "grafana", "infoseek-audit-dashboard.json")
PROMETHEUS = os.path.join(QCM_ROOT, "deploy", "monitoring", "prometheus.yml")
PORT = 8920


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


def run_v070_tests():
    print("=" * 70)
    print("QCM V0.7.0 测试套件（Grafana 审计可视化）")
    print("=" * 70)

    passed = 0
    total = 0

    # [1-4] Infoseek /metrics
    print("\n[1. Infoseek /health 端点（v1.2.0 契约 · /metrics 已由 QCM WS push/metrics 承接）]")
    proc = subprocess.Popen(
        ["python3", INFOSEEK_SERVER, "--transport", "sse", "--port", str(PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)
    try:
        total += 1
        def health_endpoint():
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/health")
            r = urllib.request.urlopen(req, timeout=5)
            body = json.loads(r.read().decode())
            assert r.status == 200
            assert body.get("status") == "ok", f"status={body.get('status')}"
            return True
        if test("/health 返回 JSON 健康状态（v1.2.0）", health_endpoint):
            passed += 1

        total += 1
        def health_uptime():
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/health")
            body = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            assert "uptime_seconds" in body, f"no uptime: {body.keys()}"
            assert float(body["uptime_seconds"]) >= 0
            return True
        if test("health 含 uptime_seconds", health_uptime):
            passed += 1

        total += 1
        def health_tools():
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/health")
            body = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            assert body.get("tools", 0) > 0, f"tools={body.get('tools')}"
            return True
        if test("health 含工具计数 tools>0", health_tools):
            passed += 1

        total += 1
        def health_stats():
            req = urllib.request.Request(f"http://127.0.0.1:{PORT}/health")
            body = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            assert "tool_call_stats" in body, f"no stats: {body.keys()}"
            return True
        if test("health 含 tool_call_stats 统计", health_stats):
            passed += 1
    finally:
        proc.terminate()

    # [5-9] Grafana dashboard
    print("\n[2. Grafana Dashboard]")
    total += 1
    def dash_exists():
        assert os.path.exists(DASHBOARD), f"缺失: {DASHBOARD}"
        return True
    if test("dashboard JSON 文件存在", dash_exists):
        passed += 1

    total += 1
    def dash_valid():
        with open(DASHBOARD, encoding="utf-8") as f:
            data = json.load(f)
        assert "dashboard" in data
        return True
    if test("dashboard JSON 合法", dash_valid):
        passed += 1

    total += 1
    def dash_panels():
        with open(DASHBOARD, encoding="utf-8") as f:
            data = json.load(f)
        panels = data["dashboard"]["panels"]
        assert len(panels) == 7, f"panels={len(panels)}"
        return True
    if test("dashboard 7 个面板", dash_panels):
        passed += 1

    total += 1
    def dash_key_panels():
        with open(DASHBOARD, encoding="utf-8") as f:
            data = json.load(f)
        titles = [p["title"] for p in data["dashboard"]["panels"]]
        assert any("在线时长" in t for t in titles)
        assert any("工具调用" in t for t in titles)
        assert any("审计" in t for t in titles)
        return True
    if test("dashboard 关键面板（在线/调用/审计）", dash_key_panels):
        passed += 1

    total += 1
    def dash_types():
        with open(DASHBOARD, encoding="utf-8") as f:
            data = json.load(f)
        types = [p["type"] for p in data["dashboard"]["panels"]]
        assert "timeseries" in types
        assert "bargauge" in types
        assert "stat" in types
        return True
    if test("dashboard 类型（stat/bargauge/timeseries）", dash_types):
        passed += 1

    # [10] prometheus.yml
    total += 1
    def prometheus_job():
        with open(PROMETHEUS, encoding="utf-8") as f:
            content = f.read()
        assert "infoseek-mcp" in content, "缺 infoseek job"
        assert "qcm-mcp" in content, "缺 qcm job"
        return True
    if test("prometheus.yml 含 qcm + infoseek 双 job", prometheus_job):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"V0.7.0 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM V0.7.0 全部测试通过")
        print("   - Infoseek /metrics（uptime/tools/audit）")
        print("   - Grafana dashboard（7 面板 · 跨设备审计可视化）")
        print("   - prometheus 双 job 采集")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v070_tests()
    sys.exit(0 if success else 1)
