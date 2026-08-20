#!/usr/bin/env bash
# QCM 词源自进化闭环（V8.4 Step 4 · 观测→检测→决策→回灌→报告 + A5 运行监控）
# 用法：bash scripts/word_evolution.sh [--dry-run]
#   --dry-run：只观测+检测+决策建议，不写回词库（安全模式）
# A5：每次执行结果归档 references/automation_log/（含退出状态）· 供异常告警/趋势分析
# 接入：可挂 CI 周频 / 自动化定时执行（闭环自动运转）
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
if command -v cygpath >/dev/null 2>&1; then
  ROOT="$(cygpath -w "$ROOT")"
fi
export QCM_ROOT="$ROOT"
export QCM_NO_REPORT=1
PY="python3"
[ -n "$QCM_PYTHON" ] && PY="$QCM_PYTHON"
DRY=""
[ "$1" = "--dry-run" ] && DRY="--dry-run"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/references/automation_log"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/word_evolution-$STAMP.log"

exec > >(tee -a "$LOG") 2>&1
echo "=== QCM 词源自进化（$STAMP${DRY:+ · dry-run}）==="

echo "=== [1/6] 观测环 · 未命中词统计 ==="
$PY core/hit_tracker.py --stats

echo "=== [2/6] 检测环 · 词源同类语义检测 ==="
$PY scripts/semantic_audit.py --check || true

echo "=== [3/6] 决策环 · 生命周期（回填/检查/迁移） ==="
$PY scripts/keyword_lifecycle.py --backfill
$PY scripts/keyword_lifecycle.py --check
if [ -z "$DRY" ]; then
  $PY scripts/keyword_lifecycle.py --promote || true
else
  echo "  (dry-run：跳过 --promote 写回)"
fi

echo "=== [4/6] 回灌环 · 词源协同（别名/M4） ==="
$PY scripts/corpus_sync.py alias --sync || true
$PY scripts/corpus_sync.py m4 --status | head -4

echo "=== [5/6] AI 路径健康检查（V8.4 B4 · L2 联网/LLM/Key 三态）==="
$PY -c "
import sys, os; sys.path.insert(0, 'scripts'); sys.path.insert(0, 'core')
from key_manager import _load_env_file; _load_env_file()
# ① LLM Key 状态
ds = bool(os.environ.get('DEEPSEEK_API_KEY'))
zp = bool(os.environ.get('ZHIPU_API_KEY') or os.environ.get('BOCHA_API_KEY'))
# ② L2 联网搜索可达性（Infoseek search_web 免费引擎 · 3s 探测）
web_ok = False
try:
    from infoseek_bridge import _web_search_infoseek
    web_ok = _web_search_infoseek('SPC 统计过程控制', max_results=2) is not None
except Exception:
    pass
print(f'  LLM(DeepSeek): {\"✅\" if ds else \"❌\"} · 搜索Key(智谱/博查): {\"✅\" if zp else \"❌\"} · L2联网: {\"✅\" if web_ok else \"❌\"}')
print(f'  状态: {\"全通道可用\" if (ds or zp) and web_ok else \"部分可用（LLM=\" + (\"有\" if ds else \"无\") + \" · 联网=\" + (\"有\" if web_ok else \"无\") + \"）\"}')
" || true

echo "=== [6/6] 指标采集 ==="
$PY -c "import sys; sys.path.insert(0, 'scripts'); from metrics import record_keyword_health, metrics; record_keyword_health(); print([l for l in metrics.export().splitlines() if 'qcm_' in l and not l.startswith('#')][-6:])"

echo ""
echo "✅ 词源自进化闭环执行完成${DRY:+（dry-run · 未写回词库）}（归档: $LOG）"
