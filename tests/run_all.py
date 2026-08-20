#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QCM 测试串联运行器（V8.3.1 · run_all 冒烟入口）

用法：
  python3 tests/run_all.py                 # 全部 37 测试（basic + protocol + engines + v82）
  python3 tests/run_all.py --group basic   # 仅 basic 组
  python3 tests/run_all.py --group protocol
  python3 tests/run_all.py --group engines
  python3 tests/run_all.py --group smoke   # basic + v82（快速冒烟）

约定：
  - QCM_ROOT 未设时自动指向镜像根（env 优先）
  - engines 组自动置 QCM_NO_REPORT=1（不写报告文件，保持沙箱干净）
"""
import os
import subprocess
import sys
import glob
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

GROUPS = {
    "basic": ["tests/basic/*_test.py"],
    "protocol": ["tests/protocol/*_test.py"],
    "engines": ["tests/engines/*_test.py"],
    "smoke": ["tests/basic/*_test.py", "tests/qcm_v82_test.py",
              "tests/qcm_router_golden_test.py"],  # V8.3.2 T3：路由黄金用例纳入冒烟
    "core": ["tests/engines/*_test.py", "tests/qcm_v82_test.py",
             "tests/qcm_router_golden_test.py"],   # V8.3.2 T3：CI 核心基线（无环境依赖）
    "all": ["tests/basic/*_test.py", "tests/protocol/*_test.py",
            "tests/engines/*_test.py", "tests/qcm_v82_test.py",
            "tests/qcm_router_golden_test.py"],
}


def detect_env() -> dict:
    """V8.3.2 T3：环境探测（区分实现缺陷 vs 环境缺失，防真实质量信号被噪音淹没）"""
    env = {}
    # Infoseek 安装
    infoseek = os.environ.get("INFOSEEK_ROOT")
    if not infoseek:
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from registry import find_skill
            infoseek = find_skill("infoseek")
        except Exception:
            infoseek = None
    env["infoseek"] = bool(infoseek)
    # LLM API Key（任意 provider）
    keys = [k for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                        "QWEN_API_KEY", "AZURE_OPENAI_API_KEY") if os.environ.get(k)]
    env["llm_key"] = bool(keys)
    # OTel 依赖
    try:
        import opentelemetry  # noqa: F401
        env["otel"] = True
    except Exception:
        env["otel"] = False
    # infoseek_auth 模块
    env["infoseek_auth"] = bool((ROOT / "scripts" / "infoseek_auth.py").exists())
    return env


# 已知环境依赖型测试 → 环境缺失时建议 SKIP 而非视为实现缺陷
ENV_DEP_TESTS = {
    "qcm_mcp_v041_test.py": "infoseek", "qcm_mcp_v042_test.py": "infoseek",
    "qcm_mcp_v043_test.py": "infoseek", "qcm_mcp_v044_test.py": "infoseek",
    "qcm_mcp_v050_test.py": "infoseek_auth", "qcm_mcp_v060_test.py": "infoseek",
    "qcm_mcp_v061_test.py": "infoseek", "qcm_mcp_v123_test.py": "infoseek",
    "qcm_mcp_v131_test.py": "otel", "qcm_mcp_v151_test.py": "otel",
    # V8.4 修正分类：v02（断言过时已修 17/17）· v03（14/14 已过）· v06（plugin 导入已修 18/18）
    # 真正依赖 LLM Key 的仅 v021（real mode 验证）
    "qcm_mcp_v021_test.py": "llm_key",
}


def main():
    args = sys.argv[1:]
    group = "all"
    if "--group" in args:
        i = args.index("--group")
        if i + 1 < len(args):
            group = args[i + 1]
    patterns = GROUPS.get(group, GROUPS["all"])

    files = []
    for pat in patterns:
        files.extend(sorted(glob.glob(str(ROOT / pat))))
    files = [f for f in files if "__pycache__" not in f]
    if not files:
        print(f"❌ 组 '{group}' 无测试文件")
        return 2

    env = dict(os.environ)
    env.setdefault("QCM_ROOT", str(ROOT))
    env["QCM_NO_REPORT"] = "1"

    print(f"=== QCM 测试串联（组={group} · {len(files)} 个 · QCM_ROOT={env['QCM_ROOT']}） ===")
    passed, failed = [], []
    for f in files:
        name = Path(f).name
        print(f"\n▶ {name} ...", flush=True)
        try:
            r = subprocess.run([sys.executable, f], env=env,
                               capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            failed.append(name)
            print(f"  ❌ {name}（超时 900s）")
            continue
        # 清理测试残留 server 进程（防串行端口冲突 · V8.4 修复）
        subprocess.run(["pkill", "-f", "mcp_server.py"], capture_output=True)
        subprocess.run(["pkill", "-f", "infoseek_mcp_server.py"], capture_output=True)
        time.sleep(1)
        if r.returncode == 0:
            passed.append(name)
            print(f"  ✅ {name}")
        else:
            failed.append(name)
            print(f"  ❌ {name}（exit={r.returncode}）")
            tail = [ln for ln in r.stdout.strip().splitlines() if ln.strip()][-10:]
            for ln in tail:
                print(f"     {ln}")
            if r.stderr.strip():
                for ln in r.stderr.strip().splitlines()[-3:]:
                    print(f"     [err] {ln}")

    print("\n" + "=" * 60)
    print(f"汇总：通过 {len(passed)} / {len(files)} · 失败 {len(failed)}")
    if failed:
        env_state = detect_env()
        print("\n环境状态（V8.3.2 T3）：")
        print(f"  Infoseek 安装: {'✅' if env_state['infoseek'] else '❌ 未安装'}"
              f"  · LLM API Key: {'✅' if env_state['llm_key'] else '❌ 缺失'}"
              f"  · OTel 依赖: {'✅' if env_state['otel'] else '❌ 未安装'}"
              f"  · infoseek_auth: {'✅' if env_state['infoseek_auth'] else '❌ 缺失'}")
        impl_fail, env_fail = [], []
        for f in failed:
            dep = ENV_DEP_TESTS.get(Path(f).name)
            if dep and not env_state.get(dep):
                env_fail.append(f"{Path(f).name}（缺 {dep}）")
            else:
                impl_fail.append(Path(f).name)
        if env_fail:
            print(f"\n🟠 环境性失败（{len(env_fail)} · 建议补环境后复跑 / CI 中 skip）：")
            for f in env_fail:
                print(f"  ↳ {f}")
        if impl_fail:
            print(f"\n🔴 待排查失败（{len(impl_fail)} · 需人工确认是否实现缺陷）：")
            for f in impl_fail:
                print(f"  ❌ {f}")
        if not impl_fail:
            print("\n✅ 无实现缺陷失败（全部失败均为环境缺失所致）")
            return 0
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
