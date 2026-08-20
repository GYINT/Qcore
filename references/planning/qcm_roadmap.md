# QCM MCP V0.5 → V1.0 完整任务清单（2026-08-10 规划）

> **跳过项**：Infoseek 协同（V0.4） + Q3 2026 缺口调研自动化（依赖 Infoseek）
> **规划原则**：每版本独立可交付 · 累计向上兼容 · 8 引擎 + 4 MCP 测试全绿作为门槛
> **关联文档**：qcm_mcp_eval.md · qcm_mcp_path.md · gap_tracker.md

---

## 📊 全局规划一览

| 版本 | 主题 | 任务数 | 周期 | 状态 |
|------|------|--------|------|------|
| **V0.5** | 稳定性 + 可观测性 | 5 | 1 周 | 📋 待启动 |
| **V0.6** | 可扩展性 + 配置化 | 6 | 1 周 | 📋 |
| **V0.7** | MCP 协议完整化 | 5 | 1 周 | 📋 |
| **V0.8** | 性能 + 缓存 | 5 | 1 周 | 📋 |
| **V0.9** | 安全 + 多租户 | 5 | 1 周 | 📋 |
| **V1.0** | 生产就绪 | 7 | 2 周 | 📋 |
| **总计** | - | **33 任务** | **~7 周** | - |

---

## V0.5 · 稳定性 + 可观测性（1 周）

> **目标**：让 QCM MCP Server 具备运维级可观测性 + 防滥用能力
> **跳过**：Infoseek 协同 + Q3 缺口调研自动化（依赖未就绪）

### 任务清单

| ID | 任务 | 价值 | 实施 | 测试 |
|----|------|------|------|------|
| **V0.5-01** | Metrics 端点（`/metrics` Prometheus 格式）| 监控必备 | 1 天 | 单元 + 集成 |
| **V0.5-02** | Rate Limiting（基于 IP/token）| 防滥用 | 1 天 | 压测 |
| **V0.5-03** | Structured Access Log（JSON Lines）| 排障必备 | 0.5 天 | 单元 |
| **V0.5-04** | Stats API 端点（`/stats` JSON）| 调试辅助 | 0.5 天 | 单元 |
| **V0.5-05** | 健康检查增强（LLM provider 状态）| 运维可见 | 0.5 天 | 集成 |

### 详细规格

#### V0.5-01 Metrics 端点

```python
# 输出（Prometheus 文本格式）
qcm_requests_total{method="tools/call", tool="qcm_research"} 1523
qcm_request_duration_seconds{tool="qcm_research", quantile="0.5"} 0.234
qcm_llm_calls_total{provider="deepseek", mode="real"} 89
qcm_llm_call_duration_seconds{provider="deepseek"} 1.234
qcm_corpus_files 41
qcm_active_sessions 0
```

**实施**：
- 文件：`qcm_metrics.py`（MetricsCollector 类）
- 集成：HTTPHandler.do_GET 处理 `/metrics`
- 存储：内存环形 buffer（避免重启丢失关键数据）

#### V0.5-02 Rate Limiting

```python
# 限流策略
- Per-IP: 100 req/min
- Per-Token: 1000 req/hour
- Global: 10000 req/min（防雪崩）
- 超限返回 429 + Retry-After header
```

**实施**：
- 文件：`qcm_ratelimit.py`（TokenBucket 算法）
- 配置：环境变量（QCM_RATE_LIMIT_*）
- 存储：内存 LRU cache（1000 entries）

#### V0.5-03 Structured Access Log

```json
{
  "ts": "2026-08-10T12:34:56Z",
  "level": "info",
  "method": "POST /rpc",
  "client_ip": "127.0.0.1",
  "user_agent": "claude-code/1.0",
  "tool": "qcm_research",
  "duration_s": 0.234,
  "status": 200,
  "tokens_used": 1523
}
```

#### V0.5-04 Stats API

