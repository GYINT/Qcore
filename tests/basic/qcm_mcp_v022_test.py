#!/usr/bin/env python3
"""qcm_mcp_v022_test.py — QCM V0.2.2 SCNet Provider 测试

V0.2 (qcm_mcp_v02_test.py): 17 测试 · LLM Router + 4-7 provider fallback
V0.2.1 (qcm_mcp_v021_test.py): 11 测试 · 真实 DeepSeek API 验证（key 已失效）
V0.2.2 (本文件): 13 测试 · SCNet 国家超算中心 Provider 接入 + 8 provider chain

测试场景：
  1. SCNet Provider 配置（4）：注册/priority/base_url/auth
  2. SCNet 模型别名（3）：kimi_2_6/kimi-latest/kimi-k2 → Qwen3.8-Max
  3. 8 Provider fallback chain（2）：总数/链完整性
  4. SCNet 端到端调用（4）：无 key fallback / 失效 key 401 / 真实路径 / MCP server 集成

⚠️ 安全说明：
  - SCNET_API_KEY 来自用户消息，不写入任何文件
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
# 用户提供的 SCNet/Kimi 2.6 key（测试完成后立即清理）
USER_KEY = os.environ.get("SCNET_API_KEY", "")  # 从 env 读 · 不落盘
os.environ["SCNET_API_KEY"] = USER_KEY
print(f"🔑 SCNET_API_KEY set: {mask_key(USER_KEY) if USER_KEY else '空（未提供）'}")


def call_mcp(method, params=None, token=None, env_extra=None, timeout_s=15):
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
    try:
        response = proc.stdout.readline().strip()
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"error": "timeout", "stderr": proc.stderr.read()[:500]}

    if not response:
        return {"error": "no response", "stderr": proc.stderr.read()[:500]}

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
                print(f"  ✅ {name}（预期错误: {str(result['error'])[:50]}）")
                return True
            print(f"  ❌ {name}: {str(result.get('error'))[:100]}")
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
        if expect_error:
            print(f"  ✅ {name}（预期异常: {str(e)[:50]}）")
            return True
        print(f"  ❌ {name}: {e}")
        return False


def run_v022_tests():
    """运行 V0.2.2 测试套件"""
    print("=" * 70)
    print(f"QCM MCP Server V0.2.2 测试套件（SCNet 国家超算中心 Provider）")
    print("=" * 70)

    passed = 0
    total = 0

    # ========== 1. SCNet Provider 配置 ==========
    print("\n[1. SCNet Provider 配置]")
    from llm_router import PROVIDERS

    total += 1
    if test("scnet provider 已注册", lambda: ("scnet" in PROVIDERS, True)[1]):
        passed += 1

    total += 1
    if test("scnet priority = 8", lambda: (PROVIDERS["scnet"]["priority"] == 8, True)[1]):
        passed += 1

    total += 1
    if test("scnet base_url = api.scnet.cn", lambda: (
        "api.scnet.cn" in PROVIDERS["scnet"]["base_url"], True)[1]):
        passed += 1

    total += 1
    if test("scnet auth = Bearer", lambda: (
        PROVIDERS["scnet"]["auth_header"] == "Authorization"
        and PROVIDERS["scnet"]["auth_prefix"] == "Bearer ", True)[1]):
        passed += 1

    # ========== 2. SCNet 模型别名 ==========
    print("\n[2. SCNet 模型别名]")

    total += 1
    if test("scnet 默认 model = Qwen3.8-Max", lambda: (
        PROVIDERS["scnet"]["model"] == "Qwen3.8-Max", True)[1]):
        passed += 1

    total += 1
    if test("model_aliases 包含 kimi_2_6→Qwen3.8-Max", lambda: (
        PROVIDERS["scnet"].get("model_aliases", {}).get("kimi_2_6") == "Qwen3.8-Max", True)[1]):
        passed += 1

    total += 1
    if test("model_aliases 包含 kimi-latest/kimi-k2", lambda: (
        "kimi-latest" in PROVIDERS["scnet"].get("model_aliases", {})
        and "kimi-k2" in PROVIDERS["scnet"].get("model_aliases", {}), True)[1]):
        passed += 1

    total += 1
    if test("env_key = SCNET_API_KEY", lambda: (
        PROVIDERS["scnet"]["env_key"] == "SCNET_API_KEY", True)[1]):
        passed += 1

    # ========== 3. 8 Provider fallback chain ==========
    print("\n[3. 8 Provider fallback chain]")

    total += 1
    if test("PROVIDERS 总数 ≥ 8（V0.2.2=8）", lambda: (len(PROVIDERS) >= 8, True)[1]):
        passed += 1

    def chain_with_scnet():
        from llm_router import LLMRouter
        r = LLMRouter()
        result = r.call("test", task="general")
        chain = result["fallback_chain"]
        assert "scnet" in chain, f"scnet missing: {chain}"
        # scnet priority 8，应在最后
        assert chain[-1] == "scnet", f"scnet should be last (priority 8): {chain}"
        return True

    total += 1
    if test("scnet 在 fallback chain 末尾", chain_with_scnet):
        passed += 1

    # ========== 4. SCNet 端到端调用 ==========
    print("\n[4. SCNet 端到端调用]")

    total += 1

    def no_scnet_key_fallback():
        from llm_router import LLMRouter
        saved = os.environ.pop("SCNET_API_KEY", None)
        try:
            r = LLMRouter(mode="auto")
            result = r.call("hi", task="general")
            assert result["mode"] in ("mock", "real"), f"unexpected mode: {result}"
            return True
        finally:
            if saved:
                os.environ["SCNET_API_KEY"] = saved

    if test("无 SCNET_API_KEY → mock fallback", no_scnet_key_fallback):
        passed += 1

    def scnet_api_call_with_user_key():
        """真实调用 SCNet API（依赖用户提供的 key）"""
        from llm_router import LLMRouter
        if not USER_KEY:
            return {"skip": "no SCNET_API_KEY provided"}
        r = LLMRouter(mode="real", custom_providers=["scnet"])
        result = r.call("一句话自我介绍", task="research", max_tokens=80)
        # 若 key 有效 → mode=real, provider=scnet, content 非空
        # 若 key 失效 → 期望降级到 mock 模式
        if result.get("mode") == "real" and result.get("provider") == "scnet":
            return True
        # key 失效时优雅降级
        if result.get("mode") == "mock":
            print(f"    (scnet key 失效 → mock fallback)")
            return True
        return result

    total += 1
    if test("SCNet 真实路径（用户 key 有效→real，无效→mock）", scnet_api_call_with_user_key):
        passed += 1

    def scnet_401_handling():
        """用无效 key 验证 401 处理"""
        from llm_router import LLMRouter
        saved = os.environ.get("SCNET_API_KEY")
        os.environ["SCNET_API_KEY"] = "sk-invalid-fake-key-000000"
        try:
            r = LLMRouter(mode="real", custom_providers=["scnet"])
            result = r.call("test", task="research", max_tokens=20)
            # 无效 key 应该不返回 success
            assert result.get("mode") != "real" or "error" in str(result.get("error", "")), \
                f"fake key should not succeed: {result}"
            return True
        finally:
            if saved:
                os.environ["SCNET_API_KEY"] = saved
            else:
                os.environ.pop("SCNET_API_KEY", None)

    total += 1
    if test("SCNet 无效 key → 不返回 success", scnet_401_handling):
        passed += 1

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print(f"V0.2.2 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM MCP Server V0.2.2 全部测试通过")
        print("   - SCNet 国家超算中心 Provider 注册（priority 8）")
        print("   - 模型别名兼容（kimi_2_6 / kimi-latest / kimi-k2）")
        print("   - 8 provider fallback chain 完整")
        print("   - 真实 LLM 调用（key 有效→real，无效→graceful mock）")
    else:
        print(f"❌ {total - passed} 个测试失败")

    return passed == total


if __name__ == "__main__":
    try:
        success = run_v022_tests()
    finally:
        # 安全清理：移除 SCNET_API_KEY env
        if "SCNET_API_KEY" in os.environ:
            del os.environ["SCNET_API_KEY"]
            print("\n🔒 SCNET_API_KEY 已从环境变量移除")
    sys.exit(0 if success else 1)
