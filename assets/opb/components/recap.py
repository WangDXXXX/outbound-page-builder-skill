"""战报组件集。quote-ticker 显式声明 modes=("web",)——
滚动轮播在静态图里不成立，长图直接删，不降级成静态列表（决策 D10）。"""
from .base import Component, register, esc, ComponentError

# ── stat-caption：数字必须自证意义（蓝军第6条）────────────
# caption 是 slots 的必填项（base.render 会在缺槽位时报 SlotMissing），
# 因此"数字必须带一句人话解释"不是靠调用方自觉，是结构性强制的。
#
# 2026-07-30 新增（Task 15 F3）：可选的 compare_to 槽位——蓝军第7条"对比>
# 绝对值"，但此前 facts.json 里的 compare_to 字段只是被 load_facts() 解析
# 进内存，从没有任何断言或组件真正读过它（同类问题：Task 14 已发现的
# verified 字段），outline.json 的作者填了也白填。这里选择让 stat-caption
# 直接渲染对比，而不是走"compare-bars 单独承担对比、verify.py 对未使用的
# compare_to 发 WARN"这条路——理由：stat-caption 是全项目用得最多的数字
# 展示组件（hero/buzz/who_came/works/survey 五个槽位都在用，compare-bars
# 只服务 vs_last 一个槽位），把"对比"下沉到 stat-caption 这一级，蓝军第7条
# 才能在每一处露出数字的地方都生效，不是只在专门的对比屏才生效；一条
# WARN 提示"数据在但没用上"仍然要靠人自觉去补，而组件直接渲染是结构性的。
# compare_to 保持可选（不进 slots 元组），不给它就是原来的行为，向后兼容
# ——sh-invite 案例里所有已有 stat-caption 用法一个字符都不用改。
def _stat(d, mode):
    cls = "stat stat-stack" if mode == "longpic" else "stat"
    cmp_html = ""
    cmp = d.get("compare_to")
    if cmp:
        cmp_html = f'<span class="cmp">较{esc(cmp["label"])} {esc(cmp["value"])}</span>'
    return (f'<div class="{cls}"><span class="v">{esc(d["value"])}</span>'
            f'<span class="l">{esc(d["label"])}</span>'
            f'<span class="c">{esc(d["caption"])}</span>{cmp_html}</div>')

register(Component(
    name="stat-caption", slots=("value", "label", "caption"),
    css=""".stat{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;
  align-items:baseline;padding:16px 0;border-bottom:1px solid var(--hair)}
.stat .v{font-family:var(--font-mono);font-size:34px;line-height:1;color:var(--accent)}
.stat .l{font-size:15px;color:var(--fg)}
.stat .c{grid-column:2;font-size:12.5px;line-height:1.8;color:var(--fg-3)}
.stat .cmp{grid-column:2;font-size:12px;line-height:1.6;color:var(--fg-2);margin-top:2px}
.stat-stack{display:block}
.stat-stack .v{display:block;margin-bottom:6px}
.stat-stack .l{display:block;margin-bottom:4px}
.stat-stack .c{display:block}
.stat-stack .cmp{display:block;margin-top:4px}""",
    render=_stat))

# ── compare-bars：对比对象必须点名（蓝军第5条）────────────
# legend.a/legend.b 永远渲染成文字（而不仅是给条形上色的隐藏语义），
# 宽度按 pairs 里 a/b 的原始数值相对当次最大值换算百分比——数值本身也保留
# 在条内，不是只有条长没有数字。web 图例在侧（.cb-body 横向 flex）、
# longpic 图例转到条形上方且横排（S3 单列节奏下的图例变体）。
def _compare_bars(d, mode):
    pairs = d["pairs"]
    vals = [float(p["a"]) for p in pairs] + [float(p["b"]) for p in pairs]
    mx = max(vals) if vals else 0
    rows = []
    for p in pairs:
        pa = round(float(p["a"]) / mx * 100, 1) if mx else 0
        pb = round(float(p["b"]) / mx * 100, 1) if mx else 0
        rows.append(
            f'<div class="cb-row"><span class="cb-label">{esc(p["label"])}</span>'
            f'<div class="cb-track"><div class="cb-bar cb-a" style="width:{esc(pa)}%">'
            f'<b>{esc(p["a"])}</b></div></div>'
            f'<div class="cb-track"><div class="cb-bar cb-b" style="width:{esc(pb)}%">'
            f'<b>{esc(p["b"])}</b></div></div></div>')
    cls = "cb cb-stack" if mode == "longpic" else "cb"
    legend = (f'<div class="cb-legend"><span class="lg lg-a">{esc(d["legend"]["a"])}</span>'
              f'<span class="lg lg-b">{esc(d["legend"]["b"])}</span></div>')
    return (f'<div class="{cls}"><h2>{esc(d["title"])}</h2>'
            f'<div class="cb-body">{legend}<div class="cb-rows">{"".join(rows)}</div></div></div>')

