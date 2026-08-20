# QCM × Infoseek 传输层 + 认证层协同规划（V0.4.2 · 2026-08-12）

> **目标**：跨设备/跨用户协同的传输层（SSE/HTTP）与认证层（OAuth 2.0）完整设计
> **关联**：action-orders.md §8.5（降级协议）· QCM V0.9（OAuth 已实现）· Infoseek v3.0.0 GA（SSE/HTTP 已支持）

---

## 一、现状盘点

| 项 | QCM | Infoseek |
|----|-----|----------|
| stdio | ✅ V0.1 | ✅ v1.5.0 |
| HTTP /rpc | ✅ V0.3 | ✅ v1.5.2 |
| SSE | ✅ V0.3 | ✅ v1.5.1 |
| WebSocket | ❌（V0.7.1 推迟）| ❌ |
| Bearer Token | ✅ V0.1 | ✅ v1.5.1 |
| OAuth 2.0 | ✅ V0.9（client_credentials + JWT）| ❌（需实施）|
| RBAC | ✅ V0.9 | ❌ |
| Secret 加密 | ✅ V0.9（Fernet）| ❌ |
| Multi-tenant | ⚠️ V0.9.3 推迟 | ❌ |

---

## 二、传输层规划（SSE + HTTP）

### 2.1 三层传输选择矩阵

| 协同场景 | 传输 | 理由 |
|----------|------|------|
| 本地单设备（QCM→Infoseek）| stdio | 最快 · 零网络 |
| 跨设备（QCM 客户端→Infoseek 服务端）| **HTTP /rpc** | 短请求-响应 · 成熟 |
| 长任务（research_v3 30s+）| **SSE** | 逐步推送 · 可中断 |
| 流式研究（streaming_research 7 步）| **SSE** | first yield <500ms 立即可见 |
| 双向实时（未来）| WebSocket（V0.7.1）| 全双工 |

### 2.2 SSE 协同协议（推荐主路径）

```
QCM 客户端                          Infoseek 服务端（--transport sse --port 8080）
    │  POST /rpc {"method":"initialize"}            │
    │──────────────────────────────────────────────→│
    │  POST /rpc {"method":"tools/call",             │
    │    "params":{"name":"research_stream",         │
    │              "arguments":{"subject":"..."}}}   │
    │──────────────────────────────────────────────→│
    │  GET /sse（流式连接）                           │
    │←──────────────────────────────────────────────│
    │  event: progress  data: {"step":"score_complete"}     │
    │  event: progress  data: {"step":"wikidata_complete"}  │
    │  event: progress  data: {"step":"entity_graph_complete"}│
    │  event: progress  data: {"step":"conflict_complete"}   │
    │  event: progress  data: {"step":"profile_complete"}    │
    │  event: progress  data: {"step":"trajectory_complete"} │
    │  event: result   data: {"step":"report_complete","report":"..."} │
```

### 2.3 HTTP /rpc 协同协议（短调用）

```
POST http://infoseek:8080/rpc
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "research_v3",
    "arguments": {"subject": "焊接虚焊", "lite": true}
  }
}
```

### 2.4 传输降级链（跨设备）

```
SSE（流式）→ 不可用 → HTTP /rpc（短调用）→ 不可用 → stdio（本地）→ 不可用 → mock（§8.5）
```

---

## 三、认证层规划（OAuth 2.0）

### 3.1 认证演进（现状 → 目标）

| 阶段 | 现状 | 目标（V0.4.2+）|
|------|------|----------------|
| V0.9 现状 | Bearer Token（静态）+ client_credentials | ✅ 已有 |
| 跨设备 | 每设备独立 token（无法撤销）| **OAuth 2.0 + JWT（可撤销）** |
| 跨用户 | 无用户概念 | **RBAC（viewer/contributor/editor/admin）** |
| 企业级 | 无 SSO | **OIDC（Keycloak 对接）** |

### 3.2 OAuth 2.0 授权流程（client_credentials）

```
┌─────────┐        ┌──────────────┐        ┌─────────────┐
│ QCM 客户端│ ────→ │ OAuth Provider│ ────→ │ Infoseek    │
│ (设备 A) │        │ (Keycloak)   │        │ (服务端)    │
└─────────┘        └──────────────┘        └─────────────┘
    ① client_id + client_secret
    ② POST /oauth/token → access_token (JWT)
    ③ Authorization: Bearer <JWT>
    ④ RBAC 检查（scope: tools/call + resource: infoseek）
    ⑤ audit.log（user_id + device_id + action）
```

### 3.3 JWT 结构（QCM V0.9 已实现 · Infoseek 对齐）

```json
{
  "sub": "client_1234",
  "scope": ["tools/call", "resources/read"],
  "roles": ["contributor"],
  "tenant": "team-a",
  "exp": 1786516000,
  "iat": 1786512400
}
```

### 3.4 RBAC 角色矩阵（跨设备协同）

