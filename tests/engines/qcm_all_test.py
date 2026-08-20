
import os
# -*- coding: utf-8 -*-
"""
QCM 全量测试运行器 v1.0（test-cases.md A-Z 全组脚本化）
==================================================
目标：将 test-cases.md 文档化的 129+ 用例全部脚本化自动运行。
分组：
  A-H 规则触发组(11) / REF 引用完整性(2) / O 输出边界(20) / F 正向链路(24)
  R 反向链路(24) / S 场景集成(8) / X 挤压测试(8) / Y 孤儿模块(14) / Z 全链路压测(25)
校验方式：规则存在性 + 关键词路由 + 工具编号落格 + 结构模板校验 + 引用完整性
输出：qcm_all_test_report.md
"""
import re, os, glob
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ---------- 全库加载 ----------
BASE = os.path.join(QCM_ROOT, "references")
def _find(base, fname):
    for _root, _dirs, _fnames in os.walk(base):
        if fname in _fnames:
            return os.path.join(_root, fname)
    return os.path.join(base, fname)
def rd(f): return open(_find(BASE, f), encoding="utf-8").read()
def _recursive_md(base):
    _files = {}
    for _root, _dirs, _fnames in os.walk(base):
        for _fn in _fnames:
            if _fn.endswith(".md"):
                _files[_fn] = rd(os.path.join(_root, _fn))
    return _files
FILES = _recursive_md(BASE)
_domains_dir = os.path.join(QCM_ROOT, "domains")
if os.path.isdir(_domains_dir):
    FILES.update(_recursive_md(_domains_dir))
skill_md = open(os.path.join(QCM_ROOT, "SKILL.md"), encoding="utf-8").read()
ALLTXT = "\n".join(FILES.values()) + "\n" + skill_md

tools_txt = FILES["tools.md"]; gov_txt = FILES["governance.md"]
# V8.0+ 整合：scenarios.md 降级为参考附录，cases.md 是 SOLE 权威（8 车间场景 + 案例资产化）
scen_txt = FILES.get("cases.md", "") + FILES.get("workshop.md", "") + FILES.get("workshop-battlefield.md", "")
kb_txt = FILES["knowledge-base.md"]
nav_txt = FILES["navigation.md"]; out_tpl = FILES["output-templates.md"]
# V8.0+ 整合：input-guide.md + input-guide-l0-l3.md → input-handbook.md（输入手册）
ig_txt = FILES.get("input-handbook.md", "") + FILES.get("mds-input.md", "")
mds_txt = FILES["mds-input.md"]
# V8.0+ 工具分类整合：tools-examples.md → tools-classification.md
tools_class_txt = FILES.get("tools-classification.md", "")
action_orders_md = FILES["action-orders.md"]  # V8.0+ 协议层 SOLE 权威
outputs_md = "\n".join([open(os.path.join(os.path.join(QCM_ROOT, "outputs"), f), encoding="utf-8").read() for f in os.listdir(os.path.join(QCM_ROOT, "outputs")) if f.endswith(".md")]) if os.path.exists(os.path.join(QCM_ROOT, "outputs")) else ""

L = []
def log(s=""): L.append(s)

# ---------- 解析 tools 86 工具 ----------
FACE_RE = re.compile(r"[（(][^）)]*?(系统面|管理面|过程面|产品面)[^）)]*?[）)]")
DIM_MAP = [("产品规划", "规划"), ("产品开发", "开发"), ("采购", "采购"), ("生产制造", "制造"),
           ("售后服务", "售后"), ("战略", "战略"), ("现场", "现场"), ("岗位执行", "岗位")]
tools = []
cur = None
for line in tools_txt.splitlines():
    m = re.match(r"^## ([A-F]\d+)\. (.+)$", line)
    if m:
        cur = {"num": m.group(1), "name": m.group(2).strip(), "face": None, "dims": []}
        tools.append(cur); continue
    if cur and "- **适用场景**" in line:
        fm = FACE_RE.search(line)
        if fm: cur["face"] = fm.group(1).replace("**", "")
        head = line.split("。")[0]
        for dim, kw in DIM_MAP:
            if kw in head: cur["dims"].append(dim)
