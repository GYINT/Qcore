
import os
# -*- coding: utf-8 -*-
"""
QCM 全链接闭环测试 v1.0（输入-场景-工具-输出）
==================================================
六跳闭环：J1 端到端定位 → J2 多链筛选 → J3 横轴16格(层×面) → J4 工具取物 → J5 治理格 → J6 输出模板
6 个典型输入用例（变异/失效/目标/供方/规划/客诉 六型）
输出：qcm_loop_test_report.md
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

nav = rd("navigation.md"); out_tpl = rd("output-templates.md")
tools_txt = rd("tools.md"); gov_txt = rd("governance.md")
scen_txt = rd("scenarios.md"); input_guide = rd("input-guide.md")

L = []
def log(s=""): L.append(s)

# ---------- 解析 ----------
# tools: 77 工具 (num, name, dims, face)
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

def dim_to_layer(d):
    if d in ("战略", "产品规划"): return "战略层"
    if d in ("产品开发", "采购"): return "管理层"
    if d in ("生产制造", "售后服务"): return "业务层"
    return "执行层"

# 16格映射: (层, 面) -> [工具号]
grid = {}
for t in tools:
    for d in t["dims"]:
        key = (dim_to_layer(d), t["face"] or "未标注")
        grid.setdefault(key, []).append(t["num"])
# 面缺失工具按其 dims 推测（用场景面默认）：无 face 时跳过显式校验，标记推断
tool_nums = {t["num"] for t in tools}

# governance 层级→责任人/活动
gov_role = {}
for line in gov_txt.splitlines():
    m = re.match(r"^### 2\.\d+ (工序级|岗位级|现场级|车间级|部门级|公司级)（", line)
    if m: gov_role[m.group(1)] = True
    m2 = re.match(r"^## 2\.\d+ .*?（(工序级|岗位级|现场级|车间级|部门级|公司级)）", line)
    if m2: gov_role[m2.group(1)] = True

# 输出模板 L1-L4
tpl_lv = set(re.findall(r"^## (L[1-4]) 输出模板", out_tpl, re.M))
nav_lv = set(re.findall(r"^## (L[1-4])", out_tpl, re.M))

# ---------- 用例定义（16 格全覆盖） ----------
# 每用例: 名称/层/面/端到端/多链/预期工具/治理层级/输出级
CASES = [
    {"name": "质量战略与体系搭建", "layer": "战略层", "face": "系统面", "e2e": "OTC", "chain": "系统链",
     "tools": ["方针管理", "COPQ", "ISO 9001"], "gov": "公司级", "lv": "L4"},
    {"name": "质量目标展开（catchball）", "layer": "战略层", "face": "管理面", "e2e": "OTC", "chain": "系统链",
     "tools": ["方针管理", "X-Matrix"], "gov": "公司级", "lv": "L3"},
    {"name": "全链质量成本优化", "layer": "战略层", "face": "过程面", "e2e": "OTC", "chain": "发生链",
     "tools": ["DMAIC", "COPQ"], "gov": "公司级", "lv": "L3"},
    {"name": "客户需求战略定位", "layer": "战略层", "face": "产品面", "e2e": "MTL", "chain": "发生链",
     "tools": ["KANO", "VOC"], "gov": "公司级", "lv": "L3"},
    {"name": "体系审核与成熟度", "layer": "管理层", "face": "系统面", "e2e": "OTC", "chain": "系统链",
     "tools": ["ISO 9001", "CMMI"], "gov": "部门级", "lv": "L3"},
    {"name": "供应商绩效管控", "layer": "管理层", "face": "管理面", "e2e": "LTC", "chain": "流出链",
     "tools": ["记分卡", "供应商审核"], "gov": "部门级", "lv": "L3"},
    {"name": "NPI 门控管理", "layer": "管理层", "face": "过程面", "e2e": "MTL", "chain": "发生链",
     "tools": ["Stage-Gate", "APQP"], "gov": "部门级", "lv": "L3"},
    {"name": "产品需求定义", "layer": "管理层", "face": "产品面", "e2e": "MTL", "chain": "发生链",
     "tools": ["VOC", "KANO", "QFD"], "gov": "部门级", "lv": "L3"},
    {"name": "过程审核（VDA6.3）", "layer": "业务层", "face": "系统面", "e2e": "OTC", "chain": "系统链",
     "tools": ["VDA 6.3", "供应商审核"], "gov": "车间级", "lv": "L2"},
    {"name": "过程监控判异", "layer": "业务层", "face": "管理面", "e2e": "OTC", "chain": "发生链",
     "tools": ["SPC", "层别法"], "gov": "车间级", "lv": "L2"},
    {"name": "工艺参数优化", "layer": "业务层", "face": "过程面", "e2e": "OTC", "chain": "发生链",
     "tools": ["DOE", "控制计划"], "gov": "车间级", "lv": "L3"},
    {"name": "出货检验（OQC）", "layer": "业务层", "face": "产品面", "e2e": "LTC", "chain": "流出链",
     "tools": ["AQL", "VDA 6.5"], "gov": "车间级", "lv": "L2"},
    {"name": "标准作业遵守审计（组合引用#32）", "layer": "执行层", "face": "系统面", "e2e": "OTC", "chain": "系统链",
     "tools": ["标准作业"], "gov": "现场级", "lv": "L1"},
    {"name": "现场异常响应", "layer": "执行层", "face": "管理面", "e2e": "OTC", "chain": "流出链",
     "tools": ["安灯", "QRQC"], "gov": "现场级", "lv": "L1"},
    {"name": "首件确认（FAI）", "layer": "执行层", "face": "过程面", "e2e": "OTC", "chain": "发生链",
     "tools": ["FAI", "检查表"], "gov": "工序级", "lv": "L1"},
    {"name": "自检互检（FAI 执行形态）", "layer": "执行层", "face": "产品面", "e2e": "LTC", "chain": "流出链",
     "tools": ["FAI"], "gov": "工序级", "lv": "L1"},
]

# 工具名检索（支持缩写）+ 落格别名（scenarios 显式标注的组合/别名引用）
def find_tool(name):
    for t in tools:
        if name.lower() in t["name"].lower():
            return t
    return None

ALIAS = {"4M": [5, 18], "4M1E": [5, 18], "5why": [3], "5w2h": [3], "5W2H": [3],
         "QRQC": [3, 37], "双归零": [3, 37], "FAI": [17, 13], "首件": [17, 13]}
def tool_ok(name):
    return find_tool(name) is not None or name in ALIAS

log("=" * 74)
log("QCM 全链接闭环测试报告（输入-场景-工具-输出，v1.0）")
log("=" * 74)
log("六跳链路：J1 端到端 → J2 多链 → J3 横轴16格 → J4 工具取物 → J5 治理格 → J6 输出模板")

all_pass = True
for i, c in enumerate(CASES, 1):
    log(f"\n{'─'*70}\n用例{i}：{c['name']}")
    jumps = []
    # J1 端到端
    j1 = c["e2e"] in nav
    jumps.append(("J1 端到端", j1, f"{c['e2e']} 定义"))
    # J2 多链
    j2 = c["chain"] in nav and "链" in c["chain"]
    jumps.append(("J2 多链", j2, f"{c['chain']} 定义"))
    # J3 横轴16格（层×面→工具）
    grid_tools = grid.get((c["layer"], c["face"]), [])
    j3 = len(grid_tools) > 0
    jumps.append(("J3 横轴16格", j3, f"{c['layer']}×{c['face']} → {len(grid_tools)} 工具 {grid_tools[:6]}"))
    # J4 工具取物（预期工具存在性 + 落格别名）
    miss_tools = [nm for nm in c["tools"] if not tool_ok(nm)]
    j4 = not miss_tools
    jumps.append(("J4 工具取物", j4, f"{c['tools']} 缺 {miss_tools if miss_tools else '无'}"))
    # J5 治理格
    j5 = c["gov"] in gov_role or any(c["gov"] in ln for ln in [rd("governance.md")[:3000]])
    j5 = c["gov"] in gov_txt
    jumps.append(("J5 治理格", j5, f"{c['gov']} 在 governance 定义"))
    # J6 输出模板
    j6 = c["lv"] in tpl_lv or c["lv"] in nav_lv
    jumps.append(("J6 输出模板", j6, f"{c['lv']} 模板存在"))
    # 汇总
    ok = all(j for _, j, _ in jumps)
    all_pass = all_pass and ok
    for tag, passed, desc in jumps:
        log(f"  {'✅' if passed else '❌'} {tag}: {desc}")
    log(f"  >> 闭环 {'全通 ✅' if ok else '断链 ⚠️'}")

log("\n" + "=" * 74)
n_pass = 0
for cc in CASES:
    ok = (cc["e2e"] in nav
          and cc["chain"] in nav
          and len(grid.get((cc["layer"], cc["face"]), [])) > 0
          and not [nm for nm in cc["tools"] if not tool_ok(nm)]
          and cc["gov"] in gov_txt
          and (cc["lv"] in tpl_lv or cc["lv"] in nav_lv))
    if ok: n_pass += 1
log(f"[汇总] 全链接闭环：{len(CASES)} 用例，全通 {n_pass} 个")
log("  链路存在性依据：J1/J2=navigation.md 协议；J3=16格(tools 坐标)；J4=tools.md 实例+落格别名；J5=governance.md；J6=output-templates.md")
log("  注：J3 中未标注面工具按 dims 推断层、face 缺失时不计入显式格（面标注修复后精度提升）")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_loop_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_loop_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
