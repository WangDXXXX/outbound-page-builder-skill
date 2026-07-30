import sys, json, tempfile, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import build as BD

OUTLINE = {
    "genre": "invite", "title": "测试邀请函",
    "og": {"title": "og 标题", "description": "og 描述"},
    "slots": [
        {"key": "hero", "components": [
            {"name": "sysbar", "data": {"text": "8 月 1 日 · 上海"}},
            {"name": "info-meta", "data": {"items": [{"k": "日期", "v": "8 月 1 日"}]}}]},
        {"key": "why_you", "components": []},
        {"key": "agenda", "components": [
            {"name": "agenda-rows", "data": {"rows": [
                {"time": "13:00", "name": "幕零", "desc": "入局"}]}}]},
        {"key": "value", "components": []},
        {"key": "people", "components": []},
        {"key": "terms", "components": []},
        {"key": "cta", "components": [
            {"name": "cta-pills", "data": {"title": "来吗", "text": "回一个字",
             "buttons": [{"label": "确认出席", "href": "https://example.com",
                          "variant": "primary"}]}}]},
    ],
}


def _proj():
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "outline.json").write_text(json.dumps(OUTLINE, ensure_ascii=False), encoding="utf-8")
    th = d / "theme"; th.mkdir()
    (th / "tokens.css").write_text(
        ":root{--bg:#0b0b0b;--fg:#fff;--accent:#cc6437;--hair:rgba(255,255,255,.12)}",
        encoding="utf-8")
    return d


class TestBuild(unittest.TestCase):
    def test_web_build_is_self_contained_single_file(self):
        d = _proj()
        html = BD.build(str(d / "outline.json"), str(d / "theme"), "web")
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("--accent:#cc6437", html.replace(" ", ""))
        self.assertNotIn("<link", html)
        self.assertIn("测试邀请函", html)

    def test_web_has_mobile_viewport_and_og(self):
        d = _proj()
        html = BD.build(str(d / "outline.json"), str(d / "theme"), "web")
        self.assertIn('name="viewport"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn("width=device-width", html)

    def test_longpic_swaps_cta_pills_for_qr_closure(self):
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"][-1]["components"] = [
            {"name": "cta-pills", "data": {"title": "来吗", "text": "x", "buttons": []},
             "longpic": {"name": "qr-closure",
                         "data": {"qr": "data:image/png;base64,AA", "alt": "二维码",
                                  "lines": "8 月 1 日 · 上海"}}}]
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        html = BD.build(str(d / "outline.json"), str(d / "theme"), "longpic")
        self.assertIn("qrc", html)
        self.assertNotIn("btns", html)

    def test_longpic_canvas_is_430(self):
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"][-1]["components"] = []
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        html = BD.build(str(d / "outline.json"), str(d / "theme"), "longpic")
        self.assertIn("width:430px", html.replace(" ", ""))

    def test_longpic_drops_web_only_component_with_clear_error(self):
        """quote-ticker 没给 longpic 替身时必须报错，不能静默丢内容。"""
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"][1]["components"] = [{"name": "quote-ticker", "data": {"lines": ["a"]}}]
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "longpic")
        self.assertIn("quote-ticker", str(e.exception))

    def test_invalid_outline_raises_before_render(self):
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"] = [s for s in o["slots"] if s["key"] != "cta"]
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(BD.BuildError):
            BD.build(str(d / "outline.json"), str(d / "theme"), "web")

    def test_writes_out_file_when_given(self):
        d = _proj()
        p = d / "page.html"
        BD.build(str(d / "outline.json"), str(d / "theme"), "web", out=str(p))
        self.assertTrue(p.exists())