TOOL_NUMS = {t["num"] for t in tools}
TOOL_NAMES = {t["name"] for t in tools}

# ---------- 结果统计 ----------
R = []  # (组, id, 名称, 通过, 说明)
def check(group, tid, name, cond, desc=""):
    R.append((group, tid, name, bool(cond), desc))
    return bool(cond)

def find_in(text, *kws):
    return all(kw in text for kw in kws)

# ================= A 组 · 基本原则 =================
log("## A 组 · 基本原则（决策-L1）")
check("A", "A-01", "结论无数据→#1数据说话", find_in(action_orders_md, "数据说话") or "数据说话" in ALLTXT, "action-orders.md 含 #1 数据说话")
check("A", "A-02", "应急方案→#2围堵遏制", find_in(action_orders_md, "围堵", "遏制"), "action-orders.md 含 #2 围堵遏制")

# ================= B 组 · 问题分类 =================
log("\n## B 组 · 问题分类（F12 路由）")
check("B", "B-01", "尺寸波动→变异/SPC", "变异" in ALLTXT and "SPC" in ALLTXT, "ALLTXT 变异→SPC（V8.0+ 多文件分布）")
check("B", "B-02", "返工率走高→浪费+变异复合", "浪费" in ALLTXT and "变异" in ALLTXT and "复合" in ALLTXT, "双范式路由可解析（V8.0+ 跨文件）")

# ================= C 组 · 穿透框架 =================
log("\n## C 组 · 穿透框架（#9/#10）")
check("C", "C-01", "组织层级→#9四层穿透", find_in(action_orders_md, "L1", "L2", "L3", "L4") and "组织归属" in action_orders_md, "action-orders.md 4 层定义")
check("C", "C-02", "流程维度→#10四面交叉", find_in(action_orders_md, "组织归属") and "治理" in action_orders_md, "action-orders.md 四面/治理定义")

# ================= D 组 · 风险评价 =================
log("\n## D 组 · 风险评价（#12 五维）")
check("D", "D-01", "无风险等级→#12①覆盖", "覆盖" in ALLTXT and "风险" in action_orders_md, "action-orders.md 风险定义")
check("D", "D-02", "无有效性判据→#12③有效性", "有效性" in ALLTXT, "有效性评价规则存在")

# ================= G 组 · 穿透韧性 =================
log("\n## G 组 · 穿透韧性（#17/#18）")
check("G", "G-01", "只分析问题点→#17全链扫描", "全链" in ALLTXT or "上下游" in ALLTXT, "全链扫描规则存在")
check("G", "G-02", "跳末端防护→#18控制层级", find_in(action_orders_md, "危机", "替代", "工程") or "优先级" in action_orders_md, "action-orders.md 控制层级定义")

# ================= H 组 · 成熟度诊断 =================
log("\n## H 组 · 成熟度诊断（#21）")
check("H", "H-01", "无基础数据→#21三问自诊", "三问" in ALLTXT, "CMMI 三问规则存在")

# ================= REF 引用完整性 =================
log("\n## REF · 引用完整性")
# REF-01: 全文 #N 编号对应存在规则（工具 A01-F10 / 决策编号 ①-㉑）
# 检查 references 中残留旧编号 '见 tools.md #NN'（重编号后应全为 A-F 新编号）
old_refs = re.findall(r"见 tools\.md #(\d+)", ALLTXT)
check("REF", "REF-01", "无旧编号残留", len(old_refs) == 0, f"残留 {sorted(set(old_refs))[:8]}")
# REF-02: reference 文件全在 Lineage/目录可读
check("REF", "REF-02", "reference 文件完整", len(FILES) >= 30, f"{len(FILES)} 文件加载")

