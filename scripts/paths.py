#!/usr/bin/env python3
"""QCM 统一路径解析器（重组后 · 动态自适应 · 消灭硬编码）

 变更（2026-08-18 文件分类分层重组）：
  - references/ 细分 12 子目录 → 路径常量更新
  - 核心模块移入 core/ → 新增 CORE 常量 + sys.path 注入
  - 测试移入 tests/ → TESTS 指向根级 tests/

解析优先级（三层）：
  1. env QCM_ROOT（用户/部署显式指定，最高优先）
  2. 自身位置推导（paths.py 位于 scripts/ → parent.parent = Skill 根）
  3. 默认本体路径（兜底，兼容未设 env 的部署）

用法：
  from paths import ROOT, CORE, REFERENCES, COMPONENTS, OUTPUTS, SCRIPTS, TESTS, PLUGINS
"""
import os
import sys
from pathlib import Path

# ── 三层解析 ──

def _resolve_root() -> Path:
    """解析 QCM 根目录：env > 自身推导 > 默认"""
    env = os.environ.get("QCM_ROOT")
    if env:
        return Path(env).resolve()
    # 自身推导：本文件在 <root>/scripts/ → parent.parent = root
    return Path(__file__).resolve().parent.parent


ROOT = _resolve_root()

# ── 一级目录常量（单点真源 · 重组） ──
CORE = ROOT / "core"
REFERENCES = ROOT / "references"
COMPONENTS = ROOT / "components"
OUTPUTS = ROOT / "outputs"
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
ARCHIVE = ROOT / "archive"
PLUGINS = ROOT / "plugins"
DEPLOY = ROOT / "deploy"
DOMAINS = ROOT / "domains"
DOCS = ROOT / "docs"

# ── references/ 细分子目录 ──
REF_PROTOCOL = REFERENCES / "protocol"
REF_CONFIG = REFERENCES / "config"
REF_TOOLS = REFERENCES / "tools"
REF_SCENARIOS = REFERENCES / "scenarios"
REF_METHODS = REFERENCES / "methods"
REF_PEOPLE = REFERENCES / "people"
REF_CONTRACT = REFERENCES / "contract"
REF_GOVERNANCE = REFERENCES / "governance"
REF_KNOWLEDGE = REFERENCES / "knowledge"
REF_TESTING = REFERENCES / "testing"
REF_PLANNING = REFERENCES / "planning"
REF_PROMPTS = REFERENCES / "prompts"

# ── 关键文件（路径更新） ──
SKILL_MD = ROOT / "SKILL.md"
MANIFEST_YAML = ROOT / "manifest.yaml"
KEYWORD_YAML = REF_CONFIG / "keyword.yaml"
CONSTRAINT_MAP = REF_CONFIG / "constraint.yaml"
COMPONENTS_MANIFEST = REF_CONFIG / "components.yaml"
VALIDATOR_CONFIG = REF_CONFIG / "validator.yaml"
ROLE_CONFIG = REF_CONFIG / "role.yaml"
ENTITIES_YAML = REF_CONFIG / "entities.yaml"  # V8.4 P1：实体索引（标准/大师/方法）
ACTION_ORDERS = REF_PROTOCOL / "action-orders.md"
FILE_MANIFEST = ROOT / ".file-manifest.yaml"


def ensure_dirs() -> None:
    """确保关键目录存在（幂等）"""
    for d in (CORE, REFERENCES, COMPONENTS, OUTPUTS, SCRIPTS, PLUGINS,
              DEPLOY, DOMAINS, DOCS, TESTS, ARCHIVE):
        d.mkdir(parents=True, exist_ok=True)


def setup_sys_path() -> None:
    """统一 sys.path 注入：core/ 与 scripts/ 加入模块搜索路径。

    重组后 import 约定：
      from router import route          # core/（原 qcm_router）
      from validator import ...         # core/（原 qcm_output_validator）
      from paths import ROOT            # scripts/（原 qcm_paths）
      from registry import find_skill   # scripts/（原 skill_registry）
      from mcp_server import ...        # scripts/（原 qcm_mcp_server）
    """
    for d in (str(CORE), str(SCRIPTS)):
        if d not in sys.path:
            sys.path.insert(0, d)


setup_sys_path()


if __name__ == "__main__":
    print(f"ROOT        = {ROOT}")
    print(f"CORE        = {CORE}")
    print(f"REFERENCES  = {REFERENCES}")
    print(f"COMPONENTS  = {COMPONENTS}")
    print(f"OUTPUTS     = {OUTPUTS}")
    print(f"SCRIPTS     = {SCRIPTS}")
    print(f"TESTS       = {TESTS}")
    print(f"PLUGINS     = {PLUGINS}")
    print(f"KEYWORD     = {KEYWORD_YAML}")
    print(f"ACTION      = {ACTION_ORDERS}")
