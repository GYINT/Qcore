# QCM MCP Server 故障排查

## 常见问题

### 1. Server 启动失败

**症状**：`Address already in use` 或 `Permission denied`

**解决方案**：
```bash
# 端口占用
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows
# 改用其他端口
python scripts/mcp_server.py --port 8081

# 权限问题（< 1024 端口）
sudo python scripts/mcp_server.py --port 80
# 或用 8080+ 端口
```

### 2. Token 认证失败

**症状**：`HTTP 401 Unauthorized` 或 `invalid_client`

**排查步骤**：
```bash
# 检查环境变量
echo $QCM_AUTH_TOKEN
echo $QCM_REQUIRE_TOKEN

# 确保两者一致
export QCM_REQUIRE_TOKEN=1
export QCM_AUTH_TOKEN="your-secret"

# 测试 OAuth 流程
curl -X POST http://localhost:8080/oauth/token \
  -d "grant_type=client_credentials&client_id=default-client&client_secret=your-secret"
```

### 3. LLM API 调用失败

**症状**：`HTTP 401 Authorization Required`（来自 DeepSeek 等）

**排查**：
```bash
# 检查 API key
echo $DEEPSEEK_API_KEY

# 测试 API 单独调用
python3 -c "
import os
import urllib.request, json
req = urllib.request.Request(
    'https://api.deepseek.com/v1/chat/completions',
    data=json.dumps({'model':'deepseek-chat','messages':[{'role':'user','content':'ping'}]}).encode(),
    headers={'Authorization':'Bearer '+os.environ['DEEPSEEK_API_KEY'],'Content-Type':'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.read().decode())
"

# 如 key 失效 → 在 DeepSeek 控制台重新生成
```

### 4. Cache 不工作

**症状**：重复调用仍然很慢

**排查**：
```bash
# 检查 cache 目录
ls -la /tmp/qcm-cache/

# 检查 cache 大小
curl http://localhost:8080/stats | python3 -m json.tool | grep -A 5 cache

# 强制重建
rm -rf /tmp/qcm-cache/
# 重启 server
```

### 5. Rate Limit 触发

**症状**：`HTTP 429 Too Many Requests` + `Retry-After` header

**排查**：
```bash
# 查看当前使用
curl http://localhost:8080/stats | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('rate_limiter'))
"

# 调整限流（环境变量）
export QCM_RATE_LIMIT_PER_IP=1000
export QCM_RATE_LIMIT_PER_TOKEN=10000
```

### 6. Hot Reload 不工作

**症状**：修改 corpus 后内容未更新

**排查**：
```bash
# 确认 --watch-corpus 已启用
ps aux | grep qcm_mcp_server | grep -o watch-corpus

# 检查 stderr 日志
python scripts/mcp_server.py --watch-corpus --watch-interval 5 2>&1 | grep CorpusWatcher
# 应看到 [CorpusWatcher] Reloaded: {...}

# 检查 mtime 是否更新
stat <QCM_ROOT>/references/action-orders.md
```

### 7. Audit Log 不写入

**症状**：`/tmp/qcm-mcp-audit/audit-*.log` 文件不存在或为空

**排查**：
```bash
# 检查目录权限
mkdir -p /tmp/qcm-mcp-audit
chmod 755 /tmp/qcm-mcp-audit

# 指定自定义目录
export QCM_AUDIT_DIR=/var/log/qcm-mcp
mkdir -p $QCM_AUDIT_DIR
python scripts/mcp_server.py

# 触发一次调用验证
curl http://localhost:8080/rpc -d '...'
ls -la $QCM_AUDIT_DIR/
```

### 8. K8s Pod 启动失败

**症状**：`CrashLoopBackOff` 或 `ImagePullBackOff`

**排查**：
```bash
# 查看事件
kubectl describe pod -n qcm -l app.kubernetes.io/name=qcm-mcp

# 查看日志
kubectl logs -n qcm -l app.kubernetes.io/name=qcm-mcp --previous

# 常见问题：
# - Secret 未创建 → kubectl get secret -n qcm
# - PVC 未挂载 → kubectl get pvc -n qcm
# - 资源不足 → 调整 values.yaml resources
```

### 9. MCP 客户端连接失败

**症状**：Claude Desktop 提示 "MCP server not responding"

**排查**：
```bash
# stdio 模式：手动执行命令看错误
python scripts/mcp_server.py

# HTTP 模式：检查网络
curl http://localhost:8080/health/live

# Claude Desktop 配置：
# 1. ~/.config/claude_desktop_config.json（macOS）
# 2. %APPDATA%\Claude\claude_desktop_config.json（Windows）
{
  "mcpServers": {
    "qcm": {
      "command": "python",
      "args": ["/absolute/path/to/scripts/mcp_server.py"]
    }
  }
}
```

### 10. OpenAPI 规范错误

**症状**：Swagger UI 加载失败

**排查**：
```bash
# 验证 YAML 语法
python3 -c "import yaml; yaml.safe_load(open('openapi.yaml'))"

# 在线验证
# https://editor.swagger.io/?url=http://localhost:8080/openapi.yaml
```

## 性能问题

### 启动慢

```bash
# 删除 corpus cache 重建
rm -rf /tmp/qcm-cache/
# 首次启动会慢（~1s），后续启动 < 200ms
```

### 工具调用慢

```bash
# 检查 metrics
curl http://localhost:8080/metrics | grep duration

# 可能原因：
# 1. LLM API 慢（real mode）→ 用 mock mode 测试
# 2. 工具处理慢 → 优化 corpus 大小
# 3. 网络问题 → 检查 LLM 端点延迟
```

### 内存占用高

```bash
# 查看 RSS
ps aux | grep qcm_mcp | grep -o rss=[0-9]*

# 可能原因：
# 1. corpus 太大（40+ 文件 · ~2MB）
# 2. LLM cache 太多 → 调小 TTL
# 3. Audit log 太大 → 启用 log rotation
```

## 调试模式

启用 debug 日志：

```python
# 修改 scripts/mcp_server.py
logging.basicConfig(level=logging.DEBUG)
```

或环境变量：
```bash
export PYTHONUNBUFFERED=1
python scripts/mcp_server.py 2>&1 | tee /tmp/qcm-debug.log
```

## 报告 Bug

收集诊断信息：

```bash
# 1. 系统信息
python3 --version
uname -a

# 2. QCM MCP 版本
python scripts/mcp_server.py --help 2>&1

# 3. 测试结果
python qcm_runner.py

# 4. 关键日志
tail -100 /tmp/qcm-mcp-audit/audit-*.log

# 5. 环境变量（脱敏）
env | grep -i QCM
env | grep -i API_KEY | sed 's/=.*/=***/'

# 6. 网络测试
curl -v http://localhost:8080/health/live

# 7. 提交 issue
# <issues-url>
```

## 紧急情况

如需立即停止服务并清理：

```bash
# 找到所有 QCM MCP 进程
ps aux | grep qcm_mcp | grep -v grep | awk '{print $2}' | xargs -r kill -9

# 清理 cache（保留 corpus 源文件）
rm -rf /tmp/qcm-cache/

# Docker
docker ps | grep qcm-mcp | awk '{print $1}' | xargs -r docker stop
docker system prune -f

# K8s
kubectl scale deployment -n qcm qcm-mcp --replicas=0
```

## 联系方式

- GitHub Issues：<issues-url>
- 邮件：<support-email>
- 文档：<docs-url>