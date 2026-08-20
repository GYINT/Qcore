# QCM MCP Server 集成路径（QCM MCP Path）

> **目标**：把 QCM 从「文件型 Skill」升级为「MCP Server 型技能」，与 Infoseek（v2.1.3+）同层对等
> **协议层 SOLE 权威**：`action-orders.md` §8 QCM-Infoseek 归因协议 + §10 Infoseek 收敛协议
> **设计参考**：Infoseek MCP v1.5.0+（6 工具 + stdio/SSE + Bearer Token）

---

## 一、QCM MCP Server 架构设计

### 1.1 核心组件

```
┌──────────────────────────────────────────────────────────┐
│  QCM MCP Server (qcm_mcp_server.py)                      │
├──────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ Transport  │  │ Auth       │  │ Routing    │          │
│  │ stdio/SSE  │  │ Bearer     │  │ T-L 路由   │          │
│  └────────────┘  └────────────┘  └────────────┘          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ 6 Tools    │  │ Corpus     │  │ LLM Router │          │
│  │ research   │  │ 文件加载   │  │ 4 provider │          │
│  │ score...   │  │ action-    │  │ fallback   │          │
│  │ decide     │  │ action-orders.md │  │            │          │
│  │ solve...   │  │ tools.md   │  │            │          │
│  │ audit      │  │ cases.md   │  │            │          │
│  │ validate   │  │ outputs/   │  │            │          │
│  └────────────┘  └────────────┘  └────────────┘          │
└──────────────────────────────────────────────────────────┘
```

### 1.2 工具清单（6 Tools）

| # | 工具名 | 输入 | 输出 | 对应协议 |
|---|--------|------|------|----------|
| 1 | `qcm_research` | query (str), level (L1-L4), context (dict) | 4 形态输出之一 + trace | action-orders.md §1-§7 |
| 2 | `qcm_score_source` | url (str), content (str), domain (str) | score (0-100), tier (1-4), reason | action-orders.md §12 风险评价 |
| 3 | `qcm_decide` | problem_text, urgency (T1-T4) | layer (L1-L4), tools (A-F), masters | action-orders.md §3 决策路由 |
| 4 | `qcm_solve_problem` | problem_dict (T-L 全字段), context | 5 段式输出 + 双归零判据 | action-orders.md §6 围堵消除 |
| 5 | `qcm_audit` | decision_output (dict) | 字段校验 + 引用追溯 + 风险 | action-orders.md §12 五维风险 |
| 6 | `qcm_validate` | output_text (str), form (case/decision/assessment/quick) | 40 检查矩阵 + 通过率 | outputs/ 4 形态 × 10 项 |

### 1.3 传输与认证

| 项 | 配置 | 参考 Infoseek |
|----|------|---------------|
| **stdio** | 默认（开发/Cursor/Codex） | infoseek_mcp_server.py --transport stdio |
| **SSE** | 生产（HTTP 部署） | --transport sse --port 8080 |
| **Bearer Token** | INFOSEEK_AUTH_TOKEN → QCM_AUTH_TOKEN | openssl rand -hex 32 |
| **健康检查** | GET /health | K8s 探针 |
| **审计日志** | audit.log | JSON Lines |

### 1.4 LLM 路由（4 Provider Fallback）

| Provider | 优先级 | 用途 | Fallback |
|----------|--------|------|----------|
| DeepSeek | P0 | 中文深度推理 | → OpenAI |
| OpenAI GPT-4o | P1 | 多模态/工具调用 | → Claude |
| Claude Sonnet | P2 | 长文本/合规 | → Qwen |
| Qwen-Max | P3 | 中文 fallback | → DeepSeek |

---

## 二、6 工具契约详解

### 2.1 `qcm_research`

**功能**：端到端质量调研（输入 T1-T4 → 4 形态输出）

**输入 schema**：
```json
{
  "query": "焊接虚焊客诉复发怎么破",
  "level_hint": "T3",                  // T1/T2/T3/T4
  "context": {
    "industry": "汽车",
    "process": "焊接",
    "urgency": "重要",
    "crisis_grade": "中度"
  }
}
```

**输出 schema**：
```json
{
  "version": "QCM v8.0+",
  "form": "case-application",         // 4 形态之一
  "level": "L3",
  "tools_used": ["A01 SPC", "B01 FMEA", "F01 8D"],
  "masters": ["戴明", "克劳士比"],
  "output_markdown": "...",
  "trace": {
    "t1_to_l1": {...},
    "t2_to_l2": {...},
    "t3_to_l3": {...},
    "t4_to_l4": {...}
  },
  "confidence": 0.85,
  "data_sources": ["action-orders.md §6", "cases.md §焊接"]
}
```

