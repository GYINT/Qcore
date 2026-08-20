# 行业知识包 · 消费电子（Consumer Electronics / SMT·PCBA·芯片封装）

> QCM 规模化行业包 #1（V8.4 C3b）
> 用途：消费电子硬件制造（SMT 贴片、PCBA、半导体封装、整机组装）质量场景沉淀，
> 供 QCM「⑤知识沉淀」「①危机处置」意图在处理行业查询时检索消费。
> 关联核心词库：`references/config/keyword.yaml`（词条别名见 keyword.yaml 的英文 aliases）。

## 1. 行业概述
消费电子制造链路：晶圆(Wafer) → 芯片封装(Package/Bonding) → SMT 贴片 → PCBA → 整机组装 → 出货。
质量重心在**焊接可靠性、尺寸精度、电气性能、良率(yield)与直通率(FPY)**。

## 2. 典型失效模式 / 缺陷（→ 意图①危机处置）
| 缺陷 | 英文 | 机理 | 关联词条 |
|------|------|------|----------|
| 虚焊 | cold solder joint | 润湿不良、温度曲线不足 | 虚焊 / 润湿不良(poor wetting) |
| 连焊 | bridging | 锡量过多、钢网开口过大 | 连焊 |
| 少锡 | insufficient solder | 钢网堵塞、印刷偏移 | 少锡 |
| 多锡 | excess solder | 钢网开口过大 | 多锡 |
| 金线虚焊/断线 | gold wire bond defect | 键合参数漂移、二焊点脱落 | 金线 / 键合(bonding) / 断线 |
| 锡须 | tin whisker | 无铅镀层内应力 | 锡须 |
| 翘曲 | warpage | 板材 CTE 不匹配、回流热应力 | 翘曲 |
| 分层 | delamination | 板材吸湿、胶层失效 | 分层 |
| 气泡/空洞 | void | 助焊剂挥发不全 | 气泡(void) |
| 裂纹 | crack / micro crack | 机械应力、热冲击 | 裂纹 / 微裂纹 |
| 短路 | short circuit | 连锡、异物桥接 | 短路 |
| 开路 | open circuit | 虚焊、断线、PCB 断线 | 开路 |
| 润湿不良 | poor wetting | 氧化、污染、温度不足 | 润湿不良 |
| ESD 损伤 | ESD | 静电放电击穿 | ESD |
| 阻抗异常 | impedance | 线宽/介质偏差 | 阻抗 |
| 绝缘不良 | insulation fail | 污染、间距不足 | 绝缘 |
| 耐压击穿 | hi-pot fail | 介质厚度不足 | 耐压 |

## 3. 关键质量指标（KPI）
- **良率 yield**：良品数 / 投入数 → keyword `良率`(yield)
- **直通率 FPY / first pass yield**：一次通过率 → keyword `直通率`(FPY)
- **PPM**：百万缺陷率 → keyword `ppm`(PPM)
- **CPK**：过程能力指数（≥1.33 为达标）→ keyword `cpk`(Cpk)
- **SPC**：统计过程控制 → keyword `spc`(SPC)

## 4. 适用质量方法 / 工具
- 8D / 5Why：危机根因（意图①）
- FMEA（DFMEA/PFMEA）：失效预防（keyword `fmea`）
- SPC + 控制图：过程监控（keyword `spc`）
- DOE：工艺窗口优化（意图②流程优化）
- APQP / PPAP：新品导入（keyword `apqp` / `npi`）

## 5. 行业专属术语表（与 keyword.yaml 别名对齐）
焊接=welding/solder · 注塑=injection molding · 冲压=stamping · 切削=cutting · 加工=machining ·
工序=process step · 工艺=process/technology · 参数=parameter · 设计=design · 开发=development ·
供应商=supplier · 来料=incoming material · 采购=procurement · 物流=logistics · 现场=shop floor/gemba ·
车间=workshop · 巡检=patrol inspection · 体系=qms · 风险=risk · 隐患=hidden danger ·
直通率=FPY/first pass yield · 断刀=tool breakage · 微裂纹=micro crack · 让刀=tool deflection ·
椭圆=ovality · 孔壁粗糙=hole wall roughness · 冷链断裂=cold chain break · 超储=overstock

## 6. 典型场景示例
- "SMT 虚焊导致整机开机不良，客诉增多" → ①危机处置（虚焊 + 客诉）
- "金线键合二焊点脱落，良率跌破 95%" → ①危机处置（金线 + 良率 + 跌破）
- "PCBA 连焊 ppm 超标，Cpk 1.1" → ①危机处置（连焊 + ppm + Cpk）
- "消费电子新品导入如何做 DFMEA" → ⑤知识沉淀 / ④知识学习
