"""邀请函组件集：信息条 / 议程 / 议题卡 / 致辞块 / 须知 / 钩子网格 /
CTA 按钮组 / 二维码闭环。长图变体全部按 S1/S3/S8 内建，调用方不需要记规则。"""
from .base import Component, register, esc

# ── info-meta ─────────────────────────────────────────────
def _info_meta(d, mode):
    cls = "meta-row" if mode == "longpic" else "meta-grid"
    cells = "".join(
        f'<div><span class="k">{esc(i["k"])}</span><span class="v">{esc(i["v"])}</span></div>'
        for i in d["items"])
    return f'<div class="meta {cls}">{cells}</div>'

register(Component(
    name="info-meta", slots=("items",),
    css=""".meta{margin-top:36px;border-top:1px solid var(--hair)}
.meta .k{font-size:11px;letter-spacing:.2em;color:var(--fg-3)}
.meta .v{font-size:15px;letter-spacing:.06em;color:var(--fg)}
.meta-grid{display:grid;grid-template-columns:1fr 1fr;border-left:1px solid var(--hair)}
.meta-grid div{padding:16px 12px;text-align:center;
  border-right:1px solid var(--hair);border-bottom:1px solid var(--hair)}
.meta-grid .k{display:block;margin-bottom:7px}
.meta-row div{display:flex;justify-content:space-between;align-items:baseline;
  padding:14px 2px;border-bottom:1px solid var(--hair)}
@media(min-width:600px){.meta-grid{grid-template-columns:repeat(4,1fr)}}""",
    render=_info_meta))

# ── agenda-rows ───────────────────────────────────────────
def _agenda(d, mode):
    stack = mode == "longpic"
    cls = "act act-stack" if stack else "act"
    rows = "".join(
        f'<div class="{cls}"><span class="t">{esc(r["time"])}</span>'
        f'<span class="n">{esc(r["name"])}</span>'
        f'<span class="d">{esc(r["desc"])}</span></div>' for r in d["rows"])
    return f'<div class="acts">{rows}</div>'

register(Component(
    name="agenda-rows", slots=("rows",),
    css=""".acts{border-top:1px solid var(--hair);margin-top:26px}
.act{border-bottom:1px solid var(--hair);padding:20px 0;
  display:grid;grid-template-columns:auto 1fr;gap:4px 16px;align-items:baseline}
.act .t{font-family:var(--font-mono);font-size:12px;letter-spacing:.06em;
  color:var(--fg-2);white-space:nowrap}
.act .n{font-size:17px;letter-spacing:.04em;grid-column:2;color:var(--fg)}
.act .d{grid-column:2;font-size:13.5px;line-height:1.85;color:var(--fg-2);margin-top:4px}
.act-stack{display:block;padding:22px 0}
.act-stack .t{display:block;margin-bottom:9px;color:var(--accent)}
.act-stack .n{display:block;font-size:20px;margin-bottom:9px}
.act-stack .d{display:block;margin-top:0;
  text-align:justify;text-justify:inter-ideograph;text-wrap:pretty}
@media(min-width:600px){.act{grid-template-columns:130px 1fr;gap:6px 24px}}""",
    render=_agenda))

# ── talk-card ─────────────────────────────────────────────
# brief 原示例把 d["title"]/d["hook"] 未经 esc() 直接拼进输出——与 Task 8
# footer-brand/section-head 是同一类缺陷（对外发布材料，标题/钩子文案完全可能
# 来自表格粘贴，混入 <>&" 不该被当成标签解析）。这里补上转义。
def _talk_card(d, mode):
    who_cls = "who who-stack" if mode == "longpic" else "who"
    people = "".join(
        f'<p class="p"><i>{esc(p["name"])}</i><span>{esc(p["role"])}</span></p>'
        for p in d["people"])
    return (f'<article class="card">'
            f'<i class="corner c1"></i><i class="corner c2"></i>'
            f'<i class="corner c3"></i><i class="corner c4"></i>'
            f'<span class="badge">{esc(d["index"])}</span>'
            f'<h3>{esc(d["title"])}</h3><p class="hook">{esc(d["hook"])}</p>'
            f'<div class="{who_cls}">{people}</div></article>')

