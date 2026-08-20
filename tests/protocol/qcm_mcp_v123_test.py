#!/usr/bin/env python3
"""qcm_mcp_v123_test.py — QCM 协同扩展包同步测试（任务3 + 任务1修正）

覆盖（8 用例）：
  1. detect_infoseek 检测到安装
  2. 协同文件映射完整（6 文件）
  3. sync_collab 同步成功
  4. 幂等（二次运行 skipped）
  5. 扩展目录文件存在
  6. 清单文件生成
  7. Infoseek 侧可导入（sys.path 注入）
  8. --check 模式
"""

import json
import os
import sys
import subprocess

QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(QCM_ROOT, "scripts")
sys.path.insert(0, SCRIPTS)


def test(name, fn):
    try:
        result = fn()
        if result is True:
            print(f"  ✅ {name}")
            return True
        print(f"  ❌ {name}: {result}")
        return False
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False


def run_v123_tests():
    print("=" * 70)
    print("QCM 任务3 测试套件（协同扩展包同步）")
    print("=" * 70)

    passed = 0
    total = 0

    from collab_sync import detect_infoseek, sync_collab, COLLAB_FILES

    # [1] 检测
    print("\n[1. Infoseek 检测]")
    total += 1
    def detect():
        root = detect_infoseek()
        assert root is not None, "未检测到 Infoseek"
        assert (root / "scripts" / "infoseek_mcp_server.py").exists()
        return True
    if test("detect_infoseek 检测到安装", detect):
        passed += 1

    # [2] 映射（任务1：仅 Infoseek 端协同点 3 文件）
    total += 1
    def mapping():
        from pathlib import Path
        from collab_sync import LEGACY_QCM_FILES
        assert len(COLLAB_FILES) == 3, f"文件数={len(COLLAB_FILES)}"
        for src in COLLAB_FILES:
            assert Path(SCRIPTS, src).exists(), f"源缺失: {src}"
        # 确认不含 QCM 端 4 文件
        for legacy in LEGACY_QCM_FILES:
            assert legacy not in COLLAB_FILES, f"不应包含: {legacy}"
        return True
    if test("仅 Infoseek 端协同点（3 文件 · 不含 QCM 4）", mapping):
        passed += 1

    # [3] 同步
    print("\n[2. 同步]")
    total += 1
    def sync_ok():
        root = detect_infoseek()
        result = sync_collab(root, force=True)
        assert len(result["synced"]) == 3, f"synced={result['synced']}"
        assert not result["failed"]
        return True
    if test("sync_collab 同步 3 文件 + 清理 QCM 4", sync_ok):
        passed += 1

    # [4] 幂等
    total += 1
    def idempotent():
        root = detect_infoseek()
        result = sync_collab(root, force=False)
        assert len(result["synced"]) == 0, f"应全部 skipped: {result['synced']}"
        assert len(result["skipped"]) == 3, f"skipped={result['skipped']}"
        return True
    if test("幂等（二次运行 skipped）", idempotent):
        passed += 1

    # [5] 文件存在
    total += 1
    def files_exist():
        ext = detect_infoseek() / "extensions" / "qcm"
        for name in ["qcm_client.py", "tracing.py", "qcm_graphql.py"]:
            assert (ext / name).exists(), f"缺失: {name}"
        # 确认 QCM 端 4 文件已清理
        for name in ["infoseek_bridge.py", "gap_detector.py",
                     "audit.py", "auth.py"]:
            assert not (ext / name).exists(), f"不应存在: {name}"
        return True
    if test("扩展目录 3 协同点存在 + QCM 4 已清理", files_exist):
        passed += 1

    # [6] 清单
    total += 1
    def manifest():
        ext = detect_infoseek() / "extensions" / "qcm"
        mf = ext / "qcm-collab-manifest.json"
        assert mf.exists()
        data = json.loads(mf.read_text(encoding="utf-8"))
        assert data["schema"] == "qcm-collab-v1"
        assert len(data["files"]) == 3, f"files={list(data['files'].keys())}"
        return True
    if test("协同清单生成（schema + 3 协同点）", manifest):
        passed += 1

    # [7] Infoseek 侧可导入
    total += 1
    def importable():
        ext = str(detect_infoseek() / "extensions" / "qcm")
        import importlib
        saved = sys.path
        sys.path.insert(0, ext)
        try:
            for mod in ["qcm_client", "tracing", "qcm_graphql"]:
                importlib.import_module(mod)
            return True
        finally:
            sys.path = saved
    if test("Infoseek 侧 3 模块可导入", importable):
        passed += 1

    # [8] --check
    total += 1
    def check_mode():
        r = subprocess.run(["python3", "-B", os.path.join(SCRIPTS, "collab_sync.py"),
                            "--check"], capture_output=True, text=True, timeout=15)
        assert "检测到 Infoseek" in r.stdout
        return True
    if test("--check 模式", check_mode):
        passed += 1

    # 总结
    print("\n" + "=" * 70)
    print(f"任务3 测试结果：{passed}/{total} 通过")
    print("=" * 70)
    if passed == total:
        print("✅ QCM 协同扩展包全部测试通过（任务1 修正）")
        print("   - Infoseek 检测 + 3 协同点同步 + QCM 4 清理 + 幂等")
        print("   - 协同清单 + Infoseek 侧可导入")
    else:
        print(f"❌ {total - passed} 个测试失败")
    return passed == total


if __name__ == "__main__":
    success = run_v123_tests()
    sys.exit(0 if success else 1)
