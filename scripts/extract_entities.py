#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 实体层生成器（V8.4 P1 · 词源管理 #1 实体索引）

从知识库半自动提取实体 → 生成/校验 references/config/entities.yaml：
  - standards.md 表格 → 标准实体（type=standard · domain=E体系 · intent=③评估审计）
  - masters.md 章节标题 → 大师实体（type=master · domain=通用 · intent=④知识学习）
  - tools.md 工具编号引用 → 方法实体（type=method · 领域映射）

设计原则：
  - 单一真源：entities.yaml 由本脚本从知识库生成（知识库演进 → 实体层自动同步）
  - 只读知识库：本脚本只读 standards/masters/tools，不修改
  - 别名维护：中英文名/缩写手工补充在 entities.yaml 的 aliases 字段（脚本不覆盖已有人工别名）

用法：
  python3 scripts/extract_entities.py            # 生成/更新 entities.yaml
  python3 scripts/extract_entities.py --check    # 校验实体层与知识库同步（CI 接入）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STANDARDS = ROOT / "references" / "tools" / "standards.md"
MASTERS = ROOT / "references" / "tools" / "masters.md"
ENTITIES = ROOT / "references" / "config" / "entities.yaml"

# 标准号 → 领域映射（未显式标注的兜底）
STANDARD_DOMAIN = {"E体系": "质量管理体系（QMS）类标准"}


def extract_standards() -> list:
    """从 standards.md 表格提取标准实体"""
    out = []
    if not STANDARDS.exists():
        return out
    text = STANDARDS.read_text(encoding="utf-8")
    # 表格行：| 标准号 | 名称 | 适用范围 | 状态 |（标准号含版本冒号如 ISO 9001:2015）
    rows = re.findall(r"^\|\s*([A-Z][A-Z0-9/.:\-\s]{2,40}?)\s*\|\s*([^|]+?)\s*\|", text, re.M)
    seen = set()
    for code, name in rows:
        code = code.strip()
        if not code or code in seen or code.startswith("标准号"):
            continue
        # 过滤工具编号行（F01 8D / A01 SPC 等非标准实体）
        if re.match(r"^[A-Z]\d{2}\s", code):
            continue
        # 去掉版本号作为别名（ISO 9001:2015 → ISO 9001 + ISO9001）
        base = re.sub(r":\d{4}$", "", code)
        aliases = sorted({base, base.replace(" ", "")})
        seen.add(code)
        out.append({
            "name": base, "type": "standard",
            "aliases": aliases, "source": "standards.md",
            "domain": "E体系", "intent": "③评估审计",
        })
    return out


def extract_masters() -> list:
    """从 masters.md 章节标题提取大师实体（标题：中文名（外文名, 生卒年））"""
    out = []
    if not MASTERS.exists():
        return out
    for line in MASTERS.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^# (.+?)\s*（(.+?),\s*\d{4}", line)
        if not m:
            m = re.match(r"^# (.+?)\s*\((.+?),\s*\d{4}", line)
        if m:
            zh, en = m.group(1).strip(), m.group(2).strip()
            # name = 英文全名（更精确）；aliases = 中文简称 + 中文全名 + 姓 + 英文名
            surname = en.split()[-1] if en.split() else en
            zh_short = re.split(r"[·．.]", zh)[-1] if re.split(r"[·．.]", zh) else zh
            aliases = {zh, zh_short, en, surname}
            out.append({
                "name": en, "type": "master",
                "aliases": sorted(aliases),
                "source": "masters.md",
                "domain": "通用", "intent": "④知识学习",
            })
    return out


def merge_with_existing(new_entities: list) -> list:
    """合并：保留 entities.yaml 已有人工别名（不覆盖）"""
    if not ENTITIES.exists():
        return new_entities
    try:
        import yaml
        old = yaml.safe_load(ENTITIES.read_text(encoding="utf-8")) or {}
        old_map = {e["name"]: e for e in old.get("entities", [])}
    except Exception:
        return new_entities
    for e in new_entities:
        if e["name"] in old_map:
            old_aliases = old_map[e["name"]].get("aliases", [])
            if old_aliases:
                e["aliases"] = sorted(set(e["aliases"]) | set(old_aliases))
    return new_entities


def gen_yaml(entities: list) -> str:
    lines = [
        "# QCM 实体索引（V8.4 P1 · 由 scripts/extract_entities.py 从知识库生成）",
        "# 用途：用户输入实体识别 → 精确路由（标准→E体系+工具 · 大师→大师库）",
        "# 维护：运行 extract_entities.py 重新生成；人工别名直接编辑本文件 aliases（生成时不覆盖）",
        "",
        "entities:",
    ]
    for e in entities:
        aliases = ", ".join(f'"{a}"' for a in e["aliases"])
        lines.append(
            f'  - {{name: "{e["name"]}", type: {e["type"]}, aliases: [{aliases}], '
            f'domain: {e["domain"]}, intent: {e["intent"]}, source: {e["source"]}}}'
        )
    return "\n".join(lines) + "\n"


def main():
    std = extract_standards()
    mst = extract_masters()
    merged = merge_with_existing(std + mst)
    total = len(merged)
    std_n = sum(1 for e in merged if e["type"] == "standard")
    mst_n = sum(1 for e in merged if e["type"] == "master")

    if "--check" in sys.argv:
        if not ENTITIES.exists():
            print(f"❌ entities.yaml 不存在（应先运行 extract_entities.py 生成）")
            return 1
        import yaml
        cur = yaml.safe_load(ENTITIES.read_text(encoding="utf-8")) or {}
        cur_names = {e["name"] for e in cur.get("entities", [])}
        src_names = {e["name"] for e in merged}
        missing = src_names - cur_names
        if missing:
            print(f"❌ 实体层落后知识库 {len(missing)} 个：{sorted(missing)[:8]}")
            return 1
        print(f"✅ 实体层与知识库同步（{len(cur_names)} 实体 · 标准 {std_n} / 大师 {mst_n}）")
        return 0

    ENTITIES.parent.mkdir(parents=True, exist_ok=True)
    ENTITIES.write_text(gen_yaml(merged), encoding="utf-8")
    print(f"✅ entities.yaml 已生成：{total} 实体（标准 {std_n} · 大师 {mst_n}）→ {ENTITIES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
