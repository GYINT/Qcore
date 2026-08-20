#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 大语料索引生成器（P2-8 懒加载支撑）

扫描大语料文件（>30KB），为每个生成锚点索引 yaml：
  references/index/<name>.index.yaml

用法：
  python3 scripts/gen_corpus_index.py            # 全量（4 大文件）
  python3 scripts/gen_corpus_index.py --check    # 仅校验索引新鲜度（mtime）
"""
import os
import re
import sys
import io
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "references" / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# 大语料清单（>30KB 单体文件 · 激活即全量读入风险）
CORPUS = [
    ("references/tools/tools.md", "工具库（SPC/防错/8D 等 90+ 工具实例）"),
    ("references/knowledge/knowledge-base.md", "知识库（案例集/外部素材）"),
    ("references/tools/masters.md", "大师库（21 位质量大师心智模型）"),
    ("references/scenarios/cases.md", "案例库（双归零/行业案例）"),
]

HEADING = re.compile(r"^(#{1,3})\s+(.+)$")


def gen_index(rel: str, note: str) -> Path:
    src = ROOT / rel
    if not src.exists():
        print(f"⚠ 跳过（不存在）: {rel}")
        return None
    lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
    # 收集标题行
    heads = []  # (line_no_0based, level, title)
    for i, ln in enumerate(lines):
        m = HEADING.match(ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
    if not heads:
        print(f"⚠ 无标题结构: {rel}")
        return None
    # 计算区间：标题 → 下一个同级或更高级标题前
    anchors = []
    for idx, (i, lvl, title) in enumerate(heads):
        end = len(lines)
        for j in range(idx + 1, len(heads)):
            if heads[j][1] <= lvl:  # 同级或更高级
                end = heads[j][0]
                break
        anchors.append({
            "title": title,
            "level": lvl,
            "line": i + 1,
            "end_line": end,
            "lines": end - i,
        })
    data = {
        "file": rel,
        "note": note,
        "size_bytes": src.stat().st_size,
        "size_kb": round(src.stat().st_size / 1024, 1),
        "anchor_count": len(anchors),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "anchors": anchors,
    }
    out = INDEX_DIR / (src.stem + ".index.yaml")
    # 手写 yaml（避免 PyYAML 依赖 · 结构简单）
    buf = [f"# QCM 大语料索引（自动生成 · 勿手改）", f"file: {rel}",
           f"note: {note}", f"size_bytes: {data['size_bytes']}",
           f"size_kb: {data['size_kb']}", f"anchor_count: {data['anchor_count']}",
           f"generated: {data['generated']}", "anchors:"]
    for a in anchors:
        buf.append(f"  - {{title: {_yaml_str(a['title'])}, level: {a['level']}, line: {a['line']}, end_line: {a['end_line']}, lines: {a['lines']}}}")
    out.write_text("\n".join(buf) + "\n", encoding="utf-8")
    print(f"✅ {rel} → {out.relative_to(ROOT)}（{len(anchors)} 锚点 · {data['size_kb']}KB）")
    return out


def _yaml_str(s: str) -> str:
    s = s.replace('"', "'").replace("{", "（").replace("}", "）").replace(":", "：")
    return s


def check_freshness() -> int:
    stale = 0
    for rel, _note in CORPUS:
        src = ROOT / rel
        idx = INDEX_DIR / (src.stem + ".index.yaml")
        if not idx.exists():
            print(f"⚠ 索引缺失: {rel}")
            stale += 1
        elif idx.stat().st_mtime < src.stat().st_mtime:
            print(f"⚠ 索引过期（源文件更新）: {rel}")
            stale += 1
    if stale == 0:
        print("✅ 索引全部新鲜")
    return stale


def main():
    if "--check" in sys.argv:
        return 1 if check_freshness() else 0
    for rel, note in CORPUS:
        gen_index(rel, note)
    print(f"\n索引目录: {INDEX_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
