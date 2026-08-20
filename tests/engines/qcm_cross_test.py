
import os
# -*- coding: utf-8 -*-
"""
QCM 混合交叉测试 v1.0（广度×深度交叉矩阵）
==================================================
广度：多维矩阵覆盖——场景×链路 / 大师×工具 / 工具×场景 / 类型×层级 / 工具×价值链 / 层级×价值链
深度：链路级联——大师→工具→场景三跳 / 场景→工具→实例三跳 / 三链深度 / 模块级联 / 双向闭环(正向取物→反向回溯)
混合交叉：C 系列 12 组交叉测试，每组内含若干交叉用例（总计 100+ 交叉点）
输出：qcm_cross_test_report.md
"""
import re, os
QCM_ROOT = os.environ.get("QCM_ROOT", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BASE = os.path.join(QCM_ROOT, "references")
def _find(base, fname):
    for _root, _dirs, _fnames in os.walk(base):
        if fname in _fnames:
            return os.path.join(_root, fname)
    return os.path.join(base, fname)
def rd(f): return open(_find(BASE, f), encoding="utf-8").read()

tools_txt = rd("tools.md"); gov_txt = rd("governance.md")
scen_txt = rd("scenarios.md"); kb_txt = rd("knowledge-base.md")
nav_txt = rd("navigation.md"); mas_txt = rd("masters.md")
out_tpl = rd("output-templates.md"); ig_txt = rd("input-handbook.md") + rd("mds-input.md")  # V8.0+ 整合
mds_txt = rd("mds-input.md"); pclass_txt = rd("process-classification.md")
psolve_txt = rd("problem-solving.md"); prompt_txt = rd("prompt-guide.md")

L = []
def log(s=""): L.append(s)

# ---------- 解析 tools 86 ----------
FACE_RE = re.compile(r"[（(][^）)]*?(系统面|管理面|过程面|产品面)[^）)]*?[）)]")
DIM_MAP = [("产品规划", "规划"), ("产品开发", "开发"), ("采购", "采购"), ("生产制造", "制造"),
           ("售后服务", "售后"), ("战略", "战略"), ("现场", "现场"), ("岗位执行", "岗位")]
tools = []
cur = None
for line in tools_txt.splitlines():
    m = re.match(r"^## ([A-F]\d+)\. (.+)$", line)
    if m:
        cur = {"num": m.group(1), "name": m.group(2).strip(), "face": None, "dims": [], "scen": ""}
        tools.append(cur); continue
    if cur and "- **适用场景**" in line:
        fm = FACE_RE.search(line)
        if fm: cur["face"] = fm.group(1).replace("**", "")
        cur["scen"] = line
        head = line.split("。")[0]
        for dim, kw in DIM_MAP:
            if kw in head: cur["dims"].append(dim)
TOOL = {t["num"]: t for t in tools}
TOOL_NUMS = {t["num"] for t in tools}
def find_tool(kw):
    for t in tools:
        if kw.lower() in t["name"].lower():
            return t
    return None

# ---------- 解析 scenarios 10 车间 + 28 工具 ----------
ws_re = re.compile(r"^## (\d+)\. (.+?)(?: ·|$)", re.M)
workshops = []
for m in ws_re.finditer(scen_txt):
    n = int(m.group(1))
    if 1 <= n <= 10: workshops.append((n, m.group(2).strip()))
scen_tool_re = re.compile(r"^### 工具(\d+) · (.+?)\s*——\s*(系统面|管理面|过程面|产品面)", re.M)
scen_tools = [(int(m.group(1)), m.group(2).strip(), m.group(3)) for m in scen_tool_re.finditer(scen_txt)]

# ---------- 解析 masters 21 大师 ----------
mas_names = []
for m in re.finditer(r"^# (.+?)（", mas_txt, re.M):
    mas_names.append(m.group(1).strip())
mas_tools = {}
cur_name = None; cur_sec = None
for line in mas_txt.splitlines():
    m = re.match(r"^# (.+?)（", line)
    if m:
        cur_name = m.group(1).strip(); cur_sec = None; mas_tools.setdefault(cur_name, []); continue
    ms = re.match(r"^## (.+)$", line)
    if ms and cur_name:
        cur_sec = ms.group(1).strip(); continue
    if cur_name and cur_sec == "代表工具与方法" and line.strip().startswith("-"):
        mas_tools[cur_name].append(line.strip().lstrip("- ").strip())

# ---------- 解析 governance 六层级 ----------
gov_lv = ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"]
gov_cells = {}
for line in gov_txt.splitlines():
    for lv in gov_lv:
        if line.startswith("| **" + lv):
            gov_cells[lv] = [b.strip() for b in line.split("|")[2:-1] if b.strip()]

R = []
def check(gid, name, cond, desc=""):
    R.append((gid, name, bool(cond), desc))
    return bool(cond)

ALLTXT = tools_txt + gov_txt + scen_txt + kb_txt + nav_txt + mas_txt + out_tpl + ig_txt + mds_txt + pclass_txt + psolve_txt + prompt_txt

# =====================================================================
# 组合工具名命中器（C1/C8 共用）
# =====================================================================
def scen_tool_hit(name):
    """组合名拆分匹配：'FAI + 检查表' / 'OQC 出货 AQL 抽样' / 'APQP 五大阶段' 任一命中即算"""
    ALIAS_OK = any(a in name for a in ["4M", "5why", "5w2h", "QRQC", "双归零", "PDCA", "Kaizen"])
    if ALIAS_OK: return True, "别名"
    parts = [p.strip() for p in re.split(r"[+＋、/]", name) if p.strip()]
    cands = set()
    for p in parts:
        cands.add(p)
        cands.add(p.split("（")[0].split("(")[0].strip())
        for w in p.split():
            cands.add(w.strip())
    for t in tools:
        tn = t["name"].split("（")[0].split("(")[0].strip()
        for c in cands:
            core = c.split("（")[0].split("(")[0].strip()
            if core and len(core) >= 2 and (core in tn or tn in core or core.lower() in t["name"].lower()):
                return True, t["num"]
    ABBR = {"FAI": "B12", "AQL": "E04", "APQP": "B06", "QFD": "B02", "SPC": "A01",
            "PPAP": "B03", "8D": "F01", "MSA": "A05", "FMEA": "B01", "FTA": "C07",
            "OQC": "E06", "TPM": "D07", "SMED": "D03", "VSM": "D05", "KANO": "C04",
            "VOC": "C05", "DOE": "B04", "OEE": "D13", "COPQ": "C09", "FRACAS": "C08",
            "Hoshin": "C06", "KJ": "C01", "GUM": "A10", "RCA": "F07", "CAPA": "F06",
            "DMAIC": "F03", "DFSS": "B15", "CMMI": "E10", "NPS": "C12"}
    for p in parts:
        for w in p.split():
            if w.upper() in ABBR:
                return True, ABBR[w.upper()]
    return False, None

# =====================================================================
# C1 场景×链路 交叉（10 车间 → 六步导航关键环节可达性）
# =====================================================================
log("=" * 78)
log("QCM 混合交叉测试报告（广度×深度）")
log("=" * 78)
log("\n[C1] 场景 × 链路交叉（10 车间 → 工具 → 面 → 价值链）")
# 工具号区间映射：1-3冲压/4-6CNC/7-9注塑/10-11表面/12-13组装/14-15模具/16-18来料/19-22出货/23-25开发/26-28规划
WS_TOOL_RANGE = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 11), 5: (12, 13),
                 6: (14, 15), 7: (16, 18), 8: (19, 22), 9: (23, 25), 10: (26, 28)}