register(Component(
    name="compare-bars", slots=("title", "pairs", "legend"),
    css=""".cb{margin-top:30px}
.cb-body{display:flex;gap:26px;align-items:flex-start;margin-top:18px}
.cb-legend{flex:0 0 auto;display:grid;gap:10px}
.lg{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--fg-2)}
.lg::before{content:"";width:10px;height:10px;border-radius:50%;background:var(--accent)}
.lg-b::before{background:var(--accent-2)}
.cb-rows{flex:1 1 auto;display:grid;gap:16px;min-width:0}
.cb-row{display:grid;gap:6px}
.cb-label{font-size:13.5px;color:var(--fg)}
.cb-track{height:10px;border-radius:var(--radius-s);background:var(--bg-2);position:relative}
.cb-bar{height:100%;border-radius:var(--radius-s);display:flex;align-items:center;min-width:2px}
.cb-bar b{font-family:var(--font-mono);font-weight:400;font-size:11px;color:var(--fg);
  margin-left:8px;white-space:nowrap}
.cb-a{background:var(--accent)}
.cb-b{background:var(--accent-2)}
.cb-stack{display:block}
.cb-stack .cb-body{display:block}
.cb-stack .cb-legend{display:flex;flex-direction:row;gap:18px;margin-bottom:18px}""",
    render=_compare_bars))

# ── quote-card：长图去链接（S1）────────────────────────────
def _quote_card(d, mode):
    body = f'<p class="q">{esc(d["text"])}</p>'
    if mode == "web" and d.get("link"):
        who = (f'<a class="s" href="{esc(d["link"])}" target="_blank" rel="noopener">'
               f'{esc(d["speaker"])} ↗</a>')
    else:
        who = f'<span class="s">{esc(d["speaker"])}</span>'
    return f'<div class="qc">{body}{who}</div>'

register(Component(
    name="quote-card", slots=("text", "speaker", "link"),
    css=""".qc{background:var(--bg-2);border:1px solid var(--hair);
  border-radius:var(--radius-m);padding:20px 18px}
.qc .q{font-size:15px;line-height:1.9;color:var(--fg);margin-bottom:12px;
  text-align:justify;text-justify:inter-ideograph;text-wrap:pretty}
.qc .s{font-size:12.5px;color:var(--fg-3);text-decoration:none}
.qc a.s{color:var(--accent)}""",
    render=_quote_card))

# ── quote-ticker：web only（D10）───────────────────────────
# 内容整体复制一份接在自己后面（{items}{items}），配合 translateX(-50%) 做
# 无缝循环——这是纯 CSS 跑马灯的标准手法，长图没有"时间"这个维度可以滚动，
# 所以不声明 longpic，也不允许调用方把它当成静态列表来读（modes 只含 web，
# base.render 撞到 longpic 会直接抛 ModeUnsupported）。
def _ticker(d, mode):
    items = "".join(f'<span class="tk-i">{esc(t)}</span>' for t in d["lines"])
    return (f'<div class="tk"><div class="tk-track">{items}{items}</div></div>')

register(Component(
    name="quote-ticker", slots=("lines",), modes=("web",),
    css=""".tk{overflow:hidden;border-top:1px solid var(--hair);
  border-bottom:1px solid var(--hair);padding:14px 0}
.tk-track{display:flex;gap:28px;white-space:nowrap;
  animation:tk 42s linear infinite;will-change:transform}
.tk:hover .tk-track{animation-play-state:paused}
.tk-i{font-size:13.5px;color:var(--fg-2)}
@keyframes tk{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){
  .tk-track{animation:none;flex-wrap:wrap;white-space:normal}}""",
    render=_ticker))

