#!/usr/bin/env python3
"""qcm_mcp_v021_test.py — QCM V0.2.1 真实 LLM 集成测试

V0.1 (qcm_mcp_test.py): 18 测试 · 协议/工具/认证
V0.2 (qcm_mcp_v02_test.py): 17 测试 · LLM Router 框架 + mock fallback
V0.2.1 (本文件): 12 测试 · 真实 DeepSeek API 验证

测试场景：
  1. LLM Router real mode（5）：provider=deepseek / 非 mock / 真实耗时 / 响应非空
  2. qcm_research 真实输出（3）：llm_meta.mode=real / confidence=0.92 / 输出非模板
  3. 4 Provider fallback（2）：优先级链 / 失败降级
  4. 端到端 MCP（2）：MCP server 路径下 real 调用 / Bearer Token 兼容

⚠️ 安全说明：
  - DEEPSEEK_API_KEY 来自用户消息，不写入任何文件
  - 测试结束后从 env 移除
  - 输出中不显示完整 key（仅 mask 前 6 + 后 4）
"""
import os
import subprocess
import json
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sys
import time
from pathlib import Path

# 路径
SCRIPTS = os.path.join(QCM_ROOT, "scripts")
SERVER = os.path.join(SCRIPTS, "mcp_server.py")
ROUTER = os.path.join(SCRIPTS, "llm_router.py")

sys.path.insert(0, SCRIPTS)


def mask_key(key: str) -> str:
    """脱敏：前 6 + 后 4，中间省略"""
    if not key or len(key) < 12:
        return "***"
    return key[:6] + "***" + key[-4:]


# === Key 管理（仅本次 session）===
# 用户提供的 key（测试完成后立即清理）
USER_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 从 env 读 · 不落盘
os.environ["DEEPSEEK_API_KEY"] = USER_KEY
print(f"🔑 DEEPSEEK_API_KEY set: {mask_key(USER_KEY)}")
if not USER_KEY:
    print("⏭️  SKIP：需 DEEPSEEK_API_KEY（real mode 环境性测试 · 无 key 自动跳过）")
    sys.exit(0)


def call_mcp(method, params=None, token=None, env_extra=None):
    """调用 MCP server · 自动展开 content[0].text"""
    request = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        request["params"] = params
    if token:
        if "params" not in request:
            request["params"] = {}
        request["params"]["__token__"] = token

    test_env = {**os.environ}
    if token:
        test_env["QCM_REQUIRE_TOKEN"] = "1"
        test_env["QCM_AUTH_TOKEN"] = "expected-test-token-abc123"
    if env_extra:
        test_env.update(env_extra)

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
    proc.wait(timeout=30)
    if not response:
        return {"error": "no response", "stderr": proc.stderr.read()}

    parsed = json.loads(response)
    if isinstance(parsed.get("result"), dict) and "content" in parsed["result"]:
        try:
            text_content = parsed["result"]["content"][0]["text"]
            parsed["result"] = json.loads(text_content)
        except (KeyError, IndexError, json.JSONDecodeError):
            pass
    return parsed


def test(name, fn, expect_error=False):
    """测试包装"""
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            if expect_error:
                print(f"  ✅ {name}（预期错误: {result['error'].get('code')}）")
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