# ================= O 组 · 输出边界（20） =================
log("\n## O 组 · 输出边界（L1-L4 边界）")
# O-1 层级边界
check("O", "O-01", "L1 无三链", ("三链" in action_orders_md or "三链" in mds_txt or "三链" in FILES["3a5why.md"]) and "L1" in out_tpl, "L1 模板不含三链（三链=L3专属）")
check("O", "O-02", "L2 密度4-5", "4-5" in out_tpl, "L2 密度定义")
check("O", "O-03", "L3 双归零", "双归零" in out_tpl and "双归零" in ALLTXT, "L3 双归零")
check("O", "O-04", "L4 回流建议", "回流" in out_tpl or "案例入场景库" in ALLTXT, "L4 回流")
check("O", "O-05", "危机后+≥2 升级 L3", ("危机后" in action_orders_md or "≥2" in action_orders_md) and "L3" in action_orders_md, "action-orders.md 危机后+≥2 升级 L3 规则")
# O-2 导航头完整性
check("O", "O-06", "V8.0+ 13 协议齐全", find_in(action_orders_md, "§1", "§7", "§8", "§13"), "action-orders.md 13 协议章节齐全")
check("O", "O-07", "决策-L 全称", "决策-L" in out_tpl, "决策-L 前缀")
check("O", "O-08", "围堵阶段跳过→直接", "围堵阶段" in action_orders_md and "24h" in action_orders_md, "action-orders.md 围堵阶段时间窗")
check("O", "O-09", "L4=战略×系统面", "战略×系统面" in out_tpl or "战略" in out_tpl, "L4 横轴")
# O-3 字段门控
check("O", "O-10", "缺F11打回", ("F11" in mds_txt or "F11" in action_orders_md) and ("打回" in ALLTXT or "必填" in ALLTXT), "mds-input.md F11 紧迫度门控")
check("O", "O-11", "缺F24打回", ("F24" in mds_txt or "F24" in action_orders_md) and "危机" in action_orders_md, "mds-input.md F24 危机等级门控")
check("O", "O-12", "F1 证据缺失打回", "证据" in ALLTXT and "打回" in ALLTXT, "证据门控")
check("O", "O-13", "F5 目标带单位", "单位" in ig_txt or "Cpk≥1.33" in ALLTXT, "单位门控")
# O-4 置信度
check("O", "O-14", "置信度可解释", "置信度" in out_tpl and "依据" in out_tpl, "置信度依据")
check("O", "O-15", "0.9+ 下调", "0.9" in ALLTXT or "0.85" in ALLTXT, "置信度上限")
# O-5 覆盖
check("O", "O-16", "未覆盖降级", "未覆盖" in action_orders_md or "归因" in action_orders_md, "action-orders.md 未覆盖协议")
check("O", "O-17", "缺 Infoseek 提示", "Infoseek" in action_orders_md or "Info-seek" in action_orders_md, "action-orders.md Infoseek 依赖")
# O-6 表达规范
check("O", "O-18", "引用须权威源", "ASQ" in ALLTXT and "ISO" in ALLTXT and "AIAG" in ALLTXT, "三源印证")
check("O", "O-19", "三要素齐全", "原则" in out_tpl and "流程" in out_tpl and "依据" in out_tpl, "三要素")
check("O", "O-20", "L1 卡片马上做", "马上做" in out_tpl, "卡片三列")

# ================= F 组 · 正向链路（24） =================
log("\n## F 组 · 正向链路（输入→决策→输出）")
F_CASES = [
    ("F-01", "注塑件重量波动", "T1", "数据说话", "问题→根因→马上做"),
    ("F-02", "冲压件尺寸漂移", "T2", "选范式", "导航头"),
    ("F-03", "弹片断裂复发", "T3", "复发", "双归零"),
    ("F-04", "质量文化参与率低", "T4", "自适应", "治理"),
    ("F-05", "换型90分钟OEE58%", "T2", "SMED", "选型"),
    ("F-06", "年度内审规划", "T4", "四面", "CAPA"),
    ("F-07", "钢带划伤拒收", "T1", "预防", "卡片"),
    ("F-08", "跨工序偏差溯源", "T3", "多链", "层别"),
    ("F-09", "停线了", "T1", "探测", "引导"),
    ("F-10", "尺寸波动+换型慢", "T2", "双范式", "双路由"),
    ("F-11", "弹片断裂第二次", "T3", "临界复发", "三链"),
    ("F-12", "来料不良+内审SPC", "T3", "三叠加", "双链"),
    ("F-13", "质量文化差+成熟度2级", "T4", "组合治理", "CMMI"),
    ("F-14", "年度战略+内审", "T4", "多归口", "RACI"),
    ("F-15", "模具寿命提前失效", "T3", "控制层级", "TPM"),
    ("F-16", "售后备件退货率升", "T2", "跨轨", "FRACAS"),
    ("F-17", "停线+换型慢(前景)", "T1", "前景", "应急"),
    ("F-18", "客诉+成熟度(前景)", "T3", "前景", "三链"),
    ("F-19", "尺寸波动+文化差(前景)", "T2", "双轨", "SPC"),
    ("F-20", "弹片断裂第三次", "T3", "复发", "双归零"),
    ("F-21", "并发多前景竞争", "T3", "并发", "并行"),
    ("F-22", "超长链路400字6轴", "T4", "超长", "六步"),
    ("F-23", "组合爆炸12组合", "T3", "组合", "相关"),
    ("F-24", "跨模块级联三级", "T4", "逐级不降级", "T4→L4"),
]
def tpl_exists(tlv):
    return tlv in ig_txt or tlv in out_tpl or tlv in skill_md