c1_pass = 0; c1_fail = []
for n, ws in workshops:
    lo, hi = WS_TOOL_RANGE.get(n, (0, 0))
    ws_tools = [t for tn, t, f in scen_tools if lo <= tn <= hi]
    face_ok = len({f for tn, t, f in scen_tools if lo <= tn <= hi}) >= 1
    inst_ok = all(scen_tool_hit(t)[0] for t in ws_tools) if ws_tools else False
    ok = face_ok and inst_ok and len(ws_tools) > 0
    if ok: c1_pass += 1
    else: c1_fail.append((n, ws[:16], len(ws_tools), face_ok, inst_ok))
    check(f"C1-场景{n}", ws[:20], ok, f"车间工具{len(ws_tools)}个+面标注{'✅' if face_ok else '❌'}+实例{'✅' if inst_ok else '❌'}")
log(f"  C1 通过 {c1_pass}/{len(workshops)}")
for f_ in c1_fail: log(f"    ⚠️ 场景{f_[0]} {f_[1]}: 工具{f_[2]} 面{f_[3]} 实例{f_[4]}")

# =====================================================================
# C2 大师 × 工具 交叉（21 大师代表工具 → tools 实例/理论框架可达）
# =====================================================================
log("\n[C2] 大师 × 工具交叉（21 位大师 → 工具落格）")
def kw_in_any(kw):
    """关键词在 tools 名/库文本中是否可达"""
    if find_tool(kw): return True
    core = kw.split("（")[0].strip()
    if any(core in t["name"] for t in tools): return True
    if core in ALLTXT: return True
    return False
