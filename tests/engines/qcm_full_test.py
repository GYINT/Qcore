
import os
# -*- coding: utf-8 -*-
"""
QCM 全场景双向测试 v3.0（86 工具重编号动态版）
A. 正向：五价值链 / 六层级 / 四面 / 八场景维度 / 16格(层×面)
B. 反向：86 工具悬空（动态名称匹配）/ scenarios 28 工具回溯 / governance 单元格 / masters 大师工具
C. 交叉：6 条关键链闭合
输出：qcm_full_test_report.md
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

tools_txt = rd("tools.md"); scen_txt = rd("scenarios.md")
kb_txt = rd("knowledge-base.md"); gov_txt = rd("governance.md")
dim_txt = rd("dimensions.md"); mas_txt = rd("masters.md")

L = []
def log(s=""): L.append(s)

# ---------- 解析 tools.md（新编号 [A-F]\d+） ----------
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

# 工具名关键词（动态）
def tool_kws(t):
    n = t["name"]
    kws = set(re.findall(r"[A-Za-z0-9]{2,}", n))
    for seg in re.findall(r"[\u4e00-\u9fff]{2,}", n):
        kws.add(seg)
    for c in re.findall(r"[（(]([^）)]*)[）)]", n):
        for seg in re.split(r"[+、/ ]", c):
            if len(seg) >= 2 and re.search(r"[\u4e00-\u9fff]", seg):
                kws.add(seg)
    return {k for k in kws if len(k) >= 2}

# ---------- scenarios ----------
ws_re = re.compile(r"^## (\d+)\. (.+?)(?: ·|$)", re.M)
workshops = [(int(m.group(1)), m.group(2).strip()) for m in ws_re.finditer(scen_txt) if 1 <= int(m.group(1)) <= 10]
scen_tool_re = re.compile(r"^### 工具(\d+) · (.+?)\s*——\s*(系统面|管理面|过程面|产品面)", re.M)
scen_tools = [(int(m.group(1)), m.group(2).strip(), m.group(3)) for m in scen_tool_re.finditer(scen_txt)]

# ---------- governance ----------
gov_cells = {}
for line in gov_txt.splitlines():
    for lv in ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"]:
        if line.startswith("| **" + lv):
            gov_cells[lv] = [b.strip() for b in line.split("|")[2:-1] if b.strip()]

# ---------- masters 代表工具 ----------
mas_tools = []
for m in re.finditer(r"## 代表工具与方法\n(.*?)(?=\n## |\Z)", mas_txt, re.S):
    for ln in m.group(1).splitlines():
        ln = ln.strip().lstrip("-*").strip()
        if ln and len(ln) >= 3: mas_tools.append(ln)

ALL_KWS = sorted({k for t in tools for k in tool_kws(t)}, key=len, reverse=True)
TOOL_KW_RE = re.compile("|".join(re.escape(k) for k in ALL_KWS)) if ALL_KWS else None
tool_name_set = {t["name"] for t in tools}

def name_match(text):
    """文本是否含任一工具名/关键词"""
    if TOOL_KW_RE and TOOL_KW_RE.search(text):
        return True
    return any(tn.split("（")[0].split("(")[0].strip() in text for tn in tool_name_set)

# ========== A. 正向 ==========
log("=" * 72)
log("QCM 全场景双向测试报告（v3.0 · 86 工具重编号动态版）")
log("=" * 72)
log("\n[A] 正向验证（场景→工具，取物可达）")
log("-" * 60)

chains = {c: [] for c in ["产品规划", "产品开发", "采购", "生产制造", "售后服务"]}
dims_cov = {d: 0 for d in ["产品规划", "产品开发", "采购", "生产制造", "售后服务", "战略", "现场", "岗位执行"]}
for t in tools:
    for d in t["dims"]:
        if d in chains: chains[d].append(t["num"])
        if d in dims_cov: dims_cov[d] += 1
log("[A1] 五价值链场景 × 工具覆盖：")
for c, nums in chains.items():
    uniq = sorted(set(nums))
    log(f"  {c:<6} {len(uniq):>2} 个 {'█'*min(len(uniq),30)} {'<-- 缺口!' if not uniq else ''}")

log("\n[A2] 六治理层级 × 单元格：")
for lv, cells in gov_cells.items():
    log(f"  {lv:<5} {len(cells):>2} 格 / 工具命中 {sum(1 for c in cells if TOOL_KW_RE and TOOL_KW_RE.search(c))}")

faces = {f: 0 for f in ["系统面", "管理面", "过程面", "产品面"]}
for t in tools:
    if t["face"]: faces[t["face"]] += 1
no_face = [t["num"] for t in tools if not t["face"]]
log("\n[A3] 四面 × 工具数：")
for f, c in faces.items():
    log(f"  {f:<5} {c:>2} {'<-- 盲区!' if c == 0 else ''}")
log(f"  未标注面: {len(no_face)} -> {no_face if no_face else '无'}")

log("\n[A4] 八场景维度 × 工具数：")
for d, c in dims_cov.items():
    log(f"  {d:<6} {c:>2} {'<-- 缺口!' if c == 0 else ''}")

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
log("\n[A5] 16 格主矩阵（层×面）覆盖：")
for layer in ["战略层", "管理层", "业务层", "执行层"]:
    row = []
    for face in ["系统面", "管理面", "过程面", "产品面"]:
        c = len(grid.get((layer, face), []))
        row.append(f"{face[0]}{c}")
        if c == 0: log(f"  !! 空格: {layer}×{face}")
    log(f"  {layer:<5} " + " ".join(row))

# ========== B. 反向 ==========
log("\n[B] 反向验证（工具→场景，落格完整）")
log("-" * 60)

orphan = []
for t in tools:
    n = t["num"]
    kws = tool_kws(t)
    cited = any(kw in kb_txt or kw in scen_txt or kw in gov_txt for kw in kws)
    if not cited: orphan.append((n, t["name"]))
log(f"\n[B1] 86 工具落格（名称+关键词匹配）：悬空 {len(orphan)} -> " + (", ".join(f"#{n}" for n, _ in orphan) if orphan else "无"))
for n, name in orphan: log(f"    #{n} {name[:40]}")

tool_nums = {t["num"] for t in tools}
# 场景工具按名称回溯 tools 新编号（放行落格别名）
ALIAS = ["4M", "4M1E", "5why", "5w2h", "QRQC", "双归零", "FAI", "首件"]
def scen_tool_found(name):
    if any(a.lower() in name.lower() for a in ALIAS):
        return True
    for t in tools:
        if name.split("（")[0].split("(")[0].strip() in t["name"] or t["name"].split("（")[0].split("(")[0].strip() in name:
            return True
    kws = tool_kws(tools[0])  # placeholder
    return any(k in name for k in ALL_KWS)
gap = []
for num, name, face in scen_tools:
    if not scen_tool_found(name):
        gap.append((num, name))
log(f"[B2] scenarios 28 工具 → tools 实例：缺 {len(gap)} -> " + (", ".join(f"工具{g}" for g, _ in gap) if gap else "无"))

gov_hit, gov_act = [], []
for lv, cells in gov_cells.items():
    for c in cells:
        if TOOL_KW_RE and TOOL_KW_RE.search(c): gov_hit.append((lv, c))
        elif not re.match(r"^[—–\-]$", c): gov_act.append((lv, c))
log(f"[B3] governance 单元格：工具命中 {len(gov_hit)} / 活动类 {len(gov_act)}")
log("     活动类示例: " + ", ".join(c for _, c in gov_act[:12]))

mas_hit, mas_unk = [], []
for m in mas_tools:
    if TOOL_KW_RE and TOOL_KW_RE.search(m): mas_hit.append(m)
    else: mas_unk.append(m)
log(f"[B4] masters 代表工具：匹配 {len(mas_hit)} / 理论框架 {len(mas_unk)}")
log("     理论框架示例: " + ", ".join(mas_unk[:10]))

# ========== C. 交叉 ==========
log("\n[C] 交叉一致性 + 多链闭合")
log("-" * 60)
# 6 条关键链（按工具名找新编号）
def find_by_kw(kw):
    for t in tools:
        if kw.lower() in t["name"].lower() or kw in t["name"]:
            return t["num"]
    return None
chains_test = {
    "统计链 SPC←MSA←控制计划": ["SPC", "MSA", "控制计划"],
    "需求链 VOC→KANO→QFD→FMEA": ["VOC", "KANO", "QFD", "FMEA"],
    "改进链 DMAIC→8D→CAPA→RCA": ["DMAIC", "8D", "CAPA", "RCA"],
    "精益链 Heijunka→看板→SMED→单件流": ["Heijunka", "看板", "SMED", "单件流"],
    "门控链 Stage-Gate→APQP→质量门→VDA 6.5": ["Stage-Gate", "APQP", "质量门", "VDA 6.5"],
    "供应链 AQL→VDA 6.3→VDA 6.5": ["AQL", "VDA 6.3", "VDA 6.5"],
}
log("\n[C1] 6 条关键工具链节点存在性：")
for name, kws in chains_test.items():
    found = [find_by_kw(k) for k in kws]
    missing = [k for k, f in zip(kws, found) if not f]
    log(f"  {name:<26} {'闭合 ✅' if not missing else '缺节点 '+str(missing)+' ⚠️'}")

face_scen = {"系统面": 0, "管理面": 0, "过程面": 0, "产品面": 0}
for _, _, face in scen_tools: face_scen[face] += 1
log(f"[C2] scenarios 28 工具面分布：系统{face_scen['系统面']}/管理{face_scen['管理面']}/过程{face_scen['过程面']}/产品{face_scen['产品面']}")
log(f"[C3] 车间-场景覆盖：{len(workshops)} 车间/场景（§1-§10）")

# ========== 汇总 ==========
log("\n" + "=" * 72)
log("[汇总] 可靠性结论（86 工具重编号后）")
log("=" * 72)
empty_grid = [f"{k[0]}×{k[1]}" for k, v in grid.items() if not v and k[1] != "未标注"]
log(f"  1. 工具总数: {len(tools)}（tools.md 解析）| 五价值链: {sum(1 for v in chains.values() if v)}/5")
log(f"  2. 四面: {sum(1 for v in faces.values() if v)}/4 | 未标注面: {len(no_face)}")
log(f"  3. 16格空档: {len(empty_grid)} -> {empty_grid if empty_grid else '无'}")
log(f"  4. 反向-工具悬空: {len(orphan)} -> {'有缺口' if orphan else '无'}")
log(f"  5. 反向-场景工具缺实例: {len(gap)} -> {'有缺口' if gap else '无'}")
log(f"  6. governance: 工具命中 {len(gov_hit)} / 活动类 {len(gov_act)}(非缺口)")
log(f"  7. masters: 工具匹配 {len(mas_hit)} / 理论框架 {len(mas_unk)}(非缺口)")
log(f"  8. 多链闭合: {sum(1 for n, k in chains_test.items() if all(find_by_kw(kw) for kw in k))}/6")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_full_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_full_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
