"""组件拼装管线：outline.json + theme/ → 单文件自包含 HTML。
web 与 longpic 共用同一份 outline，差异全部由组件的 mode 变体承担：outline
给某个组件写 `"longpic": {...}` / `"web": {...}` 替身块，build 按目标 mode
优先取替身；组件本体不支持该 mode 且没给替身时直接报错，点名组件与两条
补救路径——绝不悄悄丢内容。这是本项目对 web/longpic 两种形态唯一的转换
机制，没有隐藏的"自动降级"或"自动转换"步骤。"""
import json
import pathlib
import re

from .components import base as C
from . import theme as T
from .skeleton import validate_outline, CTA_SWAP


class BuildError(Exception):
    pass


_MODES = ("web", "longpic")

_HEAD_WEB = """<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="use-iframe" content="true">
<meta name="html-box-height-mode" content="auto">
<meta name="format-detection" content="telephone=no">"""

_HEAD_LP = '<meta name="viewport" content="width=device-width, initial-scale=1">'

_RESET = """*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
img{max-width:100%;height:auto;display:block}
.wrap{margin:0 auto;padding:0 var(--pad);position:relative;z-index:2}
section{padding:var(--gap) 0;position:relative}
.prose{font-size:15px;line-height:2;color:var(--fg-2);max-width:38em;
  text-align:justify;text-justify:inter-ideograph;text-wrap:pretty}
.prose+.prose{margin-top:18px}
.prose b{font-weight:400;color:var(--fg)}
.rule{height:1px;background:var(--hair);border:0;margin:0}"""

_BODY_WEB = """body{background:var(--bg);color:var(--fg);font-family:var(--font-cn);
  font-weight:400;width:100%;max-width:100%;overflow-x:hidden;
  -webkit-font-smoothing:antialiased;font-size:15px;line-height:1.9;letter-spacing:.01em}
.wrap{max-width:var(--maxw)}"""

_BODY_LP = """body{background:var(--bg);color:var(--fg);font-family:var(--font-cn);
  font-weight:400;width:430px;overflow-x:hidden;-webkit-font-smoothing:antialiased;
  font-size:15px;line-height:1.95;letter-spacing:.01em}"""

_REVEAL_JS = """(function(){var e=document.querySelectorAll('.rv');
if(!('IntersectionObserver' in window)){e.forEach(function(x){x.classList.add('on')});return}
var o=new IntersectionObserver(function(en){en.forEach(function(x,i){if(x.isIntersecting){
var el=x.target;setTimeout(function(){el.classList.add('on')},Math.min(i*60,240));
o.unobserve(el)}})},{threshold:.08,rootMargin:'0px 0px -6% 0px'});
e.forEach(function(x){o.observe(x)})})();"""

# 与 theme.py 内部提取 :root 变量的正则同一套写法（简单的名值抓取，不是真正
# 的 CSS 解析器，够用即可）——不直接 import theme 的私有 _VAR/_collect，
# 那两个名字带下划线是明确的"不对外承诺稳定"信号，跨模块依赖别人的私有实现
# 细节，对方一次重构就可能悄悄改变本模块的行为。
_TOKEN_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}\n]+)")


def _swap_hint(name: str) -> str:
    """CTA_SWAP 只记录本项目里唯一一对"故意互为替身"的组件
    （cta-pills ↔ qr-closure）。命中时把已知替身名字直接塞进报错文案，
    "补一个替身"就从抽象建议变成一个可以直接抄的名字；quote-ticker 这类
    没有替身的组件不在表里，自然拿不到提示——报错退回纯通用文案，不能靠
    这张表硬凑一个不存在的候选出来。"""
    if name in CTA_SWAP:
        return CTA_SWAP[name]
    for k, v in CTA_SWAP.items():
        if v == name:
            return k
    return ""