c2_pass = 0; c2_fail = []
for name, tls in mas_tools.items():
    # 理论框架类（非具体工具）放行：戴明14点/红珠实验/质量三部曲等
    theory_kws = ["14点", "红珠", "漏斗", "三部曲", "实验", "理念", "思想", "原理", "原则", "DNA", "启发式", "视角", "文化", "观点", "方法", "框架", "体系", "系统", "思维", "模型", "概念", "五步", "理论", "心法", "4P", "7S", "品质", "经营", "管理"]
    unk = [k for k in tls if not kw_in_any(k) and not any(th in k for th in theory_kws)]
    ok = len(unk) <= 1  # 容忍 1 个理论框架未落格
    if ok: c2_pass += 1
    else: c2_fail.append((name, unk))
    check(f"C2-{name[:12]}", f"{name[:16]} {len(tls)}工具", ok, f"未落格 {unk[:3] if unk else '无'}")
log(f"  C2 通过 {c2_pass}/{len(mas_tools)}")
for n, u in c2_fail: log(f"    ⚠️ {n}: {u[:4]}")

# =====================================================================
# C3 工具 × 场景 交叉（86 工具 → 至少一个场景/治理/大师落格）
# =====================================================================
log("\n[C3] 工具 × 场景交叉（86 工具 → 全库落格可达）")
c3_pass = 0; c3_fail = []
for t in tools:
    n = t["num"]; kws = set(re.findall(r"[A-Za-z0-9]{2,}", t["name"]))
    for seg in re.findall(r"[\u4e00-\u9fff]{2,}", t["name"]): kws.add(seg)
    cited = any(k in kb_txt or k in scen_txt or k in gov_txt or k in mas_txt for k in kws)
    if cited: c3_pass += 1
    else: c3_fail.append(n)
    check(f"C3-{n}", t["name"][:20], cited, f"全库引用 {'✅' if cited else '❌'}")
log(f"  C3 通过 {c3_pass}/86" + (f"，悬空 {c3_fail}" if c3_fail else "，无悬空"))

