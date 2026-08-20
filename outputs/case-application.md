---
form: case_application
version: 8.3
status: stable
sections: [行动要项/事态导航/危机沟通/行动措施/后续计划/双归零]
---

# 输出层 · 案例应用（Case Application · V5.0+ 严格分离）

> **定位**：输出层 4 大形态之 ① · 实战案例完整 5 段式 · 协议层依赖最全（§1-§7）· Token ~700
> **V5.0+ 严格分离**：本模板**不复述**协议层 4×N 维度表 · 不展开底层工具/标准/大师 · 时间维度默认折叠
> **协议层引用**：`action-orders.md`（单一权威 · 严格分离声明）

---

## 1. 标准模板（V5.0+ 严格分离）

```markdown
# {案例名称}（{危机等级} · {行业} · V5.0+ 严格分离）

【路由】意图={意图} · 领域={领域} · 置信度={置信度}（如有歧义请纠正 · §14 场景路由判定）
【工具预选】{领域工具集}（A制造→SPC/MSA · B设计→DOE/QFD · C供应链→8D/SCAR · D现场→5Why/鱼骨 · E体系→内审/管理评审 · F战略→方针管理 · R风险→FMEA · Q客户→KANO/VOC）

【行动要项】 <!-- 组件：_action_items -->
策略：{策略内容}
方向：{方向内容}
优先级：{优先级}（护栏 {护栏依据}）

【事态导航】 <!-- 组件：_state_nav -->
危机：{危机等级} · {危机描述}
根因：{根因 1} + {根因 2}
机遇链：{机遇链主链} 主 + {协同链} 协同
做多少：围堵（{时间}）→ 消除（{时间}）→ 纠正（{时间}）→ 预防（{时间}）

【危机沟通】3T × 3 列表（6 列） <!-- 组件：_crisis_comm -->
围堵阶段·第一幕·0-30 min：{话术}
消除阶段·第二幕·30 min-6 h：{话术}
纠正阶段·第三幕·6 h-3 d：{话术}

【行动措施】动作阶段 × 案例数据 <!-- 组件：_measures -->（V5.0+ 严格分离·不展开 4×N 表格）
> V8.2 决策桥：复杂场景（D≥4+特征）下，AO 卡内容由探针画像填充（导航阶段→§4 精化 · 组织层→§5 责任 · 16格→措施范围 · 多链→方案维度 · 取物→工具列 · 定深→归零版本）
> V8.2：措施条目带迷你 RACI（责任 R / 配合 C / 知会 I · 每措施必有 A=问责，A 由 §5 责任层映射；C/I 各 ≤2；涉及供应商→{{role:SQE}} A、客户→{{role:CQE}} A）
围堵阶段（{时间} · ⏳）：{具体动作}【R:{责任} · C:{配合} · I:{知会}】（探针：{16格落点/组织层}）
消除阶段（{时间} · ⏳）：{具体动作}【R:{责任} · C:{配合} · I:{知会}】（探针：{多链起点/取物工具}）
纠正阶段（{时间} · ⏳）：{具体动作} + 双归零 L3 完整版（10 项 + ✅/⏳ · 详见 action-orders.md §3.4）（探针：{措施范围}）
预防阶段（{时间} · ⏳）：{具体动作} + L4 组织治理 4 层 × N 维度（详见 action-orders.md §7）（探针：{治理格}）

【后续计划】 <!-- 组件：_followup -->
L2（{责任层}·决策授权）：{一句话}
L3（{责任层}·执行验证）：{一句话}
L4（{责任层}·沉淀推广）：{一句话}

【双归零】按动作阶段展开 <!-- 组件：_dual_zero -->（详见 action-orders.md §3.4）
围堵阶段：L1 简版（启动信号·前 3 技术 + 前 2 管理）
消除阶段：L2 简版（前 5 条）含措施有效 + 举一反三前项
纠正阶段：L3 完整版（5×5 = 10 项 + ✅/⏳）
预防阶段：L4 总结版（10 项全 ✅ · 经验入 AO-4 + 横向推广）

【定位探针】（可选段 · V8.2 · 默认折叠 · 触发词 `展开定位`）
> 触发：D≥4（中度及以上）+ 特征开关（多链/隐蔽/复发）· 重度无特征半展开
- 组织层：{战略/管理/业务/执行} 归属 + 责任层
- 流程面：{系统/管理/过程/产品} 切入
- 多链：{发生链→流出链→系统链} 起点顺序
- 16 格落点（全展开时）：{组织四层 × 流程四面 交叉格}
- 纵轴定深：{L1-L4}
- 取物：{治理格 + 工具格 + 置信度}
- 诊断结论 + 导航：特征={多链/隐蔽/复发} → AO-{映射阶段} · 3A5WHY {链}展开 · 工具 {编号}
  （映射表见 action-orders §2.1 · 多特征优先级：复发>隐蔽>多链）
- 分层检阅（超复杂时）：L1 概览 → L2 单链 → L3 逐格（§6 折叠）

```

