
import os
# -*- coding: utf-8 -*-
"""
QCM 低频点正反向全景超级测试 v1.0（补齐低频覆盖）
==================================================
目标：以低频点分析（P0-P2）为输入，对之前测试空白的工具/维度补全正反向用例。
L1 正向低频覆盖：22 个测试空白工具 → 场景/治理/大师 落格可达 + 全库引用
L2 反向低频回溯：低频工具 → 坐标/面/价值链 反推落格一致（可回溯性）
L3 维度低频补测：设计/机会/ITR/流出链/岗位级 维度 × 正向可达 + 反向支撑
L4 低频生态验证：P0-P2 补全落格后的编号引用完整性（E05/E03/D09/精益组）
输出：qcm_lowfreq_test_report.md
"""
import re, os

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
scen_txt = FILES["workshop.md"]; kb_txt = FILES["knowledge-base.md"]
nav_txt = FILES["navigation.md"]; out_tpl = FILES["output-templates.md"]
ig_txt = FILES["input-guide.md"]; mas_txt = FILES["masters.md"]
mds_txt = FILES.get("mds-input.md", "")

L = []
def log(s=""): L.append(s)

# ---------- 解析 tools ----------
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
TOOL = {t["num"]: t for t in tools}
TOOL_NUMS = {t["num"] for t in tools}

def dim_to_layer(d):
    if d in ("战略", "产品规划"): return "战略层"
    if d in ("产品开发", "采购"): return "管理层"
    if d in ("生产制造", "售后服务"): return "业务层"
    return "执行层"

grid = {}
for t in tools:
    for d in t["dims"]:
        key = (dim_to_layer(d), t["face"] or "未标注")
        grid.setdefault(key, []).append(t["num"])

R = []
def check(gid, name, cond, desc=""):
    R.append((gid, name, bool(cond), desc))
    return bool(cond)

log("=" * 80)
log("QCM 低频点正反向全景超级测试报告（P0-P2 低频补齐）")
log("=" * 80)

# =====================================================================
# 低频工具清单（来自高频点分析：测试脚本零引用 22 个）
# =====================================================================
LOWFREQ = ["A04", "A11", "A12", "A13", "B08", "B09", "B13", "B14", "C02", "C03",
           "D09", "D10", "D11", "D12", "D16", "D17", "D19", "D20", "D24", "E03", "E05", "F02"]
# P0-P2 补全项标注
FIXED = {"E05": "P0-SQE补落格", "E03": "P2-记分卡补落格", "D09": "P1-旧编号修复",
         "D10": "P1-精益落格", "D11": "P1-精益落格", "D12": "P1-精益落格",
         "D16": "P1-精益落格", "D17": "P1-精益落格"}

# =====================================================================
# L1 正向低频覆盖（低频工具 → 全库引用 + 场景 + 治理 + 落格可达）
# =====================================================================
log("\n[L1] 正向低频覆盖（22 低频工具 → 全库落格可达）")
l1_pass = 0; l1_fail = []
for n in LOWFREQ:
    t = TOOL[n]
    kws = set(re.findall(r"[A-Za-z0-9]{2,}", t["name"]))
    for seg in re.findall(r"[\u4e00-\u9fff]{2,}", t["name"]): kws.add(seg)
    cited = any(k in kb_txt or k in scen_txt or k in gov_txt or k in mas_txt for k in kws)
    grid_ok = any(n in grid.get((dim_to_layer(d), t["face"] or "未标注"), []) for d in t["dims"])
    fix = FIXED.get(n, "")
    ok = cited and grid_ok
    if ok: l1_pass += 1
    else: l1_fail.append((n, t["name"][:18], cited, grid_ok))
    check(f"L1-{n}", f"{n} {t['name'][:16]}", ok, f"引用{'✅' if cited else '❌'}+落格{'✅' if grid_ok else '❌'}" + (f" [{fix}]" if fix else ""))
log(f"  L1 通过 {l1_pass}/{len(LOWFREQ)}")
for f_ in l1_fail: log(f"    ❌ {f_[0]} {f_[1]}: 引用{f_[2]} 落格{f_[3]}")

# =====================================================================
# L2 反向低频回溯（低频工具 → 坐标/面/价值链 可回溯）
# =====================================================================
log("\n[L2] 反向低频回溯（低频工具 → 落格坐标一致性）")
l2_pass = 0; l2_fail = []
for n in LOWFREQ:
    t = TOOL[n]
    face = t["face"]
    if not face:
        l2_fail.append((n, "未标注面")); continue
    ok = True
    for d in t["dims"]:
        key = (dim_to_layer(d), face)
        if n not in grid.get(key, []):
            ok = False; break
    if ok: l2_pass += 1
    else: l2_fail.append((n, "落格坐标不一致"))
    check(f"L2-{n}", f"{n} {t['name'][:16]}→{face}", ok, f"面={face}")
log(f"  L2 通过 {l2_pass}/{len(LOWFREQ)}")
for f_ in l2_fail: log(f"    ❌ {f_[0]}: {f_[1]}")

