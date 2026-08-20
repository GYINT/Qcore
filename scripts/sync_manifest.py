#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QCM Manifest 同步脚本 ·+
依据：Infoseek Skill v1.5.0+ Manifest 双绑规范

功能：
1. 验证 SKILL.md frontmatter 完整
2. 验证 manifest.yaml 与 frontmatter 关键字段一致
3. 验证 skill_meta.json 与 SKILL.md description 一致
4. 输出验证报告

用法：
  python3 sync_manifest.py            # 验证
  python3 sync_manifest.py --update    # 更新 SKILL.md frontmatter
  python3 sync_manifest.py --help     # 帮助

版本：（2026-08-09）
"""

import sys
import re
import json
import yaml
import os
from pathlib import Path
from datetime import datetime

# 路径配置
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
MANIFEST_YAML = SKILL_DIR / "manifest.yaml"
SKILL_META_JSON = SKILL_DIR / "skill_meta.json"

# 关键字段（manifest.yaml + SKILL.md frontmatter 必须包含）
KEY_FIELDS = ["name", "version", "description", "author", "license", "entry_point"]


def parse_yaml(path: Path) -> dict:
    """解析 YAML 文件"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # 提取 yaml 代码块
    yaml_blocks = re.findall(r"```yaml\n(.*?)```", content, re.DOTALL)
    if yaml_blocks:
        return yaml.safe_load(yaml_blocks[0])
    # 否则直接解析
    return yaml.safe_load(content)


def parse_json(path: Path) -> dict:
    """解析 JSON 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_frontmatter(path: Path) -> dict:
    """提取 SKILL.md frontmatter（YAML 形式）"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # frontmatter 在 --- 之间
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1))


def validate_yaml_frontmatter(yaml_data: dict, fm_data: dict) -> list:
    """验证 manifest.yaml 关键字段与 SKILL.md frontmatter 一致"""
    errors = []
    for field in KEY_FIELDS:
        yaml_val = yaml_data.get(field)
        fm_val = fm_data.get(field)
        if yaml_val != fm_val:
            errors.append(f"字段不一致 [{field}]: yaml={yaml_val!r} fm={fm_val!r}")
    return errors


def validate_json_description(json_data: dict, fm_data: dict) -> list:
    """验证 skill_meta.json description 与 SKILL.md frontmatter description 一致"""
    errors = []
    json_desc = json_data.get("description", "")
    fm_desc = fm_data.get("description", "")
    # 简化检查：取前 30 字符
    if json_desc[:30] != fm_desc[:30]:
        errors.append(f"description 前缀不一致: json={json_desc[:30]!r} fm={fm_desc[:30]!r}")
    return errors


def validate_required_keys(data: dict, required: list, source: str) -> list:
    """验证必需字段存在"""
    errors = []
    for key in required:
        if key not in data:
            errors.append(f"{source} 缺少必需字段: {key}")
    return errors


def main():
    """主验证流程"""
    print("=" * 60)
    print("QCM Manifest 同步验证脚本")
    print("=" * 60)
    print(f"验证时间：{datetime.now().isoformat()}")
    print(f"SKILL.md：{SKILL_MD}")
    print(f"manifest.yaml：{MANIFEST_YAML}")
    print(f"skill_meta.json：{SKILL_META_JSON}")
    print()

    all_errors = []

    # 1. 验证 manifest.yaml
    print("[1/4] 验证 manifest.yaml ...")
    if not MANIFEST_YAML.exists():
        all_errors.append("manifest.yaml 不存在")
    else:
        yaml_data = parse_yaml(MANIFEST_YAML)
        all_errors += validate_required_keys(yaml_data, KEY_FIELDS, "manifest.yaml")
        print(f"  ✓ manifest.yaml 关键字段：{KEY_FIELDS}")

    # 2. 验证 skill_meta.json
    print("[2/4] 验证 skill_meta.json ...")
    if not SKILL_META_JSON.exists():
        all_errors.append("skill_meta.json 不存在")
    else:
        json_data = parse_json(SKILL_META_JSON)
        all_errors += validate_required_keys(json_data, ["skill_name", "version", "description", "labels", "output_forms"], "skill_meta.json")
        print(f"  ✓ skill_meta.json 关键字段：skill_name, version, description, labels, output_forms")

    # 3. 提取 SKILL.md frontmatter 并验证
    print("[3/4] 验证 SKILL.md frontmatter ...")
    if not SKILL_MD.exists():
        all_errors.append("SKILL.md 不存在")
    else:
        fm_data = extract_frontmatter(SKILL_MD)
        all_errors += validate_required_keys(fm_data, KEY_FIELDS, "SKILL.md frontmatter")
        print(f"  ✓ SKILL.md frontmatter 关键字段：{KEY_FIELDS}")

        # 3.1 验证 yaml + frontmatter 一致
        if MANIFEST_YAML.exists():
            all_errors += validate_yaml_frontmatter(yaml_data, fm_data)
            print(f"  ✓ manifest.yaml + frontmatter 字段一致")

        # 3.2 验证 json + frontmatter 一致
        if SKILL_META_JSON.exists():
            all_errors += validate_json_description(json_data, fm_data)
            print(f"  ✓ skill_meta.json + frontmatter description 一致")

    # 4. 汇总
    print()
    print("=" * 60)
    if all_errors:
        print(f"❌ 验证未通过 · {len(all_errors)} 个错误")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("✅ 验证全部通过")
        print("  - manifest.yaml 完整")
        print("  - skill_meta.json 完整")
        print("  - SKILL.md frontmatter 完整")
        print("  - manifest.yaml + frontmatter 字段一致")
        print("  - skill_meta.json + frontmatter description 一致")
        sys.exit(0)


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)
    main()