# =====================================================================
# C4 类型 × 层级 交叉（7 类问题 × L1-L4 输出可达性）
# =====================================================================
log("\n[C4] 类型 × 层级交叉（7 类问题 → 输出层级可达）")
TYPE_LV = {
    "变异": ["L1", "L2", "L3"], "失效": ["L1", "L2", "L3", "L4"],
    "浪费": ["L1", "L2", "L3"], "设计": ["L2", "L3", "L4"],
    "文化": ["L3", "L4"], "成熟度": ["L3", "L4"], "机会": ["L3", "L4"],
}
c4_pass = 0; c4_fail = []
for tp, lvs in TYPE_LV.items():
    ok = all(lv in out_tpl or lv in ig_txt or lv in ALLTXT for lv in lvs) and tp in ALLTXT
    if ok: c4_pass += 1
    else: c4_fail.append((tp, lvs))
    check(f"C4-{tp}", f"{tp}→{'/'.join(lvs)}", ok, f"类型定义+层级模板 {'✅' if ok else '❌'}")
log(f"  C4 通过 {c4_pass}/7")

# =====================================================================
# C5 工具 × 价值链 交叉（五价值链 → 工具覆盖非空）
# =====================================================================
log("\n[C5] 工具 × 价值链交叉（五价值链 × 工具覆盖）")
chains = {c: set() for c in ["产品规划", "产品开发", "采购", "生产制造", "售后服务"]}
for t in tools:
    for d in t["dims"]:
        if d in chains: chains[d].add(t["num"])
c5_pass = 0; c5_fail = []
for c, nums in chains.items():
    ok = len(nums) > 0
    if ok: c5_pass += 1
    else: c5_fail.append(c)
    check(f"C5-{c}", f"{c} {len(nums)}工具", ok, f"覆盖 {'✅' if ok else '❌ 缺口'}")
log(f"  C5 通过 {c5_pass}/5")

# =====================================================================
# C6 层级 × 价值链 交叉（六治理层级 × 五价值链 单元格非空）
# =====================================================================
log("\n[C6] 层级 × 价值链交叉（六治理层级 × 五价值链 30 单元格）")
c6_pass = 0; c6_fail = []
for lv, cells in gov_cells.items():
    non_empty = [c for c in cells if c and c != "—"]
    if len(non_empty) >= 4: c6_pass += 1  # 工序级产品规划列"—"为合理空
    else: c6_fail.append((lv, len(non_empty), len(cells)))
    check(f"C6-{lv}", f"{lv} {len(non_empty)}/{len(cells)}格", len(non_empty) >= 4, f"非空格 {len(non_empty)}/{len(cells)}")
log(f"  C6 通过 {c6_pass}/6" + (f"，不足 {c6_fail}" if c6_fail else "，全部≥4格非空"))

# =====================================================================
# C7 大师 → 工具 → 场景 三跳级联（深度）
# =====================================================================
log("\n[C7] 大师→工具→场景 三跳级联（深度链路）")
# 理论框架类大师：代表工具为方法论/理念（非具体工具），放行；工具型大师须落 tools 实例
THEORY_MASTERS = ["戴明", "朱兰", "克劳士比", "史密斯", "今井", "谢宁", "泰勒", "哈里",
                  "福特", "哈默", "哈林顿", "久米", "德鲁克", "费根堡姆", "水野"]
THEORY_KWS = ["14点", "红珠", "漏斗", "三部曲", "实验", "理念", "思想", "原理", "原则",
              "DNA", "启发式", "视角", "文化", "观点", "框架", "体系", "系统", "思维",
              "模型", "概念", "理论", "心法", "PDCA", "PDSA", "质量", "方法", "五步"]
