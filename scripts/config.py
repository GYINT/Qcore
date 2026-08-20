#!/usr/bin/env python3
"""qcm_config.py — QCM MCP YAML Config Loader

功能：
  - 加载 YAML config 文件
  - 环境变量替换 ${VAR} 语法
  - 默认配置 fallback
  - Schema 验证（缺字段用默认值）
  - 热重载（mtime 检测）

支持配置项：
  server: transport / host / port / auth
  corpus: references_dir / outputs_dir
  providers: priority / enabled / api_key / base_url
  tools: enabled / custom plugins
  rate_limit: per_ip / per_token / global
  audit: log_dir / max_size_mb
  logging: level / format / audit_dir

用法：
  from config import config
  print(config.get("server.port"))
"""
import os
import re
import time
import threading
from typing import Any, Dict, Optional

# 归一化：路径统一由 qcm_paths 解析（消灭硬编码）
from paths import REFERENCES, OUTPUTS, PLUGINS


# ============ 默认配置 ============
DEFAULT_CONFIG = {
    "server": {
        "transport": "stdio",  # or "http"
        "host": "127.0.0.1",
        "port": 8080,
        "auth": {
            "require_token": False,
            "token_env": "QCM_AUTH_TOKEN",
        },
    },
    "corpus": {
        "references_dir": str(REFERENCES),
        "outputs_dir": str(OUTPUTS),
    },
    "providers": {
        "deepseek": {"priority": 1, "enabled": True, "api_key_env": "DEEPSEEK_API_KEY"},
        "openai":   {"priority": 2, "enabled": True, "api_key_env": "OPENAI_API_KEY"},
        "claude":   {"priority": 3, "enabled": True, "api_key_env": "ANTHROPIC_API_KEY"},
        "qwen":     {"priority": 4, "enabled": True, "api_key_env": "DASHSCOPE_API_KEY"},
        # 新增
        "ollama":   {"priority": 5, "enabled": True, "api_key_env": "OLLAMA_KEY",
                     "base_url": "http://localhost:11434/v1", "model": "llama3"},
        "azure_openai": {"priority": 6, "enabled": False,
                         "api_key_env": "AZURE_OPENAI_API_KEY",
                         "endpoint_template": "${AZURE_OPENAI_ENDPOINT}/openai/deployments/${AZURE_DEPLOYMENT}",
                         "model": "gpt-4o"},
        "lm_studio": {"priority": 7, "enabled": True, "api_key_env": "LM_STUDIO_KEY",
                      "base_url": "http://localhost:1234/v1", "model": "local-model"},
    },
    "tools": {
        "enabled": [
            "qcm_research", "qcm_score_source", "qcm_decide",
            "qcm_solve_problem", "qcm_audit", "qcm_validate",
        ],
        "custom_plugins_dir": str(PLUGINS),
    },
    "rate_limit": {
        "per_ip": 100,
        "per_ip_window_s": 60,
        "per_token": 1000,
        "per_token_window_s": 3600,
        "global_limit": 10000,
        "global_window_s": 60,
    },
    "audit": {
        "log_dir": "/tmp/qcm-mcp-audit",
        "max_size_mb": 100,
    },
    "logging": {
        "level": "info",  # debug/info/warning/error
        "format": "json",  # json or text
    },
}


class ConfigLoader:
    """YAML config 加载器（懒加载 + 热重载）"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.environ.get("QCM_CONFIG", "qcm_config.yaml")
        self._config: Dict = {}
        self._mtime: float = 0
        self._lock = threading.Lock()

    def load(self, force: bool = False) -> Dict[str, Any]:
        """加载配置（自动检测变化）"""
        with self._lock:
            if not force and self._config and self._is_fresh():
                return self._config

            self._config = self._load_yaml()
            self._mtime = self._get_mtime() if os.path.exists(self.config_path) else 0
            return self._config

    def _is_fresh(self) -> bool:
        """检查文件是否有更新"""
        if not os.path.exists(self.config_path):
            return True
        return self._get_mtime() == self._mtime

    def _get_mtime(self) -> float:
        try:
            return os.path.getmtime(self.config_path)
        except OSError:
            return 0

    def _load_yaml(self) -> Dict[str, Any]:
        """加载 YAML 文件（环境变量替换 + 默认值填充）"""
        config = self._deep_copy(DEFAULT_CONFIG)

        if not os.path.exists(self.config_path):
            return config

        try:
            import yaml  # PyYAML（stdlib 之外的依赖）
        except ImportError:
            # 降级：手写简单 YAML 解析（仅支持 key: value）
            yaml_data = self._simple_yaml_parse()
        else:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = self._replace_env_vars(content)
            yaml_data = yaml.safe_load(content) or {}

        # 深度合并
        self._deep_merge(config, yaml_data)

        return config

    def _simple_yaml_parse(self) -> Dict:
        """简化的 YAML 解析（仅 1 层 key: value）"""
        result = {}
        if not os.path.exists(self.config_path):
            return result
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if ":" in line:
                        key, _, value = line.partition(":")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        value = os.environ.expandvars(value)
                        if value.lower() in ("true", "false"):
                            value = value.lower() == "true"
                        elif value.isdigit():
                            value = int(value)
                        result[key] = value
        except Exception:
            pass
        return result

    def _replace_env_vars(self, content: str) -> str:
        """替换 ${VAR} → 环境变量值"""
        pattern = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")

        def replacer(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))

        return pattern.sub(replacer, content)

    def _deep_merge(self, target: Dict, source: Dict):
        """深度合并 dict（source 覆盖 target）"""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _deep_copy(self, obj):
        """深度复制"""
        import copy
        return copy.deepcopy(obj)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（点路径，如 'server.port'）"""
        config = self.load()
        keys = key.split(".")
        current = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current


# 全局实例
config = ConfigLoader()


if __name__ == "__main__":
    # Demo
    print("=== 默认配置 ===")
    cfg = config.load()
    print(f"  server.transport: {cfg['server']['transport']}")
    print(f"  server.port: {cfg['server']['port']}")
    print(f"  providers.deepseek.enabled: {cfg['providers']['deepseek']['enabled']}")
    print(f"  providers.ollama.base_url: {cfg['providers']['ollama']['base_url']}")
    print()
    print("=== 点路径访问 ===")
    print(f"  config.get('server.port'): {config.get('server.port')}")
    print(f"  config.get('providers.ollama.base_url'): {config.get('providers.ollama.base_url')}")
    print(f"  config.get('nonexistent.key', 'default'): {config.get('nonexistent.key', 'default')}")