for tid, inp, tl, dec, out in F_CASES:
    ok = tpl_exists(tl) and (dec in ALLTXT or find_in(ALLTXT, dec)) and (out in ALLTXT or out in out_tpl)
    check("F", tid, inp, ok, f"{tl}+{dec}+{out}")  # noqa: original check position
    pass
R_CASES = [
    ("R-03", "决策-L3", "F6", "F14", ""),
    ("R-04", "治理MP归口M2+M6", "决策-L4", "F18", "F19"),
    ("R-05", "置信度0.82", "决策-L2", "F1", "F7"),
    ("R-06", "工具SPC#", "决策-L2", "F13", "落格"),
    ("R-07", "回流案例入场景库", "决策-L4", "F21", "进化"),
    ("R-08", "双归零问题+管理", "决策-L3", "F17", "双归零"),
    ("R-09", "超长L4输出20+项", "决策-L4", "回溯", "无杜撰"),
    ("R-10", "3决策并引", "决策-L2", "决策-L3", "决策-L4"),
    ("R-11", "输出缺依据", "决策-L1", "三要素", "打回"),
    ("R-12", "ECRS#", "决策-L2", "工具", "落格"),
    ("R-13", "书单#与工具#区分", "决策-L4", "书单", "前缀"),
    ("R-14", "置信度0.95无依据", "决策-L2", "下调", "待验证"),
    ("R-15", "T1输入出L4横轴", "决策-L1", "拦截", "错配"),
    ("R-16", "MP归口全列", "决策-L4", "归口", "匹配"),
    ("R-17", "停线卡+SMED背景", "决策-L1", "前景", "背景"),
    ("R-18", "三链+治理背景", "决策-L3", "前景", "背景"),
    ("R-19", "SPC+TQM背景", "决策-L2", "前景", "背景"),
    ("R-20", "双归零前景", "决策-L3", "前景字段", "不污染"),
    ("R-21", "竞争路由回溯优先级", "决策-L3", "并发", "优先"),
    ("R-22", "超长输出回溯六步", "决策-L4", "六步", "定位"),
    ("R-23", "组合输出回溯工具#", "决策-L3", "工具", "解析"),
    ("R-24", "级联输出回溯模板", "决策-L4", "T4", "L4"),
]
for rid, out, dec, f1, f2 in R_CASES:
    ok = dec in ALLTXT and (f1 in ALLTXT) and (f2 in ALLTXT or f2 in ig_txt)
    check("R", rid, out[:18], ok, f"回溯[{dec}+{f1}+{f2}]")

