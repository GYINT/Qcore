---
form: decision_card
version: 8.3
status: stable
sections: [决策/责任/动作]
---

# 输出层 · 决策卡片（Decision Card · V5.0+ 严格分离）

> **定位**：输出层 4 大形态之 ② · 应急/选型决策的精简 5 段式 · 协议层依赖 §1 AO 卡 + §4 触发 · Token ~50
> **V5.0+ 严格分离**：本模板仅引用协议层 AO 卡与触发条件 · **不展开 5×5 双归零** · **不复述 4×N 表格**
> **核心用途**：让决策者 30 秒内抓住核心 · 应急响应 / 选型决策 / 治理决策

---

## 1. 标准模板（V5.0+ 严格分离 · 3 行决策卡）

```markdown
【应急决策卡】围堵阶段

【路由】意图={意图} · 领域={领域} · 置信度={置信度}（如有歧义请纠正 · §14 场景路由判定）
├─ 决策：D 总分 {N}（{D1+D2+D3}）→ ITIL P{1-4}
├─ 责任：{责任主体}（{L 层子标签}·{时间维度}）
├─ 动作：{响应动作 1} + {响应动作 2} + {响应动作 3}【R:{责任} · C:{配合} · I:{知会}】
└─ 双归零：{L 层} 简版（{展开级别}）

【选型决策卡】消除阶段
├─ 决策：{决策主题}（{3 维度评估}）
├─ 责任：{责任主体}（{L 层子标签}·{时间维度}）
├─ 动作：{选型动作 1} + {选型动作 2}【R:{责任} · C:{配合} · I:{知会}】
└─ 双归零：{L 层} 简版（{展开级别}）

【治理决策卡】预防阶段
├─ 决策：{决策主题}（{触发条件}）
├─ 责任：{责任主体}（{L 层子标签}·{时间维度}）
├─ 动作：{治理动作 1} + {治理动作 2}【R:{责任} · C:{配合} · I:{知会}】
└─ 双归零：{L 层} 总结版（10 项全 ✅）
```

---

## 2. 模板字段说明

| 字段 | 含义 | 协议层引用 |
|------|------|----------|
| `{N}` | D 总分（0-9）| action-orders §3.1 |
| `{D1+D2+D3}` | 传播性+严重性+紧迫性 | action-orders §3.1 |
| `{1-4}` | ITIL P1-P4 | action-orders §3.2 |
| `{责任主体}` | 应急：客服+店长 / 选型：副总+CEO / 治理：董事会 | action-orders §5 |
| `{L 层子标签}` | L1/L2/L3/L4 | action-orders §1 |
| `{时间维度}` | 24h/1-2周/2-3周/季末 | action-orders §1 |
| `{响应动作 1+2+3}` | 围堵/消除/预防具体动作（≤3 步）| action-orders §1 |
| `{3 维度评估}` | 工艺/成本/风险 或 质量/成本/时效 | action-orders §1.2 |
| `{展开级别}` | L1 简版/L2 简版/L3 完整/L4 总结 | action-orders §3.4 |

---

## 3. 严格分离规则（V5.0+）

| 规则 | 内容 |
|------|------|
| ① | **仅 3 行决策**（决策 + 责任 + 动作）· 不展开 5 段式 |
| ② | **不展示完整 5 段式** · 不展示 D 折叠段 |
| ③ | **不展开双归零 5×5** · 仅引用展开级别名称 |
| ④ | **不引用工具/标准/大师标签**（决策卡片不展开底层）|
| ⑤ | **30 秒决策支持** · 一张卡片 = 一个决策点 |

---

## 4. 决策卡片 4 模板（按动作阶段）

### 4.1 围堵阶段决策卡（D ≥4 触发）

```
【围堵决策卡】
├─ 决策：D{N}（{D1}/{D2}/{D3}）→ {危机等级} → ITIL P{1-4}
├─ 责任：{责任主体}（{L 层子标签}·24h 内）
├─ 动作：① {隔离/首响} ② {溯源/补偿} ③ {8D D1-D2 启动}
└─ 双归零：L1 简版（前 3 技术 + 前 2 管理）
```

### 4.2 消除阶段决策卡（试点决策）

```
【消除决策卡】
├─ 决策：{决策主题}（3 维度：{维度1} / {维度2} / {维度3}）
├─ 责任：{责任主体}（L2 选型级·1-2 周）
├─ 动作：① {选型方案} ② {试点验证}
└─ 双归零：L2 简版（前 5 条）含措施有效 + 举一反三
```

### 4.3 纠正阶段决策卡（执行落地）

```
【纠正决策卡】
├─ 决策：{执行主题}（L3 执行级·2-3 周）
├─ 责任：{责任主体}（工艺/设备工程师·执行验证）
├─ 动作：① {8D D4-D7} ② {CAPA} ③ {同型排查}
└─ 双归零：L3 完整版（10 项 + ✅/⏳）
```

### 4.4 预防阶段决策卡（治理沉淀）