class TestBuildRobustness(unittest.TestCase):
    """brief 给的六条测试之外的补强，都对应任务说明里点名的具体风险，而不是
    泛泛加测试凑数：mode 拼错不能被悄悄当成 longpic 处理；outline.slots 的
    形状坑要端到端过一遍（不只在 skeleton 单测层面证明）；不完整的
    theme/tokens.css 必须靠 theme.emit_tokens_css 兜住结构性令牌，不能让
    原文件缺什么页面就缺什么；CTA_SWAP 要真的被用起来而不是导出了却没人碰；
    替身块本身也可能选错 mode，不能只查"给没给替身"这一半。"""

    def test_invalid_mode_raises_clear_error(self):
        """mode 参数拼错（比如 "pdf"）不能被当成 longpic 悄悄处理——各处
        mode 分支都是 `if mode == "web" else ...` 的二选一写法，任何非
        "web" 的拼写都会被当成 longpic 走掉而不报错，页面会用错误的画布
        宽度/viewport 悄悄拼出来。"""
        d = _proj()
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "pdf")
        self.assertIn("pdf", str(e.exception))

    def test_invalid_mode_raises_even_with_zero_components(self):
        """上一条用的是默认 OUTLINE 夹具，里面有真实组件——mode 拼错时，
        第一个被处理的组件恰好会在 _pick 里因为"不支持该 mode"报错，
        这条防线本身没问题，但它会掩盖"顶层 mode 合法性检查究竟有没有做"
        这件事：如果 outline 所有槽位的 components 都是空列表，_pick 一次
        都不会被调用，只靠 _pick 兜底的话，非法 mode 会被 `if mode == "web"
        else ...` 这类二选一写法悄悄当成 longpic，产出一个没人要求过的
        430px 页面而不报任何错——本地实测过这个具体后果（构造零组件 outline
        直接 build 成 "pdf"，不报错、且 width:430px 出现在输出里）。
        这条测试专门盖住"没有任何组件可以顺带报错"这个场景，隔离验证顶层
        mode 检查本身在起作用。"""
        d = pathlib.Path(tempfile.mkdtemp())
        empty_outline = {
            "genre": "invite", "title": "空槽位",
            "slots": [{"key": k, "components": []} for k in
                      ["hero", "why_you", "agenda", "value", "people", "terms", "cta"]],
        }
        (d / "outline.json").write_text(json.dumps(empty_outline, ensure_ascii=False),
                                        encoding="utf-8")
        th = d / "theme"; th.mkdir()
        (th / "tokens.css").write_text(
            ":root{--bg:#0b0b0b;--fg:#fff;--accent:#cc6437;--hair:rgba(255,255,255,.12)}",
            encoding="utf-8")
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(th), "pdf")
        self.assertIn("pdf", str(e.exception))

    def test_missing_tokens_file_raises_clear_error(self):
        d = _proj()
        (d / "theme" / "tokens.css").unlink()
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "web")
        self.assertIn("tokens.css", str(e.exception))

    def test_build_rejects_non_list_slots_with_clear_error(self):
        """踩坑清单点名的那个坑，端到端过一遍完整管线：outline.slots 被
        手滑写成字符串时，build() 必须报出命名清楚的 BuildError，而不是让
        validate_outline 内部一个不知所云的 TypeError/AttributeError 冒出来
        （或者更糟：被某处过宽的 except 兜住、悄悄当成通过）。"""
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"] = "hero,why_you,agenda"
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "web")
        self.assertIn("列表", str(e.exception))

    def test_incomplete_theme_gets_structural_fallbacks_filled(self):
        """theme/tokens.css 在夹具里只给了 4 个令牌（--bg/--fg/--accent/
        --hair），真机渲染要用到的 --pad/--gap/--font-cn/--maxw 不能因为
        主题没写就在 :root 里整个消失——组件与 reset 层 CSS 大量直接引用
        这几个（.wrap{padding:0 var(--pad)}、body{font-family:var(--font-cn)}、
        .wrap{max-width:var(--maxw)}），令牌解析不到时对应声明整条失效
        （padding 会直接归零，不是退化成某个默认值）。必须靠
        theme.emit_tokens_css 的内置兜底补上，不能只把 tokens.css 原文
        整段照抄进页面——brief 原实现就是原文整段照抄，这条测试在那个
        实现下会失败。"""
        d = _proj()
        html = BD.build(str(d / "outline.json"), str(d / "theme"), "web")
        css_flat = html.replace(" ", "").replace("\n", "")
        self.assertIn("--pad:", css_flat)
        self.assertIn("--font-cn:", css_flat)
        self.assertIn("--maxw:", css_flat)

    def test_unsupported_mode_error_suggests_known_swap_partner(self):
        """cta-pills 缺 longpic 替身时，报错应该点出 CTA_SWAP 里记录的已知
        替身候选 `qr-closure`，把"补一个替身"从抽象建议变成一个可以直接抄
        的名字——CTA_SWAP 是 skeleton.py 明确导出的接口，不能只导出不使用。
        default OUTLINE 夹具的 cta 槽位本来就没给 longpic 替身，直接原样
        build 成 longpic 即可触发。"""
        d = _proj()
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "longpic")
        msg = str(e.exception)
        self.assertIn("cta-pills", msg)
        self.assertIn("qr-closure", msg)

    def test_web_only_component_without_known_swap_gets_no_bogus_hint(self):
        """quote-ticker 没有 CTA_SWAP 记录的替身，报错不能硬编出一个看似
        有效的候选名字——没有已知替身就该只给通用补救话术，不能让人以为
        存在一个可以直接套到 quote-ticker 头上的替身。"""
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"][1]["components"] = [{"name": "quote-ticker", "data": {"lines": ["a"]}}]
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "longpic")
        self.assertNotIn("qr-closure", str(e.exception))

    def test_substitute_that_itself_does_not_support_target_mode_is_rejected(self):
        """替身块本身也必须支持目标 mode——outline 把一个 web-only 组件
        错填成 longpic 替身时（这里故意把 quote-ticker 塞成 cta-pills 的
        longpic 替身），不能让 components.base 层更难懂的 ModeUnsupported
        直接漏给调用方，必须是命名清楚的 BuildError，点出选错的是哪个替身。"""
        d = _proj()
        o = json.loads((d / "outline.json").read_text(encoding="utf-8"))
        o["slots"][-1]["components"] = [
            {"name": "cta-pills", "data": {"title": "来吗", "text": "x", "buttons": []},
             "longpic": {"name": "quote-ticker", "data": {"lines": ["a", "b"]}}}]
        (d / "outline.json").write_text(json.dumps(o, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(BD.BuildError) as e:
            BD.build(str(d / "outline.json"), str(d / "theme"), "longpic")
        self.assertIn("quote-ticker", str(e.exception))


if __name__ == "__main__":
    unittest.main()