def _pick(comp: dict, mode: str) -> dict:
    """按 mode 选组件本体或替身。

    outline 的静态形状（替身块必须是带合法 name 的对象、name 必须指向已注册
    组件）已经在 build() 调用 validate_outline 时校验过；这里只处理
    validate_outline 天生做不到的一件事——"运行期要 build 成哪个 mode，
    选中的这一个（本体或替身）是否真支持这个 mode"，因为 validate_outline
    不接收 mode 参数，同一份 outline 本来就要喂给 web 和 longpic 两次。

    两条路径都可能因为"选中的东西不支持目标 mode"而报错，不能只查一半：
    1）给了替身但替身自己也不支持目标 mode（替身选错了）；
    2）没给替身，组件本体也不支持目标 mode（且没有已知替身可提示）。
    两种情况都必须是命名清楚的 BuildError，不能任由 components.base 层
    更难懂的 ModeUnsupported 直接漏给调用方。"""
    alt = comp.get(mode)
    if alt is not None:
        alt_name = alt["name"]
        alt_spec = C.get(alt_name)
        if mode not in alt_spec.modes:
            raise BuildError(
                f"组件 `{comp.get('name')}` 给的 `{mode}` 替身是 `{alt_name}`，"
                f"但 `{alt_name}` 自己也不支持 {mode} 模式（声明为 {alt_spec.modes}）——"
                f"这个替身选错了，换一个真正支持 {mode} 的组件。")
        return alt
    name = comp["name"]
    spec = C.get(name)
    if mode not in spec.modes:
        hint = _swap_hint(name)
        hint_txt = f"已知替身是 `{hint}`。" if hint else ""
        raise BuildError(
            f"组件 `{name}` 不支持 {mode} 模式（声明为 {spec.modes}），"
            f"outline 里也没给这个组件条目提供 `{mode}` 替身。{hint_txt}"
            f"要么在这个组件条目里加一个 `{mode}` 替身块，"
            f"要么把它从 {mode} 版 outline 里显式删掉——不能悄悄丢内容。")
    return comp


def _parse_tokens(text: str) -> dict:
    """从 tokens.css 文本里挖出 `--name: value;` 对。不要求这份文件本身就把
    19 个 canonical 令牌写全——theme.emit_tokens_css 会用内置默认值补上
    结构性令牌（--pad/--gap/--maxw/--radius-*/--font-*）的缺口，这里只管
    尽量多抓，抓不到的交给它兜底。"""
    return {k: v.strip() for k, v in _TOKEN_RE.findall(text)}


def build(outline_path: str, theme_dir: str, mode: str = "web", out: str | None = None) -> str:
    if mode not in _MODES:
        raise BuildError(f"不支持的 mode `{mode}`，只支持 {_MODES}")

    op = pathlib.Path(outline_path)
    if not op.exists():
        raise BuildError(f"outline 文件不存在：{outline_path}")
    try:
        outline = json.loads(op.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise BuildError(f"{outline_path} 不是合法 JSON：{e}") from e
    if not isinstance(outline, dict):
        raise BuildError(f"outline 顶层必须是对象，收到 {type(outline).__name__}")

    # 先校验骨架，未过则在这里直接抛出——渲染阶段的任何 C.render 调用都还
    # 没发生，也不会有任何文件被写出去。
    genre = outline.get("genre", "")
    errs = validate_outline(outline, genre)
    if errs:
        raise BuildError("outline 校验未过：\n  - " + "\n  - ".join(errs))

    og = outline.get("og", {})
    if not isinstance(og, dict):
        raise BuildError(f"outline.og 必须是对象，收到 {type(og).__name__}")

    tp = pathlib.Path(theme_dir) / "tokens.css"
    if not tp.exists():
        raise BuildError(f"主题目录缺 tokens.css：{tp}")
    tokens = T.emit_tokens_css(_parse_tokens(tp.read_text(encoding="utf-8")))

    used, body = [], []
    for slot in outline["slots"]:
        chunks = []
        for comp in slot.get("components", []):
            picked = _pick(comp, mode)
            used.append(picked["name"])
            chunks.append(C.render(picked["name"], picked.get("data", {}), mode))
        if chunks:
            body.append(f'<section data-slot="{slot["key"]}"><div class="wrap">'
                        + "".join(chunks) + "</div></section>")

    og_tags = "".join(
        f'\n<meta property="og:{k}" content="{C.esc(v)}">' for k, v in og.items())
    head = _HEAD_WEB if mode == "web" else _HEAD_LP
    body_css = _BODY_WEB if mode == "web" else _BODY_LP
    script = f"\n<script>{_REVEAL_JS}</script>" if mode == "web" else ""

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
{head}
<title>{C.esc(outline.get("title", ""))}</title>{og_tags}
<style>
{tokens}
{_RESET}
{body_css}
{C.collect_css(used)}
</style>
</head>
<body>
{"".join(body)}
</body>{script}
</html>
"""
    if out:
        pathlib.Path(out).write_text(html, encoding="utf-8")
        return out
    return html