```python
GET /stats
{
  "uptime_s": 3600,
  "total_requests": 15234,
  "by_tool": {"qcm_research": 4521, "qcm_decide": 3211, ...},
  "by_provider": {"deepseek": 1234, "openai": 567, ...},
  "errors": {"rate_429": 12, "internal": 3},
  "corpus_size_kb": 2048
}
```

#### V0.5-05 健康检查增强

```python
GET /health/ready (V0.5 增强版)
{
  "status": "ready",
  "corpus": {"files": 41, "size_kb": 2048, "loaded_in_s": 0.123},
  "llm": {
    "mode": "real",
    "providers_with_keys": ["deepseek"],
    "recent_calls": {"deepseek": {"calls": 89, "success": 87, "fail": 2}},
  },
  "metrics": {"requests_total": 15234, "errors_total": 23},
}
```

### V0.5 测试用例（预估 15 个）

```
Metrics 端点（3）：
  - GET /metrics · 返回 Prometheus 格式
  - GET /metrics · 包含所有关键指标
  - /metrics · 不计请求（避免递归）

Rate Limiting（4）：
  - 100 req/min 正常
  - 第 101 req 返回 429
  - Per-token 限流
  - Retry-After header

Access Log（3）：
  - 写入 JSON Lines
  - 含 client_ip + tool
  - 失败不阻塞主流程

Stats（3）：
  - /stats 返回 200
  - 按工具/Provider 统计
  - uptime 计算

Health（2）：
  - /health/ready 含 LLM 状态
  - /health/degraded 状态
```

---

## V0.6 · 可扩展性 + 配置化（1 周）

> **目标**：让 QCM MCP Server 支持第三方扩展 + 配置驱动
> **关键产出**：YAML config + Plugin loader + Ollama/Azure + Docker

### 任务清单

| ID | 任务 | 价值 | 实施 | 测试 |
|----|------|------|------|------|
| **V0.6-01** | YAML Config 文件（`qcm_config.yaml`）| 解耦硬编码 | 1 天 | 单元 |
| **V0.6-02** | Plugin 系统（动态加载 tool/provider）| 第三方扩展 | 2 天 | 集成 |
| **V0.6-03** | 新增 3 Provider（Ollama / Azure OpenAI / LM Studio）| 本地+企业 | 1 天 | 集成 |
| **V0.6-04** | WebSocket transport（可选）| 替代 SSE | 1 天 | 集成 |
| **V0.6-05** | Docker 镜像（官方 base image）| 一键部署 | 1 天 | 集成 |
| **V0.6-06** | Docker Compose（QCM + Prometheus + Grafana）| 全栈演示 | 0.5 天 | 集成 |

### 详细规格

#### V0.6-01 YAML Config

```yaml
# qcm_config.yaml
server:
  transport: stdio  # or http
  http:
    host: 127.0.0.1
    port: 8080
  auth:
    require_token: true
    token_env: QCM_AUTH_TOKEN

corpus:
  references_dir: /path/to/references
  outputs_dir: /path/to/outputs

providers:
  deepseek:
    priority: 1
    enabled: true
  openai:
    priority: 2
    enabled: true
  ollama:  # V0.6 新增
    priority: 5
    enabled: true
    base_url: http://localhost:11434/v1
    model: llama3

tools:
  enabled:
    - qcm_research
    - qcm_decide
    - qcm_solve_problem
    - qcm_audit
    - qcm_validate
    - qcm_score_source
  custom:
    - name: my_company_tool
      path: /path/to/plugin.py

logging:
  level: info
  format: json  # or text
  audit_dir: /var/log/qcm-mcp

rate_limit:
  per_ip: 100
  per_token: 1000
  global: 10000
```

#### V0.6-02 Plugin 系统

```python
# 第三方 plugin 示例（my_plugin.py）
from qcm_mcp_server import register_tool

@register_tool(name="my_custom_tool", description="...", input_schema={...})
def my_custom_tool(arg1: str) -> dict:
    return {"result": f"处理 {arg1}"}

# 主程序自动发现 plugins/ 目录下的 .py 文件
# 每个 plugin 文件可以注册多个 tool
```