### 2.2 `qcm_score_source`

**功能**：对源 URL/内容做 5 维评分（对应 Infoseek Anchor_Score）

| 维度 | 权重 | 评估 |
|------|------|------|
| 主题一致性 | 30% | 与 QCM 主题/工艺/工具的契合度 |
| 来源可信度 | 40% | tier 1-4（ISO/IATF/AIAG-VDA/ASQ = tier 1）|
| 时效性 | 20% | 衰减系数（< 30 天 ×1.0；> 365 天 ×0.3）|
| 完整性 | 10% | 是否覆盖 T1-T4 + L1-L4 |

**输出**：
```json
{
  "score": 78.5,
  "tier": 2,
  "gate": "核心自动采集（≥70）",
  "reason": "AIAG-VDA 2019 + 主题契合 + 时效 0.9",
  "domain_match": ["汽车", "SPC", "FMEA"]
}
```

### 2.3 `qcm_decide`

**功能**：T-L 路由决策（T1-T4 → L1-L4）

**逻辑**（来自 action-orders.md §3）：
- T1 (5 字段 40 秒) → L1 (24h 操作级)
- T2 (+8 字段 2 分) → L2 (1-2 周选型级)
- T3 (+4 字段 4 分) → L3 (2-3 周执行级)
- T4 (+5 字段 6 分) → L4 (贯穿整季治理级)

**输出**：
```json
{
  "layer": "L3",
  "tools": ["A01", "B01", "F01"],
  "masters": ["戴明", "克劳士比"],
  "rationale": "复发≥2 + T3 输入 → 三链闭环 + 8D + 双归零"
}
```

### 2.4 `qcm_solve_problem`

**功能**：完整解决问题（5 段式 + 双归零）

**输入**：完整 T1-T4 字段（F1-F24）+ 上下文

**输出**：5 段式 markdown
```
1. 行动要项（围堵/消除/纠正/预防）
2. 事态导航（时间线 + 决策点）
3. 危机沟通（ITIL P1-P4 模板）
4. 行动措施（具体步骤 + 责任人）
5. 双归零（技术归零 + 管理归零）
```

### 2.5 `qcm_audit`

**功能**：审计已生成决策/输出

**校验项**：
- 字段完整性（必填 vs 实际）
- 引用追溯（每条引用必须指向 action-orders.md 或 cases.md）
- 风险评估（五维：覆盖/有效性/可追溯/可重复/可持续）
- 工具落格（A-F 编号在 86 工具范围内）
- 大师引用（21 位核心范围内）

**输出**：
```json
{
  "audit_score": 92.5,
  "passed": true,
  "warnings": ["F15 未引用 action-orders.md §6"],
  "errors": [],
  "suggestions": ["补充 8D D4-D7 步骤"]
}
```

### 2.6 `qcm_validate`

**功能**：4 形态输出合规校验（10 项 × 4 = 40 检查）

| 形态 | 10 项检查 |
|------|-----------|
| case-application | 5 段式完整/数据说话/双归零/工具编号/大师引用/三链/治理/标准/危机等级/可追溯 |
| decision-card | 围堵 24h/3 行精简/工具明确/责任清晰/数据支撑/风险/治理/标准/合规/可执行 |
| assessment-report | 4 层 × 25 分/趋势分析/根因/治理/标准/文化/可持续/可对比/数据源/可审计 |
| quick-response | 30 秒判定/D 总分表/应急动作/责任人/上报路径/复盘/预防/工具/标准/合规 |

**输出**：
```json
{
  "form": "case-application",
  "checks_passed": 38,
  "checks_failed": 2,
  "score": 95.0,
  "failures": ["check_07_标准引用缺失", "check_10_可追溯链路断裂"]
}
```

---

## 三、实施路线图（v0.1 → v1.0）

### 阶段 1：v0.1 MVP（预计 1 周）
- [ ] 实现 stdio 传输（最简）
- [ ] 6 工具 stub（无 LLM 调用，纯规则）
- [ ] T-L 路由决策（硬编码）
- [ ] 文件 corpus 加载（read-only）
- [ ] Bearer Token 认证（基础）

**验收**：能通过 stdio 调用 6 工具；输出符合 action-orders.md 协议

### 阶段 2：v0.2 LLM 集成（预计 1 周）
- [ ] LLM Router 4 provider
- [ ] `qcm_research` 接入 LLM
- [ ] `qcm_solve_problem` 接入 LLM
- [ ] 自动 fallback 链路
- [ ] 成本监控