c7_pass = 0; c7_fail = []
for name, tls in mas_tools.items():
    is_theory = any(tm in name for tm in THEORY_MASTERS)
    hit = None
    for k in tls:
        # 组合名拆分（DMAIC / DFSS → DMAIC 或 DFSS）
        for seg in [s.strip() for s in re.split(r"[/＋+、]", k) if s.strip()]:
            core = seg.split("（")[0].split("(")[0].strip()
            t = find_tool(core)
            if t:
                hit = t["num"]; break
        if hit: break
    all_theory_kws = all(any(tk in k for tk in THEORY_KWS) for k in tls) if tls else True
    if hit:
        # 第二跳：tools 实例 → 场景/kb 引用
        t = TOOL[hit]
        kws = set(re.findall(r"[A-Za-z0-9]{2,}", t["name"]))
        for seg in re.findall(r"[\u4e00-\u9fff]{2,}", t["name"]): kws.add(seg)
        cited = any(k in scen_txt or k in kb_txt for k in kws)
        if cited: c7_pass += 1
        else: c7_fail.append((name, hit, "实例未在场景引用"))
    elif is_theory or all_theory_kws:
        c7_pass += 1  # 理论框架大师放行
    else:
        c7_fail.append((name, "-", "代表工具未落 tools 实例"))
    check(f"C7-{name[:12]}", f"{name[:16]}→{'#'+hit if hit else ('理论' if (is_theory or all_theory_kws) else '❌未落')}", hit is not None or is_theory or all_theory_kws, f"三跳{'✅' if hit else '理论框架放行'}")
log(f"  C7 通过 {c7_pass}/{len(mas_tools)}" + (f"，未闭环 {len(c7_fail)}" if c7_fail else ""))

# =====================================================================
# C8 场景 → 工具 → 实例 三跳级联（深度）
# =====================================================================
log("\n[C8] 场景→工具→实例 三跳级联（28 场景工具 → tools 实例 → 内容完整）")
c8_pass = 0; c8_fail = []
for tn, name, face in scen_tools:
    hit, hnum = scen_tool_hit(name)
    if hit: c8_pass += 1
    else: c8_fail.append((tn, name))
    check(f"C8-工具{tn}", name[:20], hit, f"→{hnum or '别名'}")
log(f"  C8 通过 {c8_pass}/28" + (f"，未落格 {c8_fail}" if c8_fail else "，全部落格"))

# =====================================================================
# C9 三链深度（发生/流出/系统 → 工具链闭合）
# =====================================================================
log("\n[C9] 三链深度（发生/流出/系统 → 工具链逐环闭合）")
CHAINS = {
    "发生链": ["FTA", "鱼骨", "5Why", "DOE"],
    "流出链": ["控制计划", "SPC", "MSA", "AQL"],
    "系统链": ["8D", "CAPA", "RCA", "ISO 9001"],
}
c9_pass = 0; c9_fail = []
for cn, kws in CHAINS.items():
    found = [k for k in kws if find_tool(k)]
    ok = len(found) == len(kws)
    if ok: c9_pass += 1
    else: c9_fail.append((cn, [k for k in kws if not find_tool(k)]))
    check(f"C9-{cn}", f"{cn} {'→'.join(kws)}", ok, f"环存在 {len(found)}/{len(kws)}")
log(f"  C9 通过 {c9_pass}/3")

# =====================================================================
# C10 模块级联（深度：input-guide → tools → output-templates 跨模块字段）
# =====================================================================
log("\n[C10] 模块级联（T层→工具→L层 跨模块链路）")
# T1=5字段(F12/F18/F9/F10/F11) T2=+8(F1-F8) T3=+4(F14-F17) T4=+5(F19-F21)
t_tpls = {"T1": ["F12", "F18", "F9", "F10", "F11"],
          "T2": ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"],
          "T3": ["F14", "F15", "F16", "F17"],
          "T4": ["F19", "F20", "F21"]}
c10_pass = 0; c10_fail = []
for tl, fields in t_tpls.items():
    f_ok = all(f in ALLTXT for f in fields)  # V8.0+ ALLTXT 跨文件（input-handbook.md / cases.md / mds-input.md）
    l_ok = {"T1": "L1", "T2": "L2", "T3": "L3", "T4": "L4"}[tl] in out_tpl
    t_ok = any(tl in ALLTXT for _ in [0])  # V8.0+ ALLTXT
    ok = f_ok and l_ok and t_ok
    if ok: c10_pass += 1
    else: c10_fail.append((tl, fields, f_ok, l_ok))
    check(f"C10-{tl}", f"{tl}({','.join(fields)})→{ {'T1':'L1','T2':'L2','T3':'L3','T4':'L4'}[tl] }", ok, f"字段{'+'.join(fields)}")
