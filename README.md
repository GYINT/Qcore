# QCM · Quality Crisis Management

> 质量问题解决指导 Skill。**v1.0.0 发布版** · 把「质量危机处置 + 体系治理评估 + 知识沉淀」封装成可复用的问题解决流水线。

[![Status](https://img.shields.io/badge/status-GA%20stable-brightgreen)](#)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](#)
[![Tests](https://img.shields.io/badge/tests-38%20suites%20PASS-success)](#)
[![License](https://img.shields.io/badge/license-Apache_2.0-green.svg)](LICENSE)

---

## 5 秒看懂

```bash
# MCP server（10 工具：问题解决核心 6 + Infoseek 协同 3 + 插件 1）
python scripts/mcp_server.py
```

```text
输入场景 → 协议匹配（action-orders 14 章）→ 场景路由（意图×领域）→ 4 形态输出
案例应用 / 决策卡片 / 评估报告 / 快速响应（防御性标注 + 缺口协同）
```

---

## 🎉 v1.0.0 发布亮点

| 能力 | 说明 |
|------|------|
| 🏗️ **4 层级架构** | 输出/协议/输入/底层严格分离 + 验证层 + 协同层（5 范式贯穿）|
| 📜 **14 章协议权威** | action-orders.md 单一权威：AO 卡 / 危机管理 / 触发矩阵 / 双归零 / 治理 4 层 |
| 🧭 **场景路由消费** | 意图 × 领域 → 形态 × 组件动态组合（置信度门控 + 无命中兜底）|
| 🧩 **组件池三机制** | 归一化注册（容量约束）+ 热度分级（new/active/stable）+ 约束映射（意图×D×复杂度）|
| 🛡️ **防御性输出** | `[unverified]` 标注 + 数据时效 + 边界声明 + 复述禁令 |
| 🤝 **Infoseek 协同** | 5 维缺口触发 + 混合策略 3 阶段 + L0→L3 降级链（可选依赖）|
| ✅ **回归全绿** | 38 套件 PASS + 验证器 96/96 + 守卫 9 检 0 问题 |

---

## 快速上手

### 1. 安装 / 升级

```bash
pip install -r requirements.txt          # 核心依赖（PyYAML）
pip install -r requirements-optional.txt # 可选能力（LLM / GraphQL / OTel 等）
# 完整依赖说明见 DEPENDENCIES.md
```

### 2. MCP 集成

项目提供 `.mcp.json`（双服务器配置，可直接被 Claude/Codex 等客户端加载）：

```json
{
  "mcpServers": {
    "qcm-search": {
      "command": "${QCM_ROOT}/scripts/mcp_server.py",
      "args": ["--transport", "stdio"],
      "env": {
        "QCM_ROOT": "${QCM_ROOT}",
        "QCM_AUTH_TOKEN": "${QCM_AUTH_TOKEN}"
      }
    },
    "infoseek-search": {
      "command": "${INFOSEEK_ROOT}/scripts/infoseek_mcp_server.py",
      "args": ["--transport", "stdio"],
      "env": {
        "INFOSEEK_ROOT": "${INFOSEEK_ROOT}"
      }
    }
  }
}
```

> 💡 Windows 环境请将 `command` 改为 `python3` + `args: ["脚本路径", "--transport", "stdio"]`。

**工具列表（10 个）**：
- 问题解决核心 6 个：`qcm_research` / `qcm_decide` / `qcm_solve_problem` / `qcm_score_source` / `qcm_audit` / `qcm_validate`
- Infoseek 协同 3 个：`qcm_attribution` / `qcm_attribution_phase` / `qcm_gap_detect`
- 插件扩展 1 个：`qcm_plugin_echo`（热加载样例）

### 3. 环境变量

| 变量 | 用途 | 默认 |
|------|------|------|
| `QCM_ROOT` | QCM 安装根（路径归一化）| 自身推导 |
| `INFOSEEK_ROOT` | Infoseek 安装根（跨 Skill 协同）| 探测列表 |
| `QCM_KEYWORDS` | 词库路径覆盖 | references/config/keyword.yaml |
| `QCM_AUTH_TOKEN` | MCP 认证 Token | — |

---

## 文档导航

| 文档 | 用途 |
|------|------|
| [SKILL.md](SKILL.md) | Skill 完整定义（概念/能力/触发词）|
| [version_history.md](version_history.md) | 对外版本历史 |
| [DEPENDENCIES.md](DEPENDENCIES.md) | 外部依赖清单 + 作用 + 降级路径 |
| [API_KEYS.md](API_KEYS.md) | 外部 API Key 清单 + 效益（不含真实密钥值）|
| [references/protocol/action-orders.md](references/protocol/action-orders.md) | 14 章协议权威 |
| [references/contract/](references/contract/) | 输入契约（mds-input + 指引）|
| [references/config/](references/config/) | 词库 + 路由 + 组件配置 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 版本变更日志 |
| [docs/INSTALL.md](docs/INSTALL.md) | 安装指南 |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 故障排查 |
| [tests/](tests/) | 测试套件（38 套，run_all.py 聚合）|

---

## 版本路线

| 版本 | 状态 | 备注 |
|------|------|------|
| v1.0.0 | 🟢 **当前发布版** | 版本归一化 · 4 层级架构 · 14 章协议 · 场景路由消费 · 组件池三机制 |
| 0.0.0-pre | ✅ 历史 | 发布前基线（原内部 V8.3.1 体系，历史归档于 docs/CHANGELOG.md）|
| 后续 | 🟡 待办 | 词库命中率淘汰机制 · suggest_research 接线 · 行业知识包扩展 |

---

## 测试矩阵

> ⚠️ 用例数为各套件自报（PASS 计数）。运行入口：`python tests/run_all.py`（脚本风格，勿用 pytest）。

| 套件组 | 套件数 | 类别 |
|--------|--------|------|
| engines（8）| qcm_all / cross / loop / combo / super / reverse / full / lowfreq | 引擎回归 |
| basic（20）| qcm_mcp v0.1→v0.9 系列 | MCP 协议 + 能力演进 |
| protocol（8）| v1.1→v1.6 系列（GraphQL / OTel / WS / 双通道）| 高级协议 |
| 主测试（2）| qcm_v82_test（27 用例）/ qcm_router_golden_test（15 用例）| 场景路由 + 歧义回归 |

> 环境差异说明：`v021`（需 LLM Key）与 `v071`（Infoseek ws 已移除）在缺失环境自动 SKIP，不误报 FAIL；`v131/v151` 需 OTel 依赖（`env_restore.sh --deps` 一键恢复）。

---

## 项目结构

```
QCM/
├── SKILL.md               # Skill 定义（yfm + 文档）
├── manifest.yaml          # 平台 manifest
├── skill_meta.json        # 元数据（版本/范式/维度/输出形态）
├── README.md              # 本文件
├── version_history.md     # 版本历史
├── DEPENDENCIES.md        # 依赖声明
├── API_KEYS.md            # Key 声明（不含真实值）
├── core/                  # 核心库（路由/组装/验证/组件扫描/缺口检测）
│   ├── router.py          # 场景路由（意图×领域 → 形态×组件）
│   ├── assembler.py       # 输出组装（母模板锚点提取）
│   ├── validator.py       # 4 形态验证器（96/96）
│   ├── component_scan.py  # 组件热度分级
│   └── gap_detector.py    # 5 维缺口检测
├── scripts/               # 适配层 + MCP server + 工具模块
│   ├── mcp_server.py      # MCP server 门面（10 工具）
│   ├── infoseek_bridge.py # QCM↔Infoseek 归因桥（L0→L3 降级）
│   ├── sync_manifest.py   # 双绑校验
│   ├── config_sync.py     # 守卫 9 检
│   └── ...
├── references/            # 协议 + 契约 + 词库 + 配置 + 索引
│   ├── protocol/action-orders.md  # 14 章协议权威
│   ├── contract/          # mds-input + 输入指引
│   ├── config/            # keyword/entities/components/constraint 等 10 配置
│   └── index/             # cases/knowledge-base/masters/tools 索引
├── components/            # 组件池（28 组件，索引自动生成勿手改）
├── outputs/               # 4 形态模板（唯一真源）
├── plugins/               # 插件扩展（热加载）
├── deploy/                # 部署资产（docker/k8s/monitoring/api）
├── docs/                  # CHANGELOG / INSTALL / TROUBLESHOOTING / eval
└── tests/                 # 38 套件（basic/protocol/engines + 主测试）
```

---

## 贡献与反馈

- **Bug 报告**：附 `qcm --version`（或 server 启动日志）+ 最小复现
- **协议问题**：附涉及的 action-orders 章节号
- **功能请求**：附用例 + 期望输出形态
- **测试失败**：运行 `python tests/run_all.py` 附完整输出

---

> v1.0.0 | 4 层级架构 · 14 章协议 · 4 形态 · 场景路由消费 · 组件池三机制 | 全行业质量危机管理 | Apache-2.0 License
