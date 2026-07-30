"""通用组件：顶栏 / 区块头 / 氛围层 / 品牌页脚 / 滚动渐显容器。"""
from .base import Component, register, esc

# ── sysbar 顶栏信息条 ──────────────────────────────────────
def _sysbar(d, mode):
    return (f'<div class="sysbar"><span>{esc(d["text"])}</span></div>')

register(Component(
    name="sysbar", slots=("text",),
    css=""".sysbar{background:var(--bg-sunken);border-bottom:1px solid var(--hair);
  padding:10px 14px;text-align:center;position:relative;z-index:5}
.sysbar span{font-family:var(--font-mono);font-size:11px;line-height:1.3;
  letter-spacing:.04em;color:var(--fg-2)}""",
    render=_sysbar))

# ── section-head 区块头 ────────────────────────────────────
def _sechead(d, mode):
    eb = f'<span class="eyebrow">{esc(d["eyebrow"])}</span>' if d.get("eyebrow") else ""
    return f'<div class="sechead">{eb}<h2>{esc(d["title"])}</h2></div>'

register(Component(
    name="section-head", slots=("eyebrow", "title"),
    css=""".sechead{margin-bottom:30px}
.eyebrow{display:block;font-size:12px;letter-spacing:.28em;color:var(--fg-3);margin-bottom:14px}
h2{font-size:clamp(21px,5.4vw,34px);line-height:1.45;font-weight:400;
  letter-spacing:.01em;max-width:19em;color:var(--fg)}""",
    render=_sechead))

# ── atm-layer 氛围层 ───────────────────────────────────────
# 2026-07-29 修复：.atm 曾经自己就是那个用负值 inset 出血的元素
# （position:absolute;inset:-15%），没有任何容器为它兜底裁切。web 模式下
# 容器远比视口宽，肉眼看不出来；longpic 固定 430px 画布下，.atm 自己的盒子
# 会真实地把 wrap/section/body/html 全部撑宽（Task 12 render_longpic.audit()
# 首次做真实浏览器渲染时抓到：含 atm-layer 的 longpic 输出 docOverflow=176，
# 出图从 1290px 变成 1818px 宽——审计脚本没错，是这个组件在 longpic 模式下
# 从未被真实渲染验证过）。
#
# 修法：让 .atm 只做「裁切窗口」——自己贴着容器（inset:0），不出血，并且
# overflow:hidden；把原来的负值 inset 移到新增的 .atm-inner 上。.atm-inner
# 的 containing block 是 .atm 自己（因为 .atm 也是 position:absolute），
# 所以 .atm-inner 出血的部分会被 .atm 的 overflow:hidden 正常裁掉，不会再
# 越级冒到 wrap/section/body/html。视觉效果不变——模糊图层本来就该被视口边缘
# 裁切，只是裁切窗口从来没人真正设过。
def _atm(d, mode):
    n = 2 if mode == "longpic" else 3
    blobs = "".join(f'<div class="blob b{i+1}"></div>' for i in range(n))
    return (f'<div class="atm"><div class="atm-inner">{blobs}</div></div>'
            f'<div class="grain"></div>')

_GRAIN = ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' "
          "width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' "
          "baseFrequency='.85' numOctaves='3'/></filter>"
          "<rect width='140' height='140' filter='url(%23n)'/></svg>\")")

register(Component(
    name="atm-layer", slots=(),
    css=""".atm{position:absolute;inset:0;overflow:hidden;z-index:0;pointer-events:none}
.atm-inner{position:absolute;inset:-15%}
.blob{position:absolute;border-radius:50%;filter:blur(70px);opacity:.5;background:var(--bg-2)}
.b1{width:80vw;height:80vw;left:-24%;top:0}
.b2{width:66vw;height:66vw;right:-20%;top:26%}
.b3{width:44vw;height:44vw;left:34%;bottom:-6%;opacity:.35}
.grain{position:absolute;inset:0;z-index:1;opacity:.05;pointer-events:none;
  background-image:""" + _GRAIN + "}",
    render=_atm))

# ── footer-brand 品牌页脚（S7：长图版收小）────────────────
def _footer(d, mode):
    w = 74 if mode == "longpic" else 104
    return (f'<footer><div class="wrap foot">'
            f'<img class="logo-fs" style="width:{w}px" src="{esc(d["logo"])}" alt="{esc(d["alt"])}">'
            f'<p>{esc(d["lines"])}</p></div></footer>')

register(Component(
    name="footer-brand", slots=("logo", "alt", "lines"),
    css="""footer{border-top:1px solid var(--hair);padding:30px 0 46px}
.foot{display:grid;gap:18px;justify-items:center;text-align:center}
.logo-fs{opacity:.85}
.foot p{font-size:11.5px;letter-spacing:.1em;color:var(--fg-3);line-height:1.9}""",
    render=_footer))

# ── reveal-wrap 滚动渐显（长图必须全显）──────────────────
def _reveal(d, mode):
    cls = "" if mode == "longpic" else " rv"
    return f'<div class="{d.get("extra_class", "")}{cls}">{d["inner"]}</div>'

register(Component(
    name="reveal-wrap", slots=("inner",),
    css=""".rv{opacity:0;transform:translateY(12px);
  transition:opacity .7s cubic-bezier(.2,.7,.3,1),transform .7s cubic-bezier(.2,.7,.3,1)}
.rv.on{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){.rv{opacity:1;transform:none;transition:none}}""",
    render=_reveal))