# ── speaker-grid：每人两图（封面 + 花絮），longpic 单列 ───
def _speaker_grid(d, mode):
    cls = "sg sg-1col" if mode == "longpic" else "sg"
    cards = "".join(
        f'<div class="sg-card"><div class="sg-imgs">'
        f'<img class="sg-cover" src="{esc(p["cover"])}" alt="{esc(p["name"])}">'
        f'<img class="sg-shot" src="{esc(p["shot"])}" alt="{esc(p["name"])}"></div>'
        f'<p class="sg-name">{esc(p["name"])}</p><p class="sg-role">{esc(p["role"])}</p></div>'
        for p in d["people"])
    return f'<div class="{cls}">{cards}</div>'

register(Component(
    name="speaker-grid", slots=("people",),
    css=""".sg{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:26px}
.sg-card{display:grid;gap:10px}
.sg-imgs{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.sg-imgs img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:var(--radius-s);
  background:var(--bg-2);display:block}
.sg-name{font-size:14.5px;color:var(--fg);margin-top:2px}
.sg-role{font-size:12px;color:var(--fg-3)}
.sg-1col{grid-template-columns:1fr}
@media(min-width:600px){.sg{grid-template-columns:repeat(3,1fr)}}""",
    render=_speaker_grid))

# ── photo-mosaic：web 拼贴网格，longpic 单列大图 ──────────
def _photo_mosaic(d, mode):
    cls = "pm pm-1col" if mode == "longpic" else "pm"
    cells = "".join(
        f'<div class="pm-cell"><img src="{esc(p["src"])}" alt="{esc(p["alt"])}"></div>'
        for p in d["photos"])
    return f'<div class="{cls}">{cells}</div>'

register(Component(
    name="photo-mosaic", slots=("photos",),
    css=""".pm{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:26px}
.pm-cell{aspect-ratio:1;overflow:hidden;background:var(--bg-2);border-radius:var(--radius-s)}
.pm-cell img{width:100%;height:100%;object-fit:cover;display:block}
.pm-cell:nth-child(5n+1){grid-column:span 2;grid-row:span 2;aspect-ratio:auto}
.pm-1col{grid-template-columns:1fr}
.pm-1col .pm-cell{aspect-ratio:auto}
.pm-1col .pm-cell:nth-child(5n+1){grid-column:span 1;grid-row:span 1}
@media(min-width:600px){.pm{grid-template-columns:repeat(4,1fr)}}""",
    render=_photo_mosaic))

# ── donut：SVG 环形，显式 width（Task 6 层6 断言拦默认 300px）─
# 圆环用 r=15.91549430918954 让周长≈100，stroke-dasharray 直接吃百分比；
# 起点用 stroke-dashoffset=25 转到 12 点钟方向，后续每段的 offset 再减去
# 累计百分比，首尾相接。配色只从 4 个 canonical 令牌里按下标循环取
# （--accent/--accent-2/--fg-2/--fg-3），永远不落到具体色值——CANONICAL
# 里强调色只有两个，第三段起退到弱化的中性文字色而不是新发明一个颜色。
_DONUT_PALETTE = ("var(--accent)", "var(--accent-2)", "var(--fg-2)", "var(--fg-3)")

