#!/usr/bin/env python3
"""qcm_plugin.py — QCM MCP Plugin System

动态加载 tool 插件：
  - 自动发现 plugins/ 目录下的 .py 文件
  - 每个 plugin 可注册多个 tool
  - Plugin 用 @register_tool 装饰器（来自 mcp_server）

Plugin 文件示例（plugins/my_company_tool.py）：
  from mcp_server import register_tool

  @register_tool(
      name="my_custom_tool",
      description="公司自定义工具",
      input_schema={"type": "object", "properties": {...}, "required": [...]}
  )
  def my_custom_tool(arg1: str) -> dict:
      return {"result": f"处理 {arg1}"}

用法：
  from plugin import PluginLoader
  loader = PluginLoader("/path/to/plugins")
  tools = loader.load_all() # 返回 ["my_custom_tool", ...]
"""
import os
import sys
import importlib.util
import logging
from typing import List, Optional


class PluginLoader:
    """Plugin 动态加载器"""

    def __init__(self, plugins_dir: str, logger=None):
        self.plugins_dir = plugins_dir
        self.logger = logger or logging.getLogger(__name__)
        self._loaded_modules = {}

    def discover(self) -> List[str]:
        """发现 plugin 文件（.py，不含 _ 开头的）"""
        if not os.path.isdir(self.plugins_dir):
            return []
        plugins = []
        for fname in sorted(os.listdir(self.plugins_dir)):
            if fname.endswith(".py") and not fname.startswith("_"):
                plugins.append(os.path.join(self.plugins_dir, fname))
        return plugins

    def load_all(self, force: bool = False) -> List[str]:
        """加载所有 plugin，返回注册的工具名列表"""
        loaded_tools = []
        for plugin_path in self.discover():
            try:
                tool_names = self.load_one(plugin_path, force=force)
                loaded_tools.extend(tool_names)
                self.logger.info(f"Loaded plugin: {plugin_path} → {tool_names}")
            except Exception as e:
                self.logger.error(f"Failed to load plugin {plugin_path}: {e}")
        return loaded_tools

    def load_one(self, plugin_path: str, force: bool = False) -> List[str]:
        """加载单个 plugin"""
        if not force and plugin_path in self._loaded_modules:
            return []

        # 清理可能的缓存
        module_name = os.path.basename(plugin_path).replace(".py", "")
        if module_name in sys.modules:
            del sys.modules[module_name]

        # 修复：直接 compile + exec（SourceFileLoader 会缓存源，导致 hot reload 失效）
        with open(plugin_path, "r", encoding="utf-8") as f:
            source = f.read()
        code = compile(source, plugin_path, "exec")

        module = type(sys)(module_name)
        module.__file__ = plugin_path
        sys.modules[module_name] = module
        exec(code, module.__dict__)

        self._loaded_modules[plugin_path] = module
        self.logger.info(f"Plugin loaded: {plugin_path}")

        # 返回注册的工具（从 qcm_mcp_server.TOOL_REGISTRY）
        from mcp_server import TOOL_REGISTRY
        return [name for name in TOOL_REGISTRY.keys() if not name.startswith("_")]

    def hot_reload(self) -> List[str]:
        """热重载（清空已加载模块 + 重新加载）"""
        # 1. 快照旧模块（V8.3.2 T2：先快照再清空，修复空遍历导致 sys.modules 清理失效）
        old_modules = list(self._loaded_modules.items())
        # 2. 清空本地缓存
        self._loaded_modules = {}
        # 3. 清理 sys.modules（按已加载 plugin 的模块名）
        for plugin_path, module in old_modules:
            module_name = os.path.basename(plugin_path).replace(".py", "")
            if module_name in sys.modules:
                del sys.modules[module_name]
        # 4. 额外清理（兜底 · 含 plugin/qcm_plugin 关键字）
        for key in list(sys.modules.keys()):
            if any(p in key for p in ["plugin", "qcm_plugin"]):
                del sys.modules[key]
        # 5. 重新加载
        return self.load_all()

    def list_loaded(self) -> List[str]:
        """返回已加载的 plugin 路径"""
        return list(self._loaded_modules.keys())


if __name__ == "__main__":
    # Demo: 创建临时 plugin 测试
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建示例 plugin
        plugin_code = '''
from mcp_server import register_tool

@register_tool(
    name="demo_plugin_tool",
    description="Demo plugin tool",
    input_schema={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
)
def demo_plugin_tool(x: str) -> dict:
    return {"result": f"plugin got: {x}"}
'''
        plugin_path = os.path.join(tmpdir, "demo_plugin.py")
        with open(plugin_path, "w") as f:
            f.write(plugin_code)

        # 加载 plugin
        loader = PluginLoader(tmpdir)
        tools = loader.load_all()
        print(f"Loaded tools: {tools}")

        # 调用插件工具
        from mcp_server import TOOL_REGISTRY
        if "demo_plugin_tool" in TOOL_REGISTRY:
            result = TOOL_REGISTRY["demo_plugin_tool"]["handler"](x="hello")
            print(f"Tool result: {result}")