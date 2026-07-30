"""邀请函组件集测试。覆盖 brief 给定的基线用例，并补足 brief 未覆盖的
转义回归（title/hook/text/lines/paras）与新组件（keynote-block/terms-list/
hook-grid）的模式分支双向验证。"""
import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.components import base as B
import opb.components  # noqa: F401 触发全量注册


class TestInviteComponents(unittest.TestCase):
    # ── 基线：8 件全部注册 ──────────────────────────────────
    def test_all_eight_registered(self):
        have = set(B.all_components())
        for n in ("info-meta", "agenda-rows", "talk-card", "keynote-block",
                  "terms-list", "hook-grid", "cta-pills", "qr-closure"):
            self.assertIn(n, have)

    # ── info-meta ─────────────────────────────────────────
    def test_info_meta_web_is_grid_longpic_is_row(self):
        d = {"items": [{"k": "日期", "v": "8 月 1 日"}, {"k": "席位", "v": "50 席"}]}
        self.assertIn("meta-grid", B.render("info-meta", d, "web"))
        self.assertIn("meta-row", B.render("info-meta", d, "longpic"))

    # ── agenda-rows ───────────────────────────────────────
    def test_agenda_longpic_stacks_time_above_name(self):
        d = {"rows": [{"time": "13:00–13:45", "name": "幕零 · 入局", "desc": "领编号"}]}
        lp = B.render("agenda-rows", d, "longpic")
        self.assertLess(lp.index("13:00"), lp.index("幕零"))
        self.assertIn("act-stack", lp)

    # ── talk-card ─────────────────────────────────────────
    def test_talk_card_escapes_people_names(self):
        out = B.render("talk-card", {"index": "01", "title": "t", "hook": "h",
                                     "people": [{"name": "<b>x</b>", "role": "r"}]}, "web")
        self.assertNotIn("<b>x</b>", out)

    def test_talk_card_escapes_title_and_hook(self):
        """brief 给定的 talk-card 示例代码原样把 d["title"]/d["hook"] 未转义地拼进
        输出——与 Task 8 footer-brand/section-head 同一类缺陷。删掉实现里对
        title/hook 的 esc() 调用，本测试变红。"""
        out = B.render("talk-card", {"index": "01", "title": "<i>粗体标题</i>",
                                     "hook": "<u>下划线钩子</u>", "people": []}, "web")
        self.assertNotIn("<i>粗体标题</i>", out)
        self.assertNotIn("<u>下划线钩子</u>", out)
        self.assertIn("&lt;i&gt;", out)

    # ── keynote-block ─────────────────────────────────────
    def test_keynote_block_renders_each_paragraph_and_escapes(self):
        d = {"paras": ["<script>bad()</script>", "第二段落"]}
        out = B.render("keynote-block", d, "web")
        self.assertNotIn("<script>bad()</script>", out)
        self.assertEqual(out.count('<p class="prose">'), 2)
        self.assertIn("第二段落", out)

    def test_keynote_block_longpic_has_tighter_padding_class(self):
        """表格要求「同 web，padding 收小」。删掉 mode 三元判断（把 cls 硬编码成
        固定值）任一分支，本测试变红。"""
        d = {"paras": ["正文"]}
        web = B.render("keynote-block", d, "web")
        lp = B.render("keynote-block", d, "longpic")
        self.assertNotIn("keynote-tight", web)
        self.assertIn("keynote-tight", lp)

    # ── terms-list ────────────────────────────────────────
    def test_terms_list_longpic_puts_index_on_own_line(self):
        d = {"items": [{"index": "01", "text": "不直播、不录播。"}]}
        self.assertIn("ri-stack", B.render("terms-list", d, "longpic"))

    def test_terms_list_web_is_not_stacked(self):
        """与上一条构成双向验证：证明 ri-stack 只在 longpic 出现，不是常驻字符串。
        删掉 mode 判断、让 web 也带 ri-stack，本测试变红。"""
        d = {"items": [{"index": "01", "text": "t"}]}
        self.assertNotIn("ri-stack", B.render("terms-list", d, "web"))

    def test_terms_list_escapes_text(self):
        d = {"items": [{"index": "01", "text": "<img src=x onerror=alert(1)>"}]}
        out = B.render("terms-list", d, "web")
        self.assertNotIn("<img src=x", out)
        self.assertIn("&lt;img", out)

    # ── hook-grid ─────────────────────────────────────────
    def test_hook_grid_web_two_col_longpic_one_col(self):
        d = {"title": "吧台", "items": [{"en": "Base", "q": "上下文", "note": "n", "hl": False}]}
        web = B.render("hook-grid", d, "web")
        lp = B.render("hook-grid", d, "longpic")
        self.assertNotIn("pours-1col", web)
        self.assertIn("pours-1col", lp)

    def test_hook_grid_marks_highlighted_item_and_escapes_q(self):
        """双向验证 hl 分支：同一次渲染里一条 hl=False 一条 hl=True，
        断言两种 class 都出现而不是恒真恒假。同时验证 q 字段转义。"""
        d = {"title": "吧台", "items": [
            {"en": "Base", "q": "<b>普通</b>", "note": "n1", "hl": False},
            {"en": "Loop", "q": "共生", "note": "n2", "hl": True},
        ]}
        out = B.render("hook-grid", d, "web")
        self.assertNotIn("<b>普通</b>", out)
        self.assertIn("共生", out)
        self.assertIn('class="pour hl"', out)
        self.assertIn('class="pour">', out)

    def test_missing_slot_names_the_slot_for_hook_grid(self):
        with self.assertRaises(B.SlotMissing) as e:
            B.render("hook-grid", {"title": "t"}, "web")
        self.assertIn("items", str(e.exception))

    # ── cta-pills ─────────────────────────────────────────
    def test_cta_pills_is_web_only(self):
        self.assertEqual(B.get("cta-pills").modes, ("web",))
        with self.assertRaises(B.ModeUnsupported):
            B.render("cta-pills", {"title": "t", "text": "x", "buttons": []}, "longpic")

    def test_external_links_carry_noopener(self):
        out = B.render("cta-pills", {"title": "t", "text": "x", "buttons": [
            {"label": "确认出席", "href": "https://example.com", "variant": "primary"}]}, "web")
        self.assertIn('rel="noopener"', out)
        self.assertIn('target="_blank"', out)

    def test_cta_pills_escapes_title_and_text(self):
        out = B.render("cta-pills", {"title": "<i>t</i>", "text": "<u>x</u>",
                                     "buttons": []}, "web")
        self.assertNotIn("<i>t</i>", out)
        self.assertNotIn("<u>x</u>", out)

    def test_cta_pills_default_variant_is_primary(self):
        """删掉 b.get("variant","primary") 的默认值，本测试变红。"""
        out = B.render("cta-pills", {"title": "t", "text": "x", "buttons": [
            {"label": "确认", "href": "https://example.com"}]}, "web")
        self.assertIn('class="pill primary"', out)

    # ── qr-closure ────────────────────────────────────────
    def test_qr_closure_is_longpic_only(self):
        self.assertEqual(B.get("qr-closure").modes, ("longpic",))

    def test_qr_closure_contains_time_place_and_qr(self):
        out = B.render("qr-closure", {"qr": "data:image/png;base64,AA", "alt": "二维码",
                                      "lines": "8 月 1 日 · 上海"}, "longpic")
        for k in ("8 月 1 日", "上海", "<img"):
            self.assertIn(k, out)

    def test_qr_closure_escapes_lines_and_alt(self):
        out = B.render("qr-closure", {"qr": "data:image/png;base64,AA",
                                      "alt": "<b>二维码</b>",
                                      "lines": "<script>x</script>"}, "longpic")
        self.assertNotIn("<b>二维码</b>", out)
        self.assertNotIn("<script>x</script>", out)


if __name__ == "__main__":
    unittest.main()