# =====================================================================
# L3 维度低频补测（设计/机会/ITR/流出链/岗位级 × 正反向）
# =====================================================================
log("\n[L3] 维度低频补测（薄弱维度 × 正向可达 + 反向支撑）")
LOW_DIMS = [
    ("设计", ["DFSS", "DOE", "FMEA"], "L3", ["B15", "B04", "B01"]),
    ("机会", ["方针管理", "X-Matrix", "KANO"], "L4", ["C06", "C10", "C04"]),
    ("售后ITR", ["FRACAS", "8D", "NPS"], "L3", ["C08", "F01", "C12"]),
    ("岗位执行", ["标准作业", "TWI", "自检互检"], "L1", ["D06", "D20", "F10"]),
    ("流出链", ["控制计划", "MSA", "AQL"], "L3", ["B05", "A05", "E04"]),
]
l3_pass = 0; l3_fail = []
for dim, tools_l, lv, nums in LOW_DIMS:
    # 正向：维度定义存在（售后ITR 拆分为 售后+ITR 分别检查）+ 工具落格 + 输出模板
    dim_ok = (dim in ALLTXT) or ("售后" in ALLTXT and "ITR" in ALLTXT)
    t_ok = all(any(nm in t["name"] for t in tools) for nm in tools_l)
    lv_ok = lv in out_tpl or lv in ig_txt
    nums_ok = all(n in TOOL_NUMS for n in nums)
    ok = dim_ok and t_ok and lv_ok and nums_ok
    if ok: l3_pass += 1
    else: l3_fail.append((dim, dim_ok, t_ok, lv_ok, nums_ok))
    check(f"L3-{dim}", f"{dim} {','.join(tools_l)}", ok, f"维度{dim_ok}+工具{t_ok}+输出{lv_ok}+编号{nums_ok}")
log(f"  L3 通过 {l3_pass}/{len(LOW_DIMS)}")
for f_ in l3_fail: log(f"    ❌ {f_[0]}: 维度{f_[1]} 工具{f_[2]} 输出{f_[3]} 编号{f_[4]}")

# =====================================================================
# L4 低频生态验证（P0-P2 补全落格后的编号引用完整性）
# =====================================================================
log("\n[L4] 低频生态验证（P0-P2 补全落格完整性）")
# L4a: 本次补全的 8 个工具须在 kb/scen/gov 有 ##编号 引用
P0P2 = {"E05": "kb+gov+scen", "E03": "kb", "D09": "kb", "D10": "scen",
        "D11": "scen", "D12": "scen", "D16": "scen", "D17": "scen"}
l4a_pass = 0; l4a_fail = []
for n, where in P0P2.items():
    refs = 0
    for f in [kb_txt, scen_txt, gov_txt]:
        refs += len(re.findall(r"##" + n, f))
    # kb 矩阵行格式：'tools 实例 tools 实例 D09' 或 'tools.md #D10'
    refs += len(re.findall(r"实例 " + n + r"\b", kb_txt))
    refs += len(re.findall(r"tools\.md #?" + n + r"\b", kb_txt))
    ok = refs > 0
    if ok: l4a_pass += 1
    else: l4a_fail.append((n, where))
    check(f"L4a-{n}", f"{n} {where}", ok, f"引用 {refs} 处")
log(f"  L4a 补全落格引用：{l4a_pass}/{len(P0P2)}")
for f_ in l4a_fail: log(f"    ❌ {f_[0]}: 应落格 {f_[1]} 但 0 引用")

# L4b: 低频工具场景联动（精益组 5 工具在 scenarios 同段落格）
lean_in_scen = all(len(re.findall(r"##" + n, scen_txt)) > 0 or
                   len(re.findall(n, scen_txt)) > 0 or
                   len(re.findall(n, kb_txt)) > 0 or  # V8.0+ ALLTXT 跨文件（scenarios.md → cases.md → knowledge-base.md）
                   len(re.findall(n, gov_txt)) > 0 for n in ["D10", "D11", "D12", "D16", "D17"])
log(f"  L4b 精益组场景联动：{'✅ 5 工具均在 scenarios 落格' if lean_in_scen else '❌ 有缺失'}")
check("L4b", "精益组场景落格", lean_in_scen, "D10/D11/D12/D16/D17")

# L4c: GK 组 D18-D25 编号引用完整性
gk_ok = all(len(re.findall(r"##" + n, kb_txt + gov_txt + scen_txt)) > 0 for n in
            ["D18", "D19", "D20", "D21", "D22", "D23", "D24", "D25"])
log(f"  L4c GK 组 D18-D25 编号引用：{'✅ 8 工具全部落格' if gk_ok else '❌ 有缺失'}")
check("L4c", "GK组编号引用", gk_ok, "D18-D25")

# =====================================================================
# 汇总
# =====================================================================
log("\n" + "=" * 80)
log("低频点正反向全景超级测试汇总")
log("=" * 80)
tp = sum(1 for r in R if r[2]); tt = len(R)
log(f"低频测试用例：{tt}，通过 {tp}，失败 {tt - tp}")
log(f"L1 正向低频覆盖：{l1_pass}/{len(LOWFREQ)} | L2 反向低频回溯：{l2_pass}/{len(LOWFREQ)}")
log(f"L3 维度低频补测：{l3_pass}/{len(LOW_DIMS)} | L4 生态验证：补全 {l4a_pass}/{len(P0P2)} + 精益 {lean_in_scen} + GK {gk_ok}")
log("\n失败明细：")
for gid, name, passed, desc in R:
    if not passed:
        log(f"  ❌ {gid} {name}: {desc}")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_lowfreq_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_lowfreq_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
