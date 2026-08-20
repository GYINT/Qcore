---
form: quick_response
version: 8.3
status: stable
sections: [判定/立即动作]
---

# 输出层 · 快速响应（Quick Response · V5.0+ 严格分离）

> **定位**：输出层 4 大形态之 ④ · 现场判定 / 应急处置 / 巡检 · 协议层依赖 §3.1 危机判定（D 总分）· Token ~30
> **V5.0+ 严格分离**：本模板仅引用 D 总分判定 · **不展开 D1+D2+D3 评分细则** · **不复述 4×N 表格**
> **核心用途**：让一线人员 30 秒内判定危机等级并立即行动 · 现场应急

---

## 1. 标准模板（V5.0+ 严格分离 · 1-2 段式）

```markdown
【路由】意图={意图} · 领域={领域} · 置信度={置信度}（§14 场景路由判定）
【现场快速判定】
├─ 危机等级：{危机等级} · D 总分 {N}/9（{D1+D2+D3} 简评）
├─ ITIL P 等级：P{1-4}（{触发条件}）
└─ 立即动作：{立即动作 1} + {立即动作 2}（责任：{责任主体}·{L 层子标签}）

【后续】
- 围堵阶段：{24h 内必做}
- 升级条件：{升级阈值}（如 D 总分升至 ≥7 或 ≥10% 复发率）
```

---

## 2. 极简模板（30 秒版本 · 仅 1 行）

```
【判定】{危机等级}（D={N}）→ ITIL P{1-4} → AO-1 围堵（{24h}·{责任主体}）
```

---

## 3. 模板字段说明

| 字段 | 含义 | 协议层引用 |
|------|------|----------|
| `{危机等级}` | 微型/普通/中度/重度 | action-orders §3.2 |
| `{N}/9` | D 总分（0-9）| action-orders §3.1 |
| `{D1+D2+D3}` | 3 维简评（1-3/1-3/0-3）| action-orders §3.1 |
| `{1-4}` | ITIL P1 Critical / P2 High / P3 Medium / P4 Low | action-orders §3.2 |
| `{触发条件}` | D 总分 ≥4 / 客户紧急 / 同型 ≥2 次 | action-orders §4 |
| `{立即动作 1+2}` | 围堵：隔离/首响/溯源 | action-orders §1.1 |
| `{责任主体}` | 应急：客服+店长 / 围堵：车间主任+主操 | action-orders §5 |
| `{L 层子标签}` | L1 / L2 / L3 / L4 | action-orders §1 |
| `{24h}` | 围堵阶段时间维度（默认折叠）| action-orders §1.1 |
| `{升级阈值}` | D 升级 / 复发率 / 客户投诉升级 | action-orders §3.2 |

---

## 4. D 总分快速判定（30 秒参考表）

| D 总分 | 危机等级 | ITIL | AO 模板 | 立即动作 |
|--------|---------|------|---------|---------|
| 0-2 | 微型 L1 | P4 Low | AO-1 简化（4 字段）| 监控 + 记录 |
| 3 | 普通 L1 | P3 Medium | AO-1 标准 6 字段 | 24h 内处理 |
| **4-6** | **中度 L1** | **P2 High** | **AO-1 危机型 6+3T** | **24h 围堵 + 3T 沟通** |
| **7-9** | **重度 L1** | **P1 Critical** | **AO-1 危机型 6+3T + 双归零 + 升级** | **24h 围堵 + 危机升级 + 董事会** |

---

## 5. 严格分离规则（V5.0+）

| 规则 | 内容 |
|------|------|
| ① | **1-2 段式** · 不展开 5 段式 |
| ② | **不展示 D1+D2+D3 评分细则** · 仅引用 D 总分 |
| ③ | **不引用工具/标准/大师** · 仅判定+立即动作 |
| ④ | **30 秒判定支持** · 一行 = 一个判定 |
| ⑤ | **后续必给**（围堵阶段必做 + 升级阈值）|

---

## 6. 现场判定 4 模板

### 6.1 服务现场（零售/餐饮）

```
【判定】重度危机（D=8）→ ITIL P1 Critical → AO-1 围堵（24h·客服+店长）
├─ 立即动作：① 客服致歉+撤热搜 ② 同批次下架+全额退款
└─ 升级条件：晒图传播 ≥10 个平台 / 投诉 ≥3 起
```

### 6.2 生产现场（制造业）

```
【判定】中度危机（D=6）→ ITIL P2 High → AO-1 危机型（24h·车间主任+主操）
├─ 立即动作：① 同批次隔离+停机检查 ② 8D D1-D2 启动
└─ 升级条件：Cpk 降至 <1.0 / 客户端投诉 / 同型 ≥3 套
```

### 6.3 客服现场（IT/服务）

```
【判定】重度危机（D=9）→ ITIL P1 Critical → AO-1 危机型+升级（24h·客服主管+值班工程师）
├─ 立即动作：① 系统隔离+故障定级 ② RTO ≤30min 启动+客户通知
└─ 升级条件：业务中断 ≥1h / 数据丢失 / ≥10 客户受影响
```