register(Component(
    name="talk-card", slots=("index", "title", "hook", "people"),
    css=""".card{background:var(--bg-2);border-radius:var(--radius-m);
  padding:26px 20px;border:1px solid var(--hair);position:relative;overflow:hidden}
.card::after{content:"";position:absolute;left:20px;right:20px;top:0;height:1px;
  background:var(--accent);opacity:.5}
.corner{position:absolute;width:5px;height:5px;border:1px solid var(--fg-3)}
.c1{left:8px;top:8px}.c2{right:8px;top:8px}.c3{left:8px;bottom:8px}.c4{right:8px;bottom:8px}
.badge{display:inline-block;border:1px solid var(--fg-3);border-radius:var(--radius-l);
  padding:4px 12px;font-family:var(--font-mono);font-size:11px;letter-spacing:.1em;
  color:var(--fg);margin-bottom:16px}
.card h3{font-size:clamp(19px,4.8vw,27px);line-height:1.42;font-weight:400;
  margin-bottom:14px;max-width:17em;color:var(--fg)}
.card .hook{font-size:14.5px;line-height:1.95;color:var(--fg-2);max-width:32em;
  text-align:justify;text-justify:inter-ideograph;text-wrap:pretty}
.who{margin-top:20px;padding-top:16px;border-top:1px solid var(--hair);display:grid;gap:8px}
.who .p{font-size:13px;line-height:1.7;color:var(--fg-2)}
.who .p i{font-style:normal;color:var(--fg);margin-right:.6em}
.who-stack .p i{display:block;margin-bottom:3px;font-size:14.5px}
.who-stack .p span{display:block;font-size:12.5px}
@media(min-width:600px){.who{grid-template-columns:1fr 1fr;gap:10px 24px}}""",
    render=_talk_card))

# ── keynote-block ─────────────────────────────────────────
# web/longpic 结构完全相同（描边块 + 正文段落），唯一差异是 longpic 的内边距
# 收小——这是表里唯一一个「两种模式共用同一份骨架，只调一个数值」的组件。
def _keynote(d, mode):
    cls = "keynote keynote-tight" if mode == "longpic" else "keynote"
    paras = "".join(f'<p class="prose">{esc(p)}</p>' for p in d["paras"])
    return f'<div class="{cls}">{paras}</div>'

register(Component(
    name="keynote-block", slots=("paras",),
    css=""".keynote{margin-top:30px;padding:22px 20px;
  border:1px solid var(--hair);background:var(--bg-sunken)}
.keynote .prose{max-width:none;font-size:14.5px;line-height:1.95;color:var(--fg-2);
  text-align:justify;text-justify:inter-ideograph;text-wrap:pretty}
.keynote .prose+.prose{margin-top:14px}
.keynote-tight{padding:16px 14px}
@media(min-width:600px){.keynote{padding:30px 28px}}""",
    render=_keynote))

# ── terms-list ────────────────────────────────────────────
# web：.ri 两列 grid，编号在左、正文在右。
# longpic（S3 单列条家族的编号变体）：表格只写「.i display:block」，但光改 .i
# 不会让编号真的跑到正文上面——.ri 本身仍是两列 grid，.i 只是在自己的格子里变
# 块级，视觉上还是并排。要让编号真正独占一行、正文另起一行，容器也必须跟着从
# grid 退回 block。这里在 brief 的基础上把 .ri-stack 本身也标为 block，
# 使其与 agenda-rows 的 act-stack、talk-card 的 who-stack 是同一种「S3 单列
# 堆叠」处理，而不是半吊子实现。
def _terms(d, mode):
    stack = mode == "longpic"
    cls = "ri ri-stack" if stack else "ri"
    rows = "".join(
        f'<div class="{cls}"><span class="i">{esc(it["index"])}</span>'
        f'<span class="t">{esc(it["text"])}</span></div>' for it in d["items"])
    return f'<div class="rules">{rows}</div>'

register(Component(
    name="terms-list", slots=("items",),
    css=""".rules{display:grid;gap:1px;background:var(--hair);
  border:1px solid var(--hair);margin-top:26px}
.ri{background:var(--bg);padding:20px 18px;display:grid;
  grid-template-columns:auto 1fr;gap:14px}
.ri .i{font-family:var(--font-mono);font-size:11px;letter-spacing:.1em;
  color:var(--accent);padding-top:4px}
.ri .t{font-size:14.5px;line-height:1.9;color:var(--fg-2)}
.ri-stack{display:block}
.ri-stack .i{display:block;margin-bottom:8px}
.ri-stack .t{display:block}""",
    render=_terms))

