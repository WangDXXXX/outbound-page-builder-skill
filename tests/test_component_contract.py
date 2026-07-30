"""全组件契约：注册表里每一个组件都必须满足这些约束。
新增组件通常无需改本文件、自动纳入检查——但如果新组件引入了新的槽位形状
（列表套字典、字典）或新的单模式声明（如纯 longpic），仍需相应扩充下面的
SAMPLE / EXPECTED_* / 模式不变式，否则契约测试会误报或干脆崩溃
（Task 9 引入 talk-card 的 people、cta-pills 的 buttons、qr-closure 的
modes=("longpic",) 时都踩过一次；Task 10 又添了两种新情况：compare-bars 的
legend 是第一个「字典」形状槽位、bar-h 与 award-list 的 modes=("web","longpic")
默认元组不需要新豁免（quote-ticker 的 ("web",) 单模式同理，cta-pills 早已把这条
路铺好），以及 speaker-grid 把已有的 people 键从 {name,role} 扩成
{name,role,cover,shot}——同一键名、两种形状，只能取并集，见各处内联注释）。

Task 10 复核轮又补了三类检查，别再丢：
1. 硬编码颜色检查曾经只扫过静态 c.css 字段——render() 里手写的内联
   style（donut 按数据下标给分段配色）完全绕得过去，css 为空也能
   蒙混过关。现在 test_no_hardcoded_colors_in_rendered_output 额外把每个
   组件的渲染产物也扫一遍（剥掉 data: URI 负载，见 _strip_data_uris 的
   注释），新增组件如果要在 render() 里给内联颜色，必须用 var(--x)。
2. 同一个盲区对 canonical 令牌白名单检查同样成立——test_all_css_vars_are_canonical
   也只扫 c.css。test_all_css_vars_in_rendered_output_are_canonical 补上
   render() 输出这一侧，复用同一套 _sample_for/_strip_data_uris。两条
   "只扫 css、不扫渲染输出"的盲区是同一类缺陷的两个实例，新增检查时如果
   只顾静态 css 字段，先问一句"render() 里会不会手写同类内容"。
3. SAMPLE 是扁平字典，两个组件共用同一槽位名但形状不同时（qr-closure 的
   lines 是标量字符串，quote-ticker 的 lines 是字符串列表）没法只改一份
   通用样例——字符串本身可迭代，塞给 quote-ticker 不崩但会被拆成单字符
   「假引言」，覆盖是凑巧不是形状对。真冲突就用 PER_COMPONENT_SAMPLE 按
   (组件名, 槽位名) 精确覆盖，不要为了迁就一个组件改另一个组件的通用样例。
   本文件里目前只有 quote-ticker/lines 这一例，新增组件复用已有键名时先
   检查形状是否兼容，不兼容就照此模式加一条，不要静默复用不兼容的样例。"""
import re, sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.components import base as B
import opb.components as _load  # 触发全量注册
from opb.theme import CANONICAL

