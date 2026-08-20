# 行业知识包 · 新能源（New Energy / 动力电池·储能电池·电芯·PACK）

> QCM 规模化行业包 #2（V8.4 C3b）
> 用途：新能源电池（动力电池、储能电池、3C 锂电）制造与质量场景沉淀，
> 供 QCM「⑤知识沉淀」「①危机处置」意图在处理行业查询时检索消费。
> 关联核心词库：`references/config/keyword.yaml`（已注册词条：良率/直通率/供应商/焊接/spc/cpk/ppm/fmea）。

## 1. 行业概述
新能源电池制造链路：正极/负极/隔膜/电解液（四大主材）→ 极片（涂布/辊压/分切）→ 电芯（卷绕/叠片 + 装配 + 注液 + 化成）→ 模组(Module) → PACK（含 BMS）→ 整车/储能系统。
质量重心在**安全（热失控防护）、一致性（容量/内阻/循环）、良率(yield)与直通率(FPY)**。本行业安全属性极强，失效多为高风险危机事件（意图①）。

## 2. 典型失效模式 / 缺陷（→ 意图①危机处置）
| 缺陷 | 英文 | 机理 | 关联词条 |
|------|------|------|----------|
| 热失控 | thermal runaway | 内短路/过充/机械滥用/高温触发链式反应 | 热失控 / 内短路 / 过充 |
| 内短路 | internal short circuit (ISC) | 隔膜刺穿、异物、枝晶穿透 | 内短路 / 隔膜 |
| 析锂 | lithium plating | 低温快充、大倍率、负极嵌锂不足 | 析锂 |
| 枝晶 | dendrite | 锂沉积过量、循环老化 | 析锂 / 枝晶 |
| 容量衰减 | capacity fade | SEI 增长、活性锂损耗 | 容量 / 循环 |
| 内阻增大 | resistance growth (DCIR↑) | 界面劣化、产气、接触不良 | 内阻 |
| 胀气/膨胀 | swelling | 产气（电解液分解）、析锂 | 膨胀 |
| 漏液 | leakage | 密封失效、壳体损伤 | 漏液 |
| 极片缺陷 | electrode defect | 涂层不均/厚边/异物/划痕 | 极片 / 涂布 |
| 焊接不良（极柱/tab） | weld defect | 激光焊参数漂移、虚焊、炸焊 | 焊接(welding) |
| 隔膜刺穿 | separator puncture | 毛刺、金属异物 | 隔膜 / 内短路 |
| 过充 | overcharge | 充电器/BMS 失效、截止电压超标 | 过充 / BMS |
| 自放电过大 | self-discharge | 微短路、杂质 | 自放电 |
| 循环寿命衰减 | cycle life decay | 结构失稳、电解液消耗 | 循环 |
| PACK 装配缺陷 | pack assembly defect | 铜排连接松动、绝缘不良 | 装配 / 绝缘 |

## 3. 关键质量指标（KPI）
- **良率 yield**：良品数 / 投入数 → keyword `良率`(yield)
- **直通率 FPY / first pass yield**：一次通过率 → keyword `直通率`(FPY)
- **PPM**：百万缺陷率 → keyword `ppm`(PPM)
- **CPK**：过程能力指数（≥1.33 为达标）→ keyword `cpk`(Cpk)
- **SPC**：统计过程控制 → keyword `spc`(SPC)
- **容量一致性**：同批次电芯容量极差/σ → keyword `容量`(容量一致性由其派生)
- **内阻 IR / DCIR**：直流内阻分布
- **循环寿命 cycle life**：容量衰减至 80% 的循环次数
- **能量密度 energy density**：Wh/kg、Wh/L

## 4. 适用质量方法 / 工具
- 8D / 5Why：安全危机根因（意图①，热失控/起火必走）
- FMEA（DFMEA/PFMEA）：电池系统/电芯失效预防（keyword `fmea`/`dfmea`/`pfmea`）
- SPC + 控制图：涂布面密度、注液量、焊接强度过程监控（keyword `spc`）
- DOE：化成工艺窗口、电解液配方优化（意图②流程优化）
- APQP / PPAP：电池新品导入（keyword `apqp` / `npi`）
- 安全滥用测试：针刺、热箱、过充、外部短路（触发热失控边界验证）

## 5. 行业专属术语表（与 keyword.yaml 别名对齐）
电芯=cell · 模组=module · PACK=battery pack · 极片=electrode · 正极=cathode · 负极=anode ·
隔膜=separator · 电解液=electrolyte · 集流体=current collector · 极柱=terminal/post · 铜排=busbar ·
BMS=battery management system · SOC=state of charge · SOH=state of health · 化成=formation ·
分容=grading/capacity sorting · 卷绕=winding · 叠片=stacking · 注液=electrolyte filling ·
涂布=coating · 辊压=calendering · 焊接=welding · 装配=assembly · 良率=yield · 直通率=FPY ·
内阻=internal resistance · 析锂=lithium plating · 热失控=thermal runaway · 容量=capacity · 循环=cycle ·
供应商=supplier · 来料=incoming material · 现场=shop floor/gemba

## 6. 典型场景示例
- "某车型电池包热失控起火，社交平台舆论发酵" → ①危机处置（热失控 + 起火 + 舆论）
- "电芯析锂导致低温续航骤降，冬季客诉激增" → ①危机处置（析锂 + 续航 + 客诉）
- "PACK 激光焊虚焊 ppm 超标，Cpk 1.05" → ①危机处置（焊接 + ppm + Cpk）
- "动力电池新品导入如何做 PFMEA" → ⑤知识沉淀 / ④知识学习
- "储能集装箱电芯膨胀鼓包，安全隐患排查" → ①危机处置（膨胀 + 安全）
