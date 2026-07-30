"""层6 结构：必备元素 / 无未替换占位符 / SVG 显式 width。"""
import re

_PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
_SVG = re.compile(r"<svg\b([^>]*)>")

def check(ctx) -> list[str]:
    fails = []
    if _PLACEHOLDER.search(ctx.html):
        fails.append(f"存在未替换占位符: {_PLACEHOLDER.search(ctx.html).group(0)}")
    for must in ctx.cfg.must_contain:
        if must not in ctx.html:
            fails.append(f"必备元素缺失: {must}")
    for attrs in _SVG.findall(ctx.html):
        if "width=" not in attrs:
            fails.append("内联 svg 缺显式 width（默认 300px 会挤坏 topbar/footer）")
    return fails