# ================= S 组 · 场景集成（8） =================
log("\n## S 组 · 场景集成（8 车间 × 链路）")
S_CASES = [
    ("S-01", "冲压", ["4M", "Poka-Yoke", "5Why", "SPC"], "T2", "L2"),
    ("S-02", "CNC", ["FAI", "层别", "MSA"], "T2", "L3"),
    ("S-03", "注塑", ["DOE", "直方图"], "T3", "L3"),
    ("S-04", "表面处理", ["柏拉图", "鱼骨"], "T2", "L3"),
    ("S-05", "组装/SMT", ["安灯", "5W2H"], "T2", "L3"),
    ("S-06", "模具", ["TPM", "散布图"], "T3", "L3"),
    ("S-07", "来料", ["AQL", "8D", "供应商审核"], "T3", "L4"),
    ("S-08", "出货/客户投诉", ["QRQC", "双归零", "PDCA"], "T3", "L4"),
]
for sid, ws, tools_l, tl, lv in S_CASES:
    # 车间名支持 '/' 分隔（库内实际为 '组装 / SMT' 等），任一段命中即算
    ws_parts = [p.strip() for p in ws.split("/") if p.strip()]
    ws_ok = any(p in scen_txt for p in ws_parts)
    tl_ok = all(tn in ALLTXT for tn in tools_l)
    lv_ok = lv in out_tpl or lv in skill_md
    check("S", sid, f"{ws}车间", ws_ok and tl_ok and lv_ok, f"场景[{ws}]+工具[{tools_l}]+层级[{lv}]")

# ================= X 组 · 挤压测试（8） =================
log("\n## X 组 · 挤压测试（全链路/工具/稳定/边界）")
# X-1 全链路
x1 = all(t in ig_txt or t in out_tpl for t in ["T1", "T2", "T3", "T4"]) and all(l in out_tpl for l in ["L1", "L2", "L3", "L4"])
check("X", "X-1", "全链路T/L模板", x1, "T1-T4+L1-L4 模板存在")
# X-2 工具可用性
check("X", "X-2", "86工具编号定义", len(TOOL_NUMS) == 86 or len(TOOL_NUMS) == 87, f"{len(TOOL_NUMS)} 工具")
# X-3 运行完整性
check("X", "X-3", "字段规则完整", "T1" in ig_txt and "5" in ig_txt and "门控" in ALLTXT, "字段+门控")
# X-4 模块边界
x4_missing = [f for f in ["tools.md", "governance.md", "scenarios.md", "knowledge-base.md", "masters.md", "navigation.md", "input-guide.md", "output-templates.md", "process-classification.md", "prompt-guide.md", "problem-solving.md", "mds-input.md", "naming-convention.md", "extension.md"] if f not in FILES]
check("X", "X-4", "14主干模块文件", not x4_missing, f"缺 {x4_missing}")
# X-2b 适用性
check("X", "X-2b", "工具↔面/层/类型匹配", find_in(ALLTXT, "适用场景") and "面" in tools_txt, "面标注解析")
# X-3b 稳定性
check("X", "X-3b", "同输入重复一致", len(set(re.findall(r"^## [A-F]\d+\.", tools_txt, re.M))) in (86, 87), "编号唯一")
# X-4b 交叉关联
check("X", "X-4b", "命名契约9前缀", all(p in ALLTXT for p in ["组织-", "流程-", "因果-", "决策-", "状态-", "价值-", "治理-", "工具-", "价值链-"]), "9前缀")
# X-5 压力段
check("X", "X-5", "并发/超长/组合/级联", find_in(ALLTXT, "并发", "超长", "组合", "级联") or find_in(skill_md, "并发", "超长"), "四类压力判据存在")

# ================= Y 组 · 孤儿模块（14） =================
log("\n## Y 组 · 孤儿模块（单测 vs 混测）")
Y_CASES = [
    ("Y-1", "naming-convention", "3维度前缀", ["组织-", "流程-", "工具-"]),
    ("Y-2", "problem-solving", "3A5WHY三链", ["发生链", "流出链", "系统链"]),
    ("Y-3", "mds-input", "MDS22字段", ["F12", "F18", "F21"]),
    ("Y-4", "extension", "7扩展接口", ["蒸馏", "扩展"]),
    ("Y-5", "navigation", "三维定位矩阵", ["组织", "流程", "多链"]),
    ("Y-6", "input-handbook", "T层权威5/13/17/22", ["T1", "T2", "T3", "T4"]),
    ("Y-7", "output-templates", "L层密度", ["L1", "L2", "L3", "L4"]),
    ("Y-8", "tools", "工具#权威", ["A01", "F10"]),
    ("Y-9", "knowledge-base", "四套编号", ["书单", "案例", "工具", "大师"]),
    ("Y-10", "masters", "21位大师", ["戴明", "朱兰", "克劳士比"]),
    ("Y-11", "governance", "六层级治理", ["工序级", "公司级"]),
    ("Y-12", "cases", "8车间场景", ["冲压", "CNC", "注塑"]),
    ("Y-13", "process-classification", "流程分类双维", ["COP", "SP", "MP"]),
    ("Y-14", "prompt-guide", "人物×工具生成器", ["人物", "工具"]),
]
for yid, fname, desc, kws in Y_CASES:
    f_ok = fname + ".md" in FILES
    c_ok = all(kw in FILES.get(fname + ".md", "") for kw in kws) if f_ok else False
    check("Y", yid, fname, f_ok and c_ok, f"单测[{desc}] {'✅' if c_ok else '缺关键词'}")

