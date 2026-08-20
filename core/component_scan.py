#!/usr/bin/env python3
"""QCM 组件热度扫描工具（热门组件复用识别）
机制：扫描 references/config/constraint.yaml 引用 → 统计组件 ref_count → 热度分级（复用 §11 状态机）
输出：复用 TOP 榜 + 低复用告警（0-1 消费 → 评估合并）+ 容量校验（≤35）
用法：python3 core/component_scan.py
"""
import os
import sys
from collections import Counter

QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_mapping_refs() -> Counter:
    """从 references/config/constraint.yaml 提取 mapping 段 components 引用。"""
    refs = Counter()
    path = os.path.join(QCM_ROOT, "references", "config", "constraint.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"约束映射文件缺失: {path}")
    in_mapping = False
    collecting = False
    buf = ""
    with open(path, encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if s.startswith("mapping:"):
                in_mapping = True
                continue
            if not in_mapping:
                continue
            if s.startswith("components:"):
                buf = s.split(":", 1)[1].strip()
                collecting = True
            elif collecting:
                buf += " " + s
            if collecting and "]" in buf:
                for c in _split_comps(buf):
                    refs[c] += 1
                collecting = False
    return refs


def _split_comps(s: str) -> list:
    """解析 components: [_meta, _route, ...] 列表。"""
    s = s.strip().strip("[]").strip()
    return [x.strip() for x in s.split(",") if x.strip().startswith("_")]


def extract_components() -> dict:
    """从 references/config/components.yaml 提取 {组件名: status}（V8.3.0 路径修正）。"""
    comps = {}
    path = os.path.join(QCM_ROOT, "references", "config", "components.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"组件注册表缺失: {path}")
    name, status = None, "defined"
    with open(path, encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if s.startswith("_") and ":" in s and not s.startswith("#"):
                if name:
                    comps[name] = status
                name = s.split(":", 1)[0].strip()
                status = "defined"
            elif s.startswith("status:"):
                status = s.split(":", 1)[1].strip().strip('"').strip("'")
        if name:
            comps[name] = status
    return comps


def grade(ref_count: int, status: str) -> str:
    """热度分级（复用 §11 状态机）。"""
    if status == "archived":
        return "archived"
    if status == "new":
        return "new"
    if ref_count >= 3:
        return "stable"
    if ref_count >= 2:
        return "active"
    return "new"  # 1 消费 = 待观察


def main():
    refs = extract_mapping_refs()
    manifest = extract_components()
    print("=" * 60)
    print(f"QCM 组件热度扫描（{len(manifest)} 组件 · 容量约束 ≤35）")
    print("=" * 60)
    print(f"\n复用 TOP 榜（ref_count ≥2）：")
    top = [(c, n) for c, n in refs.most_common() if n >= 2]
    for c, n in sorted(top, key=lambda x: -x[1]):
        st = manifest.get(c, "未注册!")
        print(f"  {c:<24} {n} 消费  [{grade(n, st)}]")
    print(f"\n低复用告警（ref_count ≤1 · 评估合并）：")
    low = [c for c in manifest if refs.get(c, 0) <= 1 and manifest[c] != "new"]
    for c in sorted(low):
        print(f"  {c:<24} {refs.get(c, 0)} 消费  [评估合并候选]")
    print(f"\n未消费组件（mapping 未引用）：")
    unused = [c for c in manifest if refs.get(c, 0) == 0]
    for c in sorted(unused):
        print(f"  {c:<24} 0 消费")
    print(f"\n容量：{len(manifest)}/35 {'✅' if len(manifest) <= 35 else '❌ 超限'}")
    missing = [c for c in refs if c not in manifest]
    if missing:
        print(f"❌ 悬空引用（mapping 引用但未注册）：{missing}")
        return 1
    print("✅ 引用闭合（mapping ⊆ manifest）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
