#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 词源语义协同工具集（V8.4 P3/P5 · 词源管理 #3 别名回灌 + M4 批量回源）

模块 A · 别名回灌（alias_sync）：Infoseek entity_aliases 归并结果 → QCM SYNONYM_MAP
模块 B · M4 批量回源（m4_backfill）：gap_tracker pending_infoseek 记录 → Infoseek 调研 → resolved

用法：
  python3 scripts/corpus_sync.py alias --check     # 探测 Infoseek 别名源可用性
  python3 scripts/corpus_sync.py alias --sync      # 同步别名 → SYNONYM_MAP（Infoseek 可用时）
  python3 scripts/corpus_sync.py m4 --status       # gap_tracker 待回源统计
  python3 scripts/corpus_sync.py m4 --dry-run      # 展示将回填的记录（不调用外部）
  python3 scripts/corpus_sync.py m4 --run          # 实际回填（Infoseek 可用时）

设计原则：
  - Infoseek = optional：不可用时全部优雅降级（显式提示 + 退出码 0），不崩溃
  - 对齐 §8.5 降级协议（L0 探测 → 可用才调外部，否则本地兜底）
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from paths import KEYWORD_YAML as KEYWORD  # V8.4 路径归一
GAP_TRACKER = ROOT / "references" / "gap_tracker.md"
# 跨 skill 探测（registry.find_skill 优先）
INFOSEEK_CANDIDATES = [
    os.environ.get("INFOSEEK_ROOT", ""),
    str(ROOT.parent / "infoseek"),
]


def probe_infoseek():
    """探测 Infoseek 安装路径（registry 优先，环境变量兜底）"""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from registry import find_skill
        p = find_skill("infoseek")
        if p:
            return Path(p)
    except Exception:
        pass
    for c in INFOSEEK_CANDIDATES:
        if c and (Path(c) / "core" / "entity_aliases.py").exists():
            return Path(c)
    return None


def alias_available() -> bool:
    p = probe_infoseek()
    return bool(p and (p / "core" / "entity_aliases.py").exists())


def alias_sync() -> dict:
    """同步 Infoseek 别名 → QCM SYNONYM_MAP（读 Infoseek alias 词典，合并入 keyword.yaml synonyms）"""
    import yaml
    p = probe_infoseek()
    if not p:
        return {"status": "skipped", "reason": "Infoseek 未安装（可选依赖 · 降级跳过）", "merged": 0}

    alias_file = p / "core" / "entity_aliases.py"
    if not alias_file.exists():
        return {"status": "skipped", "reason": f"Infoseek 别名模块缺失: {alias_file}", "merged": 0}

    # 解析 Infoseek alias 结构（启发式：提取 ALIASES 类数据）
    src = alias_file.read_text(encoding="utf-8")
    alias_groups = re.findall(r'["\']([^"\']{2,40})["\']\s*[:=]\s*(\[[^\]]{2,400}\])', src)
    if not alias_groups:
        return {"status": "skipped", "reason": "Infoseek 别名词典格式未匹配（保持 QCM 侧不变）", "merged": 0}

    data = yaml.safe_load(KEYWORD.read_text(encoding="utf-8")) or {}
    syn = data.setdefault("synonyms", {})
    merged = 0
    for main, alt_list in alias_groups:
        main = main.strip()
        if not main or main in syn:
            continue
        try:
            alts = [a.strip().strip("'\"") for a in re.findall(r'["\']([^"\']+)["\']', alt_list)]
            if alts and all(a != main for a in alts):
                syn[main] = [main] + alts
                merged += 1
        except Exception:
            continue

    if merged:
        KEYWORD.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return {"status": "synced" if merged else "no_new", "merged": merged, "total_groups": len(alias_groups)}


def gap_tracker_entries() -> list:
    """解析 gap_tracker.md 的 pending_infoseek 记录（按问题去重 · 同一缺口多次 L3 只记一条）"""
    if not GAP_TRACKER.exists():
        return []
    rows, seen = [], set()
    for line in GAP_TRACKER.read_text(encoding="utf-8").splitlines():
        if "pending_infoseek" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3:
                key = cells[1]  # 按问题去重
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"time": cells[0], "problem": cells[1], "dims": cells[2]})
    return rows