**验收**：LLM 调用成功率 ≥95%；fallback 链路验证

### 阶段 3：v0.3 SSE + 生产化（预计 1 周）
- [ ] SSE 传输（HTTP）
- [ ] GET /health 健康检查
- [ ] audit.log 审计
- [ ] K8s 探针
- [ ] 文档（README + .mcp.json）

**验收**：能通过 HTTP/SSE 调用；K8s 部署成功

### 阶段 4：v0.4 Infoseek 协同（预计 1 周）
- [ ] 与 Infoseek MCP 互联（QCM 调 Infoseek）
- [ ] 缺口自动暴露（V8.0+ §13）
- [ ] 混合策略 3 阶段触发
- [ ] 自动入库主库

**验收**：Q3 2026 P1（AI 工具 G 域 + ISO 42001）调研自动完成

### 阶段 5：v1.0 正式版（预计 2 周）
- [ ] 全量回归（8 引擎 × 579 用例）
- [ ] 业界一流 Skill 5.00/5.00 验证
- [ ] 完整文档（SKILL.md + manifest.yaml）
- [ ] 双源同步 + 灾备
- [ ] 双 MCP 互通验证

**验收**：QCM 与 Infoseek 双 MCP 协同工作；缺口调研 0 手动介入

---

## 四、与 Infoseek 协同架构

```
用户 (Claude/Codex)
    ↓ MCP 协议
┌─────────────────────────────────────────┐
│  QCM MCP Server        Infoseek MCP     │
│  (qcm_mcp_server.py)   (infoseek_*_server.py)│
│  ┌─────────────────┐   ┌──────────────┐ │
│  │ qcm_research    │ ←→│ search       │ │
│  │ qcm_decide      │ ←→│ research     │ │
│  │ qcm_solve_problem│   │ score_source │ │
│  │ qcm_audit       │   │ evaluate     │ │
│  └─────────────────┘   └──────────────┘ │
│         ↓                   ↓           │
│     action-orders.md   infoseek_db.json │
│     tools.md           archives/        │
│     cases.md                           │
└─────────────────────────────────────────┘
    ↓ 缺口暴露驱动（V8.0+ §13）
┌─────────────────────────────────────────┐
│  gap_tracker.md（Q3 2026 待办）          │
│  - GAP-001 ISO 42001                    │
│  - GAP-002 AI 工具 G 域                 │
│  - GAP-003 数字孪生                     │
│  - GAP-004/005 软件/金融                │
│  - GAP-006 ESG                          │
│  - GAP-007 AI 大师                      │
│  - GAP-008/009 区块链/物流              │
└─────────────────────────────────────────┘
```

**协同触发**（QCM MCP v0.4）：
1. QCM 处理 T-L 输入，识别缺口
2. 缺口分 ≥3 → 调用 `infoseek_research`
3. Infoseek 5 维评分 → 主库/归因历史/终止
4. QCM 消化入库（action-orders.md / cases.md / tools.md）
5. audit.log 记录 + 反哺 gap_tracker.md

---

## 五、关键决策（待用户确认）

### 决策 1：MVP 优先级
- A) 6 工具全 stub（v0.1 一次性交付）
- B) 先 2 工具（decide + validate）后补（v0.1 + v0.1.5）

### 决策 2：LLM Provider 优先级
- A) DeepSeek 优先（中文质量 + 成本）
- B) OpenAI 优先（生态成熟）
- C) Claude 优先（合规/长文）

### 决策 3：传输协议优先级
- A) stdio 优先（开发友好）
- B) SSE 优先（生产部署）

### 决策 4：Infoseek 协同时机
- A) v0.4 阶段再协同（先稳定 QCM）
- B) v0.2 阶段就联通（边开发边协同）

---

## 六、参考文档

| 文档 | 路径 | 用途 |
|------|------|------|
| Infoseek MCP 集成契约 | `references/Infoseek_MCP_v1_5` | 仿照 6 工具 + stdio/SSE + Bearer Token |
| action-orders v8plus | `references/action-orders.md` | 协议层 SOLE 权威 |
| gap_tracker.md | `references/gap_tracker.md` | 缺口任务待办（Q3 2026）|
| quarterly_update.md | `references/quarterly_update.md` | 季度更新节奏 |

---

**路径启动条件**：用户确认决策 1-4 → 进入 v0.1 实施
**预计落地**：v0.1 MVP ~1 周；v1.0 ~5-6 周
**关键里程碑**：v0.4 = Infoseek 协同 + Q3 2026 缺口调研自动化