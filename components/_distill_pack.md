---
kind: dynamic
fields:
  industry: {type: string, required: true}
  process_map: {type: string, required: true}
  scenarios: {type: string, required: false}
  tools_diff: {type: string, required: false}
  anchors: {type: string, required: false}
---
<!-- 蒸馏清单组件（A+B 决策 · V8.3 修复 · 吸收 industry-adaptation ADAPTER 七段） -->
<!-- 触发：⑤知识沉淀（新行业/新工艺接入）· gap=True 联动 Infoseek（§13 缺口驱动） -->
【蒸馏清单】{industry} 行业适配（ADAPTER 七段压缩）
├─ A 行业画像：{行业定位} · 端到端流程映射 {process_map} · 关键标准 {standards}
├─ D 工序细分：{工序 F10b 行业版 → 缺陷 → 控制参数 → 质量工具（复用编号）}
├─ A 典型场景：{场景 1} + {场景 2}（QCM 穿透格式 · 工具落格已标）
├─ P 工具落格：通用沿用 {复用清单} · 行业特有 {新增候选（编号向后兼容）}
├─ T 测试验证：增量用例 {test-cases 编号} · 8 引擎回归 {全绿/明细} · 双向可达
├─ E 案例锚点：权威来源 {三源印证} · 案例 {1-2 个} · 黑名单排除
└─ R 注册版本：{适配包 v1.0} · ima_skill_create 重注册 · 更新履历

【缺口联动】{gap 标注} → Infoseek 调研（锚点发现 → 5 维评分 → 置信度 ≥70 入库 / 40-69 归因历史 / <40 终止）
