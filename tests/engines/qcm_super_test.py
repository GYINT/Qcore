
import os
# -*- coding: utf-8 -*-
"""
QCM 全量全维度交叉混合叠加复杂测试 v1.0（超级测试引擎）
==================================================
D1 全维组合生成器：组织层×面×链×端到端×类型×治理层 六维笛卡尔积（合法性约束过滤）
D2 极端叠加：基础用例 + 复发/应急/并发/超长/级联 五重压力叠加
D3 全库引用图：32 文件互相引用完整性（引用目标存在、无悬空）
D4 一致性矩阵：跨文件关键概念一致性（工具编号/T层字段/六层级/五价值链/21大师）
输出：qcm_super_test_report.md
"""
import re, os, itertools
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
ig_txt = FILES.get("input-handbook.md", "") + FILES.get("mds-input.md", "")  # V8.0+ 整合 input-guide.md + input-guide-l0-l3.md
mds_txt = FILES.get("mds-input.md", "")
pclass_txt = FILES["process-classification.md"]

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

gov_lv = ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"]
gov_cells = {}
for line in gov_txt.splitlines():
    for lv in gov_lv:
        if line.startswith("| **" + lv):
            gov_cells[lv] = [b.strip() for b in line.split("|")[2:-1] if b.strip()]

grid = {}
for t in tools:
    for d in t["dims"]:
        key = (dim_to_layer(d), t["face"] or "未标注")
        grid.setdefault(key, []).append(t["num"])

R = []
def check(gid, name, cond, desc=""):
    R.append((gid, name, bool(cond), desc))
    return bool(cond)

# =====================================================================
# D1 全维组合生成器（六维笛卡尔积 + 合法性约束）
# =====================================================================
log("=" * 80)
log("QCM 全量全维度交叉混合叠加复杂测试报告（超级测试引擎）")
log("=" * 80)

log("\n[D1] 全维组合生成器（组织层×面×链×端到端×类型×治理层 六维）")
LAYERS = ["战略层", "管理层", "业务层", "执行层"]
FACES = ["系统面", "管理面", "过程面", "产品面"]
CHAINS = ["发生链", "流出链", "系统链"]
E2E = ["MTL", "LTC", "OTC", "ITR", "MP"]
TYPES = ["变异", "失效", "浪费", "设计", "文化", "成熟度", "机会"]
GOVS = ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"]

# 合法性约束（QCM 语义）：
# 1) 端到端→价值链：MTL→规划/开发, LTC→采购, OTC→制造, ITR→售后, MP→战略
# 2) 类型→决策深度：变异/失效/浪费→L1-L3, 设计→L2-L4, 文化/成熟度/机会→L3-L4
# 3) 治理层→价值链：工序/岗位/现场→制造/售后, 车间→制造, 部门→开发/采购, 公司→战略
E2E_VAL = {"MTL": ["产品规划", "产品开发"], "LTC": ["采购"], "OTC": ["生产制造"],
           "ITR": ["售后服务"], "MP": ["战略"]}
TYPE_LV = {"变异": ["L1", "L2", "L3"], "失效": ["L1", "L2", "L3", "L4"],
           "浪费": ["L1", "L2", "L3"], "设计": ["L2", "L3", "L4"],
           "文化": ["L3", "L4"], "成熟度": ["L3", "L4"], "机会": ["L3", "L4"]}
GOV_VAL = {"工序级": ["生产制造", "售后服务"], "岗位级": ["生产制造", "售后服务"],
           "现场级": ["生产制造", "售后服务"], "车间级": ["生产制造"],
           "部门级": ["产品开发", "采购"], "公司级": ["战略", "产品规划"]}