# 2026-07-30 修复（Task 15 F5）：圆环几何和图例文字对 pct 字段的语义理解
# 曾经不一致——圆环用 pct/sum(pct)*100 重新归一化（等于在说"pct 可以是
# 任意计数，我会帮你换算成百分比"），但图例直接把传入的原始 pct 值当百分比
# 显示（"{s['pct']}%"，不用归一化结果）。真实复现过这个不一致：传入满意度
# 原始计数 41/27/2/1（总 71），圆环会按 41/71≈57.7% 正确画，但图例逐字显示
# "41%"——41 不是 41%，是 71 里的 41，读者会看到一个和圆环视觉比例对不上、
# 且本身就是错误陈述的百分比数字，直接违反蓝军第6/8条。
#
# 两种修法：(a) 图例改用归一化后的 pct，接受任意计数输入、组件自己转换；
# (b) 拒绝不归一（不加起来≈100）的输入，逼调用方自己先算好百分比再传。
# 选 (b)：这个项目里凡是"调用方数据形状不对"的场景，一律是显式报错
# （SlotMissing/ModeUnsupported/BuildError/ConfigError/UnbanError/ThemeError
# 贯穿全项目），没有"静默接受、尽量猜"的先例；而且 (a) 会掩盖另一类真实
# 错误——如果调用方漏传了一个类别（比如满意度四档漏了"不太满意"），
# 三档自动归一成 100% 一样能画出一个"完整"的圆环，视觉上完全看不出少了
#一类，比"数字对不上"更难发现。拒绝并把两种可能原因都讲清楚，让调用方
# 自己检查是漏类别还是没换算，比静默兼容更符合这个项目一贯的判断。
def _donut(d, mode):
    segs = d["segments"]
    total = sum(float(s["pct"]) for s in segs) or 1
    if abs(total - 100) > 0.5:
        raise ComponentError(
            f"donut 各 segment 的 pct 加起来是 {total:.1f}，不是 100（容差 0.5）——"
            f"两种可能：① 传的是原始计数不是百分比，自己先换算成真实百分比再传"
            f"（历史踩坑：41/27/2/1 这组原始计数传进来，圆环会按 41/71≈57.7% 正确"
            f"绘制，但图例会直接显示「41%」，那不是41%，是71里的41，图例和圆环"
            f"会对不上）；② 传的确实是百分比但漏了一类，导致加起来不到100——两种"
            f"情况都不该被组件悄悄接受。")
    rings, legend, cum = [], [], 0.0
    for i, s in enumerate(segs):
        pct = float(s["pct"]) / total * 100
        color = _DONUT_PALETTE[i % len(_DONUT_PALETTE)]
        offset = 25 - cum
        rings.append(
            f'<circle class="dn-seg" style="stroke:{color}" cx="21" cy="21" '
            f'r="15.91549430918954" fill="none" stroke-width="3.6" '
            f'stroke-dasharray="{pct:.2f} {100 - pct:.2f}" '
            f'stroke-dashoffset="{offset:.2f}"></circle>')
        # 图例现在显示的是同一个归一化后的 pct（跟圆环同一个数），不是原始
        # 输入 s["pct"]——两处保证画的是同一个数字，不会再各算各的。
        pct_txt = f"{round(pct, 1):g}"
        legend.append(
            f'<li><i style="background:{color}"></i>'
            f'<span>{esc(s["label"])} · {esc(pct_txt)}%</span></li>')
        cum += pct
    return (f'<div class="dn"><h2>{esc(d["title"])}</h2>'
            f'<div class="dn-wrap">'
            f'<svg class="dn-svg" width="168" height="168" viewBox="0 0 42 42">'
            f'<circle class="dn-bg" cx="21" cy="21" r="15.91549430918954" '
            f'fill="none" stroke-width="3.6"></circle>'
            f'{"".join(rings)}</svg>'
            f'<ul class="dn-legend">{"".join(legend)}</ul></div></div>')

register(Component(
    name="donut", slots=("title", "segments"),
    css=""".dn{margin-top:30px}
.dn-wrap{display:flex;align-items:center;gap:28px;flex-wrap:wrap;margin-top:18px}
.dn-svg{flex:0 0 auto}
.dn-bg{stroke:var(--hair)}
.dn-legend{list-style:none;display:grid;gap:10px;flex:1 1 160px;min-width:140px}
.dn-legend li{display:flex;align-items:center;gap:10px;font-size:13.5px;color:var(--fg-2)}
.dn-legend i{display:inline-block;width:10px;height:10px;border-radius:50%;flex:0 0 auto}""",
    render=_donut))

# ── bar-h：横条，web/longpic 同一份骨架（同 keynote-block 的模式）──
def _bar_h(d, mode):
    rows = []
    for r in d["rows"]:
        rows.append(
            f'<div class="bh-row"><div class="bh-top">'
            f'<span class="bh-label">{esc(r["label"])}</span>'
            f'<span class="bh-pct">{esc(r["pct"])}%</span></div>'
            f'<div class="bh-track"><div class="bh-fill" style="width:{esc(r["pct"])}%">'
            f'</div></div><p class="bh-note">{esc(r["note"])}</p></div>')
    return f'<div class="bh"><h2>{esc(d["title"])}</h2><div class="bh-rows">{"".join(rows)}</div></div>'

register(Component(
    name="bar-h", slots=("title", "rows"),
    css=""".bh{margin-top:30px}
.bh-rows{display:grid;gap:18px;margin-top:18px}
.bh-top{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px}
.bh-label{font-size:14.5px;color:var(--fg)}
.bh-pct{font-family:var(--font-mono);font-size:13px;color:var(--accent)}
.bh-track{height:8px;border-radius:var(--radius-s);background:var(--bg-2);overflow:hidden}
.bh-fill{height:100%;border-radius:var(--radius-s);background:var(--accent)}
.bh-note{margin-top:6px;font-size:12.5px;line-height:1.7;color:var(--fg-3)}""",
    render=_bar_h))