# ── hook-grid ─────────────────────────────────────────────
# 亮色反转段：唯一会把文字画在 --invert-bg 上的组件。CANONICAL 里反转侧只有
# --invert-bg / --invert-fg 两个令牌，没有对应的「反转侧弱化文字」令牌，所以
# en/note 这类需要弱化的说明文字改用契约测试明确放行的中性 rgba(0,0,0,α)
# 遮罩（黑到白背景上按透明度出灰，与暗色区用 rgba(255,255,255,α) 是同一手法
# 的镜像），不能借用 --fg-2/--fg-3——那两个令牌是为暗底调的浅色，糊在亮底上
# 基本不可读。
def _hook_grid(d, mode):
    cls = "pours pours-1col" if mode == "longpic" else "pours"
    cells = "".join(
        f'<div class="pour{" hl" if it.get("hl") else ""}">'
        f'<div class="en">{esc(it["en"])}</div>'
        f'<div class="q">{esc(it["q"])}</div>'
        f'<div class="n">{esc(it["note"])}</div></div>'
        for it in d["items"])
    return (f'<section class="bone"><div class="wrap">'
            f'<h2>{esc(d["title"])}</h2>'
            f'<div class="{cls}">{cells}</div></div></section>')

register(Component(
    name="hook-grid", slots=("title", "items"),
    css=""".bone{background:var(--invert-bg);padding:var(--gap) 0}
.bone h2{font-size:clamp(21px,5.4vw,30px);line-height:1.45;font-weight:400;
  max-width:19em;margin-bottom:22px;color:var(--invert-fg)}
.pours{display:grid;grid-template-columns:1fr 1fr;gap:1px;
  background:rgba(0,0,0,.12);border:1px solid rgba(0,0,0,.12)}
.pour{background:var(--invert-bg);padding:20px 18px}
.pour .en{font-family:var(--font-mono);font-size:11px;letter-spacing:.14em;
  color:rgba(0,0,0,.45);margin-bottom:8px}
.pour .q{font-size:17px;line-height:1.5;letter-spacing:.03em;
  color:var(--invert-fg);margin-bottom:8px}
.pour .n{font-size:13.5px;line-height:1.8;color:rgba(0,0,0,.6)}
.pour.hl .q{color:var(--accent)}
.pours-1col{grid-template-columns:1fr}
@media(min-width:1000px){.pours{grid-template-columns:repeat(4,1fr)}}""",
    render=_hook_grid))

# ── cta-pills：S1 交互归零 —— 显式声明只支持 web ──────────
# brief 原示例把 d["title"]/d["text"] 未经 esc() 直接拼进输出，同一类缺陷。
def _cta(d, mode):
    btns = "".join(
        f'<a class="pill {esc(b.get("variant", "primary"))}" href="{esc(b["href"])}" '
        f'target="_blank" rel="noopener">{esc(b["label"])}</a>' for b in d["buttons"])
    return (f'<div class="cta"><h2>{esc(d["title"])}</h2>'
            f'<p class="prose">{esc(d["text"])}</p><div class="btns">{btns}</div></div>')

register(Component(
    name="cta-pills", slots=("title", "text", "buttons"), modes=("web",),
    css=""".cta{text-align:center;padding:60px 0 var(--gap)}
.cta h2{max-width:100%;margin:0 auto 20px}
.cta .prose{margin:0 auto 30px;text-align:center;max-width:26em;color:var(--fg-2)}
.btns{display:grid;gap:12px;max-width:330px;margin:0 auto}
.pill{display:block;background:transparent;border:1px solid var(--fg);
  border-radius:var(--radius-l);padding:15px 26px;color:var(--fg);text-decoration:none;
  font-size:15px;letter-spacing:.1em;min-height:48px;line-height:1.4;
  transition:background .22s,color .22s}
.pill:active,.pill:hover{background:var(--fg);color:var(--bg)}
.pill.secondary{border-color:var(--fg-3);color:var(--fg-2)}
@media(min-width:600px){.btns{display:flex;justify-content:center;max-width:none}
.pill{display:inline-block}}""",
    render=_cta))

# ── qr-closure：S8 尾部自带闭环 —— 只支持 longpic ─────────
# brief 原示例把 d["lines"] 未经 esc() 直接拼进输出，同一类缺陷。
def _qr(d, mode):
    return (f'<div class="qrc"><img class="qr" src="{esc(d["qr"])}" alt="{esc(d["alt"])}">'
            f'<p class="qrl">{esc(d["lines"])}</p></div>')

register(Component(
    name="qr-closure", slots=("qr", "alt", "lines"), modes=("longpic",),
    css=""".qrc{text-align:center;padding:54px 0 40px}
.qr{width:168px;margin:0 auto 18px;border-radius:var(--radius-s);background:var(--fg)}
.qrl{font-size:14px;line-height:1.95;color:var(--fg-2);letter-spacing:.05em}""",
    render=_qr))
