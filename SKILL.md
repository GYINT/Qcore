---
name: QCM
version: 1.0.0
display_name: Quality Crisis Management（QCM）
description: 'QCM 问题解决指导 Skill · 4 层级架构（输出/协议/输入/底层）· 严格分离 · 动作阶段主·时间维度子 · 输出层 4 形态 · 场景路由消费（意图×领域→形态×组件动态组合）· 组件池三机制（归一化/热度/约束映射）· 5 范式 · action-orders.md 14 章协议权威 · 文件层治理（生命周期/守卫 9 检/归档）· 路径归一化（paths/registry）· 插件扩展（plugins/ 热加载）· 回归全绿 · Infoseek 协同 5 维缺口检测 + 混合策略 3 阶段触发'
author: Forka
license: Apache-2.0
entry_point: SKILL.md
protocol_authority: references/protocol/action-orders.md
manifest: manifest.yaml
manifest_sync: scripts/sync_manifest.py
output_validator: core/validator.py
test_engine: 多引擎回归 + 验证器 全绿
---

# QCM · Quality Crisis Management（质量问题解决指导 Skill）

> 把「质量危机处置 + 体系治理评估 + 知识沉淀」封装成一条可复用的问题解决流水线：输入场景 → 协议匹配 → 场景路由 → 4 形态输出。
> 对外发布版本 **1.0.0** ｜ 内部开发版本基线 **0.0.0**（见 `skill_meta.json` 的 `internal_version`）

---

## 目录

