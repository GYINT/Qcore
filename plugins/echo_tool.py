"""QCM 样例插件（演示插件扩展机制 · T-P1 建立）

机制：
  1. 插件文件放入 plugins/（.py，不以 _ 开头）
  2. 内部用 @register_tool 装饰器注册 MCP 工具
  3. qcm_mcp_server 启动时自动挂载（PluginLoader.load_all）

用法示例：本插件注册一个 echo 工具，可被 MCP 客户端调用。
"""
from mcp_server import register_tool


@register_tool(
    name="qcm_plugin_echo",
    description="QCM 插件样例：回显输入文本（验证插件扩展链路）",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要回显的文本"},
        },
        "required": ["text"],
    },
)
def echo_tool(text: str) -> dict:
    """回显工具：验证插件从 plugins/ 加载并注册到 TOOL_REGISTRY"""
    return {"echo": text, "plugin": "echo_tool", "status": "ok"}