**Plugin Loader**：
```python
class PluginLoader:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
    
    def load_all(self) -> List[str]:
        """加载所有 plugin，返回加载的工具名列表"""
        ...
    
    def hot_reload(self):
        """热重载（V0.8 实施）"""
        ...
```

#### V0.6-03 新 Provider

```python
PROVIDERS["ollama"] = {
    "priority": 5,
    "base_url": "http://localhost:11434/v1",  # 或用户配置
    "endpoint": "/chat/completions",
    "model": "llama3",  # 或 qwen2.5 / mistral
    "auth_header": "Authorization",
    "auth_prefix": "Bearer ",  # Ollama 接受任意 token
    "env_key": "OLLAMA_HOST",  # 或 "ANY_KEY"
    "max_tokens_param": "max_tokens",
    "timeout_s": 60,  # 本地可能慢
}

PROVIDERS["azure_openai"] = {
    "priority": 6,
    "base_url": "${AZURE_OPENAI_ENDPOINT}/openai/deployments/${AZURE_DEPLOYMENT}",
    "endpoint": "/chat/completions?api-version=2024-12-01-preview",
    "model": "gpt-4o",  # deployment name
    "auth_header": "api-key",
    "auth_prefix": "",
    "env_key": "AZURE_OPENAI_API_KEY",
    "max_tokens_param": "max_tokens",
    "timeout_s": 30,
}

PROVIDERS["lm_studio"] = {
    "priority": 7,
    "base_url": "http://localhost:1234/v1",
    "endpoint": "/chat/completions",
    "model": "local-model",
    "auth_header": "Authorization",
    "auth_prefix": "Bearer ",
    "env_key": "LM_STUDIO_HOST",
    "max_tokens_param": "max_tokens",
    "timeout_s": 60,
}
```

#### V0.6-04 WebSocket Transport（可选）

```python
# WebSocket 端点
GET /ws (Upgrade: websocket)
- 客户端建立 WS 连接
- 通过 WS 发送 JSON-RPC 请求
- 服务端通过 WS 推送响应（含流式）
```

#### V0.6-05 Docker 镜像

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY scripts/ ./scripts/
COPY references/ ./references/
COPY outputs/ ./outputs/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV QCM_ROOT=/app
EXPOSE 8080
ENTRYPOINT ["python", "scripts/qcm_mcp_server.py", "--transport", "http", "--port", "8080"]
```

#### V0.6-06 Docker Compose

```yaml
version: '3.8'
services:
  qcm-mcp:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./logs:/var/log/qcm-mcp
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### V0.6 测试用例（预估 18 个）

```
YAML Config（4）：
  - 加载合法 YAML
  - 缺字段用默认值
  - 错误字段报告错误
  - 环境变量替换 ${VAR}

Plugin 系统（5）：
  - 自动发现 plugin 文件
  - 加载单文件多 tool
  - 加载错误隔离
  - Plugin 优先级
  - Plugin 元数据查询

Provider（5）：
  - Ollama ping（无真实服务）
  - Azure OpenAI URL 模板
  - LM Studio 配置

WebSocket（2）：
  - 建立连接
  - 收发 JSON-RPC

Docker（2）：
  - 镜像构建成功
  - 容器启动正常
```

---

## V0.7 · MCP 协议完整化（1 周）

> **目标**：实现 MCP 2024-11-05 全部核心 API + 跟进 2025-03 流式响应
> **关键产出**：Resources API + Prompts API + Sampling API + Streaming

### 任务清单

