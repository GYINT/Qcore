#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 大语料懒加载读取器（P2-8）

替代"激活即全量读入"：按锚点/关键词按需读取大语料片段。

用法：
  from corpus_loader import load_section, search_corpus, list_anchors

  load_section("tools.md", "A01. SPC 统计过程控制") # 返回该章节文本
  search_corpus("双归零")                             # 跨 4 大文件关键词定位
  list_anchors("masters.md")                          # 锚点清单（标题/行号/行数）
"""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "references" / "index"

# 大语料文件映射（stem → 相对路径）
CORPUS_FILES = {
    "tools": "references/tools/tools.md",
    "knowledge-base": "references/knowledge/knowledge-base.md",
    "masters": "references/tools/masters.md",
    "cases": "references/scenarios/cases.md",
}

_LINE_CACHE = {}
_INDEX_CACHE = {}


def _load_index(stem: str) -> dict:
    if stem in _INDEX_CACHE:
        return _INDEX_CACHE[stem]
    idx_path = INDEX_DIR / f"{stem}.index.yaml"
    if not idx_path.exists():
        return {}
    data = {}
    anchors = []
    current = None
    for ln in idx_path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s.startswith("file: "):
            data["file"] = s[6:].strip()
        elif s.startswith("anchor_count: "):
            data["anchor_count"] = int(s[14:].strip())
        elif s.startswith("- {title:"):
            # 解析 {title: xxx, level: N, line: N, end_line: N, lines: N}
            m = re.match(r"- \{title: (.+), level: (\d+), line: (\d+), end_line: (\d+), lines: (\d+)\}", s)
            if m:
                anchors.append({
                    "title": m.group(1), "level": int(m.group(2)),
                    "line": int(m.group(3)), "end_line": int(m.group(4)),
                    "lines": int(m.group(5)),
                })
    data["anchors"] = anchors
    _INDEX_CACHE[stem] = data
    return data


def _load_lines(stem: str) -> list:
    if stem in _LINE_CACHE:
        return _LINE_CACHE[stem]
    rel = CORPUS_FILES.get(stem)
    if not rel:
        return []
    path = ROOT / rel
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    _LINE_CACHE[stem] = lines
    return lines


def list_anchors(stem: str) -> list:
    """返回锚点清单 [{title, level, line, end_line, lines}]"""
    data = _load_index(stem)
    return data.get("anchors", [])


def load_section(stem: str, title: str) -> str:
    """按标题（支持模糊匹配）读取章节片段。未命中返回空串。"""
    anchors = list_anchors(stem)
    if not anchors:
        return ""
    # 精确匹配优先，其次包含匹配
    hit = None
    for a in anchors:
        if a["title"] == title:
            hit = a
            break
    if hit is None:
        for a in anchors:
            if title in a["title"] or a["title"] in title:
                hit = a
                break
    if hit is None:
        return ""
    lines = _load_lines(stem)
    seg = lines[hit["line"] - 1: hit["end_line"]]
    return "\n".join(seg)


def search_corpus(keyword: str, max_hits: int = 5) -> list:
    """跨大语料关键词搜索，返回 [{file, line, text}]"""
    results = []
    kw = keyword.lower()
    for stem, rel in CORPUS_FILES.items():
        lines = _load_lines(stem)
        for i, ln in enumerate(lines):
            if kw in ln.lower():
                results.append({"file": rel, "line": i + 1, "text": ln.strip()[:120]})
                if len(results) >= max_hits:
                    return results
    return results


def total_sections(stem: str) -> int:
    """锚点数（用于统计/报告）"""
    return len(list_anchors(stem))