---

## 2. 模板字段说明

| 字段 | 含义 | 协议层引用 |
|------|------|----------|
| `{案例名称}` | 案例标题 | — |
| `{危机等级}` | 微型/普通/中度/重度 | action-orders §3.2 |
| `{行业}` | 服务业零售/制造业/航空业等 | — |
| `{策略/方向/优先级}` | 行动要项 3 要素 | action-orders §2.1 |
| `{护栏依据}` | 毛利护栏/合规护栏/安全护栏 | — |
| `{根因 1+2}` | 事态导航·查要因 | action-orders §2 |
| `{机遇链}` | OTC/ITR/MTL/LTC 主+协同 | action-orders §3 |
| `{时间}` | 各动作阶段时间窗（24h/1-2周/2-3周/季末）| action-orders §1 |
| `{话术}` | 3T × 3 列表 · 6 列 | action-orders §3.3 |
| `{具体动作}` | 案例具体动作（不复述协议层定义）| action-orders §1 |
| `{责任层}` | 制造业/零售业等 | action-orders §5 |
| `{工具标签}` | F01/A01/B01 等编号 | tools.md |
| `{标准标签}` | GB/IATF/AS9100 等 | governance.md |
| `{大师标签}` | Deming/Taguchi 等 | masters.md |

---

## 3. 严格分离规则（V5.0+）

| 规则 | 内容 |
|------|------|
| ① | **不复述协议层 4×N 表格** · 直接引用 action-orders.md §1 §4 |
| ② | **不展开底层工具详情** · 仅引用标签（F01 8D/A01 SPC 等）|
| ③ | **不展开标准条款** · 仅引用标签（GB 19001/IATF 16949 等）|
| ④ | **不展开大师观点** · 仅引用标签（Deming/Taguchi 等）|
| ⑤ | **时间维度默认折叠**（⏳）· 触发词 `展开时间轴` 展开 |
| ⑦ | **后续计划每层 1 句话**（去工具堆砌）|
| ⑧ | **双归零引用展开级别名称** · 不展开 5×5 表格 |

---

## 4. 示例 · 见 cases.md §六 §7

| 案例 | 行业 | 等级 | 链接 |
|------|------|------|------|
| 花店差评危机 | 服务业零售 | 重度 D=8 | cases.md §六 |
| 汽车零部件模具磨损 | 制造业 | 重度 D=8 | cases.md §六 |
| 半导体晶圆厂光刻良率暴跌 | 制造业·高技术 | 中度 D=6 | cases.md §七-A |
| 航空宇航型号件飞行参数偏移 | 航空业 | 重度 D=7 | cases.md §七-B |

---

## 5. 4 形态定位（V6.0 P4）

```
输出层 4 大形态：
├─ ① 案例应用（本文件 · V5.0+ 严格分离 · Token ~700）
├─ ② 决策卡片（outputs/decision-card.md · 精简 · Token ~50）
├─ ③ 评估报告（outputs/assessment-report.md · 评分 · Token ~120）
└─ ④ 快速响应（outputs/quick-response.md · 即时 · Token ~30）
```

> **引用协议层**：action-orders.md §2.3 "5 段式 × 4 输出形态映射表" 已定义各形态依赖 · 本文件为 ① 案例应用形态。

---

## 6. V6.1-6.3 增强契约（Phase 1+2+3）

### 6.1 输入契约（input_schema · V6.2）

```yaml
input_schema:
  type: object
  required:
    - case_name (string)        # 案例名称
    - industry (string)         # 行业
    - crisis_description (string)  # 危机描述
    - crisis_level (enum)        # 微型/普通/中度/重度
  optional:
    - mds_fields (object)        # MDS F1-F24 部分字段
    - affected_party (string)   # 受影响方（客户端/内部/供应链）
    - timeline (string)          # 危机时间线
  validation:
    - crisis_level ∈ {微型, 普通, 中度, 重度}
    - crisis_description ≥20 字符
```

