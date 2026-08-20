# -*- coding: utf-8 -*-
"""QCM 压力测试（V8.4 · 只读为主 · 不修改词库）

覆盖 5 类压力：
  ① 高频调用：route 500 次（性能 + 稳定性）
  ② 并发安全：多线程并发 route（GIL 下的正确性）
  ③ 大数据量：超长文本 10 万字 + 词库全量加载
  ④ hit_tracker 批量写入：500 词未命中落盘（JSON 持久化压力）
  ⑤ 全量工具链：semantic_audit + lifecycle 全量扫描耗时
"""
import sys
import os
import time
import json
import threading
from pathlib import Path

QCM_ROOT = os.environ.get("QCM_ROOT", str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, os.path.join(QCM_ROOT, "core"))
sys.path.insert(0, os.path.join(QCM_ROOT, "scripts"))
os.environ["QCM_ROOT"] = QCM_ROOT

from router import route, load_keywords

passed = 0
total = 0
fails = []


def test(name, fn):
    global passed, total
    total += 1
    try:
        fn()
        passed += 1
        print(f"  ✅ {name}")
    except Exception as e:
        fails.append((name, str(e)))
        print(f"  ❌ {name}: {type(e).__name__}: {e}")


print("=" * 70)
print("QCM 压力测试")
print("=" * 70)

# ============ ① 高频调用 ============
print("\n[1. 高频调用 · route × 500]")

def high_freq():
    samples = [
        "注塑车间卡扣座尺寸超差，Cpk 0.82 客户拒收",
        "良率太低了怎么改善",
        "SPC 控制图怎么用",
        "我司要过 IATF 16949 认证",
        "戴明是怎么讲质量改进的",
        "今天天气不错",
    ]
    t0 = time.time()
    for i in range(500):
        r = route(samples[i % len(samples)])
        assert r.get("intent"), f"第 {i} 次返回异常"
    dt = time.time() - t0
    avg_ms = dt * 1000 / 500
    print(f"    500 次耗时 {dt:.2f}s · 平均 {avg_ms:.2f} ms/次")
    assert avg_ms < 50, f"平均耗时 {avg_ms:.1f}ms 超预期（>50ms）"
test("route 500 次（平均 <50ms）", high_freq)

# ============ ② 并发安全 ============
print("\n[2. 并发安全 · 8 线程 × 100 次]")

def concurrency():
    errors = []
    def worker(wid):
        try:
            for i in range(100):
                r = route(f"注塑缩水客诉 {wid}-{i}")
                assert r.get("intent")
                route("良率太低怎么改善")
        except Exception as e:
            errors.append(f"线程{wid}: {type(e).__name__}: {e}")
    threads = [threading.Thread(target=worker, args=(w,)) for w in range(8)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    dt = time.time() - t0
    print(f"    8 线程 × 100 次 = 800 次 · {dt:.2f}s · 错误 {len(errors)}")
    assert not errors, f"并发错误: {errors[:3]}"
test("8 线程并发 800 次路由零错误", concurrency)

# ============ ③ 大数据量 ============
print("\n[3. 大数据量]")

def huge_text():
    q = "失效缺陷客诉" * 25000  # 10 万字
    t0 = time.time()
    r = route(q)
    dt = time.time() - t0
    print(f"    10 万字输入 · {dt:.2f}s · intent={r['intent']}")
    assert dt < 5, f"10 万字处理 {dt:.1f}s 过慢"
test("10 万字超长文本 <5s", huge_text)

def full_load():
    t0 = time.time()
    load_keywords()
    dt = time.time() - t0
    print(f"    词库全量加载 {dt:.2f}s")
    assert dt < 2, f"词库加载 {dt:.1f}s 过慢"
test("词库全量加载 <2s", full_load)

# ============ ④ hit_tracker 批量写入 ============
print("\n[4. hit_tracker 批量写入 · 500 词]")

def hit_batch():
    from hit_tracker import record_miss, stats, _save
    t0 = time.time()
    for i in range(500):
        record_miss(f"冷门词{i}机理{i % 50}分析")
    dt = time.time() - t0
    s = stats()
    print(f"    500 词写入 {dt:.2f}s · 跟踪 {s.get('total_tracked', 0)} 词")
    assert dt < 10, f"批量写入 {dt:.1f}s 过慢"
    # 清理（压力测试不留污染 · 扁平结构 {word: {...}}）
    _save({})
test("hit_tracker 500 词批量写入 + 清理", hit_batch)

# ============ ⑤ 全量工具链 ============
print("\n[5. 全量工具链耗时]")

def tool_chain():
    import subprocess
    t0 = time.time()
    r1 = subprocess.run([sys.executable, os.path.join(QCM_ROOT, "scripts", "semantic_audit.py"), "--check"],
                        capture_output=True, text=True, timeout=60)
    t1 = time.time()
    r2 = subprocess.run([sys.executable, os.path.join(QCM_ROOT, "scripts", "keyword_lifecycle.py"), "--check"],
                        capture_output=True, text=True, timeout=60)
    t2 = time.time()
    print(f"    semantic_audit {t1-t0:.1f}s · keyword_lifecycle {t2-t1:.1f}s")
    assert r1.returncode == 0, f"semantic_audit 失败: {r1.stderr[-200:]}"
    assert r2.returncode == 0, f"lifecycle 失败: {r2.stderr[-200:]}"
    assert t2 - t0 < 30, f"工具链总耗时 {t2-t0:.1f}s 过慢"
test("semantic_audit + lifecycle 全量 <30s", tool_chain)

# ============ 总结 ============
print("\n" + "=" * 70)
print(f"压力测试结果：{passed}/{total} 通过")
print("=" * 70)
if fails:
    for name, err in fails:
        print(f"  ❌ {name}: {err}")
    sys.exit(1)
print("✅ 压力测试全部通过")
sys.exit(0)
