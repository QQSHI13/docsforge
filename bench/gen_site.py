#!/usr/bin/env python3
"""Generate a deterministic docs site for engine benchmarking.

Both engines get byte-identical Markdown and the same extension set, so a
comparison measures the engines rather than different inputs. The content mix
(headings, CJK prose, code fences, mermaid, tables, admonitions) mirrors a
real-world CTF Wiki style site, which is what exercises the hot paths
(superfences, search indexing, nav rendering).
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import yaml

CJK = (
    "文档构建性能测试 中文内容 密码学 逆向工程 堆溢出 格式化字符串 漏洞利用 "
    "内核 提权 反调试 沙箱逃逸 虚拟机 混淆 控制流平坦化 符号表 重定位"
)

EXTENSIONS = [
    "admonition",
    "md_in_html",
    {"codehilite": {"guess_lang": False}},
    "def_list",
    "footnotes",
    {"toc": {"permalink": True}},
    "pymdownx.arithmatex",
    "pymdownx.caret",
    "pymdownx.details",
    "pymdownx.emoji",
    "pymdownx.highlight",
    "pymdownx.inlinehilite",
    "pymdownx.magiclink",
    "pymdownx.mark",
    "pymdownx.superfences",
    "pymdownx.tabbed",
    "pymdownx.tasklist",
    "pymdownx.tilde",
]

# Deduplicate `toc` (the plain string and the configured mapping would clash).
def _extensions() -> list:
    seen: set[str] = set()
    out = []
    for entry in EXTENSIONS:
        name = next(iter(entry)) if isinstance(entry, dict) else entry
        if name in seen:
            continue
        seen.add(name)
        out.append(entry)
    return out


CODE_BLOCK = """```python
def collide(table: list[int], n: int) -> int:
    # 计算第 {k} 组哈希碰撞
    acc = 0
    for i in range(n):
        acc = (acc * 31 + table[i % len(table)]) & 0xFFFFFFFF
    return acc
```
"""

MERMAID = """```mermaid
graph TD
    A[输入] --> B{校验}
    B -->|通过| C[解析]
    B -->|失败| D[拒绝]
    C --> E[输出]
```
"""


def page_text(idx: int, rng: random.Random) -> str:
    """Build one deterministic Markdown page."""
    parts = [f"# 第 {idx} 篇测试文档", ""]
    parts += [
        '!!! note "说明"',
        "    本节内容用于基准测试，覆盖标题、代码块、表格、列表与公式。",
        "",
    ]
    for s in range(rng.randint(3, 5)):
        parts += [f"## 小节 {s + 1}", ""]
        words = [rng.choice(CJK.split()) for _ in range(rng.randint(30, 70))]
        parts += [" ".join(words), ""]
        if s % 2 == 0:
            parts += [CODE_BLOCK.format(k=rng.randint(1, 9))]
        if s % 3 == 2:
            parts += [MERMAID]
        if s % 3 == 1:
            parts += [
                "| 名称 | 值 | 备注 |",
                "| --- | --- | --- |",
                "| alpha | 1 | 示例 |",
                "| beta | 2 | 示例 |",
                "",
            ]
        parts += [
            "- 列表项 A",
            "- 列表项 B",
            "    - 嵌套项 C",
            "",
            "行内公式 $E = mc^2$ 与代码 `socket.socket()`。",
            "",
        ]
    return "\n".join(parts)


def write_configs(root: Path, concurrency: int) -> None:
    """Write equivalent docsforge.yml and mkdocs.yml into ``root``."""
    common = {
        "site_name": "DocsForge Bench",
        "site_url": "https://bench.example.com/",
        "docs_dir": "docs",
        "site_dir": "site",
        "theme": {"name": "material", "language": "zh"},
        "markdown_extensions": _extensions(),
    }

    docsforge_cfg = dict(common)
    docsforge_cfg["privacy"] = False
    docsforge_cfg["offline"] = {"mode": "none"}
    docsforge_cfg["concurrency"] = concurrency
    (root / "docsforge.yml").write_text(
        yaml.safe_dump(docsforge_cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    mkdocs_cfg = dict(common)
    mkdocs_cfg["plugins"] = ["search"]
    (root / "mkdocs.yml").write_text(
        yaml.safe_dump(mkdocs_cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def generate(root: Path, pages: int, seed: int = 1234, concurrency: int = 1) -> None:
    """Create ``root`` as a fresh site with ``pages`` Markdown files."""
    docs = root / "docs"
    if root.exists():
        shutil.rmtree(root)
    docs.mkdir(parents=True)
    for idx in range(pages):
        rng = random.Random(seed + idx)
        # Spread across 8 sections, mirroring a nested real site.
        section = f"sec{idx % 8:02d}"
        target = docs / section / f"page-{idx:04d}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_text(idx, rng), encoding="utf-8")
    (docs / "index.md").write_text("# 基准测试首页\n\n欢迎。\n", encoding="utf-8")
    write_configs(root, concurrency)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="bench-site", help="target directory")
    ap.add_argument("--pages", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--concurrency", type=int, default=1,
                    help="value written into docsforge.yml")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    generate(root, args.pages, args.seed, args.concurrency)
    print(f"generated {args.pages + 1} pages under {root}")
    print(f"  docsforge.yml concurrency = {args.concurrency}")


if __name__ == "__main__":
    main()