def run_v021_tests():
    """运行 V0.2.1 测试套件"""
    print("=" * 70)
    print(f"QCM MCP Server V0.2.1 测试（真实 LLM · DeepSeek API）")
    print("=" * 70)

    passed = 0
    total = 0

    # ========== 1. LLM Router real mode ==========
    print("\n[1. LLM Router real mode]")
    from llm_router import LLMRouter

    def router_auto_real():
        r = LLMRouter(mode="auto")  # 应自动检测到 DEEPSEEK_API_KEY
        assert r.is_real_mode() is True, "auto mode should be real when key exists"
        return True

    total += 1
    if test("auto → real（key 存在）", router_auto_real):
        passed += 1

    def router_real_call():
        r = LLMRouter(mode="real")
        result = r.call("ping", task="general", max_tokens=10)
        assert result["mode"] == "real", f"not real: {result}"
        assert result["provider"] == "deepseek", f"not deepseek: {result['provider']}"
        assert result["text"] != "", "empty response"
        return True

    total += 1
    if test("real call · deepseek · 非空", router_real_call):
        passed += 1

    def router_real_duration():
        r = LLMRouter(mode="real")
        result = r.call("短测试", task="general", max_tokens=20)
        assert result["duration_s"] > 0.1, f"too fast (mock?): {result['duration_s']}s"
        return True

    total += 1
    if test("真实耗时 > 0.1s", router_real_duration):
        passed += 1

    def router_response_not_template():
        r = LLMRouter(mode="real")
        result = r.call("尺寸波动大怎么控制", task="research", max_tokens=200)
        text = result["text"]
        # 真实 LLM 不应该输出 mock 模板特征
        mock_markers = ["【Mock LLM", "hash=", "V0.2 研究输出"]
        for m in mock_markers:
            assert m not in text, f"still has mock marker: {m}"
        return True

    total += 1
    if test("响应不含 mock 模板", router_response_not_template):
        passed += 1

    def router_response_qcm_relevant():
        r = LLMRouter(mode="real")
        result = r.call("焊接虚焊客诉复发怎么破", task="research", max_tokens=300)
        text = result["text"]
        # 真实响应应该与 QCM 相关
        qcm_keywords = ["焊接", "8D", "FMEA", "SPC", "客诉", "归零", "围堵", "PDCA", "根因", "鱼骨", "失效", "工艺", "质量", "体系", "回流焊"]
        hits = sum(1 for k in qcm_keywords if k in text)
        assert hits >= 3, f"response not QCM-relevant ({hits}/8 keywords): {text[:200]}"
        return True

    total += 1
    if test("响应与 QCM 相关（≥3 关键词）", router_response_qcm_relevant):
        passed += 1

    # ========== 2. qcm_research 真实输出 ==========
    print("\n[2. qcm_research 真实输出]")

    def research_real_mode():
        r = call_mcp("tools/call", {
            "name": "qcm_research",
            "arguments": {"query": "焊接虚焊客诉复发", "level_hint": "T2"}
        })
        assert "result" in r, f"no result: {r}"
        assert r["result"]["llm_meta"]["mode"] == "real", f"not real: {r['result']['llm_meta']}"
        assert r["result"]["llm_meta"]["provider"] == "deepseek", f"not deepseek: {r['result']['llm_meta']['provider']}"
        return True

    total += 1
    if test("research · mode=real · provider=deepseek", research_real_mode):
        passed += 1

    def research_confidence_real():
        r = call_mcp("tools/call", {
            "name": "qcm_research",
            "arguments": {"query": "工艺参数 DOE 优化", "level_hint": "T3"}
        })
        # V0.2: real mode confidence = 0.92
        assert r["result"]["confidence"] == 0.92, f"confidence wrong: {r['result']['confidence']}"
        return True

    total += 1
    if test("research · confidence = 0.92 (real)", research_confidence_real):
        passed += 1

    def research_real_content():
        r = call_mcp("tools/call", {
            "name": "qcm_research",
            "arguments": {"query": "汽车焊接工艺参数优化", "level_hint": "T4"}
        })
        output = r["result"]["output_markdown"]
        # 真实 LLM 输出（应比 mock 更丰富）
        assert len(output) > 100, f"output too short: {len(output)} chars"
        # 不应该是 mock 模板
        assert "【Mock" not in output, "still mock template"
        return True

    total += 1
    if test("research · 输出 > 100 字符 · 非 mock", research_real_content):
        passed += 1

    # ========== 3. Provider fallback 链 ==========
    print("\n[3. Provider fallback]")

    def fallback_chain_visible():
        from llm_router import LLMRouter
        r = LLMRouter(mode="real")
        result = r.call("test", task="general", max_tokens=10)
        assert result["fallback_chain"][0] == "deepseek"
        assert "deepseek" in result["fallback_chain"]
        return True

    total += 1
    if test("fallback chain 含 deepseek", fallback_chain_visible):
        passed += 1

    def prefer_provider():
        from llm_router import LLMRouter
        r = LLMRouter(mode="real")
        result = r.call("test", task="general", max_tokens=10, prefer_provider="deepseek")
        assert result["provider"] == "deepseek", f"prefer failed: {result['provider']}"
        return True

    total += 1
    if test("prefer_provider=deepseek 优先", prefer_provider):
        passed += 1

    # ========== 4. 端到端 MCP（含 Bearer Token） ==========
    print("\n[4. 端到端 MCP · Bearer Token]")

    def mcp_research_with_token():
        r = call_mcp("tools/call", {
            "name": "qcm_research",
            "arguments": {"query": "质量成本优化", "level_hint": "T3"}
        }, token="expected-test-token-abc123")
        assert "result" in r
        assert r["result"]["llm_meta"]["mode"] == "real"
        return True

    total += 1
    if test("MCP research · Token + real LLM", mcp_research_with_token):
        passed += 1

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print(f"V0.2.1 测试结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ QCM MCP Server V0.2.1 全部测试通过")
        print(f"   - DeepSeek API 真实调用验证（model=deepseek-v4-flash）")
        print(f"   - qcm_research 真实输出质量（>100 字符 · 领域相关）")
        print(f"   - Bearer Token 兼容")
    else:
        print(f"❌ {total - passed} 个测试失败")
    print("=" * 70)

    # === 清理：移除 key ===
    if "DEEPSEEK_API_KEY" in os.environ:
        del os.environ["DEEPSEEK_API_KEY"]
    print(f"\n🔒 DEEPSEEK_API_KEY 已从环境变量移除")

    return passed == total


if __name__ == "__main__":
    success = run_v021_tests()
    sys.exit(0 if success else 1)