| ID | 任务 | 价值 | 实施 | 测试 |
|----|------|------|------|------|
| **V0.7-01** | MCP Resources API（resources/list + resources/read）| 暴露 corpus | 1 天 | 集成 |
| **V0.7-02** | MCP Prompts API（prompts/list + prompts/get）| 标准化调用 | 1 天 | 集成 |
| **V0.7-03** | MCP Sampling API（sampling/createMessage）| 高级用法 | 1 天 | 集成 |
| **V0.7-04** | MCP 2025-03 流式响应（notifications/stream + progress）| 大输出友好 | 2 天 | 集成 |
| **V0.7-05** | MCP 协议版本自动协商（capabilities 完整声明）| 兼容新版 | 0.5 天 | 单元 |

### 详细规格

#### V0.7-01 Resources API

```python
# List available resources
POST /rpc {"method": "resources/list"}
{
  "result": {
    "resources": [
      {"uri": "qcm://corpus/action-orders.md", "name": "action-orders", "mimeType": "text/markdown"},
      {"uri": "qcm://corpus/tools.md", "name": "tools", "mimeType": "text/markdown"},
      {"uri": "qcm://tools/A01", "name": "tool A01 SPC", "mimeType": "application/json"},
      ...
    ]
  }
}

# Read specific resource
POST /rpc {"method": "resources/read", "params": {"uri": "qcm://corpus/action-orders.md"}}
{
  "result": {
    "contents": [{"uri": "qcm://corpus/action-orders.md", "text": "..."}]
  }
}
```

**资源类型**：
- `qcm://corpus/{filename}` - 任意 corpus 文件
- `qcm://tools/{num}` - 工具定义（A01-F10）
- `qcm://masters/{name}` - 大师档案（21 位）
- `qcm://standards/{name}` - 标准引用

#### V0.7-02 Prompts API

```python
POST /rpc {"method": "prompts/list"}
{
  "result": {
    "prompts": [
      {
        "name": "qcm_research_default",
        "description": "QCM 默认研究 prompt 模板",
        "arguments": [
          {"name": "query", "required": true},
          {"name": "level_hint", "required": false},
        ]
      },
      ...
    ]
  }
}

POST /rpc {"method": "prompts/get", "params": {"name": "qcm_research_default", "arguments": {...}}}
{
  "result": {
    "messages": [
      {"role": "user", "content": {"type": "text", "text": "..."}}
    ]
  }
}
```

**预设 prompt 模板**：
- `qcm_research_default` - 通用研究
- `qcm_decide_emergency` - 紧急决策
- `qcm_audit_quick` - 快速审计
- `qcm_solve_5why` - 5Why 求解

#### V0.7-03 Sampling API

```python
# 服务端反向调用 LLM（sampling/createMessage）
POST /rpc {"method": "sampling/createMessage", "params": {
  "messages": [...],
  "maxTokens": 1024,
  "modelPreferences": {"hints": [{"name": "qcm-recommended"}]}
}}
{
  "result": {
    "role": "assistant",
    "content": {"type": "text", "text": "..."},
    "model": "deepseek-chat",
    "stopReason": "endTurn"
  }
}
```

#### V0.7-04 流式响应

```python
# notifications/progress
POST /rpc {"method": "tools/call", "params": {...}}
# 服务端持续推送：
{"method": "notifications/progress", "params": {"progressToken": "...", "progress": 25, "total": 100}}
{"method": "notifications/progress", "params": {"progressToken": "...", "progress": 50, "total": 100}}
{"method": "notifications/progress", "params": {"progressToken": "...", "progress": 100, "total": 100}}

# 流式完成
{"method": "notifications/message", "params": {"data": "..."}}
{"method": "notifications/complete", "params": {"result": {...}}}
```

### V0.7 测试用例（预估 20 个）

```
Resources（5）：
  - resources/list 包含 corpus 资源
  - resources/read 单个文件
  - resources/read 不存在的 URI 报错
  - 资源 URI 格式
  - MIME type 正确

Prompts（5）：
  - prompts/list 包含预设模板
  - prompts/get 返回 messages
  - 必填参数校验
  - 参数替换
  - 自定义 prompt 注册

Sampling（4）：
  - sampling/createMessage 调 LLM
  - modelPreferences 过滤
  - maxTokens 上限
  - stopReason 正确

Streaming（6）：
  - tools/call 返回 progressToken
  - progress 推送 ≥1 次
  - progress 100% 后 complete
  - 中断连接
  - 错误时 partial result
  - SSE 推送 progress
```