# ── timeline-heartbeat：24 小时直方图 + marks；longpic 直方图保留、
# marks 从时间轴上的定位标记转成纯列表（不是整个组件退化，只退化 marks 这层）──
def _timeline(d, mode):
    buckets = d["buckets"]
    counts = [float(b["count"]) for b in buckets]
    mx = max(counts) if counts else 0
    cols = []
    for i, b in enumerate(buckets):
        h = round(float(b["count"]) / mx * 100, 1) if mx else 0
        hr = (f'<span class="hb-hr">{esc(b["hour"])}</span>' if i % 3 == 0
              else '<span class="hb-hr"></span>')
        cols.append(f'<div class="hb-col"><div class="hb-bar" style="height:{esc(h)}%"></div>{hr}</div>')
    marks = d["marks"]
    if mode == "longpic":
        items = "".join(f'<li><b>{esc(m["hour"])}:00</b> {esc(m["label"])}</li>' for m in marks)
        marks_html = f'<ul class="hb-marks hb-marks-list">{items}</ul>'
    else:
        items = "".join(
            f'<span class="hb-mark" style="left:{esc(round(float(m["hour"]) / 24 * 100, 1))}%">'
            f'<i></i><b>{esc(m["label"])}</b></span>' for m in marks)
        marks_html = f'<div class="hb-marks hb-marks-axis">{items}</div>'
    return (f'<div class="hb"><h2>{esc(d["title"])}</h2>'
            f'<div class="hb-chart">{"".join(cols)}</div>{marks_html}</div>')

register(Component(
    name="timeline-heartbeat", slots=("title", "buckets", "marks"),
    css=""".hb{margin-top:30px}
.hb-chart{display:flex;align-items:flex-end;gap:2px;height:110px;
  border-bottom:1px solid var(--hair);margin-top:18px;padding:0 2px}
.hb-col{flex:1 1 0;display:flex;flex-direction:column;align-items:center;
  justify-content:flex-end;height:100%;gap:6px}
.hb-bar{width:100%;min-height:2px;background:var(--accent);border-radius:2px 2px 0 0}
.hb-hr{font-family:var(--font-mono);font-size:9px;color:var(--fg-3);line-height:1}
.hb-marks-axis{position:relative;height:36px;margin-top:8px}
.hb-mark{position:absolute;top:0;transform:translateX(-50%);display:flex;
  flex-direction:column;align-items:center;gap:4px;white-space:nowrap}
.hb-mark i{width:1px;height:8px;background:var(--hair)}
.hb-mark b{font-weight:400;font-size:11px;color:var(--fg-2)}
.hb-marks-list{list-style:none;display:grid;gap:8px;margin-top:16px;
  border-top:1px solid var(--hair);padding-top:16px}
.hb-marks-list li{font-size:13px;color:var(--fg-2)}
.hb-marks-list b{color:var(--accent);font-family:var(--font-mono);
  margin-right:8px;font-weight:400}""",
    render=_timeline))

# ── award-list：列表，web/longpic 同一份骨架（auto 1fr 两列网格在
# 430px 长图画布下仍然放得下，不需要 S3 堆叠——不是每个长图变体都要堆叠，
# 这里内容比例天然允许 web/longpic 复用同一份布局）──
def _award_list(d, mode):
    rows = "".join(
        f'<div class="aw-row"><span class="aw-cat">{esc(a["category"])}</span>'
        f'<span class="aw-winner">{esc(a["winner"])}</span>'
        f'<span class="aw-note">{esc(a["note"])}</span></div>' for a in d["awards"])
    return f'<div class="aw">{rows}</div>'

register(Component(
    name="award-list", slots=("awards",),
    css=""".aw{display:grid;gap:1px;background:var(--hair);
  border:1px solid var(--hair);margin-top:26px}
.aw-row{background:var(--bg);padding:18px;display:grid;
  grid-template-columns:auto 1fr;gap:4px 16px;align-items:baseline}
.aw-cat{font-family:var(--font-mono);font-size:11px;letter-spacing:.08em;
  color:var(--accent);white-space:nowrap}
.aw-winner{grid-column:2;font-size:16px;color:var(--fg)}
.aw-note{grid-column:2;font-size:12.5px;line-height:1.8;color:var(--fg-3);margin-top:2px}
@media(min-width:600px){.aw-row{grid-template-columns:140px 1fr}}""",
    render=_award_list))
