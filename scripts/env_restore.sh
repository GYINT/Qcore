#!/usr/bin/env bash
# qcm_env_restore.sh — QCM/Infoseek 环境恢复 SOP（V8.3.0 · 整改 3-1）
# 用途：环境重置后一键恢复（依赖 + Infoseek 补丁文件）
# 用法：bash scripts/qcm_env_restore.sh [--all|--deps|--infoseek]
set -e

BACKUP=${BACKUP:-/sandbox/workspace/qcm_backup_20260812/Infoseek/infoseek_complete_20260812.tar.gz}
# Infoseek 根：env 优先 > 常见路径探测（归一化 · 消灭硬编码）
INFOSEEK_ROOT="${INFOSEEK_ROOT:-}"
if [ -z "$INFOSEEK_ROOT" ] && [ -d /root/.skills/infoseek ]; then INFOSEEK_ROOT=/root/.skills/infoseek; fi
if [ -z "$INFOSEEK_ROOT" ] && [ -d /sandbox/workspace/skills/infoseek ]; then INFOSEEK_ROOT=/sandbox/workspace/skills/infoseek; fi
INFOSEK_SCRIPTS="$INFOSEEK_ROOT/scripts"

echo "=== QCM 环境恢复 SOP ==="

restore_deps() {
    echo "[1/3] 安装核心依赖..."
    pip install -q websockets graphql-core PyYAML \
        opentelemetry-api opentelemetry-sdk \
        opentelemetry-exporter-otlp-proto-http opentelemetry-exporter-otlp-proto-grpc 2>&1 | tail -1
    python3 -c "import websockets, graphql, opentelemetry; print('  deps ok:', websockets.__version__, graphql.__version__)"
}

restore_infoseek() {
    echo "[2/3] 恢复 Infoseek 补丁文件（infoseek_auth/sync_manifest/validate_skill/CHANGELOG/infoseek_mcp_server）..."
    TMP=$(mktemp -d)
    if [ -f "$BACKUP" ]; then
        tar xzf "$BACKUP" -C "$TMP" 2>/dev/null
        cp "$TMP"/scripts/infoseek_auth.py "$TMP"/scripts/sync_manifest.py \
           "$TMP"/scripts/validate_skill.py "$TMP"/scripts/infoseek_mcp_server.py "$INFOSEK_SCRIPTS/" 2>/dev/null
        cp "$TMP"/CHANGELOG.md "$INFOSEEK_ROOT/" 2>/dev/null
        echo "  已从备份恢复 5 文件"
    else
        echo "  ⚠️ 备份不存在（$BACKUP）——请手动恢复"
    fi
    # socket import 补丁（write_audit_log 依赖）
    if ! grep -q "^import socket" "$INFOSEK_SCRIPTS/infoseek_mcp_server.py" 2>/dev/null; then
        sed -i 's/^import secrets$/import secrets\nimport socket/' "$INFOSEK_SCRIPTS/infoseek_mcp_server.py"
        echo "  已补 socket import"
    fi
    rm -rf "$TMP"
    PATCHES=$(grep -c "oauth/token\|INFOSEEK_AUDIT_DIR\|export_metrics\|run_ws_server\|qcm_query" "$INFOSEK_SCRIPTS/infoseek_mcp_server.py" 2>/dev/null || echo 0)
    echo "  infoseek_mcp_server 补丁标记: $PATCHES/19"
}

restore_key() {
    echo "[3/3] LLM Key（可选 · 需用户提供）"
    if [ -z "$DEEPSEEK_API_KEY" ]; then
        echo "  ⚠️ DEEPSEEK_API_KEY 未设置——v021 真实 LLM 用例将跳过（其余套件不受影响）"
    else
        echo "  ✅ DEEPSEEK_API_KEY 已设置"
    fi
}

case "${1:---all}" in
    --deps) restore_deps ;;
    --infoseek) restore_infoseek ;;
    --all) restore_deps; restore_infoseek; restore_key ;;
    *) echo "用法: $0 [--all|--deps|--infoseek]"; exit 1 ;;
esac

echo "=== 恢复完成 · 建议跑 qcm_v82_test.py + qcm_mcp_v160_test.py 验证 ==="