---

## V0.8 · 性能 + 缓存（1 周）

> **目标**：把 QCM MCP Server 推到生产级性能（>100 QPS + <100ms p95）
> **关键产出**：多进程 + SQLite cache + LLM cache + Hot reload

### 任务清单

| ID | 任务 | 价值 | 实施 | 测试 |
|----|------|------|------|------|
| **V0.8-01** | 多进程 HTTP server（gunicorn/uvicorn 适配）| >100 QPS | 1 天 | 压测 |
| **V0.8-02** | Corpus SQLite Cache（启动时间 -50%）| 性能 | 1 天 | 基准 |
| **V0.8-03** | LLM Response Cache（prompt hash → response）| 重复 -90% | 2 天 | 集成 |
| **V0.8-04** | Hot reload corpus（mtime 检测）| 无重启更新 | 1 天 | 集成 |
| **V0.8-05** | Connection pool（HTTP 客户端复用）| 性能 | 0.5 天 | 基准 |

### 详细规格

#### V0.8-01 多进程 HTTP

```python
# gunicorn 适配
# gunicorn_config.py
workers = 4  # 进程数 = CPU 核数
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8080"
keepalive = 30

# 或 uvicorn（更现代）
uvicorn qcm_mcp_server:app --host 0.0.0.0 --port 8080 --workers 4
```

**改造点**：
- 用 `uvicorn` 替换 `ThreadingHTTPServer`
- WSGI/ASGI 应用对象替代 main()
- 共享 corpus 用 multiprocessing.Manager 或 SQLite

#### V0.8-02 SQLite Cache

```python
# corpus.db schema
CREATE TABLE corpus_files (
  name TEXT PRIMARY KEY,
  mtime INTEGER NOT NULL,
  content TEXT NOT NULL,
  size INTEGER NOT NULL
);

CREATE TABLE tools (
  num TEXT PRIMARY KEY,
  name TEXT,
  face TEXT,
  dims TEXT  -- JSON array
);

CREATE INDEX idx_corpus_mtime ON corpus_files(mtime);
```

**启动流程**：
1. 检查 `corpus.db` 是否存在
2. 对比 mtime，只重读变化的
3. 启动时间：第一次 ~1s，二次 ~50ms

#### V0.8-03 LLM Cache

```python
# cache.db schema
CREATE TABLE llm_cache (
  prompt_hash TEXT PRIMARY KEY,
  provider TEXT,
  model TEXT,
  response TEXT,
  created_at INTEGER,
  ttl_s INTEGER  # 默认 7 天
);

# 命中逻辑
if prompt_hash in cache:
    return cached_response
else:
    response = real_call()
    save_to_cache(prompt_hash, response)
    return response
```

**Cache Key**：MD5(prompt + system + temperature + max_tokens + provider)
**Cache 失效**：TTL 到期 / corpus 变更 / 用户显式 invalidate

#### V0.8-04 Hot Reload

```python
class CorpusWatcher:
    def __init__(self, directory: str):
        self.directory = directory
        self.mtimes = {}
    
    def start(self):
        """每 5 秒检查文件 mtime"""
        while True:
            for f in os.listdir(self.directory):
                current_mtime = os.path.getmtime(f)
                if self.mtimes.get(f) != current_mtime:
                    self.reload_file(f)
                    self.mtimes[f] = current_mtime
            time.sleep(5)
    
    def reload_file(self, filename):
        """重读单个文件 + 更新缓存"""
        # 更新 corpus_files / tools 表
        # 触发 plugin 重新加载（如果 V0.6 已实施）
```

### V0.8 测试用例（预估 15 个）