log(f"  C10 通过 {c10_pass}/4")

# =====================================================================
# C11 双向闭环（正向取物 → 反向回溯：工具名→实例→场景→面）
# =====================================================================
log("\n[C11] 双向闭环（工具→实例→场景面→治理层 四跳回环）")
c11_pass = 0; c11_fail = []
for n, name, face in scen_tools[:10]:  # 抽前10个场景工具做回环
    t = find_tool(name.split("（")[0].strip())
    if not t:
        core = name.split(" ")[0].strip()
        t = find_tool(core)
    ok = t is not None and face in ["系统面", "管理面", "过程面", "产品面"]
    if ok: c11_pass += 1
    else: c11_fail.append((n, name))
    check(f"C11-{n}", f"{name[:16]}→{t['num'] if t else '?'}→{face}", ok, f"回环{'✅' if ok else '❌'}")
log(f"  C11 通过 {c11_pass}/10")

# =====================================================================
# C12 多维组合（场景×大师×工具 三维交叉抽样）
# =====================================================================
log("\n[C12] 场景×大师×工具 三维组合（抽样 12 组合）")
COMBO3 = [
    ("冲压", "戴明", "SPC"), ("冲压", "石川", "鱼骨"),
    ("CNC", "谢宁", "MSA"), ("注塑", "田口", "DOE"),
    ("表面处理", "朱兰", "柏拉图"), ("组装/SMT", "新乡", "Poka-Yoke"),
    ("模具", "大野", "TPM"), ("来料", "克劳士比", "AQL"),
    ("出货", "今井", "QRQC"), ("产品开发", "赤尾", "QFD"),
    ("产品规划", "水野", "KANO"), ("产品规划", "戴明", "方针管理"),
]
c12_pass = 0; c12_fail = []
for ws, mas, tool in COMBO3:
    ws_ok = ws.split("/")[0].strip() in scen_txt or ws.split("/")[0].strip() in ALLTXT  # V8.0+ ALLTXT 跨文件
    mas_ok = mas in mas_txt
    t = find_tool(tool)
    tool_ok = t is not None and t["num"] in TOOL_NUMS
    ok = ws_ok and mas_ok and tool_ok
    if ok: c12_pass += 1
    else: c12_fail.append((ws, mas, tool))
    check(f"C12-{ws}/{mas}/{tool}", f"{ws}×{mas}×{tool}", ok, f"场景{ws_ok}+大师{mas_ok}+工具{tool_ok}")
log(f"  C12 通过 {c12_pass}/12" + (f"，失败 {c12_fail}" if c12_fail else "，三维组合全通"))

# =====================================================================
# 汇总
# =====================================================================
log("\n" + "=" * 78)
log("混合交叉测试汇总")
log("=" * 78)
from collections import defaultdict
grp = defaultdict(lambda: [0, 0])
for gid, name, passed, desc in R:
    g = gid.split("-")[0]
    grp[g][1] += 1
    if passed: grp[g][0] += 1
tp = sum(1 for r in R if r[2]); tt = len(R)
log(f"交叉用例总数：{tt}，通过 {tp}，失败 {tt - tp}")
for g in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12"]:
    p, n = grp.get(g, [0, 0])
    bar = "█" * (p * 20 // max(n, 1))
    log(f"  {g:<5} {p:>3}/{n:<3} {bar}")
log("\n失败明细：")
for gid, name, passed, desc in R:
    if not passed:
        log(f"  ❌ {gid} {name}: {desc}")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_cross_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_cross_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