### 6.4 治理现场（公司级）

```
【判定】重度危机（D=7）→ ITIL P1 Critical → AO-4 预防阶段（季末·董事会）
├─ 立即动作：① 危机复盘+双归零总结 ② 同型 3 批次横向排查
└─ 升级条件：复发率 ≥10% / 客户重大投诉 / 合规风险
```

---

## 7. 4 形态定位（V6.0 P4）

| 形态 | Token | 周期 | 触发场景 |
|------|-------|------|---------|
| ① 案例应用 | ~700 | 长期 | 实战案例 |
| ② 决策卡片 | ~50 | 即时 | 应急/选型决策 |
| ③ 评估报告 | ~120 | 季度 | 治理水平评分 |
| **④ 快速响应（本文件）** | **~30** | **即时** | **现场判定 / 应急处置** |

> **引用协议层**：action-orders.md §3.1 危机判定 + §3.2 危机分级 + §1.1 AO-1 围堵遏制。

---

## 8. V6.1-6.3 增强契约（Phase 1+2+3）

### 8.1 输入契约（input_schema · V6.2）

```yaml
input_schema:
  type: object
  required:
    - query (string)              # 现场问题描述
  optional:
    - d1 (int 1-3)                # 传播性（如已知）
    - d2 (int 1-3)                # 严重性（如已知）
    - d3 (int 0-3)                # 紧迫性（如已知）
    - location (string)           # 现场位置
    - on_site_role (string)       # 一线人员角色
  validation:
    - query ≥10 字符
    - 若 d1+d2+d3 全部提供，则计算 D 总分
```

### 8.2 输出契约（output_schema · V6.2）

```yaml
output_schema:
  type: object
  required:
    - form (string)              # "quick_response"
    - crisis_level (enum)        # 微型/普通/中度/重度
    - d_score (string)           # D 总分（如已知）
    - itil_p (enum)              # P1-P4
    - immediate_action (string)   # 立即动作
    - followup (string)          # 后续（围堵 + 升级条件）
  optional:
    - execution_trace (object)   # V6.3 新增
    - uncertainty_markers (array)
    - data_freshness (string)
    - side_effects (object)
  forbidden:
    - 财务预测
    - 内部敏感数据
    - 编造统计
    - 模糊判定（如"情况比较严重"无等级）
```

### 8.3 副作用声明（side_effects · V6.1）

```yaml
side_effects:
  changes: 判定记录可追溯（如需）
  rollback: 不适用
  idempotent: true (可重读)
  auto_retry: false
  data_pollution: 无
  state_pollution: 上下文快照不可变
  cleanup_skill: 不适用
```

### 8.4 降级路径（V6.2）

| 输入完整性 | 输出策略 |
|----------|---------|
| **D 评分完整** | D 总分 + ITIL P + AO 卡模板 + 立即动作 |
| **仅危机描述** | 默认 D = 中等（6）+ P2 + 立即动作 + 询问关键 D 评分 |
| **极简（query）** | 一行判定 + 询问关键信息（危机类型/严重程度）|

### 8.5 边界声明（V6.1）

- **不适用场景**：长期治理（用评估报告）/ 完整案例分析（用案例应用）/ 战略决策（用决策卡片）
- **输出边界**：1-2 段式 · 不展开 5 段式 · 不展示 D 折叠段 · 不引用工具标准大师标签
- **Token 边界**：快速响应 ≤50 Token · 30 秒判定支持

### 8.6 禁止内容清单（V6.2）

- 不得输出：模糊判定 / 财务预测 / 编造统计 / 内部数据
- 判定必须明确（危机等级 + ITIL P + AO 卡）
- 必须给出立即动作（≥1 步）

### 8.7 执行轨迹（execution_trace · V6.3）

```yaml
execution_trace:
  phase_1_anchor:
    inputs_received: [query, optional D 评分]
    protocol_matched: action-orders.md §3.1 危机判定
    output_form_matched: quick_response (V6.0 P4)
  phase_2_compile:
    sections_filled: [判定, 立即动作, 后续, 升级条件]
    field_count: 4 sections × 1-2 items = ~8 fields
    degraded_fields: 可能 1-2 (D 评分缺失)
  phase_3_validate:
    output_validator_result: pending
    side_effects_declared: true
    defensive_output_applied: true
    [unverified]_markers: ≥0 (D 评分缺失时标注)
  phase_4_deliver:
    output_token: ~30
    response_time: ≤30 秒
    trigger_words: 0 (快速响应不需 D 折叠)
```

### 8.8 [unverified] 标注规则（V6.2）

- **必须标注**：D 评分默认时 / 危机等级推测时 / 立即动作基于经验时
- **格式**：同案例应用 `[unverified]`

### 8.9 数据时效声明（V6.2）

```
数据时效：快速响应基于实时 D 评分判定，无历史数据依赖。
判定时延：≤30 秒（D 评分缺失则默认中等）。
升级机制：D 总分升至 ≥7 或 ≥10% 复发率 → 触发第二幕。
```