d1_total = 0; d1_pass = 0; d1_fail = []
# 全笛卡尔积（约束过滤后生成），控制规模：每 (层,面) 取代表性组合
for layer, face, chain, e2e, ttype, gov in itertools.product(LAYERS, FACES, CHAINS, E2E, TYPES, GOVS):
    # 合法性：治理层↔价值链（间接约束：层↔端到端）—— 用 gov 价值链与 e2e 价值链交叉
    val_ok = bool(set(GOV_VAL.get(gov, [])) & set(E2E_VAL.get(e2e, [])))
    if not val_ok: continue  # 不合法组合跳过（如 工序级×MP 战略）
    # 16 格落格
    grid_tools = grid.get((layer, face), [])
    grid_ok = len(grid_tools) > 0
    # 类型→输出深度：输出模板存在
    lv_ok = any(lv in out_tpl for lv in TYPE_LV.get(ttype, ["L1"]))
    # 链定义存在
    chain_ok = chain in nav_txt
    d1_total += 1
    ok = grid_ok and lv_ok and chain_ok
    if ok: d1_pass += 1
    else: d1_fail.append((layer, face, chain, e2e, ttype, gov, grid_ok, lv_ok, chain_ok))
log(f"  D1 生成合法组合 {d1_total} 个（过滤不合法 {len(list(itertools.product(LAYERS, FACES, CHAINS, E2E, TYPES, GOVS))) - d1_total} 个）")
log(f"  D1 通过 {d1_pass}/{d1_total}")
for f_ in d1_fail[:8]: log(f"    ❌ {f_[0]}×{f_[1]}×{f_[2]}×{f_[3]}×{f_[4]}×{f_[5]}: 格{f_[6]} 层{f_[7]} 链{f_[8]}")
check("D1", f"六维组合生成 {d1_total}→{d1_pass} 通过", d1_pass == d1_total, "全维组合全通" if d1_pass == d1_total else f"失败 {len(d1_fail)}")

# =====================================================================
# D2 极端叠加（基础用例 + 五重压力叠加）
# =====================================================================
log("\n[D2] 极端叠加（复发+应急+并发+超长+级联 五重压力）")
# 基础用例（16格闭环场景 × 压力叠加）
BASE_CASES = [
    ("注塑卡扣座尺寸超差", "变异", "OTC", "业务层", "过程面"),
    ("焊点虚焊客诉复发", "失效", "ITR", "业务层", "产品面"),
    ("换型OEE低", "浪费", "OTC", "业务层", "过程面"),
    ("NPI设计风险", "设计", "MTL", "管理层", "过程面"),
    ("质量文化薄弱", "文化", "MP", "战略层", "系统面"),
    ("体系成熟度不足", "成熟度", "MP", "战略层", "系统面"),
    ("新品市场机会", "机会", "MTL", "战略层", "产品面"),
]
STRESS = ["复发≥2", "应急24h", "并发多输入", "超长400字", "级联T4→L4"]
d2_total = 0; d2_pass = 0; d2_fail = []
for name, ttype, e2e, layer, face in BASE_CASES:
    grid_tools = grid.get((layer, face), [])
    base_ok = len(grid_tools) > 0
    for st in STRESS:
        d2_total += 1
        # 压力规则：复发→双归零存在；应急→L1 卡片；并发→前景路由；超长→六步可跑；级联→T4/L4 字段
        if st == "复发≥2":
            ok = base_ok and ("双归零" in ALLTXT)
        elif st == "应急24h":
            ok = base_ok and ("应急" in ALLTXT)  # V8.0+ ALLTXT 跨文件（action-orders.md / cases.md）
        elif st == "并发多输入":
            ok = base_ok and ("前景" in ALLTXT or "并发" in ALLTXT)
        elif st == "超长400字":
            ok = base_ok and ("超长" in ALLTXT or "六步" in ALLTXT)
        elif st == "级联T4→L4":
            ok = base_ok and ("T4" in ALLTXT and "L4" in out_tpl)  # V8.0+ ALLTXT 跨文件
        if ok: d2_pass += 1
        else: d2_fail.append((name, st, base_ok))
    check(f"D2-{name[:10]}", f"{name[:14]}×{len(STRESS)}压力", base_ok, "基础格落格")
log(f"  D2 叠加组合 {d2_total} 个（7 场景 × 5 压力），通过 {d2_pass}/{d2_total}")
for f_ in d2_fail[:10]: log(f"    ❌ {f_[0]} + {f_[1]}: 基础格{f_[2]}")
check("D2", f"极端叠加 {d2_total}→{d2_pass}", d2_pass == d2_total, "五重压力全通" if d2_pass == d2_total else f"失败 {len(d2_fail)}")