| 角色 | QCM 工具 | Infoseek 工具 | 协同动作 |
|------|----------|---------------|----------|
| **viewer** | 只读（research/validate）| search_anchors/fetch_content（只读）| 查询归因结果 |
| **contributor** | 全部 + attribution | research_v3/research_stream | 发起协同调研 |
| **editor** | 全部 + validate 写入 | save_archive/dedup_stats | 归档 + 治理 |
| **admin** | 全部 + config | 全部 | 配置 + 审计 |

### 3.5 跨设备协同 Token 生命周期

| 事件 | 动作 |
|------|------|
| 设备注册 | client_credentials → 长期 client_id + secret |
| 用户登录 | OAuth → 短期 JWT（1h）|
| JWT 过期 | refresh_token → 新 JWT |
| 设备吊销 | 撤销 client_id → 所有 JWT 失效 |
| 用户离职 | 撤销 subject → RBAC 降级 |

---

## 四、Infoseek 端 OAuth 实施清单（V0.4.2 任务）

| # | 任务 | 工作量 |
|---|------|--------|
| 1 | `scripts/infoseek_auth.py`：AuthManager（client_credentials + JWT + RBAC）| 0.5 天 |
| 2 | `POST /oauth/token` 端点 | 0.2 天 |
| 3 | `_check_auth` 中间件（Bearer Token + JWT 双兼容）| 0.3 天 |
| 4 | `_check_rbac` 工具级权限 | 0.3 天 |
| 5 | Secret 加密（Fernet + XOR fallback）| 0.2 天 |
| 6 | audit.log 扩展（user_id + device_id）| 0.2 天 |
| 7 | SSE + HTTP 认证集成 | 0.3 天 |
| **合计** | | **2 天** |

---

## 五、QCM 端调用远程 Infoseek（V0.4.2 扩展）

```python
# qcm_infoseek_bridge.py 扩展：transport 参数
class InfoseekBridge:
    def __init__(self, transport="stdio", host=None, port=None,
                 client_id=None, client_secret=None):
        self.transport = transport  # stdio / http / sse
        self.auth = OAuthClient(client_id, client_secret) if client_id else None
    
    def research_v3(self, subject, **kw):
        if self.transport == "stdio":
            return self._stdio_call("research_v3", subject)
        elif self.transport == "http":
            return self._http_call("research_v3", subject)  # Bearer JWT
        elif self.transport == "sse":
            return self._sse_call("research_stream", subject)  # 流式
```

### 传输自动选择逻辑

```python
def _select_transport():
    """本地 stdio · 远程 HTTP/SSE · 不可用降级"""
    if os.path.exists(INFOSEEK_SERVER):
        return "stdio"                    # 本地最优
    if os.environ.get("INFOSEEK_REMOTE_URL"):
        if os.environ.get("INFOSEEK_SSE", "1") == "1":
            return "sse"                  # 长任务流式
        return "http"                     # 短调用
    return None                           # §8.5 降级
```

---

## 六、部署拓扑（跨设备协同）

### 6.1 单设备（当前）
```
QCM (stdio) ──→ Infoseek (stdio subprocess)
```

### 6.2 跨设备（V0.4.2 目标）
```
设备 A：QCM MCP Server ──HTTP/SSE + OAuth──→ 中心 Infoseek Server（K8s）
设备 B：QCM MCP Server ──HTTP/SSE + OAuth──→ 中心 Infoseek Server
设备 C：CLI ──────────────HTTP + OAuth───→ 中心 Infoseek Server
```

### 6.3 部署形态
- **单机**：docker-compose（QCM + Infoseek 双容器）
- **K8s**：Helm Chart（qcm-mcp + infoseek-mcp + keycloak）
- **服务发现**：Service + Ingress（QCM helm 已有）

---

## 七、风险与权衡

| 风险 | 影响 | 缓解 |
|------|------|------|
| OAuth 复杂度 | 实施成本 +2 天 | 复用 QCM V0.9 qcm_auth.py（复制改造）|
| SSE 连接管理 | 长连接资源占用 | 超时 5min + keepalive + 断线重连 |
| Token 泄露 | 跨设备攻击面 | JWT 短时效 + Secret 加密 + 审计 |
| 传输降级 | 协同中断 | §8.5 降级链（L2 Web / L3 协议）|

---

## 八、实施顺序（V0.4.2）

```
Phase A · 传输层（0.5 天）
  ├─ Infoseek SSE 认证集成（Bearer + OAuth）
  └─ QCM bridge transport 参数（stdio/http/sse）

Phase B · 认证层（1.5 天）
  ├─ infoseek_auth.py（复制 QCM qcm_auth.py 适配）
  ├─ /oauth/token 端点
  └─ RBAC + audit 扩展

Phase C · 集成测试（0.5 天）
  ├─ qcm_mcp_v042_test.py（传输降级 + OAuth 用例）
  └─ 全量回归
```

**合计：~2.5 天**