```
多进程（3）：
  - 4 进程启动
  - 跨进程共享 corpus
  - 进程优雅退出

SQLite Cache（4）：
  - 首次构建 cache
  - 增量更新
  - 启动时间 <100ms
  - 损坏 cache 重建

LLM Cache（4）：
  - 命中缓存
  - 缓存写入
  - TTL 失效
  - cache invalidation

Hot Reload（4）：
  - 修改文件触发重载
  - 5 秒内生效
  - 工具更新可见
  - 无重启
```

---

## V0.9 · 安全 + 多租户（1 周）

> **目标**：让 QCM MCP Server 达到企业准入标准
> **关键产出**：OAuth 2.0 + TLS + Multi-tenant + RBAC

### 任务清单

| ID | 任务 | 价值 | 实施 | 测试 |
|----|------|------|------|------|
| **V0.9-01** | OAuth 2.0 / JWT 认证 | 企业认证 | 2 天 | 集成 |
| **V0.9-02** | TLS/HTTPS 内置（Let's Encrypt）| 端到端加密 | 1 天 | 集成 |
| **V0.9-03** | Multi-tenant（per-tenant token + corpus）| SaaS 化 | 1 天 | 集成 |
| **V0.9-04** | 细粒度 RBAC（per-tool 权限）| 权限控制 | 0.5 天 | 单元 |
| **V0.9-05** | Secret 加密（API Key 不落盘）| 安全合规 | 0.5 天 | 单元 |

### 详细规格

#### V0.9-01 OAuth 2.0

```python
# 认证流程
POST /oauth/token
grant_type=client_credentials
client_id=xxx
client_secret=xxx

# 返回
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "..."
}

# 资源访问
POST /rpc
Authorization: Bearer eyJ...
```

**支持的 grant_types**：
- `client_credentials`（最常用 · M2M）
- `authorization_code`（用户登录）
- `refresh_token`

#### V0.9-02 TLS

```python
# 启动 HTTPS server
python qcm_mcp_server.py --transport http \
  --ssl-cert /path/to/cert.pem \
  --ssl-key /path/to/key.pem

# Let's Encrypt 自动续期
python qcm_mcp_server.py --transport http \
  --lets-encrypt --domain mcp.example.com
```

#### V0.9-03 Multi-tenant

```python
# tenant 配置
tenants:
  - id: company_a
    token_env: COMPANY_A_TOKEN
    corpus_dir: /tenants/company_a/corpus
    tools:
      enabled: [qcm_research, qcm_decide]
      disabled: [qcm_solve_problem]
  
  - id: company_b
    token_env: COMPANY_B_TOKEN
    corpus_dir: /tenants/company_b/corpus
    tools:
      enabled: [qcm_research]
```

#### V0.9-04 RBAC

```python
# per-tool 权限
policies:
  - role: viewer
    tools: [qcm_research, qcm_decide]
  - role: auditor
    tools: [qcm_audit, qcm_validate]
  - role: admin
    tools: [ALL]
```

### V0.9 测试用例（预估 12 个）

```
OAuth（4）：
  - client_credentials 流程
  - access_token 验证
  - refresh_token 刷新
  - 错误 client 拒绝

TLS（3）：
  - HTTPS server 启动
  - 客户端验证证书
  - 混合 HTTP/HTTPS

Multi-tenant（3）：
  - tenant 隔离
  - token 路由
  - corpus 隔离

RBAC（2）：
  - role 限制 tool 访问
  - 越权返回 403
```

---

## V1.0 · 生产就绪（2 周）

> **目标**：QCM MCP Server v1.0 GA · 业界一流 Skill 5.00/5.00
> **关键产出**：Helm Chart + OpenAPI + 完整测试 + 性能基准 + 完整文档

### 任务清单