# 允许出现的非令牌色值：全透明、currentColor、继承、以及 rgba(255,255,255,x)/rgba(0,0,0,x)
# 这两个 rgba 是发丝线与遮罩的通用写法，四份实例都在用，不算硬编码品牌色。
_HARDCODED = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?<!--)\brgb\(")
_VAR = re.compile(r"var\((--[\w-]+)")

# data: URI 负载（多为 base64 图片，也可能是明文 SVG）会作为普通字符串出现在
# render() 输出里（qr-closure 的 <img src=...>、speaker-grid 的 cover/shot），
# 图片数据本身不该被当成"颜色硬编码"——标准 base64 字母表不含 "#"/"(" 所以
# 目前的样例数据不会误触发，但明文 data URI（如未来换成手写 SVG data URI）
# 完全可能带字面 "#RRGGBB"，扫描渲染输出前先把整段 data: 负载剥掉，
# 而不是依赖样例数据"恰好"不出现色值。
# 本项目 render() 输出里的 data URI 只出现在双引号 HTML 属性值里
# （src="data:..."），真正的负载边界是那个收尾双引号，不是空白——明文 SVG
# data URI 内部完全可能有空格（"<svg fill=#ff0000>" 这种属性间的空格），
# 早前版本把 \s 也当成终止符，会在第一个空格处提前截断、把空格之后的内容
# （包括真正的色值）漏在外面，等于没剥干净。改成只在遇到引号时停止。
_DATA_URI = re.compile(r"data:[^\"']+")

def _strip_data_uris(text: str) -> str:
    return _DATA_URI.sub("", text)

SAMPLE = {
    "title": "标题", "text": "正文", "eyebrow": "眉题", "items": [],
    "value": "628", "caption": "注脚", "label": "标签", "src": "data:image/png;base64,AA",
    "alt": "图", "href": "https://example.com", "name": "名字", "role": "头衔",
    "time": "13:00", "desc": "描述", "speaker": "说话人", "index": "01",
    "rows": [], "cards": [], "photos": [], "left": {}, "right": {},
    # Task 9 新增槽位形状：以下三个是「列表套字典」，不能落到下面的通用
    # "占位" 字符串兜底——字符串按字符迭代，元素会是单字符串而不是 dict，
    # talk-card/cta-pills 一读 p["name"]/b["href"] 就是 TypeError，
    # 不是渲染出奇怪内容那种温和失败。空 items/rows 之所以安全，是因为空列表
    # 迭代零次，从不会真正碰到 [0]["k"] 这种取值——这三个必须给出非空样例，
    # 否则 test_renders_in_every_declared_mode 只是空转、从未真正执行过循环体。
    # people 在 Task 10 被 speaker-grid 复用、形状从 {name,role} 扩到
    # {name,role,cover,shot}——同一个键名两种形状共用一份样例，取并集
    # （多出来的字段 talk-card 不读，无害；缺了 cover/shot，speaker-grid
    # 读 p["cover"] 直接 KeyError）。
    "people": [{"name": "名字", "role": "头衔",
                "cover": "data:image/png;base64,AA", "shot": "data:image/png;base64,AA"}],
    "buttons": [{"label": "标签", "href": "https://example.com", "variant": "primary"}],
    "paras": ["段落"],
    # 标量槽位，即便沿用旧的 "占位" 兜底也不会崩——补上是为了样例更真实。
    "qr": "data:image/png;base64,AA", "lines": "时间地点",
    # Task 10 新增槽位形状：同样是「列表套字典」/「字典」，同一条 TypeError/
    # KeyError 逻辑——pairs/awards/segments/buckets/marks 是列表套字典，
    # legend 是字典，通用 "占位" 兜底对这五个都会在 compare-bars/donut/
    # bar-h/timeline-heartbeat/award-list 的 render 里炸掉（legend["a"] 对
    # 字符串 "占位" 取键是 TypeError，不是 KeyError）。
    "pairs": [{"label": "标签", "a": 1, "b": 2}],
    "legend": {"a": "选项A", "b": "选项B"},
    "awards": [{"category": "标签", "winner": "获奖者", "note": "备注"}],
    "segments": [{"label": "标签A", "pct": 40}, {"label": "标签B", "pct": 60}],
    "buckets": [{"hour": 9, "count": 12}, {"hour": 20, "count": 88}],
    "marks": [{"hour": 19, "label": "标记"}],
}

# SAMPLE 是按槽位名的扁平字典，同一个键名被两个组件复用、但两边形状不同时
# （qr-closure 的 lines 是标量字符串，quote-ticker 的 lines 是字符串列表——
# quote-ticker 自己的 slots=("lines",) 意图很明确，brief 给定测试
# `B.render("quote-ticker", {"lines": ["a"]}, "longpic")` 直接锁死了列表形状），
# 通用 SAMPLE 只能二选一。Python 字符串本身可迭代，"时间地点" 塞进
# quote-ticker 不会崩，但会被按单字拆成 4 个"假引言"（"时"/"间"/"地"/"点"），
# 渲染"成功"只是因为字符串恰好可以迭代，不是因为形状对——契约测试因此从未
# 真正用一条完整的引言字符串走过 quote-ticker 的循环体。qr-closure 那边的
# 标量字符串是它本来的真实形状，不能因为 quote-ticker 的需要而改成列表
# （改了 qr-closure 在 contract 测试里会把 Python list 的 repr 显示成文案）。
# PER_COMPONENT_SAMPLE 用 (组件名, 槽位名) 精确覆盖，只在真的冲突时用，
# 优先级高于通用 SAMPLE，两边各自拿到真实形状。
PER_COMPONENT_SAMPLE = {
    ("quote-ticker", "lines"): ["示例引言一", "示例引言二"],
}

def _sample_for(c):
    return {s: PER_COMPONENT_SAMPLE.get((c.name, s), SAMPLE.get(s, "占位")) for s in c.slots}

EXPECTED_COMMON = {"sysbar", "section-head", "atm-layer", "footer-brand", "reveal-wrap"}
EXPECTED_INVITE = {
    "info-meta", "agenda-rows", "talk-card", "keynote-block",
    "terms-list", "hook-grid", "cta-pills", "qr-closure",
}
EXPECTED_RECAP = {
    "stat-caption", "compare-bars", "quote-card", "quote-ticker",
    "speaker-grid", "photo-mosaic", "donut", "bar-h",
    "timeline-heartbeat", "award-list",
}

class TestComponentContract(unittest.TestCase):
    def test_expected_components_registered(self):
        """断言通用组件必须存在——否则注册表可能被其他测试污染"""
        actual = set(B.all_components())
        missing = EXPECTED_COMMON - actual
        self.assertEqual(missing, set(), f"注册表缺少通用组件 {missing}——注册表可能被其他测试污染")

    def test_expected_invite_components_registered(self):
        """Task 9 八件邀请函组件必须存在——同一防污染断言，独立于 EXPECTED_COMMON
        单独列出，方便一眼看出污染发生在哪个组件族。"""
        actual = set(B.all_components())
        missing = EXPECTED_INVITE - actual
        self.assertEqual(missing, set(), f"注册表缺少邀请函组件 {missing}——注册表可能被其他测试污染")

    def test_expected_recap_components_registered(self):
        """Task 10 十件战报组件必须存在——同一防污染断言，独立于 EXPECTED_COMMON/
        EXPECTED_INVITE 单独列出。这条断言本身也要能失败：把某个 register()
        调用注释掉，或让某个测试文件在本文件之前把注册表清空，本测试会先报出
        缺了哪个组件，而不是让下面几条通用契约测试报出更难定位的 KeyError/
        TypeError。"""
        actual = set(B.all_components())
        missing = EXPECTED_RECAP - actual
        self.assertEqual(missing, set(), f"注册表缺少战报组件 {missing}——注册表可能被其他测试污染")

    def test_no_hardcoded_colors_in_css(self):
        for name, c in B.all_components().items():
            hits = _HARDCODED.findall(c.css)
            self.assertEqual(hits, [], f"组件 {name} 的 CSS 含硬编码颜色 {hits}")

    def test_no_hardcoded_colors_in_rendered_output(self):
        """静态 c.css 干净不代表输出干净——render() 里手写的内联 style（donut/
        compare-bars 按数据下标给分段配色）完全绕得过上面那条只扫 css 字段的
        检查。这里把每个组件在它声明的每个模式下按 _sample_for 真实渲染一次，
        剥掉 data: URI 负载后用同一条 _HARDCODED 正则扫渲染产物。
        本条断言曾经真的失手过（一个 css 为空、render() 里塞
        style="color:#af50ff" 的临时组件能让全量套件保持全绿）——teeth 见
        test_hardcoded_color_scan_has_teeth 与 task-10-report.md 的变异记录。"""
        for name, c in B.all_components().items():
            for mode in c.modes:
                out = B.render(name, _sample_for(c), mode)
                hits = _HARDCODED.findall(_strip_data_uris(out))
                self.assertEqual(hits, [], f"组件 {name}/{mode} 的渲染输出含硬编码颜色 {hits}")

    def test_hardcoded_color_scan_has_teeth(self):
        """不依赖真实组件、直接对合成字符串验证「剥 data URI + 正则扫描」组合
        逻辑本身有牙，覆盖三件事：①裸十六进制色值必须被抓到；②var() 令牌引用
        不能被误伤；③data: URI 负载里即使带十六进制片段也必须被正确剥离而不
        误伤，但 data URI 之外的真实硬编码色值不能被剥离逻辑连带放过——用
        同一段文本先验证"不剥离就会命中"，再验证"剥离后只剥掉 URI 内的那处、
        URI 外的那处仍然命中"，证明剥离不是靠正则本来就打不到 data URI。"""
        self.assertTrue(_HARDCODED.findall('<i style="color:#af50ff"></i>'),
                         "正则本身必须能抓到裸十六进制色值")
        self.assertFalse(_HARDCODED.findall('<i style="color:var(--accent)"></i>'),
                          "var() 令牌引用不能被误判为硬编码颜色")
        raw = ('<img src="data:image/svg+xml,<svg fill=#ff0000></svg>"> '
               '<i style="color:#abc123"></i>')
        self.assertTrue(_HARDCODED.findall(raw),
                         "样例必须先在不剥离时命中，才能证明剥离步骤真的做了事")
        stripped = _strip_data_uris(raw)
        self.assertNotIn("#ff0000", stripped, "data URI 负载应被整段剥离")
        self.assertEqual(_HARDCODED.findall(stripped), ["#abc123"],
                          "data URI 之外的真实硬编码颜色必须仍被抓到")

    def test_all_css_vars_are_canonical(self):
        allowed = set(CANONICAL)
        for name, c in B.all_components().items():
            for v in _VAR.findall(c.css):
                self.assertIn(v, allowed, f"组件 {name} 用了非统一令牌 {v}")

    def test_all_css_vars_in_rendered_output_are_canonical(self):
        """与硬编码颜色检查同一个盲区的镜像版本：上面那条只扫静态 c.css，
        render() 里手写的内联 var(--x) 引用不在扫描范围内——非 canonical 令牌
        在真实页面里解析不出任何值，元素静默丢色，这正是"令牌必须是 canonical
        白名单里的 19 个之一"这条规则本来要防的事。同样按 _sample_for（含
        PER_COMPONENT_SAMPLE 覆盖）渲染、剥掉 data URI 负载后扫描。
        目前 23 个已注册组件里只有 donut 在 render() 里手写内联 var()
        （--accent/--accent-2，均为 canonical），其余组件的内联 style 只有
        数值型（width/height/left 百分比、px 宽度），不含 var() 引用——
        没有组件需要"合法色值必须放行"这条豁免，此闸门目前是预防性的，
        不是纠正性的（跑一遍全量渲染实测过，非猜测）。"""
        allowed = set(CANONICAL)
        for name, c in B.all_components().items():
            for mode in c.modes:
                out = B.render(name, _sample_for(c), mode)
                for v in _VAR.findall(_strip_data_uris(out)):
                    self.assertIn(v, allowed, f"组件 {name}/{mode} 的渲染输出用了非统一令牌 {v}")

    def test_canonical_var_scan_has_teeth(self):
        """不碰共享注册表，直接对合成字符串验证「剥 data URI + _VAR 提取 +
        CANONICAL 成员检查」组合逻辑本身有牙：①canonical 令牌（--accent）
        必须被放行；②非 canonical 令牌（--nope）必须被抓到且真的不在
        CANONICAL 里（不是断言写反了誤判成立）；③data: URI 负载里即使带
        看起来像 var() 的片段也必须被剥离、不参与判定。"""
        allowed = set(CANONICAL)
        ok = _VAR.findall(_strip_data_uris('<i style="color:var(--accent)"></i>'))
        self.assertEqual(ok, ["--accent"])
        self.assertIn(ok[0], allowed, "canonical 令牌必须被放行")
        bad = _VAR.findall(_strip_data_uris('<i style="color:var(--nope)"></i>'))
        self.assertEqual(bad, ["--nope"])
        self.assertNotIn(bad[0], allowed, "样例本身必须真的不在白名单里，否则这条测试没有判别力")
        raw_with_data_uri = (
            '<img src="data:text/plain,var(--nope) lives here"> '
            '<i style="color:var(--accent)"></i>')
        hits = _VAR.findall(_strip_data_uris(raw_with_data_uri))
        self.assertEqual(hits, ["--accent"], "data URI 内的 var() 样式片段不应参与令牌判定")

    def test_every_component_declares_slots(self):
        for name, c in B.all_components().items():
            self.assertIsInstance(c.slots, tuple, name)

    def test_renders_in_every_declared_mode(self):
        for name, c in B.all_components().items():
            for mode in c.modes:
                out = B.render(name, _sample_for(c), mode)
                self.assertTrue(out.strip(), f"{name}/{mode} 渲染为空")
                self.assertNotIn("{{", out, f"{name}/{mode} 残留占位符")

    def test_quote_ticker_sample_uses_realistic_multi_char_lines(self):
        """quote-ticker 的 lines 槽位是字符串列表，PER_COMPONENT_SAMPLE 覆盖前，
        它落到通用 SAMPLE["lines"]（qr-closure 用的标量字符串 "时间地点"）、
        被当列表迭代拆成 4 个单字"引言"——不崩溃，但从未用一条完整引言走过
        循环体，覆盖是"凑巧能跑"而非"形状对"。这里直接断言 _sample_for 拿到的
        样例是多字符字符串组成的列表：删掉 PER_COMPONENT_SAMPLE 里
        ("quote-ticker","lines") 这一项，样例会退回单字符列表，本测试变红。"""
        sample = _sample_for(B.get("quote-ticker"))
        lines = sample["lines"]
        self.assertIsInstance(lines, list)
        self.assertTrue(len(lines) >= 2, "至少两条引言才能验证循环真的迭代了多次")
        for line in lines:
            self.assertGreater(len(line), 1, f"引言 {line!r} 应为完整短句而非单字符")

    def test_web_mode_supported_by_all(self):
        """写这条时（Task 8）注册表里还没有纯 longpic 组件，"人人必须支持 web"
        是当时观察到的真不变式。Task 9 引入 qr-closure（S8 尾部闭环，只在
        longpic 有意义，cta-pills 才是它的 web 替身）之后这条不再普遍成立——
        唯一豁免是显式声明为 ("longpic",) 的组件，豁免条件与
        test_longpic_omission_is_explicit 的反向检查共同锁死，不是敞口放行。"""
        for name, c in B.all_components().items():
            if c.modes == ("longpic",):
                continue
            self.assertIn("web", c.modes, f"{name} 必须支持 web（或显式声明为纯 longpic）")

    def test_longpic_omission_is_explicit(self):
        """长图不支持的组件必须显式声明 modes=("web",)，反过来 web 不支持的组件
        必须显式声明 modes=("longpic",)——两种单模式组件都不能靠调用方记得跳过。
        后半句是 Task 9 补的：qr-closure 是第一个只支持 longpic 的组件，
        原断言只查过 "web",) 这一种单模态形状，对称的另一种完全没人守。"""
        for name, c in B.all_components().items():
            if "longpic" not in c.modes:
                self.assertEqual(c.modes, ("web",), f"{name} modes 声明不规范")
            if "web" not in c.modes:
                self.assertEqual(c.modes, ("longpic",), f"{name} modes 声明不规范")
