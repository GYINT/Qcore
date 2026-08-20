#!/usr/bin/env python3
"""M-2 索引生成器：从母模板段落 + 映射 → 生成 components/ 索引文件（防标注漂移）
用法：python3 qcm_component_index_gen.py
效果：内容组件文件 = 自动生成的引用声明 + 段落摘要（与母模板同步）
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "core" / "assembler.py"  # V8.3.2 T1.7：重组后 assembler 已迁入 core/（原 scripts/ 路径失效）
COMPONENTS = ROOT / "components"


def validate_component_contracts(m) -> list:
    """T5-2 组件契约校验：
    内容组件（CONTENT_COMPONENT_SOURCE）必须有 source 注释；
    动态组件（组件文件）必须有 fields frontmatter。
    返回违规清单（空=通过）。"""
    violations = []
    content_ids = set(m.CONTENT_COMPONENT_SOURCE.keys())
    if not COMPONENTS.exists():
        return violations
    for comp_file in sorted(COMPONENTS.glob("*.md")):
        comp_id = comp_file.stem
        text = comp_file.read_text(encoding="utf-8")
        if comp_id in content_ids:
            # 内容组件：M-2 自动生成，必须有 source 注释
            if "<!-- source:" not in text:
                violations.append(f"{comp_id}: 内容组件缺 source 注释（应 M-2 生成）")
        else:
            # 动态组件：必须有 fields frontmatter
            if not text.startswith("---") or "fields:" not in text.split("---", 2)[1]:
                violations.append(f"{comp_id}: 动态组件缺 fields frontmatter")
    return violations


def main():
    spec = importlib.util.spec_from_file_location("qcm_asm", ENGINE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # T5-2 契约校验（防"注册无文件/无契约"重现）
    violations = validate_component_contracts(m)
    if violations:
        for v in violations:
            print(f"  ❌ {v}")
        print(f"组件契约校验：{len(violations)} 项违规")
        return 1
    print(f"组件契约校验：✅ {len(list(COMPONENTS.glob('*.md')))} 组件全部合规")

    gen_count = 0
    for comp_id, (fname, anchor) in m.CONTENT_COMPONENT_SOURCE.items():
        path = ROOT / "outputs" / fname
        text = path.read_text(encoding="utf-8")
        idx = text.find(anchor)
        if idx < 0:
            print(f"  ⚠️ {comp_id}: 锚点 {anchor} 缺失")
            continue
        # 提取段落摘要（前 120 字）
        seg = text[idx:idx + 200].replace("\n", " ").strip()[:120]
        idx_file = COMPONENTS / f"{comp_id}.md"
        idx_file.write_text(
            f"<!-- 内容组件（M-2 自动生成 · 勿手改 · 真源在 outputs/{fname}） -->\n"
            f"<!-- source: outputs/{fname} {anchor} -->\n"
            f"<!-- 段落摘要：{seg}... -->\n",
            encoding="utf-8")
        gen_count += 1
    print(f"M-2 ✅ 生成 {gen_count} 个组件索引（与母模板同步）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
