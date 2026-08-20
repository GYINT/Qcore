#!/usr/bin/env python3
"""qcm_mcp_v06_test.py — QCM V0.6 YAML Config + Plugin + Provider + Docker 测试

V0.6 任务清单：
  1. YAML Config 文件（qcm_config.yaml）
  2. Plugin 系统（动态加载 tool）
  3. 3 新 Provider（Ollama / Azure OpenAI / LM Studio）
  4. WebSocket transport（可选 · 本测试跳过）
  5. Docker 镜像（构建测试 · 本测试跳过实际构建）
  6. Docker Compose（文件存在性验证）

测试场景（18）：
  YAML Config（4）：
    - 默认配置加载
    - 点路径访问 config.get()
    - 环境变量替换 ${VAR}
    - 缺字段用默认值

  Plugin 系统（5）：
    - 发现 plugin 文件
    - 加载 plugin + 注册 tool
    - 调用 plugin tool
    - 热重载
    - 加载错误隔离

  Provider（5）：
    - 7 个 provider 配置完整
    - Ollama 配置正确
    - Azure OpenAI URL 模板
    - LM Studio 配置
    - Provider fallback chain

  Docker（4）：
    - Dockerfile 存在
    - requirements.txt 存在
    - docker-compose.yml 存在
    - prometheus.yml 存在
"""
import os
import sys
import tempfile
import subprocess
from pathlib import Path

QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(QCM_ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

from mcp_server import register_tool


def test(name, fn, expect_error=False):
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


def run_v06_tests():
    print("=" * 70)
    print(f"QCM MCP Server V0.6 测试（YAML Config + Plugin + Provider + Docker）")
    print("=" * 70)

    passed = 0
    total = 0

    # ========== 1. YAML Config（4） ==========
    print("\n[1. YAML Config]")

    def config_default():
        from config import config, DEFAULT_CONFIG
        cfg = config.load()
        assert cfg["server"]["transport"] == "stdio"
        assert cfg["server"]["port"] == 8080
        assert cfg["providers"]["deepseek"]["enabled"] is True
        return True

    total += 1
    if test("默认配置加载", config_default):
        passed += 1

    def config_dot_path():
        from config import config
        assert config.get("server.port") == 8080
        assert config.get("providers.ollama.base_url") == "http://localhost:11434/v1"
        assert config.get("nonexistent.key", "default") == "default"
        return True

    total += 1
    if test("点路径访问", config_dot_path):
        passed += 1

    def config_env_vars():
        os.environ["QCM_TEST_VAR"] = "test-value-12345"
        from config import ConfigLoader
        loader = ConfigLoader()
        # 创建一个临时 YAML 文件含 ${VAR}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("server:\n  host: ${QCM_TEST_VAR}\n")
            tmpfile = f.name
        loader.config_path = tmpfile
        cfg = loader.load(force=True)
        os.unlink(tmpfile)
        assert cfg["server"]["host"] == "test-value-12345"
        return True

    total += 1
    if test("环境变量替换 ${VAR}", config_env_vars):
        passed += 1

    def config_defaults_merge():
        # 用户配置只有部分字段，应合并默认值
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("server:\n  port: 9090\n")  # 只覆盖 port
            tmpfile = f.name
        from config import ConfigLoader
        loader = ConfigLoader()
        loader.config_path = tmpfile
        cfg = loader.load(force=True)
        os.unlink(tmpfile)
        assert cfg["server"]["port"] == 9090  # 用户覆盖
        assert cfg["server"]["transport"] == "stdio"  # 默认值
        return True

    total += 1
    if test("缺字段用默认值", config_defaults_merge):
        passed += 1

    # ========== 2. Plugin 系统（5） ==========
    print("\n[2. Plugin 系统]")

    def plugin_discover():
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 2 个 plugin 文件 + 1 个非 plugin
            for name in ["plugin_a.py", "plugin_b.py", "_skip.py", "readme.md"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    f.write("# stub")

            from plugin import PluginLoader
            loader = PluginLoader(tmpdir)
            plugins = loader.discover()
            assert len(plugins) == 2  # _skip.py 和 readme.md 被过滤
            return True

    total += 1
    if test("发现 plugin 文件（过滤 _ 开头）", plugin_discover):
        passed += 1

    def plugin_load_and_register():
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 plugin 文件，注册一个 tool
            plugin_code = '''
from mcp_server import register_tool

@register_tool(
    name="v06_test_plugin_tool",
    description="V0.6 test plugin",
    input_schema={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
)
def v06_test_plugin_tool(x: str) -> dict:
    return {"result": f"plugin: {x}"}
'''
            plugin_path = os.path.join(tmpdir, "test_plugin.py")
            with open(plugin_path, "w") as f:
                f.write(plugin_code)

            from plugin import PluginLoader
            from mcp_server import TOOL_REGISTRY
            # 确保 tool 不存在
            if "v06_test_plugin_tool" in TOOL_REGISTRY:
                del TOOL_REGISTRY["v06_test_plugin_tool"]

            loader = PluginLoader(tmpdir)
            tools = loader.load_all()
            assert "v06_test_plugin_tool" in TOOL_REGISTRY
            return True

    total += 1
    if test("加载 plugin + 注册 tool", plugin_load_and_register):
        passed += 1

    def plugin_call_tool():
        # 调用上面注册的 tool
        from mcp_server import TOOL_REGISTRY
        if "v06_test_plugin_tool" not in TOOL_REGISTRY:
            # 先加载
            plugin_load_and_register()
        handler = TOOL_REGISTRY["v06_test_plugin_tool"]["handler"]
        result = handler(x="hello")
        assert result == {"result": "plugin: hello"}
        return True

    total += 1
    if test("调用 plugin tool", plugin_call_tool):
        passed += 1

    def plugin_hot_reload():
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_code = '''
from mcp_server import register_tool

@register_tool(name="v06_hot_reload_tool", description="Hot reload test",
               input_schema={"type": "object"})
def v06_hot_reload_tool() -> dict:
    return {"v": "1"}
'''
            plugin_path = os.path.join(tmpdir, "hot.py")
            with open(plugin_path, "w") as f:
                f.write(plugin_code)

            from plugin import PluginLoader
            from mcp_server import TOOL_REGISTRY
            if "v06_hot_reload_tool" in TOOL_REGISTRY:
                del TOOL_REGISTRY["v06_hot_reload_tool"]

            loader = PluginLoader(tmpdir)
            loader.load_all()
            assert "v06_hot_reload_tool" in TOOL_REGISTRY

            # 修改 plugin
            plugin_code2 = plugin_code.replace('"1"', '"2"')
            with open(plugin_path, "w") as f:
                f.write(plugin_code2)

            loader.hot_reload()
            # tool 应该重新加载（但因为 name 相同，handler 被覆盖）
            assert "v06_hot_reload_tool" in TOOL_REGISTRY
            handler = TOOL_REGISTRY["v06_hot_reload_tool"]["handler"]
            result = handler()
            assert result == {"v": "2"}, f"Expected v=2, got {result}"
            return True

    total += 1
    if test("热重载 plugin", plugin_hot_reload):
        passed += 1

    def plugin_error_isolation():
        with tempfile.TemporaryDirectory() as tmpdir:
            # 错误 plugin
            bad_plugin = "raise SyntaxError('intentional error')"
            with open(os.path.join(tmpdir, "bad.py"), "w") as f:
                f.write(bad_plugin)
            # 正常 plugin
            good_plugin = '''
from mcp_server import register_tool

@register_tool(name="v06_good_plugin", description="Good",
               input_schema={"type": "object"})
def v06_good_plugin() -> dict:
    return {"ok": True}
'''
            with open(os.path.join(tmpdir, "good.py"), "w") as f:
                f.write(good_plugin)

            from plugin import PluginLoader
            from mcp_server import TOOL_REGISTRY
            if "v06_good_plugin" in TOOL_REGISTRY:
                del TOOL_REGISTRY["v06_good_plugin"]

            loader = PluginLoader(tmpdir)
            tools = loader.load_all()  # 应该忽略 bad.py 但加载 good.py
            # 错误隔离：good plugin 应该成功加载
            assert "v06_good_plugin" in TOOL_REGISTRY
            return True

    total += 1
    if test("错误隔离（坏 plugin 不影响好的）", plugin_error_isolation):
        passed += 1

    # ========== 3. Provider（5） ==========
    print("\n[3. Provider]")

    def provider_count():
        from llm_router import PROVIDERS
        # V0.2.2 起 ≥7（V0.6 加 SCNet 后 = 8）
        assert len(PROVIDERS) >= 7, f"providers < 7: {len(PROVIDERS)}"
        return True

    total += 1
    if test("≥7 个 provider 配置完整（V0.2.2 SCNet = 8）", provider_count):
        passed += 1

    def provider_ollama():
        from llm_router import PROVIDERS
        ollama = PROVIDERS["ollama"]
        assert "ollama" in PROVIDERS
        assert ollama["base_url"] == "http://localhost:11434/v1"
        assert ollama["priority"] == 5
        return True

    total += 1
    if test("Ollama 配置正确", provider_ollama):
        passed += 1

    def provider_azure():
        from llm_router import PROVIDERS
        azure = PROVIDERS["azure_openai"]
        assert "azure_openai" in PROVIDERS
        assert "${AZURE_OPENAI_ENDPOINT}" in azure["base_url"]
        assert azure["auth_header"] == "api-key"
        return True

    total += 1
    if test("Azure OpenAI URL 模板 + api-key 认证", provider_azure):
        passed += 1

    def provider_lm_studio():
        from llm_router import PROVIDERS
        lm = PROVIDERS["lm_studio"]
        assert lm["base_url"] == "http://localhost:1234/v1"
        assert lm["priority"] == 7
        return True

    total += 1
    if test("LM Studio 配置", provider_lm_studio):
        passed += 1

    def provider_fallback_chain():
        from llm_router import LLMRouter
        r = LLMRouter()
        result = r.call("test", task="general", max_tokens=5)
        chain = result["fallback_chain"]
        # V0.2.2 软断言：chain 含 7 原有 + scnet 末尾
        assert len(chain) >= 7, f"chain < 7: {chain}"
        assert chain[0] == "deepseek"  # priority 1 仍居首
        assert "ollama" in chain, f"ollama missing: {chain}"
        assert "azure_openai" in chain
        assert "lm_studio" in chain
        assert "scnet" in chain, f"scnet missing: {chain}"
        assert chain.index("deepseek") < chain.index("qwen")
        assert chain.index("qwen") < chain.index("scnet")
        return True

    total += 1
    if test("≥7 Provider fallback chain（V0.2.2 scnet 末尾）", provider_fallback_chain):
        passed += 1

    # ========== 4. Docker（4） ==========
    print("\n[4. Docker 文件]")

    def dockerfile_exists():
        assert os.path.exists(os.path.join(QCM_ROOT, "deploy", "docker", "Dockerfile"))
        return True

    total += 1
    if test("Dockerfile 存在", dockerfile_exists):
        passed += 1

    def requirements_exists():
        assert os.path.exists(os.path.join(QCM_ROOT, "requirements.txt"))
        with open(os.path.join(QCM_ROOT, "requirements.txt")) as f:
            content = f.read()
        assert "PyYAML" in content
        return True

    total += 1
    if test("requirements.txt 含 PyYAML", requirements_exists):
        passed += 1

    def compose_exists():
        assert os.path.exists(os.path.join(QCM_ROOT, "deploy", "docker", "docker-compose.yml"))
        with open(os.path.join(QCM_ROOT, "deploy", "docker", "docker-compose.yml")) as f:
            content = f.read()
        assert "qcm-mcp:" in content
        assert "prometheus:" in content
        assert "grafana:" in content
        return True

    total += 1
    if test("docker-compose.yml 含 3 service", compose_exists):
        passed += 1

    def prometheus_config_exists():
        assert os.path.exists(os.path.join(QCM_ROOT, "deploy", "monitoring", "prometheus.yml"))
        with open(os.path.join(QCM_ROOT, "deploy", "monitoring", "prometheus.yml")) as f:
            content = f.read()
        assert "qcm-mcp:8080" in content
        assert "metrics_path" in content
        return True

    total += 1
    if test("prometheus.yml 含 qcm-mcp 抓取配置", prometheus_config_exists):
        passed += 1

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print(f"V0.6 测试结果：{passed}/{total} 通过")
    if passed == total:
        print("✅ QCM MCP Server V0.6 全部测试通过")
        print("   - YAML Config：默认/点路径/${VAR}/缺字段")
        print("   - Plugin 系统：发现/加载/调用/热重载/错误隔离")
        print("   - 7 Provider（4 原有 + 3 新增）")
        print("   - Docker 配置文件齐全")
    else:
        print(f"❌ {total - passed} 个测试失败")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = run_v06_tests()
    sys.exit(0 if success else 1)