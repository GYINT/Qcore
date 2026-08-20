#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 热词生命周期执行器（V8.4 P5 · 词源管理 #2 生命周期状态机）

§11.2 五态状态机的代码化执行器：新建 → 活跃 → 稳定 → 归档 → 淘汰
驱动信号：状态元数据（status）+ 容量约束（意图≤40/领域≤20）+ 词龄/命中（可选元数据）

用法：
  python3 scripts/keyword_lifecycle.py --check    # CI 健康检查（0 严重即绿）
  python3 scripts/keyword_lifecycle.py --report   # 状态分布 + 迁移建议（dry-run）
  python3 scripts/keyword_lifecycle.py --promote  # 实际执行迁移（写回 keyword.yaml）

设计原则：
  - 只读检查默认安全（--check/--report 不改文件）；--promote 显式写回
  - 迁移规则对齐 §11.2（new→active→stable→archived→淘汰）
  - 防御性：无元数据（created_at/hit_count_30d）的词不强行迁移，仅提示
"""
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
from paths import KEYWORD_YAML as KEYWORD  # V8.4 路径归一

# 生命周期迁移规则（天数阈值 · 与 §11.2 对齐）
RULE = {
    "new_to_active_days": 14,        # 新建满 14 天 → 活跃
    "active_to_stable_days": 30,     # 活跃满 30 天 → 稳定
    "stable_archive_miss_days": 90,  # 稳定连续 90 天无命中 → 归档候选
    "archive_retention_cycles": 2,   # 归档保留 2 个周期 → 淘汰
}
# 容量上限（对齐 router.py 容量约束）
CAP_INTENT = 40
CAP_DOMAIN = 20


def load():
    import yaml
    data = yaml.safe_load(KEYWORD.read_text(encoding="utf-8")) or {}
    items = data.get("keywords", [])
    for it in items:
        it.setdefault("status", "new")
        it.setdefault("level", "base")
    return data, items


def stats(items):
    """状态分布 + 容量 + 年龄"""
    dist = {}
    for it in items:
        dist[it["status"]] = dist.get(it["status"], 0) + 1

    intent_cnt, domain_cnt = {}, {}
    for it in items:
        if it.get("status") == "archived":
            continue  # V8.4 P5：archived 退出活跃路由，不计容量
        if it.get("intent"):
            intent_cnt[it["intent"]] = intent_cnt.get(it["intent"], 0) + 1
        if it.get("domain"):
            domain_cnt[it["domain"]] = domain_cnt.get(it["domain"], 0) + 1

    # 词龄（created_at 元数据存在时）
    today = datetime.now().date()
    aged = {"new": [], "active": []}
    for it in items:
        ca = it.get("created_at")
        if ca and it["status"] in ("new", "active"):
            try:
                d = datetime.strptime(ca, "%Y-%m-%d").date()
                aged[it["status"]].append((it["word"], (today - d).days))
            except Exception:
                pass

    return dist, intent_cnt, domain_cnt, aged


def check():
    """CI 健康检查：容量超限（严重）+ 状态异常（严重）+ 迁移候选（警告）"""
    try:
        data, items = load()
    except Exception as e:
        print(f"❌ keyword.yaml 加载失败: {e}")
        return 2

    dist, intent_cnt, domain_cnt, aged = stats(items)
    issues, warns = [], []

    # ① 容量检查（严重 · 仅统计活跃词：archived 退出路由后不计入）
    for intent, cnt in sorted(intent_cnt.items()):
        if cnt > CAP_INTENT:
            issues.append(f"❌ 意图 {intent} 活跃词数 {cnt} 超限（上限 {CAP_INTENT}）——需淘汰/归档")
    for dom, cnt in sorted(domain_cnt.items()):
        if cnt > CAP_DOMAIN:
            warns.append(f"⚠️  领域 {dom} 词数 {cnt} 超限（上限 {CAP_DOMAIN}）")

    # ② 状态异常（严重）
    valid = {"new", "active", "stable", "archived"}
    for it in items:
        if it["status"] not in valid:
            issues.append(f"❌ 词 {it['word']} 状态非法: {it['status']}（合法: {valid}）")

    # ③ 迁移候选（警告 · dry-run）
    for status, limit in (("new", RULE["new_to_active_days"]), ("active", RULE["active_to_stable_days"])):
        for word, age in aged.get(status, []):
            if age >= limit:
                target = "active" if status == "new" else "stable"
                warns.append(f"ℹ️  {word}（{status} {age} 天）≥{limit} 天 → 建议 {target}（--promote 执行）")

    # ④ 元数据缺失提示（警告）
    no_meta = [it["word"] for it in items if it["status"] in ("new", "active") and not it.get("created_at")]
    if no_meta:
        warns.append(f"ℹ️  {len(no_meta)} 个 new/active 词缺 created_at 元数据（无法自动迁移，建议补充）")

    print("QCM 热词生命周期健康检查")
    print(f"  状态分布: {dist}")
    print(f"  严重问题: {len(issues)} 项 · 警告/建议: {len(warns)} 项")
    for i in issues:
        print(f"    {i}")
    for w in warns[:12]:
        print(f"    {w}")
    if len(warns) > 12:
        print(f"    … 其余 {len(warns) - 12} 条见 --report")
    return 1 if issues else 0


def report():
    """状态分布 + 迁移建议详细报告"""
    data, items = load()
    dist, intent_cnt, domain_cnt, aged = stats(items)
    print("QCM 热词生命周期状态报告")
    print(f"  总词数: {len(items)}")
    print(f"  状态分布: {dist}")
    print(f"  意图容量: {intent_cnt}")
    print(f"  领域容量: {domain_cnt}")
    for status, limit in (("new", RULE["new_to_active_days"]), ("active", RULE["active_to_stable_days"])):
        cands = [(w, a) for w, a in aged.get(status, []) if a >= limit]
        if cands:
            print(f"  [{status}→迁移候选] " + ", ".join(f"{w}({a}d)" for w, a in cands[:10]))
    return 0


def backfill_created_at():
    """V8.4 闭环 Step 2：为缺 created_at 的词回填时间戳（按状态推断 · 幂等）

    stable → 45 天前 · active → 15 天前 · new → 今天（new 需积累观察期）
    回填后 --promote 即可按年龄自动迁移（闭合决策环自动化）。
    """
    import yaml
    data, items = load()
    today = datetime.now().date()
    filled = 0
    for it in items:
        if it.get("created_at"):
            continue
        st = it.get("status", "new")
        if st == "stable":
            it["created_at"] = (today - timedelta(days=45)).isoformat()
        elif st == "active":
            it["created_at"] = (today - timedelta(days=15)).isoformat()
        else:  # new
            it["created_at"] = today.isoformat()
        filled += 1
    if filled:
        KEYWORD.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"✅ 已回填 {filled} 个词 created_at（stable=45d前 · active=15d前 · new=今天）")
    else:
        print("ℹ️  全部词已有 created_at 元数据")
    return 0


def promote():
    """实际执行迁移（写回 keyword.yaml）——保守：仅处理有 created_at 且达阈值的新/活跃词"""
    import yaml
    data, items = load()
    today = datetime.now().date()
    changed = []
    for it in items:
        ca = it.get("created_at")
        if not ca or it["status"] not in ("new", "active"):
            continue
        try:
            age = (today - datetime.strptime(ca, "%Y-%m-%d").date()).days
        except Exception:
            continue
        if it["status"] == "new" and age >= RULE["new_to_active_days"]:
            it["status"] = "active"
            changed.append((it["word"], "new→active"))
        elif it["status"] == "active" and age >= RULE["active_to_stable_days"]:
            it["status"] = "stable"
            changed.append((it["word"], "active→stable"))

    if changed:
        KEYWORD.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"✅ 已迁移 {len(changed)} 个词：")
        for w, tr in changed[:15]:
            print(f"    {w}: {tr}")
    else:
        print("ℹ️  无词达到迁移阈值（需 created_at 元数据）")
    return 0


def main():
    if "--check" in sys.argv:
        return check()
    if "--backfill" in sys.argv:
        return backfill_created_at()
    if "--promote" in sys.argv:
        return promote()
    return report()


if __name__ == "__main__":
    sys.exit(main())