| ID | 任务 | 价值 | 实施 | 测试 |
|----|------|------|------|------|
| **V1.0-01** | Helm Chart（K8s 标准化部署）| 一键 K8s | 2 天 | 集成 |
| **V1.0-02** | OpenAPI 3.1 规范（自动生成）| 集成友好 | 1 天 | 单元 |
| **V1.0-03** | 8 引擎 + 60 MCP 测试 100% 覆盖 | 质量保证 | 持续 | - |
| **V1.0-04** | 性能基准报告（含 LLM 真实路径）| 可信度 | 1 天 | 基准 |
| **V1.0-05** | 业界一流 Skill 5.00/5.00 验证 | 终极目标 | 1 天 | 完整回归 |
| **V1.0-06** | CHANGELOG + Release Notes | 运维 | 0.5 天 | - |
| **V1.0-07** | 安装部署文档（README + 故障排查）| 用户体验 | 1 天 | - |

### 详细规格

#### V1.0-01 Helm Chart

```yaml
# values.yaml
replicaCount: 2
image:
  repository: qcm/mcp-server
  tag: "1.0.0"
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: mcp.qcm.example.com
      paths:
        - path: /
          pathType: Prefix

env:
  - name: DEEPSEEK_API_KEY
    valueFrom:
      secretKeyRef:
        name: qcm-secrets
        key: deepseek-api-key

probes:
  liveness:
    httpGet:
      path: /health/live
      port: 8080
  readiness:
    httpGet:
      path: /health/ready
      port: 8080

metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

#### V1.0-02 OpenAPI 3.1

```yaml
# 自动生成 openapi.yaml
openapi: 3.1.0
info:
  title: QCM MCP Server API
  version: 1.0.0
paths:
  /rpc:
    post:
      summary: JSON-RPC 2.0 endpoint
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/JSONRPCRequest'
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JSONRPCResponse'
  /sse:
    get:
      summary: Server-Sent Events
  /metrics:
    get:
      summary: Prometheus metrics
  /health:
    get:
      summary: Health overview
  /health/live:
    get:
      summary: K8s liveness
  /health/ready:
    get:
      summary: K8s readiness
```

#### V1.0-03 测试覆盖目标

| 套件 | 现状 | V1.0 目标 |
|------|------|----------|
| 8 引擎 | 579/579 | 600+ 用例 |
| 4 MCP | 60/60 | 100+ 用例（含 V0.5-V0.9）|
| 新增（V0.5）| - | +15 Metrics/Rate Limit |
| 新增（V0.6）| - | +18 Config/Plugin/Provider |
| 新增（V0.7）| - | +20 Resources/Prompts/Sampling/Streaming |
| 新增（V0.8）| - | +15 多进程/Cache/Hot reload |
| 新增（V0.9）| - | +12 OAuth/TLS/Multi-tenant/RBAC |
| **V1.0 总计** | - | **约 850+ 用例** |

#### V1.0-04 性能基准

| 场景 | 目标 | 实测 |
|------|------|------|
| 启动时间（V0.8 SQLite cache）| <100ms | - |
| 启动时间（首次）| <1s | - |
| tools/call p50 (mock) | <50ms | - |
| tools/call p95 (mock) | <200ms | - |
| tools/call p50 (real LLM) | <3s | - |
| tools/call p95 (real LLM) | <10s | - |
| 并发 (4 workers) | >100 QPS | - |
| Memory per worker | <500MB | - |

#### V1.0-05 业界一流 5.00/5.00

5 维度评分（每项 5.00）：
- 协议完整性（MCP 全 API + 2025-03 流式）✅
- 入口层现代化（SKILL.md V8.0+ 4 层级 + 5 范式）✅
- 命名术语统一（naming-convention.md）✅
- 输出形态完整性（4 形态 × 40 检查）✅
- 测试覆盖（850+ 用例 · 8 引擎 + 6 MCP 套件）✅

**额外加分项**：
- ✅ Manifest 双绑
- ✅ K8s/Helm 部署
- ✅ OpenAPI 文档
- ✅ Docker 镜像
- ✅ OAuth 2.0 + TLS

#### V1.0-06 CHANGELOG

```markdown
# V1.0.0 (2026-XX-XX) · Production Ready