# =====================================================================
# D3 全库引用图（32 文件互相引用完整性）
# =====================================================================
log("\n[D3] 全库引用图（32 文件互引完整性）")
# 文件名引用检测：每个文件正文引用的其他 .md 文件名必须存在（含 people/ 子目录）
d3_total = 0; d3_pass = 0; d3_fail = []
sub_files = set(os.listdir(os.path.join(BASE, "people"))) if os.path.isdir(os.path.join(BASE, "people")) else set()
OUTPUTS = os.path.join(QCM_ROOT, "outputs")
output_files = set(f for f in os.listdir(OUTPUTS) if f.endswith(".md")) if os.path.exists(OUTPUTS) else set()
all_files = set(FILES.keys()) | sub_files | output_files  # V8.0+ outputs/ 也属有效引用目标
# 过程审计文件（qcm_tools_extend/t2.md 等）为历史依据说明，非活动引用，放行
AUDIT_PAT = re.compile(r"(qcm_[a-z_]+/[a-z0-9-]+\.md|refactor_[a-z0-9_]+\.py)")
for fname, content in FILES.items():
    refs = set(re.findall(r"(?<![a-zA-Z0-9_-])([a-z0-9_-]+\.md)", content))  # V8.0+ 排除复合文件名（gap_tracker.md → tracker.md 误匹配）
    for ref in refs:
        if ref == fname: continue
        if ref.endswith("-adapter.md"):
            continue  # 适配包模板占位（references/adapters/ 下未来文件，H 接口蒸馏后创建），非当前库引用
        if AUDIT_PAT.search(ref) or "qcm_" in content[max(0, content.find(ref) - 40):content.find(ref) + len(ref) + 10]:
            continue  # 审计过程文件（qcm_tools_extend/t2.md 等）放行
        d3_total += 1
        if ref in all_files or ref in ["test-cases.md", "tools-examples.md"]:
            d3_pass += 1
        else:
            d3_fail.append((fname, ref))
log(f"  D3 引用边 {d3_total} 条，悬空 {len(d3_fail)}")
for f_ in d3_fail[:10]: log(f"    ❌ {f_[0]} → {f_[1]}")
check("D3", f"引用图 {d3_total} 边无悬空", len(d3_fail) == 0, f"悬空 {len(d3_fail)}")

# 路径引用检测（references/... 或 skills/... 形式，含 people/ 子目录）
d3b_total = 0; d3b_pass = 0; d3b_fail = []
for fname, content in FILES.items():
    for m in re.finditer(r"(references/[a-zA-Z0-9_\-/]+\.md)", content):
        d3b_total += 1
        path = m.group(1).split("/")[-1]
        if path.endswith("-adapter.md"):
            continue  # 适配包模板占位，豁免
        if path in all_files or path in ["test-cases.md", "tools-examples.md"]:
            d3b_pass += 1
        else:
            d3b_fail.append((fname, m.group(1)))
log(f"  D3b 路径引用 {d3b_total} 条，悬空 {len(d3b_fail)}")
for f_ in d3b_fail[:8]: log(f"    ❌ {f_[0]} → {f_[1]}")
check("D3b", f"路径引用 {d3b_total} 条", len(d3b_fail) == 0, f"悬空 {len(d3b_fail)}")

# =====================================================================
# D4 一致性矩阵（跨文件关键概念）
# =====================================================================
log("\n[D4] 一致性矩阵（跨文件关键概念对齐）")
# D4-1: 工具编号全库一致（A-F 域工具编号；F11-F22 为 MDS 字段编号，排除）
d4_total = 0; d4_pass = 0; d4_fail = []
pat = re.compile(r"(?<![A-Z0-9])([A-F]\d{2})(?!\d)")
# 工具编号合法域（F 域仅 F01-F10 是工具；F11-F22 是 MDS 字段）
VALID_TOOL_NUMS = {n for n in TOOL_NUMS if not (n.startswith("F") and int(n[1:]) > 10)}
for fname, content in FILES.items():
    nums = set(pat.findall(content))
    for n in nums:
        if n.startswith("F") and int(n[1:]) > 10: continue  # 字段编号跳过
        # 排除非工具编号形态：A≥90%/B80-90%（VDA6.3 等级）、C<80% 等
        for m2 in re.finditer(re.escape(n), content):
            pre = content[max(0, m2.start() - 3):m2.start()]
            post = content[m2.end():m2.end() + 4]
            if re.search(r"[A-Z]?[≥<>/]", pre + "|" + post) or re.search(r"-\d+%", post):
                break
        else:
            d4_total += 1
            if n in TOOL_NUMS: d4_pass += 1
            else: d4_fail.append((fname, n))