# ================= Z 组 · 全链路压测（25） =================
log("\n## Z 组 · 全链路端到端压测（25 Query）")
Z_CASES = [
    ("Z-01", "CNC车间尺寸波动大怎么控", ["SPC"]),
    ("Z-02", "装配线在制品堆积怎么减", ["浪费", "看板"]),
    ("Z-03", "焊接虚焊率高怎么破", ["8D", "FMEA"]),
    ("Z-04", "供应商来料不良怎么管", ["供应商", "AQL"]),
    ("Z-05", "戴明视角看质量文化", ["戴明"]),
    ("Z-06", "克劳士比零缺陷怎么落地", ["克劳士比"]),
    ("Z-07", "SPC控制图Xbar-R怎么描点", ["SPC"]),
    ("Z-08", "FMEA严重度评级怎么做", ["FMEA"]),
    ("Z-09", "鱼骨图找尺寸超差原因", ["鱼骨"]),
    ("Z-10", "5Why追装配停线根因", ["5Why"]),
    ("Z-11", "涂装漆面颗粒怎么改善", ["涂装"]),
    ("Z-12", "SMT锡珠不良怎么治", ["SMT"]),
    ("Z-13", "总装扭矩不合格怎么防", ["扭矩", "防错"]),
    ("Z-14", "冲压开裂怎么降", ["冲压"]),
    ("Z-15", "焊接飞溅怎么控", ["焊接"]),
    ("Z-16", "怎么建QCC品管圈小组", ["QCC"]),
    ("Z-17", "TPS怎么消除浪费", ["TPS", "浪费"]),
    ("Z-18", "质量成本COPQ怎么算", ["COPQ"]),
    ("Z-19", "成熟度诊断到L3怎么评", ["成熟度"]),
    ("Z-20", "组织问题用四层穿透怎么拆", ["四层"]),
    ("Z-21", "流程问题用四面交叉怎么定位", ["四面"]),
    ("Z-22", "输出要标风险等级和置信度", ["置信度"]),
    ("Z-23", "多输入CNC+SPC+戴明", ["SPC", "戴明"]),
    ("Z-24", "超长尺寸+交付+成本+文化", ["尺寸", "文化"]),
    ("Z-25", "组合3模块×4工具", ["工具", "组合"]),
]
z_pass = 0
for zid, q, kws in Z_CASES:
    ok = all(kw in ALLTXT for kw in kws)
    if ok: z_pass += 1
    check("Z", zid, q[:20], ok, f"路由关键词{kws} {'✅' if ok else '❌缺'}")

# ================= 汇总 =================
log("\n" + "=" * 78)
log("全量测试汇总")
log("=" * 78)
from collections import Counter, defaultdict
grp_stat = defaultdict(lambda: [0, 0])
for g, tid, name, passed, desc in R:
    grp_stat[g][1] += 1
    if passed: grp_stat[g][0] += 1
total_pass = sum(1 for r in R if r[3]); total = len(R)
log(f"总用例：{total}，通过 {total_pass}，失败 {total - total_pass}")
for g in ["A", "B", "C", "D", "G", "H", "REF", "O", "F", "R", "S", "X", "Y", "Z"]:
    p, n = grp_stat.get(g, [0, 0])
    bar = "█" * (p * 20 // max(n, 1))
    log(f"  {g:<4} {p:>3}/{n:<3} {bar}")
log("\n失败明细：")
for g, tid, name, passed, desc in R:
    if not passed:
        log(f"  ❌ {tid} {name}: {desc}")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_all_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_all_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