def m4_status() -> dict:
    entries = gap_tracker_entries()
    infoseek_ok = alias_available()
    return {"pending": len(entries), "entries": entries[:8],
            "infoseek_available": infoseek_ok}


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0

    mode = args[0]
    flag = args[1] if len(args) > 1 else ""

    if mode == "alias":
        if flag == "--check":
            ok = alias_available()
            print(f"别名回灌源探测: {'✅ Infoseek 可用' if ok else '❌ Infoseek 未安装（可选依赖 · QCM 独立运行）'}")
            return 0
        r = alias_sync()
        print(f"别名回灌: {r['status']}（合并 {r['merged']} 组"
              + (f" · 总组 {r['total_groups']}" if r.get("total_groups") else "")
              + (f" · {r['reason']}" if r.get("reason") else "") + "）")
        return 0

    if mode == "m4":
        st = m4_status()
        if flag == "--status":
            print(f"gap_tracker 待回源: {st['pending']} 条 · Infoseek {'可用' if st['infoseek_available'] else '不可用（降级：保留记录待安装后回填）'}")
            for e in st["entries"]:
                print(f"  - [{e['time']}] {e['problem']}（{e['dims']}）")
            return 0
        if flag == "--run":
            if not st["infoseek_available"]:
                print(f"ℹ️  Infoseek 未安装，跳过实际回填（{st['pending']} 条记录保留 · 安装后重跑 --run）")
                return 0
            # V8.4 B3 真实回填：归因调研 → conf≥70 → resolved（支持 limit 分批）
            limit = 0
            if len(args) > 2 and args[2].isdigit():
                limit = int(args[2])
            entries = st["entries"]  # 已按问题去重
            if limit > 0:
                entries = entries[:limit]
            if not entries:
                print("ℹ️  无待回填记录")
                return 0
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from infoseek_bridge import qcm_attribution
            resolved, kept, failed = [], [], 0
            for e in entries:
                try:
                    r = qcm_attribution(e["problem"], qcm_failure_dimensions=[e["dims"]])
                    conf = r.get("confidence_score", 0)
                    path = r.get("degradation_path", "?")
                    if conf >= 70:
                        resolved.append((e["problem"], conf, path))
                    else:
                        kept.append((e["problem"], conf, path))
                except Exception:
                    failed += 1
            print(f"M4 真实回填完成：{len(entries)} 条（limit={limit or '全部'}）"
                  f"· 达标 resolved {len(resolved)} · 保留 {len(kept)} · 失败 {failed}")
            for p, c, d in resolved[:5]:
                print(f"  ✅ [{c}] {p[:24]}（{d}）")
            for p, c, d in kept[:3]:
                print(f"  ⏭ [{c}] {p[:24]}（{d} · <70 保留）")
            # 更新 gap_tracker：resolved 记录标记（文本替换 pending_infoseek → resolved）
            if resolved:
                try:
                    text = GAP_TRACKER.read_text(encoding="utf-8")
                    for p, c, d in resolved:
                        text = text.replace(f"| {p} |", f"| {p} |", 1)  # 保留行结构
                    # 逐行：问题匹配则改状态（保守 · 仅改该问题首条 pending）
                    lines = text.splitlines()
                    changed = 0
                    resolved_problems = {p for p, _, _ in resolved}
                    for i, ln in enumerate(lines):
                        if "pending_infoseek" in ln and any(p in ln for p in resolved_problems):
                            lines[i] = ln.replace("pending_infoseek", f"resolved_L2")
                            changed += 1
                    GAP_TRACKER.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    print(f"  📝 gap_tracker 标记 {changed} 条 → resolved")
                except Exception as e:
                    print(f"  ⚠️  gap_tracker 更新失败: {e}")
            return 0
        # --dry-run 默认
        print(f"M4 批量回源 dry-run：{st['pending']} 条待回填（Infoseek 可用性={st['infoseek_available']}）")
        for e in st["entries"]:
            print(f"  - [{e['time']}] {e['problem']}")
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
