#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 路由黄金用例（V8.3.2 T3 · 固化自案例实测 9/9 正确集）

覆盖：①危机处置（含歧义词回归）· ②流程优化 · ③评估审计 · ④知识学习 · ⑤知识沉淀 · ⑥质量文化
背景：2026-08-20 案例路由实测发现 P0 歧义路由 BUG（含歧义词的①被误路由为④），
      修复 + 词库补全后 9/9 正确，本文件将其固化为回归护栏（防回潮）。

用法：
  QCM_ROOT=<root> python3 tests/qcm_router_golden_test.py
  （由 run_all.py --group smoke / ci_core.sh 自动纳入）
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "scripts"))

from router import route  # noqa: E402

CASES = [
    # (输入, 预期意图, 说明)
    ("注塑车间门内板卡扣座装配尺寸超差，Cpk 从 1.67 跌到 0.82，客户拒收了", "①危机处置", "歧义词+故障信号 ①"),
    ("卡扣座尺寸超差，Cpk 0.82，客户拒收", "①危机处置", "歧义词 ①（P0 回归）"),
    ("SMT 焊接不良率飙升到 5%", "①危机处置", "飙升 ①（词库补全回归）"),
    ("注塑缩水导致 ppm 超标，客户投诉", "①危机处置", "超标 ①（词库补全回归）"),
    ("冲压尺寸 Cpk 跌破 1.33", "①危机处置", "跌破 ①（词库补全回归）"),
    ("喷涂色差超标，良率只有 60%", "①危机处置", "超标 ①（词库补全回归）"),
    ("冲压件毛刺划伤问题连续复发，想提升直通率", "②流程优化", "优化动词优先 ②"),
    ("想把注塑良率提升到 99%", "②流程优化", "歧义词+优化动词 → ②"),
    ("想改善冲压件直通率，降低报废", "②流程优化", "纯优化 ②"),
    ("供应商来料批次不良率攀升，需要审核评估", "③评估审计", "评估审计 ③"),
    ("什么是 FMEA 七步法，讲一下原理", "④知识学习", "知识学习 ④"),
    ("公司想建设质量文化，怎么做意识提升和氛围塑造", "⑥质量文化", "质量文化 ⑥（V8.3 意图）"),
    ("我们想进入新能源行业，落地 IATF16949 体系", "⑤知识沉淀", "知识沉淀 ⑤"),
    ("CNC 镗孔椭圆 0.002mm 怎么办", "①危机处置", "椭圆 ①"),
    ("客户投诉增多，出口产品被退货", "①危机处置", "客诉/退货 ①"),
]


def main() -> int:
    passed, failed = 0, []
    for query, expected, note in CASES:
        r = route(query)
        ok = r["intent"] == expected
        if ok:
            passed += 1
        else:
            failed.append((query, expected, r["intent"], note))
        mark = "✅" if ok else "❌"
        print(f"{mark} {query[:22]:<24} → {r['intent']}（期望 {expected}）conf={r['confidence']} {note}")

    print("\n" + "=" * 60)
    print(f"路由黄金用例：通过 {passed}/{len(CASES)}")
    if failed:
        print("失败明细：")
        for q, exp, got, note in failed:
            print(f"  ❌ {q} → 期望 {exp} 实得 {got}（{note}）")
        return 1
    print("✅ 全部通过（含 P0 歧义路由回归护栏）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