1. [这是什么](#1-这是什么)
2. [快速上手](#2-快速上手)
3. [工作流](#3-工作流)
4. [核心能力](#4-核心能力)
5. [工作机制要点](#5-工作机制要点)
6. [兼容性](#6-兼容性)
7. [路线图](#7-路线图)
8. [触发词](#8-触发词)
9. [配套文档](#9-配套文档)
10. [测试与质量](#10-测试与质量)

---

## 1. 这是什么

QCM 接收一个质量场景（危机事件 / 流程问题 / 治理评估 / 知识问答），自动完成：

1. **输入解析** — 结构化输入契约（mds-input）提取意图 / 领域 / 危机等级（关键词库 keyword.yaml 意图×领域映射）
2. **协议匹配** — 14 章协议权威（action-orders.md）自动匹配：危机分级 → 触发矩阵 → 责任层 → 输出结构
3. **场景路由** — 意图 × 领域 → 形态 × 组件动态组合（置信度驱动，缺命中自动降级）
4. **4 形态输出** — 案例应用 / 决策卡片 / 评估报告 / 快速响应（防御性标注：`[unverified]` + 数据时效 + 边界声明）
5. **缺口协同** — 5 维缺口（行业/危机类型/工具/标准/大师 ≥2）触发 Infoseek 归因（L0→L3 降级链）
6. **回归验证** — 4 形态验证器 + 守卫 9 检 + 多引擎回归（发布门禁）

**3 种使用方式**：直接对话问答 / 作为 MCP Server 被 AI Agent 调用 / 插件扩展（热加载自定义工具）。

### 1.1 适用场景

✅ 制造业质量危机 / 服务业质量危机 / 跨业态质量治理 / 体系成熟度评估 / 现场应急处置 / 质量文化诊断

### 1.2 不适用场景

❌ 纯财务问题 / 纯法务问题 / 纯营销问题 / 单一工具问答（8D 是什么 / SPC 公式等纯知识点）

---

## 2. 快速上手

### 2.1 MCP Server（10 工具）

```bash
pip install -r requirements.txt

# stdio（本地默认）
python scripts/mcp_server.py

# HTTP/SSE（Claude Desktop / Cursor 等客户端）
python scripts/mcp_server.py --transport http --port 8080
```

| 类别 | 工具 | 用途 |
|------|------|------|
| **问题解决核心（6）** | `qcm_research` / `qcm_decide` / `qcm_solve_problem` / `qcm_score_source` / `qcm_audit` / `qcm_validate` | 调研 → 判定 → 完整解决 → 来源评分 → 审计 → 输出校验 |
| **Infoseek 协同（3）** | `qcm_attribution` / `qcm_attribution_phase` / `qcm_gap_detect` | 5 维归因 / 3 阶段混合策略 / 缺口检测 |
| **插件扩展（1）** | `qcm_plugin_echo` | 插件样例（热加载验证） |

### 2.2 3 步启动

```
① 输入结构体（references/contract/mds-input.md）→ 意图/领域/危机等级
② 协议层（references/protocol/action-orders.md）→ 14 协议自动匹配
③ 输出层（outputs/ 4 形态模板）→ 按场景输出（决策卡/案例/评估/快响）
```

### 2.3 快速判定（D 总分路由）

| 场景 | 动作 | 输出形态 |
|------|------|---------|
| D 总分 ≥4 | AO-1 围堵 | 决策卡片 ② |
| 危机期 + 关键决策 | AO-2 应对 | 案例应用 ① |
| 危机期 | AO-3 分解 | 案例应用 ① |
| 危机后 + ≥2 次同类 | AO-4 治理 | 评估报告 ③ |
| 缺口暴露（5 维 ≥2） | 触发 Infoseek 归因 | §13 协同 |

### 2.4 环境变量

| 变量 | 用途 | 默认 |
|------|------|------|
| `QCM_ROOT` | QCM 安装根（路径归一化）| 自身推导 |
| `INFOSEEK_ROOT` | Infoseek 安装根（跨 Skill 协同）| 探测列表 |
| `QCM_KEYWORDS` | 词库路径覆盖 | references/config/keyword.yaml |
| `QCM_AUTH_TOKEN` | MCP 认证 Token | — |

> 完整环境变量、API Key 与依赖说明见 **`DEPENDENCIES.md`** 与 **`API_KEYS.md`**。

---

## 3. 工作流

```
输入场景（危机/流程/评估/问答）
   ↓
阶段一：输入解析（mds-input + keyword.yaml）
   意图/领域/危机等级提取 → 关键词归一化
   ↓
阶段二：协议匹配（action-orders.md 14 章）
   危机分级 §3 → 触发矩阵 §4 → 责任层 §5 → 结构契约 §2
   ↓
阶段三：场景路由（§14 路由协议）
   意图×领域 → 形态×组件 动态组合（置信度门控 + 降级）
   ↓
阶段四：形态输出（4 形态模板）
   案例应用/决策卡/评估报告/快响 + 防御性标注
   ↓
阶段五（可选）：缺口协同（§8/§10/§13）
   5 维缺口 ≥2 → Infoseek 归因（L0→L3 降级）→ 置信度门控入库
```

| 阶段 | 关键模块 | 输入 | 输出 |
|------|---------|------|------|
| 输入解析 | `references/contract/mds-input.md` / `references/config/keyword.yaml` | 场景描述 | 意图/领域/等级 |
| 协议匹配 | `references/protocol/action-orders.md` | 意图×领域 | 协议章节路由 |
| 场景路由 | `core/router.py` / `references/config/router.yaml` | 意图×领域 | 形态×组件序列 |
| 形态输出 | `outputs/*.md` / `core/assembler.py` | 组件序列 | 4 形态成品 |
| 缺口协同 | `scripts/infoseek_bridge.py` | 5 维缺口 | 归因锚点（置信度标注）|
| 回归验证 | `core/validator.py` / `scripts/config_sync.py` | 输出成品 | 96 项校验 / 9 检 |

---

## 4. 核心能力

> 按 **职能分层**：协议权威 → 输出形态 → 场景路由 → 输入词库 → 验证治理 → Infoseek 协同 → MCP 工具

### 4.1 协议层（14 章 · 单一权威）

`references/protocol/action-orders.md`：

| § | 主题 | § | 主题 |
|---|------|---|------|
| §1 | AO 卡 4×N（动作阶段主·时间维度子）| §8 | QCM–Infoseek 归因协议 |
| §2 | 5 段式结构 | §9 | 案例资产化协议 |
| §3 | 危机管理协议（D 总分 · ITIL · 3T · 双归零）| §10 | Infoseek 收敛协议 |
| §4 | L1–L4 触发矩阵 | §11 | 热词与末端触点协议 |
| §5 | 责任层定义 | §12 | 三要素新鲜度与行业适配性协议 |
| §6 | D 折叠段契约（5 触发词）| §13 | 缺口暴露驱动 Infoseek 协同协议 |
| §7 | L4 组织治理 4 层 × N 维度 | §14 | 场景路由协议（意图×领域→形态×组件）|

### 4.2 输出层（4 形态）

| 形态 | 模板 | Token | 周期 | 触发场景 |
|------|------|-------|------|---------|
| ① 案例应用 | `outputs/case-application.md` | ~700 | 长期 | 实战案例（完整 5 段式）|
| ② 决策卡片 | `outputs/decision-card.md` | ~50 | 即时 | 应急/选型/治理决策 |
| ③ 评估报告 | `outputs/assessment-report.md` | ~120 | 季度 | 治理水平评分 |
| ④ 快速响应 | `outputs/quick-response.md` | ~30 | 即时 | 现场判定/应急处置 |

每形态 10 项校验（`core/validator.py` 自动验证）：段模板 / 副作用声明 / 输入契约 / 输出契约 / 降级路径 / 执行轨迹 / `[unverified]` 标注 / 数据时效 / 边界声明 / 禁止内容清单。

### 4.3 场景路由与组件池

| 机制 | 模块 | 简述 |
|------|------|------|
| 场景路由 | `core/router.py` + `references/config/router.yaml` | 意图特征词 × 领域特征词 → 置信度 → 形态映射（无命中自动兜底）|
| 组件归一化 | `references/config/components.yaml` | 组件注册表（容量约束 ≤35）|
| 组件热度 | `core/component_scan.py` | ref_count → new/active/stable 分级（复用 §11 状态机）|
| 约束映射 | `references/config/constraint.yaml` | 意图 × D × 复杂度 → 组件序列动态映射 |

### 4.4 输入与词库

| 文件 | 用途 |
|------|------|
| `references/contract/mds-input.md` | 结构化输入契约（定位卡 + 深度卡 + 落地卡）|
| `references/contract/input-handbook.md` / `input-guide.md` / `input-guide-l0-l3.md` | 输入指引与 L0-L3 降级说明 |
| `references/config/keyword.yaml` | 意图词（5 类）+ 领域词（8 类）+ 歧义词 + 热词分层（L1/L2/L3）|
| `references/config/entities.yaml` | 实体层（标准/工具/大师，单一真源）|
| `references/config/semantic.yaml` / `disambiguation_cases.yaml` | 语义消解 + 歧义案例库 |

### 4.5 验证与治理

| 能力 | 模块 | 简述 |
|------|------|------|
| 4 形态验证 | `core/validator.py` | 96/96 校验项（4 形态 × 24 检查）|
| 双绑校验 | `scripts/sync_manifest.py` | SKILL.md + manifest.yaml + skill_meta.json 字段一致 |
| 守卫 9 检 | `scripts/config_sync.py --check` | 悬空引用/嵌套链接/硬编码/组件容量等 9 项健康检查 |
| 路径归一化 | `scripts/paths.py` + `scripts/registry.py` | 内部路径与跨 Skill 依赖零硬编码 |
| 词库生命周期 | `scripts/keyword_lifecycle.py` | 热词发现→活跃→稳定→升级 base/淘汰 |

### 4.6 Infoseek 协同

| 能力 | 说明 |
|------|------|
| 5 维触发 | 行业/危机类型/工具/标准/大师 缺口 ≥2 维 → 触发归因 |
| 混合策略 3 阶段 | Phase 1 自动浅层 → Phase 2 关键中层 → Phase 3 用户深层 |
| 写入策略 | 置信度 ≥70 入库 / 40–69 归因历史 / <40 终止 |
| 降级链 | L0 Infoseek → L1 本地 corpus → L2 Web/LLM → L3 纯协议 |
| 可选依赖 | Infoseek 未安装时自动降级，不报错 |

### 4.7 MCP 工具（10 个）

见 [2.1 快速上手](#21-mcp-server10-工具)。启动自动挂载：`PluginLoader.load_all()`（失败不阻塞）；热重载：`PluginLoader.hot_reload()`；样例：`plugins/echo_tool.py`。

---

## 5. 工作机制要点

### 5.1 场景路由（§14）

```
意图特征词（5 类）× 领域特征词（8 类）→ 置信度 = 意图命中×α + 领域命中×β
门控：高置信 → 形态×组件动态组合 | 歧义 → 置信度重算 | 无命中 → 知识学习兜底
```

### 5.2 组件池三机制

```
① 归一化：components.yaml 注册表（容量约束，防模板爆炸）
② 热度识别：ref_count → new/active/stable（复用 §11 状态机）
③ 约束映射：意图×D×复杂度 → 组件序列（constraint.yaml）
```

### 5.3 五维触发 + 混合策略

```
行业 → 工艺 → 工具 → 方法论 → 大师/思维（L1→L5）
调研深度：1 → 1-2 → 2 → 2-3 → 3
缺口 ≥2 维 → Phase 1 自动浅层 → Phase 2 关键中层 → Phase 3 用户深层（「展开 D」）
```

### 5.4 降级链（§8.5）

```
L0_infoseek → L1_local（本地 corpus）→ L2_web（AI 搜索/LLM 语义）→ L3_protocol（纯协议 + gap 记录）
```

### 5.5 防御性输出

- 复述禁令：输出层严禁逐行复述协议层 4×N 表格；严禁展开底层工具/标准/大师详情
- 时间维度默认折叠：⏳ 标记，触发词「展开时间轴」展开
- 缺口标注：必须标注 `[Infoseek 补充 · 置信度 X%]`
- 未验证来源：`[unverified]` 标注 + 数据时效 + 边界声明 + 禁止内容清单

---

## 6. 兼容性

- **0 破坏性变更**：对外 1.0.0 与内部 0.0.0 基线解耦，协议层演进（action-orders V8+）不影响发布契约
- **MCP 工具**：10 工具完整保留，新增插件经 `@register_tool` 热加载，不侵入核心
- **可选依赖**：Infoseek / LLM Key 缺失时自动降级（L1→L3），核心功能不报错
- **升级方式**：备份 → 替换目录 → 运行 `python tests/run_all.py` + `python core/validator.py` 验证

---

## 7. 路线图

详见 `docs/CHANGELOG.md`（版本脉络）与 `outputs/`（季度健康报告、优化升级路线）。

**概要**：
- **近期**：发布后优化升级（词库命中率淘汰机制评估、suggest_research 接线、组件文件切分落地）
- **中期**：行业知识包扩展（消费电子/新能源已入，继续规模化）、Infoseek 协同深化
- **长期**：跨 Skill 编排、合规审计自动化、质量文化评估体系（ISO 10010 对齐）
- **设计边界（不做）**：纯财务问题 / 纯法务问题 / 纯营销问题 / 单一工具问答

---

## 8. 触发词

按 **场景 / 技术 / 能力** 三类组织，便于不同检索维度匹配。

### 8.1 场景类（业务用途）

`质量危机` · `危机管理` · `问题解决` · `双归零` · `8D` · `5Why` · `质量治理` · `体系评估` · `成熟度评估` · `现场处置` · `应急处置` · `围堵-消除-纠正-预防` · `质量文化` · `知识沉淀` · `行业拓展`

### 8.2 技术类（方法 / 协议）

`SPC` · `FMEA` · `控制计划` · `IATF 16949` · `ISO 9001` · `AS9100` · `4M1E` · `PDCA` · `PDSA` · `ITIL P1-P4` · `D1-D3` · `AO-1/AO-2/AO-3/AO-4` · `L1-L4 触发矩阵` · `动作阶段主` · `时间维度子` · `5 段式` · `场景路由` · `组件池` · `路径归一化` · `守卫 9 检` · `缺口检测`

### 8.3 能力类（具体函数 / 工具名）

`qcm_research` · `qcm_decide` · `qcm_solve_problem` · `qcm_score_source` · `qcm_audit` · `qcm_validate` · `qcm_attribution` · `qcm_attribution_phase` · `qcm_gap_detect` · `qcm_plugin_echo` · `mcp_server` · `assembler` · `validator` · `infoseek_bridge`

---

## 9. 配套文档

| 文档 | 路径 | 用途 |
|------|------|------|
| README | `README.md` | 快速导航 + 5 秒看懂 |
| 版本历史 | `version_history.md` | 对外版本记录 |
| 协议权威 | `references/protocol/action-orders.md` | 14 章协议（单一权威）|
| 输入契约 | `references/contract/` | mds-input + 输入指引 |
| 词库配置 | `references/config/` | keyword/entities/components/constraint 等 10 配置 |
| 输出模板 | `outputs/` | 4 形态模板（唯一真源）|
| 组件池 | `components/` | 28 组件（索引自动生成，勿手改）|
| 核心库 | `core/` | 路由/组装/验证/组件扫描/缺口检测 |
| 适配层 | `scripts/` | MCP server + 桥接 + 工具模块 |
| 部署资产 | `deploy/` | docker / k8s / monitoring / api |
| 文档 | `docs/` | CHANGELOG / INSTALL / TROUBLESHOOTING / eval |
| 测试套件 | `tests/` | basic / protocol / engines（run_all.py 聚合）|

### 9.1 依赖与密钥声明

| 文档 | 用途 |
|------|------|
| `DEPENDENCIES.md` | 外部依赖清单 + 作用 + 降级路径 |
| `API_KEYS.md` | 外部 API Key 清单 + 效益（仅变量名与作用，不含真实密钥值）|

---

## 10. 测试与质量

- **测试套件**：38 个测试文件（脚本风格，聚合入口 `tests/run_all.py`）
  - 引擎回归 8 套：all / cross / loop / combo / super / reverse / full / lowfreq
  - MCP 协议 28 套：basic（v0.1→v0.9）+ protocol（v1.1→v1.6，含 GraphQL/OTel/WS）
  - 主测试：`qcm_v82_test.py`（27 用例）+ `qcm_router_golden_test.py`（15 用例）
- **运行方式**：`python tests/run_all.py`（38 套件）或 `python tests/run_all.py --group engines/core/smoke`
- **验证器**：`python core/validator.py`（4 形态 × 24 检查 = 96/96）
- **健康门禁**：`python scripts/config_sync.py --check`（守卫 9 检）+ `scripts/sync_manifest.py`（双绑）
- **质量基线**：38/38 全绿 + 验证器 96/96 + 引擎 8/8 全绿 + v82 27/27 + router golden 15/15

---

## 附录：发布到 Skill 平台

### A.1 客户端集成示例（.mcp.json）

```json
{
  "mcpServers": {
    "qcm-search": {
      "command": "${QCM_ROOT}/scripts/mcp_server.py",
      "args": ["--transport", "stdio"],
      "env": {
        "QCM_ROOT": "${QCM_ROOT}",
        "QCM_AUTH_TOKEN": "${QCM_AUTH_TOKEN}"
      }
    },
    "infoseek-search": {
      "command": "${INFOSEEK_ROOT}/scripts/infoseek_mcp_server.py",
      "args": ["--transport", "stdio"],
      "env": {
        "INFOSEEK_ROOT": "${INFOSEEK_ROOT}"
      }
    }
  }
}
```

### A.2 获取帮助

- 查看 `README.md` 5 秒看懂
- 协议问题 → `references/protocol/action-orders.md`
- 环境问题 → `DEPENDENCIES.md` / `docs/TROUBLESHOOTING.md`

---

> **核心设计原则**：4 层级架构 + 5 范式 + 14 章协议 + 4 形态 + 场景路由消费 + 组件池三机制 + 文件层治理 = QCM 终极架构。
> **应用范围**：全行业 × 全工艺 × 全触点 × 全危机（依赖 §12 行业适配性 + §13 缺口暴露驱动 Infoseek 协同）。