### 6.2 输出契约（output_schema · V6.2）

```yaml
output_schema:
  type: object
  required:
    - form (string)              # "case_application"
    - action_items (string)      # 行动要项 3 要素
    - situation_navigation (string)  # 事态导航 4 步
    - crisis_communication (string)  # 危机沟通 3T × 3 列表
    - action_measures (string)   # 行动措施 4 阶段
    - followup_plan (string)     # 后续计划 L2-L4
    - double_zero (string)        # 双归零按动作阶段
  optional:
    - execution_trace (object)   # V6.3 新增
    - uncertainty_markers (array)  # [unverified] 标注
    - data_freshness (string)    # 数据时效声明
    - side_effects (object)      # 副作用声明
  forbidden:
    - 财务预测
    - 内部敏感数据
    - 编造统计数字
    - 精确收入数字
```

### 6.3 副作用声明（side_effects · V6.1）

```yaml
side_effects:
  changes: 无副作用（仅输出文本）
  rollback: 不适用
  idempotent: true (可重读)
  auto_retry: false
  data_pollution: 无外部资源占用
  state_pollution: 上下文快照不可变（每次调用独立）
  cleanup_skill: 不适用（仅输出文本，无系统状态变更）
```

### 6.4 降级路径（progressive_enhancement · V6.2）

| 输入完整性 | 条件 | 输出策略 |
|----------|------|---------|
| **完整输入** | MDS T4 齐 22 字段 | 5 段式 + 4 阶段全部展开 |
| **部分输入** | MDS T2-T3 齐 8-17 字段 | 5 段式 + Assumptions 块声明假设 |
| **模糊输入** | MDS T1 齐 5 字段 | 询问 2-3 关键问题 + 简化 5 段式 |
| **极简输入** | 仅 query | 简化为"快速响应"（4 形态之 ④） |

### 6.5 边界声明（boundary · V6.1）

- **不适用场景**：纯财务问题 / 纯法务问题 / 纯营销问题 / 单一工具问答（用工具库 tools.md 而非 QCM）
- **输出边界**：不复述 action-orders.md §1-§7 协议层表格 · 不展开 5×5 双归零 · 不展开底层工具详情 · 不展开标准条款 · 不展开大师观点
- **Token 边界**：完整案例应用 ≤800 Token · 超过需拆分或简化

### 6.6 禁止内容清单（forbidden · V6.2）

- 不得输出：财务预测 / 内部敏感数据 / 编造统计数字 / 精确收入数字
- 不得输出：未经核实的客户名称（除公开上市公司）
- 不得输出：未注明的具体金额或预测数据
- 引用他人观点必须注明来源（[unverified] 标注）

### 6.7 执行轨迹（execution_trace · V6.3）

```yaml
execution_trace:
  phase_1_anchor:  # 锚点定位
    inputs_received: [case_name, industry, crisis_description, crisis_level]
    protocol_matched: action-orders.md §1 §4
    output_form_matched: case_application (V6.0 P4)
  phase_2_compile:  # 数据填充
    sections_filled: [行动要项, 事态导航, 危机沟通, 行动措施, 后续计划, 双归零]
    field_count: 7 sections × ~3-5 items = ~25 fields
    degraded_fields: 0 (完整输入)
  phase_3_validate:  # 验证
    output_validator_result: pending (scripts/qcm_output_validator.py)
    side_effects_declared: true
    defensive_output_applied: true
    [unverified]_markers: 0 (案例已验证)
  phase_4_deliver:  # 交付
    output_token: ~700
    trigger_words: []
```

### 6.8 [unverified] 标注规则（V6.2）

- **必须标注**：未公开数据 / 第三方数据 / 推测结论 / 行业平均估算
- **格式**：`[unverified]` 后接标注内容，例：客户满意度 95% [unverified] · 来源：调研报告
- **不需标注**：action-orders.md / cases.md 内已验证数据 / 公开标准条款 / 已发表论文

### 6.9 数据时效声明（V6.2）

```
数据时效：本案例数据基于截至 2026-08 的公开资料 + 案例库。如需更新数据，请引用最新来源。
时间范围：2024-2026
更新频率：每季度更新（如有）
```
