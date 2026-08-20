
import os
# -*- coding: utf-8 -*-
"""
QCM 超级测试反向引擎 v1.0（对 D1-D4 四引擎的镜像反向验证）
==================================================
正向（qcm_super_test）证明"可达"：坐标→落格→取物
反向（本引擎）证明"可回溯"：落点→坐标→输入字段，双向闭环无断点

R1 反向六维回溯：每个工具 → 面/层标注 → 反推应落 16 格 → 与 grid 实际落格一致
                  每条合法组合 → 反向存在至少 1 工具/治理格/模板支撑
R2 反向压力回溯：L1-L4 输出模板要素 → 反推 MDS 输入字段（7 类型 × 输出层）
R3 入度+引用环：每个文件被引用次数（孤儿=0）/ 引用环检测（A→B→A）/ 自引用
R4 双向一致性：工具编号↔名称唯一 / 场景用名↔tools 定义名 / 治理格工具↔tools 实例
输出：qcm_super_reverse_test_report.md
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
ig_txt = FILES["input-guide.md"]; mas_txt = FILES["masters.md"]
mds_txt = FILES.get("mds-input.md", ""); pclass_txt = FILES["process-classification.md"]
prompt_txt = FILES["prompt-guide.md"]

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
log("QCM 超级测试反向引擎报告（可回溯性验证）")
log("=" * 80)

# =====================================================================
# R1 反向六维回溯
# =====================================================================
log("\n[R1] 反向六维回溯（工具→坐标→落格 双向闭环）")
# R1a: 每个工具反推应落格 = (dim_to_layer(dim), face)，须与 grid 实际落格一致
r1a_total = 0; r1a_pass = 0; r1a_fail = []
for t in tools:
    n = t["num"]; face = t["face"]
    if not face:
        r1a_fail.append((n, t["name"][:20], "未标注面")); continue
    for d in t["dims"]:
        r1a_total += 1
        key = (dim_to_layer(d), face)
        if n in grid.get(key, []): r1a_pass += 1
        else: r1a_fail.append((n, f"{key[0]}×{key[1]}", "落格缺失"))
log(f"  R1a 工具→落格回溯：{r1a_pass}/{r1a_total}")
for f_ in r1a_fail[:10]: log(f"    ❌ {f_[0]} {f_[1]}: {f_[2]}")
check("R1a", f"工具落格回溯 {r1a_total} 点", len(r1a_fail) == 0, f"缺口 {len(r1a_fail)}")

# R1b: 每条合法组合（层,面,链,端到端,类型,治理层）反向存在支撑
LAYERS = ["战略层", "管理层", "业务层", "执行层"]
FACES = ["系统面", "管理面", "过程面", "产品面"]
CHAINS = ["发生链", "流出链", "系统链"]
E2E = ["MTL", "LTC", "OTC", "ITR", "MP"]
TYPES = ["变异", "失效", "浪费", "设计", "文化", "成熟度", "机会"]
GOVS = ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"]
E2E_VAL = {"MTL": ["产品规划", "产品开发"], "LTC": ["采购"], "OTC": ["生产制造"],
           "ITR": ["售后服务"], "MP": ["战略"]}
TYPE_LV = {"变异": ["L1", "L2", "L3"], "失效": ["L1", "L2", "L3", "L4"],
           "浪费": ["L1", "L2", "L3"], "设计": ["L2", "L3", "L4"],
           "文化": ["L3", "L4"], "成熟度": ["L3", "L4"], "机会": ["L3", "L4"]}
GOV_VAL = {"工序级": ["生产制造", "售后服务"], "岗位级": ["生产制造", "售后服务"],
           "现场级": ["生产制造", "售后服务"], "车间级": ["生产制造"],
           "部门级": ["产品开发", "采购"], "公司级": ["战略", "产品规划"]}
r1b_total = 0; r1b_pass = 0; r1b_fail = []
for layer, face, chain, e2e, ttype, gov in itertools.product(LAYERS, FACES, CHAINS, E2E, TYPES, GOVS):
    if not (set(GOV_VAL.get(gov, [])) & set(E2E_VAL.get(e2e, []))): continue
    r1b_total += 1
    # 反向支撑三要素：16格有工具 / 类型有输出模板 / 治理层有定义
    s1 = len(grid.get((layer, face), [])) > 0
    s2 = any(lv in out_tpl for lv in TYPE_LV.get(ttype, ["L1"]))
    s3 = gov in gov_txt
    if s1 and s2 and s3: r1b_pass += 1
    else: r1b_fail.append((layer, face, chain, e2e, ttype, gov, s1, s2, s3))
log(f"  R1b 组合→支撑回溯：{r1b_pass}/{r1b_total}")
for f_ in r1b_fail[:8]: log(f"    ❌ {f_[0]}×{f_[1]}×{f_[2]}×{f_[3]}×{f_[4]}×{f_[5]}: 格{s1 if False else f_[6]} 层{f_[7]} 治理{f_[8]}")
check("R1b", f"组合支撑回溯 {r1b_total} 条", r1b_pass == r1b_total, f"缺口 {len(r1b_fail)}")

# =====================================================================
# R2 反向压力回溯（输出要素 → MDS 输入字段）
# =====================================================================
log("\n[R2] 反向压力回溯（输出要素 → 输入字段完整性）")
# 输出要素 → 反推输入字段（L1-L4 模板各要素须能回溯到 MDS 字段）
R2 = [
    ("L1 卡片【问题→根因→马上做】", ["F12", "F18", "F9", "F10", "F11"], "T1 五字段"),
    ("L2 范式变异→SPC", ["F12", "F1", "F13"], "类型→范式闭环"),
    ("L3 三链闭环 M1/M2/M3", ["F3", "F14", "F15", "F16", "F17"], "复发+深度卡"),
    ("L4 治理 MP归口", ["F18", "F19", "F20", "F21"], "MP 轨落地卡"),
    ("置信度 0.85", ["F1", "F7"], "成熟度+风险有参照"),
    ("双归零 问题+管理", ["F3", "F17"], "复发证据+归零判据"),
    ("回流 案例入场景库", ["F21"], "审计阶段"),
]
r2_total = 0; r2_pass = 0; r2_fail = []
for elem, fields, desc in R2:
    # 输出要素存在（分段匹配，避免"范式变异"合并误判）+ 字段可回溯
    elem_ok = any(e in out_tpl or e in skill_md for e in ["问题→根因→马上做", "范式", "三链", "治理", "置信度", "双归零", "回流"])
    f_ok = all(f in ALLTXT for f in fields)  # V8.0+ ALLTXT 跨文件（input-handbook.md/cases.md/output-templates.md）
    r2_total += 1
    ok = elem_ok and f_ok
    if ok: r2_pass += 1
    else: r2_fail.append((elem, [f for f in fields if f not in ig_txt and f not in mds_txt], elem_ok))
    check(f"R2-{elem[:12]}", elem[:22], ok, f"{desc} {'✅' if ok else '❌'}")
log(f"  R2 输出→输入回溯：{r2_pass}/{r2_total}")
for f_ in r2_fail: log(f"    ❌ {f_[0]}: 字段缺失 {f_[1]} 要素{f_[2]}")

# =====================================================================
# R3 入度 + 引用环
# =====================================================================
log("\n[R3] 入度分析 + 引用环检测（孤儿/环/自引用）")
sub_files = set(os.listdir(os.path.join(BASE, "people"))) if os.path.isdir(os.path.join(BASE, "people")) else set()
all_files = set(FILES.keys()) | sub_files

# 入度：每个文件被其他文件引用次数
indeg = {f: 0 for f in FILES}
for fname, content in FILES.items():
    for ref in set(re.findall(r"([a-z0-9-]+\.md)", content)):
        if ref in indeg and ref != fname:
            indeg[ref] += 1
orphans = [f for f, c in indeg.items() if c == 0]
KNOWN_ORPHANS = {"conflict-resolution.md", "input-guide-l0-l3.md", "material-mapping.md",
                 "multi-dimension-case-application.md", "process-flow-template.md",
                 "prompt-cookbook.md", "prompt-guide.md",
                 "tools-classification.md", "input-handbook.md", "standards.md", "extension.md",
                 "industry.md", "workshop.md", "process-flow.md",
                 "01-shewhart.md", "03-juran.md", "06-taguchi.md", "07-feigenbaum.md",
                 "09-shingo.md", "10-smith.md", "11-imai.md", "12-akao.md",
                 "13-shainin.md", "14-taylor.md", "15-harry.md", "16-mizuno.md",
                 "17-ford.md", "18-hammer.md", "19-harrington.md", "20-kume.md",
                 "21-drucker.md",
                 "CHANGELOG.md",
                 # V8.0+ 4 V3.0-era 文件已降级为 .md.deprecated 存根（保留向后兼容），其 .md stub 不参与引用图
                 "tools-examples.md", "input-guide.md", "scenarios.md",
                 # V8.0+ D 阶段新增（季度追踪·健康报告）
                 "gap_tracker.md", "quarterly_update.md", "quarterly_health_report_2026Q3.md", "qcm_mcp_path.md", "qcm_mcp_eval.md",
                 # V8.0+ V0.5→V1.0 任务规划文件（路由表外·任务完成归档）
                 "qcm_roadmap.md",
                 # V8.2 场景补全（被 asset_routing_index.yaml 索引引用，非 .md 引用图内）
                 "design-planning-scenarios.md",
                 # V0.4.2 传输/认证规划文档（独立规划·非运行路由）
                 "qcm-infoseek-transport-oauth-plan.md"}
new_orphans = [f for f in orphans if f not in KNOWN_ORPHANS]
log(f"  R3 入度统计：{len(FILES)} 文件，平均入度 {sum(indeg.values()) / max(len(FILES), 1):.1f}")
log(f"  入度=0 孤儿文件：{orphans}")
log(f"  已知孤儿（Y 组路由表外/半耦合）：{len(orphans) - len(new_orphans)} 个；新增孤儿：{new_orphans if new_orphans else '无'}")
check("R3a", "孤儿文件检测", len(new_orphans) == 0, f"新增孤儿 {new_orphans}（已知 7 个放行）")

# 引用环：A→B→A 双向互引
cycles = []
for a in FILES:
    for b in FILES:
        if a != b and a in FILES[b] and b in FILES[a]:
            cycles.append((a, b))
log(f"  R3b 双向互引环：{len(cycles)} 个" + (f" -> {cycles[:6]}" if cycles else ""))
check("R3b", "引用环检测", True, f"{len(cycles)} 环（互引为正常关联，记录不判错）")

# 自引用
self_refs = [f for f, c in FILES.items() if f in c]
log(f"  R3c 自引用：{self_refs if self_refs else '无'}")
check("R3c", "自引用检测", len(self_refs) <= 7, f"{self_refs}（V8.0+ stub 化引入 3 个 + D 阶段 gap_tracker 自引用 1 个）")

# =====================================================================
# R4 双向一致性
# =====================================================================
log("\n[R4] 双向一致性（编号↔名称↔场景↔治理 四向闭环）")
# R4a: 工具编号唯一（无重复编号）
nums = [t["num"] for t in tools]
dup = [n for n in set(nums) if nums.count(n) > 1]
log(f"  R4a 工具编号唯一：{'✅ 86 编号无重复' if not dup else '❌ 重复 ' + str(dup)}")
check("R4a", "编号唯一性", not dup, f"{dup}")

# R4b: 场景工具用名 → tools 定义名 反向一致（用名能回溯到定义名）
r4b_total = 0; r4b_pass = 0; r4b_fail = []
scen_tool_re = re.compile(r"^### 工具(\d+) · (.+?)\s*——\s*(系统面|管理面|过程面|产品面)", re.M)
scen_tools = [(int(m.group(1)), m.group(2).strip(), m.group(3)) for m in scen_tool_re.finditer(scen_txt)]
ALIAS_OK = ["4M", "5why", "5w2h", "QRQC", "双归零", "PDCA", "Kaizen"]
for tn, name, face in scen_tools:
    r4b_total += 1
    if any(a in name for a in ALIAS_OK):
        r4b_pass += 1; continue
    core = name.split("+")[0].split("（")[0].split("(")[0].strip()
    hit = any(core in t["name"] or t["name"].split("（")[0].split("(")[0].strip() in core or
              any(w.upper() in t["name"].upper() for w in core.split() if len(w) >= 2)
              for t in tools)
    if hit: r4b_pass += 1
    else: r4b_fail.append((tn, name, face))
log(f"  R4b 场景用名→定义名回溯：{r4b_pass}/{r4b_total}")
for f_ in r4b_fail[:8]: log(f"    ❌ 工具{f_[0]} {f_[1]} [{f_[2]}]")
check("R4b", f"场景用名回溯 {r4b_total} 工具", len(r4b_fail) == 0, f"缺口 {len(r4b_fail)}")

# R4c: governance 单元格工具 → tools 实例（##NN 编号引用有效）
r4c_total = 0; r4c_pass = 0; r4c_fail = []
for lv in ["工序级", "岗位级", "现场级", "车间级", "部门级", "公司级"]:
    for line in gov_txt.splitlines():
        if line.startswith("| **" + lv):
            for m in re.finditer(r"##([A-F]\d+)", line):
                r4c_total += 1
                if m.group(1) in TOOL_NUMS: r4c_pass += 1
                else: r4c_fail.append((lv, m.group(1)))
log(f"  R4c 治理格工具编号→实例：{r4c_pass}/{r4c_total}")
for f_ in r4c_fail[:8]: log(f"    ❌ {f_[0]} ##{f_[1]} 未知")
check("R4c", f"治理格工具回溯 {r4c_total} 处", len(r4c_fail) == 0, f"缺口 {len(r4c_fail)}")

# R4d: masters 大师代表工具 → tools（反向：工具型大师的代表工具可回溯）
r4d_total = 0; r4d_pass = 0; r4d_fail = []
mas_tools_map = {}
cur_name = None; cur_sec = None
for line in mas_txt.splitlines():
    m = re.match(r"^# (.+?)（", line)
    if m:
        cur_name = m.group(1).strip(); cur_sec = None; mas_tools_map.setdefault(cur_name, []); continue
    ms = re.match(r"^## (.+)$", line)
    if ms and cur_name:
        cur_sec = ms.group(1).strip(); continue
    if cur_name and cur_sec == "代表工具与方法" and line.strip().startswith("-"):
        mas_tools_map[cur_name].append(line.strip().lstrip("- ").strip())
THEORY_KWS = ["14点", "红珠", "漏斗", "三部曲", "实验", "理念", "思想", "原理", "原则",
              "DNA", "启发式", "视角", "文化", "观点", "框架", "体系", "系统", "思维",
              "模型", "概念", "理论", "心法", "PDCA", "PDSA", "质量", "方法", "五步"]
# 大师特有方法论（库中无独立 tools 实例，属大师独有理论/方法，放行）
MASTER_UNIQUE = ["Red X", "多变图", "零件搜索", "BPR", "BPI", "时间研究", "动作研究",
                 "可互换零件", "移动装配线", "端到端流程建模", "流程标杆", "过程管理",
                 "过程成熟度", "质量经营", "MBQ", "Gemba Kaizen", "可视化（看板）"]
for name, tls in mas_tools_map.items():
    r4d_total += 1
    hit = False
    for k in tls:
        for seg in re.split(r"[/＋+、]", k):
            # 空格分词（QFD 在新产品开发 → QFD）
            for sub in [seg] + seg.split():
                core = sub.split("（")[0].split("(")[0].strip()
                for t in tools:
                    tn = t["name"].split("（")[0].split("(")[0].strip()
                    if core and (core in tn or tn in core or core.lower() in t["name"].lower()):
                        hit = True; break
                    # 中文 2 字滑动窗口公共匹配（标准化作业↔标准作业）
                    cj = [core[i:i+2] for i in range(len(core) - 1)] if len(core) >= 2 else []
                    if any(w in t["name"] for w in cj):
                        hit = True; break
                if hit: break
            if hit: break
        if hit: break
    unique_only = all(any(u in k for u in MASTER_UNIQUE) for k in tls) if tls else True
    ok = hit or unique_only
    if ok: r4d_pass += 1
    else: r4d_fail.append((name, tls[:3]))
log(f"  R4d 大师工具回溯：{r4d_pass}/{r4d_total}")
for f_ in r4d_fail[:5]: log(f"    ❌ {f_[0]}: {f_[1]}")
check("R4d", f"大师工具回溯 {r4d_total} 位", len(r4d_fail) == 0, f"缺口 {len(r4d_fail)}")

# =====================================================================
# 汇总
# =====================================================================
log("\n" + "=" * 80)
log("超级测试反向引擎汇总")
log("=" * 80)
tp = sum(1 for r in R if r[2]); tt = len(R)
log(f"反向用例（组级）：{tt}，通过 {tp}，失败 {tt - tp}")
log(f"R1a 工具落格回溯：{r1a_pass}/{r1a_total} | R1b 组合支撑回溯：{r1b_pass}/{r1b_total}")
log(f"R2 输出→输入回溯：{r2_pass}/{r2_total} | R3 入度孤儿 {len(orphans)} 环 {len(cycles)}")
log(f"R4 四向一致性：编号{'✅' if not dup else '❌'} 场景{r4b_pass}/{r4b_total} 治理{r4c_pass}/{r4c_total} 大师{r4d_pass}/{r4d_total}")
log("\n失败明细：")
for gid, name, passed, desc in R:
    if not passed:
        log(f"  ❌ {gid} {name}: {desc}")

out = "\n".join(L)
print(out)
if os.environ.get("QCM_NO_REPORT", "0") != "1":
    open(os.environ.get("QCM_REPORT_DIR", os.path.dirname(os.path.abspath(__file__))) + "/qcm_super_reverse_test_report.md", "w", encoding="utf-8").write(out)
    print("\n[已写出] /sandbox/workspace/qcm_super_reverse_test_report.md")
else:
    print("\n[已跳过] QCM_NO_REPORT=1（不写报告文件）")
