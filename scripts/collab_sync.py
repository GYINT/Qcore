#!/usr/bin/env python3
"""qcm_collab_sync.py — QCM × Infoseek 协同扩展包同步（任务3）

功能：
  1. 检测 Infoseek 是否安装（skill_registry.find_skill · env INFOSEEK_ROOT > 探测列表）
  2. 检测到后，将 QCM 协同文件写入 Infoseek 扩展目录（extensions/qcm/）
  3. 生成协同清单（qcm-collab-manifest.json）供 Infoseek 侧加载
  4. 幂等（重复运行不产生冲突 · 用 mtime 比较）

Infoseek 端协同点文件映射（仅 Infoseek 侧需要 · 不含 QCM 端协同文件）：
  qcm_client.py              → extensions/qcm/qcm_client.py            （反向调用 QCM 客户端）
  tracing.py                → extensions/qcm/tracing.py               （共享追踪 · 可选）
  qcm_graphql.py            → extensions/qcm/qcm_graphql.py           （共享 GraphQL · 可选）

说明：QCM 端协同文件（bridge/gap_detector/audit_aggregator/auth）属于 QCM 侧能力，
     不写入 Infoseek 扩展目录（任务1 修正）。

用法：
  python3 qcm_collab_sync.py              # 检测 + 同步（默认）
  python3 qcm_collab_sync.py --check      # 仅检测
  python3 qcm_collab_sync.py --force      # 强制覆盖
"""
import os
import sys
import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

QCM_ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS = QCM_ROOT / "scripts"

# 协同文件映射（QCM scripts → 目标相对路径）
# 任务1 修正：仅 Infoseek 端协同点（不含 QCM 端 4 文件）
COLLAB_FILES = {
    "qcm_client.py": "qcm_client.py",
    "tracing.py": "tracing.py",
    "qcm_graphql.py": "qcm_graphql.py",
}

# 已废弃的 QCM 端文件（同步时从扩展目录清理）
LEGACY_QCM_FILES = [
    "infoseek_bridge.py",
    "gap_detector.py",
    "audit.py",
    "auth.py",
]

# Infoseek 检测（归一化：skill_registry 单一真源 · env>探测>验证>None）
from registry import find_skill


def detect_infoseek() -> Optional[Path]:
    """检测 Infoseek 安装路径（委托 skill_registry）"""
    return find_skill("infoseek")


def file_hash(path: Path) -> str:
    """计算文件 SHA256"""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def sync_collab(infoseek_root: Path, force: bool = False) -> Dict:
    """同步协同文件到 Infoseek 扩展目录

    防御性（BUG FIX V8.3.1）：infoseek_root 为 None 时返回 failed 而非崩溃，
    供测试/外部调用方在 Infoseek 未安装时优雅降级。

    Returns:
        {"synced": [...], "skipped": [...], "failed": [...]}
    """
    if infoseek_root is None:
        return {"synced": [], "skipped": [], "failed": ["infoseek 未安装（INFOSEEK_ROOT 未设置）"],
                "removed": [], "manifest": {}}

    ext_dir = infoseek_root / "extensions" / "qcm"
    ext_dir.mkdir(parents=True, exist_ok=True)

    result = {"synced": [], "skipped": [], "failed": [], "removed": []}
    manifest = {}

    # 清理已废弃的 QCM 端文件（任务1）
    for legacy in LEGACY_QCM_FILES:
        legacy_path = ext_dir / legacy
        if legacy_path.exists():
            try:
                legacy_path.unlink()
                result["removed"].append(legacy)
            except Exception:
                pass

    for src_name, dst_name in COLLAB_FILES.items():
        src = SCRIPTS / src_name
        dst = ext_dir / dst_name
        if not src.exists():
            result["failed"].append(src_name)
            continue
        # 幂等：mtime + hash 比较
        if dst.exists() and not force:
            if dst.stat().st_mtime >= src.stat().st_mtime:
                result["skipped"].append(dst_name)
                manifest[dst_name] = {"hash": file_hash(dst), "status": "unchanged"}
                continue
        try:
            shutil.copy2(src, dst)
            result["synced"].append(dst_name)
            manifest[dst_name] = {"hash": file_hash(dst), "status": "synced"}
        except Exception as e:
            result["failed"].append(f"{dst_name}: {e}")

    # 写入协同清单
    manifest_file = ext_dir / "qcm-collab-manifest.json"
    manifest_data = {
        "schema": "qcm-collab-v1",
        "source": str(QCM_ROOT),
        "synced_at": datetime.now().isoformat(),
        "infoseek_version": "v3.0.0+",
        "files": manifest,
        "usage": {
            "import": "sys.path.insert(0, '<infoseek>/extensions/qcm')",
            "modules": ["qcm_client", "tracing", "qcm_graphql"],
            "integration_points": [
                "qcm_client.call_qcm（统一调用入口）",
                "qcm_client.call_qcm_remote（跨设备归因）",
                "tracing（OTel 追踪）",
            ],
        },
    }
    manifest_file.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    result["manifest"] = str(manifest_file)

    return result


def main():
    check_only = "--check" in sys.argv
    force = "--force" in sys.argv

    print("=" * 60)
    print("QCM × Infoseek 协同扩展包同步工具")
    print(f"QCM 源目录：{SCRIPTS}")
    print("=" * 60)

    infoseek = detect_infoseek()
    if infoseek is None:
        print("❌ 未检测到 Infoseek 安装")
        print("   检测路径：")
        for p in INFOSEEK_PATHS:
            print(f"     - {p or '(INFOSEEK_ROOT 未设置)'}")
        print("   安装 Infoseek 后重新运行")
        sys.exit(1)

    print(f"✅ 检测到 Infoseek：{infoseek}")
    if check_only:
        ext = infoseek / "extensions" / "qcm"
        if ext.exists():
            files = sorted(ext.glob("*.py"))
            print(f"   扩展目录已存在：{ext}（{len(files)} 个文件）")
        else:
            print(f"   扩展目录未创建：{ext}")
        sys.exit(0)

    result = sync_collab(infoseek, force=force)
    print(f"\n同步结果：")
    print(f"  ✅ 同步：{len(result['synced'])} 个 → {result['synced']}")
    print(f"  ⏭  跳过（未变更）：{len(result['skipped'])} 个")
    print(f"  🗑  清理（QCM 端废弃文件）：{len(result['removed'])} 个 → {result['removed']}")
    print(f"  ❌ 失败：{len(result['failed'])} 个 → {result['failed']}")
    if "manifest" in result:
        print(f"  📄 协同清单：{result['manifest']}")
        print(f"\n    Infoseek 侧集成：")
        print(f"      sys.path.insert(0, '{infoseek}/extensions/qcm')")
        print(f"      from infoseek_bridge import infoseek_call, qcm_attribution_remote")
    sys.exit(0 if not result["failed"] else 2)


if __name__ == "__main__":
    main()