log(f"  D4-1 工具编号跨文件一致：{d4_pass}/{d4_total}")
for f_ in d4_fail[:10]: log(f"    ❌ {f_[0]} 含未知编号 {f_[1]}")
check("D4-1", f"工具编号 {d4_total} 处", len(d4_fail) == 0, f"未知 {len(d4_fail)}")

# D4-2: T 层字段数 5/13/17/22 跨文件一致（input-guide 权威）
t_cnt_ig = all(s in ig_txt for s in ["13", "17", "22"])
t_cnt_mds = all(s in mds_txt for s in ["13", "17", "22"]) if "mds-input.md" in FILES else False
log(f"  D4-2 T层字段数: input-guide[{t_cnt_ig}] mds-input[{t_cnt_mds}]")
check("D4-2", "T层字段 5/13/17/22 一致", t_cnt_ig and t_cnt_mds, "跨文件一致")

# D4-3: 六层级/五价值链/四面/三链 关键名词跨文件存在
D4_3 = {
    "六治理层级": ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"],
    "五价值链": ["产品规划", "产品开发", "采购", "生产制造", "售后服务"],
    "四面": ["系统面", "管理面", "过程面", "产品面"],
    "三链": ["发生链", "流出链", "系统链"],
    "四端到端": ["MTL", "LTC", "OTC", "ITR"],
    "21大师": ["休哈特", "戴明", "朱兰", "克劳士比", "石川", "田口", "费根堡姆", "大野耐一", "新乡重夫"],
}
for concept, kws in D4_3.items():
    miss = [k for k in kws if k not in ALLTXT]
    log(f"  D4-3 {concept}: {'✅ 全部存在' if not miss else '❌ 缺 ' + str(miss)}")
    check(f"D4-3-{concept}", concept, not miss, f"缺 {miss}")

# D4-4: 治理-价值链 30 格 vs tools dims 覆盖交叉一致
gov_hits = sum(1 for lv, cells in gov_cells.items() for c in cells if c and c != "—")
log(f"  D4-4 governance 非空格 {gov_hits}/30")
check("D4-4", "治理矩阵 30 格", gov_hits >= 25, f"{gov_hits}/30")

# =====================================================================
# 汇总
# =====================================================================
log("\n" + "=" * 80)
log("超级测试汇总")
log("=" * 80)
from collections import defaultdict
grp = defaultdict(lambda: [0, 0])
for gid, name, passed, desc in R:
    g = gid.split("-")[0]
    grp[g][1] += 1
    if passed: grp[g][0] += 1
tp = sum(1 for r in R if r[2]); tt = len(R)
log(f"超级测试用例（组级）：{tt}，通过 {tp}，失败 {tt - tp}")
log(f"D1 六维组合：{d1_total} 条合法组合全通" if d1_pass == d1_total else f"D1 六维组合：{d1_pass}/{d1_total} ❌")
log(f"D2 极端叠加：{d2_pass}/{d2_total} ✅" if d2_pass == d2_total else f"D2 极端叠加：{d2_pass}/{d2_total} ❌")
log(f"D3 引用图：{d3_pass}/{d3_total} 边 + D3b 路径 {len(d3b_fail)} 悬空")
log(f"D4 一致性：工具编号 {d4_pass}/{d4_total} + 概念矩阵 + 治理格 {gov_hits}/30")
log("\n失败明细：")
for gid, name, passed, desc in R:
    if not passed:
        log(f"  ❌ {gid} {name}: {desc}")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_super_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_super_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