## Added
- [V0.5] Metrics · Rate Limiting · Structured Access Log · Stats API
- [V0.6] YAML Config · Plugin System · Ollama/Azure/LM Studio · WebSocket · Docker
- [V0.7] MCP Resources · Prompts · Sampling · 2025-03 Streaming
- [V0.8] Multi-process · SQLite Cache · LLM Cache · Hot Reload
- [V0.9] OAuth 2.0 · TLS/HTTPS · Multi-tenant · RBAC
- [V1.0] Helm Chart · OpenAPI 3.1 · Performance Benchmarks

## Verified
- 8 引擎：600+ 用例 100% 绿
- 6 MCP 套件：100+ 用例 100% 绿
- 业界一流评分：5.00/5.00

## Breaking Changes
- Config 从环境变量迁移到 YAML
- Default auth 从可选改为必选（OAuth 2.0）
```

### V1.0 测试用例（预估 30+）

```
Helm（5）：
  - helm install 成功
  - K8s deployment 启动
  - Service/Ingress 配置
  - probes 工作
  - 升级测试

OpenAPI（4）：
  - 自动生成
  - 字段完整
  - 与实际 API 同步
  - Swagger UI 可访问

性能基准（8）：
  - 启动时间
  - QPS
  - p50/p95
  - Memory/CPU
  - SQLite cache 效果
  - LLM cache 命中率
  - Hot reload 延迟
  - 并发扩展

完整回归（13）：
  - 8 引擎 + 5 MCP 套件
```

---

## 总任务数与周期

| 版本 | 任务数 | 测试用例 | 周期 |
|------|--------|---------|------|
| V0.5 | 5 | +15 | 1 周 |
| V0.6 | 6 | +18 | 1 周 |
| V0.7 | 5 | +20 | 1 周 |
| V0.8 | 5 | +15 | 1 周 |
| V0.9 | 5 | +12 | 1 周 |
| V1.0 | 7 | +30 | 2 周 |
| **总计** | **33** | **+110** | **~7 周** |

---

## 风险与依赖

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| **Infoseek MCP 不就绪** | 中 | 中 | Q3 缺口调研推迟到 Infoseek 就绪后 |
| **MCP 协议大版本** | 中 | 中 | V0.7 跟进 2025-03 |
| **LLM Provider 变化** | 中 | 低 | 4 provider fallback |
| **生产事故** | 低 | 高 | V0.5 Rate Limit + V0.9 OAuth |
| **性能不达标** | 中 | 中 | V0.8 多进程 + Cache |
| **安全漏洞** | 中 | 高 | V0.9 OAuth + TLS + RBAC |

---

## 待用户决策

| 决策 | 选项 | 建议 | 阻塞 |
|------|------|------|------|
| **V0.5 启动** | A) 立即开始 · B) 等待 Infoseek | A | ❌ 不阻塞 |
| **优先级排序** | 按文档顺序 · 自定义 | 按文档 | - |
| **延期交付** | Q1 2027 vs Q4 2026 | Q4 2026 | - |
| **新 Provider 优先级** | Ollama / Azure / LM Studio | Ollama（本地化趋势）| - |

---

## 参考文档

| 文档 | 路径 |
|------|------|
| 兼容性评估 | `qcm_mcp_eval.md` |
| 路径规划（旧）| `qcm_mcp_path.md` |
| 缺口追踪 | `gap_tracker.md` |
| 协议层 SOLE | `action-orders.md` V8.0+ |
| 当前版本 | `CHANGELOG.md` |

---

**启动条件**：用户确认后进入 V0.5 实施（1 周交付 Metrics + Rate Limit + Access Log + Stats + Health）。
**关键里程碑**：V0.5 = 运维级 · V0.7 = 协议完整 · V1.0 = 生产 GA · 业界一流 5.00/5.00。