```
【预防决策卡】
├─ 决策：{治理主题}（L4 治理级·危机后 + ≥2 次同类）
├─ 责任：{责任主体}（董事会+质量部·4 层 × N 维度）
├─ 动作：① {经验沉淀} ② {横向推广}
└─ 双归零：L4 总结版（10 项全 ✅ · 经验入 AO-4）
```

---

## 5. 4 形态定位（V6.0 P4）

| 形态 | Token | 周期 | 触发场景 |
|------|-------|------|---------|
| ① 案例应用 | ~700 | 长期 | 实战案例（完整 5 段式）|
| **② 决策卡片（本文件）** | **~50** | **即时** | **应急/选型/治理决策** |
| ③ 评估报告 | ~120 | 季度 | 治理水平评分 |
| ④ 快速响应 | ~30 | 即时 | 现场判定 |

> **引用协议层**：action-orders.md §2.3 · §1 AO 卡 · §4 L1-L4 触发矩阵 · §5 责任层定义。

---

## 6. V6.1-6.3 增强契约（Phase 1+2+3）

### 6.1 输入契约（input_schema · V6.2）

```yaml
input_schema:
  type: object
  required:
    - crisis_level (enum)        # 微型/普通/中度/重度
    - d_score (object)           # D1+D2+D3 评分
      - d1_communication (int 1-3)  # 传播性
      - d2_severity (int 1-3)       # 严重性
      - d3_urgency (int 0-3)        # 紧迫性
    - action_stage (enum)        # 围堵/消除/纠正/预防
  optional:
    - affected_party (string)    # 受影响方
    - timeline (string)           # 时间线
  validation:
    - d_score 总和 0-9
    - action_stage 与危机等级匹配
```

### 6.2 输出契约（output_schema · V6.2）

```yaml
output_schema:
  type: object
  required:
    - form (string)              # "decision_card"
    - decision (string)          # 决策点（D 总分 + 危机等级 + ITIL P）
    - responsibility (string)    # 责任主体
    - action (string)             # 3 步动作
    - double_zero (string)        # 展开级别引用
  optional:
    - execution_trace (object)   # V6.3 新增
    - uncertainty_markers (array)
    - data_freshness (string)
    - side_effects (object)
  forbidden:
    - 财务预测
    - 内部敏感数据
    - 编造统计数字
    - 5×5 双归零详情（仅引用展开级别）
```

### 6.3 副作用声明（side_effects · V6.1）

```yaml
side_effects:
  changes: 无副作用（仅输出决策）
  rollback: 不适用
  idempotent: true (可重读)
  auto_retry: false
  data_pollution: 无
  state_pollution: 上下文快照不可变
  cleanup_skill: 不适用
```

### 6.4 降级路径（V6.2）

| 输入完整性 | 输出策略 |
|----------|---------|
| **完整 D 评分** | D 总分 + ITIL P + AO 卡模板全显示 |
| **仅危机等级** | 显示等级 + 默认 D 评分（D=中等）+ 责任主体默认 |
| **仅围堵触发** | 仅输出"围堵决策卡"+ 询问关键 D 评分 |
| **极简（query）** | 仅一行判定 + 询问关键信息 |

### 6.5 边界声明（V6.1）

- **不适用场景**：纯财务决策 / 纯法务决策 / 战略级长期规划（用评估报告）/ 完整案例分析（用案例应用）
- **输出边界**：不展开 5×5 双归零详情（仅引用 L1/L2/L3/L4 展开级别）/ 不展示 D 折叠段 / 不引用工具标准大师标签
- **Token 边界**：决策卡片 ≤80 Token · 30 秒决策支持

### 6.6 禁止内容清单（V6.2）

- 不得输出：5×5 双归零详情 / 工具实例详情 / 标准条款 / 大师观点
- 不得输出：财务预测 / 内部数据 / 编造统计
- 决策点必须可执行（不含"待定"或"待评估"等模糊词）

### 6.7 执行轨迹（execution_trace · V6.3）

```yaml
execution_trace:
  phase_1_anchor:
    inputs_received: [crisis_level, d_score, action_stage]
    protocol_matched: action-orders.md §1.1-§1.4 (AO 卡 4 张)
    output_form_matched: decision_card (V6.0 P4)
  phase_2_compile:
    sections_filled: [决策, 责任, 动作, 双归零]
    field_count: 4 sections × 1-3 items = ~10 fields
    degraded_fields: 0 (完整输入)
  phase_3_validate:
    output_validator_result: pending
    side_effects_declared: true
    defensive_output_applied: true
    [unverified]_markers: 0
  phase_4_deliver:
    output_token: ~50
    decision_time: ≤30 秒
    trigger_words: 0 (决策卡片不需 D 折叠)
```

### 6.8 [unverified] 标注规则（V6.2）

- **必须标注**：D 评分数据来源 / 危机等级判定依据 / 责任主体分配逻辑
- **格式**：同案例应用 `[unverified]` 后接内容

### 6.9 数据时效声明（V6.2）

```
数据时效：决策卡基于实时 D 评分判定，无历史数据依赖。
D 评分依赖：现场观察 + 历史数据 + 趋势预测。
```
