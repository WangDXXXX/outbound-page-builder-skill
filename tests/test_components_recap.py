"""战报组件集测试。前 8 条是 brief Step 1 给定的基线用例（原样保留，逐字未改）；
其余是补足 brief 未覆盖的：转义回归（每个新组件至少一处）、模式分支双向验证
（S3 堆叠/展开两个方向都断言，不能只看堆叠那一侧）、循环真做了而不是照抄一份
写死的样例（2 条数据必须渲染出 2 份标记，不是"永远 2 个 img"这种巧合过关）、
以及 compare-bars/bar-h/donut 的数值计算是否真的按输入换算而不是常数。"""
import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.components import base as B
import opb.components  # noqa: F401 触发全量注册


class TestRecapComponents(unittest.TestCase):
    # ── 基线：brief Step 1 给定的 8 条，原样保留 ────────────
    def test_all_ten_registered(self):
        have = set(B.all_components())
        for n in ("stat-caption", "compare-bars", "quote-card", "quote-ticker",
                  "speaker-grid", "photo-mosaic", "donut", "bar-h",
                  "timeline-heartbeat", "award-list"):
            self.assertIn(n, have)

    def test_quote_ticker_is_web_only(self):
        """D10：滚动轮播在静态图里不成立，直接删，不降级成静态列表。"""
        self.assertEqual(B.get("quote-ticker").modes, ("web",))
        with self.assertRaises(B.ModeUnsupported):
            B.render("quote-ticker", {"lines": ["a"]}, "longpic")

    def test_quote_ticker_has_reduced_motion_fallback(self):
        self.assertIn("prefers-reduced-motion", B.get("quote-ticker").css)

    def test_stat_caption_always_renders_caption(self):
        """蓝军第6条：数字必须自证意义。"""
        out = B.render("stat-caption", {"value": "628", "label": "到场",
                                        "caption": "名册 609 + 现场登记 19"}, "web")
        self.assertIn("名册 609", out)

    def test_quote_card_web_links_longpic_plain(self):
        d = {"text": "高质量的会议", "speaker": "Cathy", "link": "https://example.com/p"}
        self.assertIn("<a", B.render("quote-card", d, "web"))
        self.assertNotIn("<a", B.render("quote-card", d, "longpic"))

    def test_compare_bars_legend_names_the_comparison_target(self):
        """蓝军第5条：对比屏必须明确对比对象。"""
        d = {"title": "对比", "legend": {"a": "杭州", "b": "北京"},
             "pairs": [{"label": "到场", "a": 297, "b": 628}]}
        out = B.render("compare-bars", d, "web")
        self.assertIn("杭州", out)
        self.assertIn("北京", out)

    def test_donut_svg_has_explicit_width(self):
        out = B.render("donut", {"title": "身份", "segments": [
            {"label": "开发", "pct": 40}, {"label": "产品", "pct": 60}]}, "web")
        self.assertRegex(out, r"<svg[^>]*\swidth=")

    def test_speaker_grid_renders_two_images_per_person(self):
        out = B.render("speaker-grid", {"people": [
            {"name": "N", "role": "R", "cover": "data:a", "shot": "data:b"}]}, "web")
        self.assertEqual(out.count("<img"), 2)

    # ── stat-caption ────────────────────────────────────────
    def test_stat_caption_longpic_stacks_vertically(self):
        """表格要求 longpic 竖排。删掉 _stat 的 cls 三元、把 cls 恒定为 "stat"，
        本测试变红；同一断言双向覆盖，web 不带 stack 类。"""
        d = {"value": "1", "label": "l", "caption": "c"}
        web = B.render("stat-caption", d, "web")
        lp = B.render("stat-caption", d, "longpic")
        self.assertNotIn("stat-stack", web)
        self.assertIn("stat-stack", lp)

    def test_stat_caption_escapes_all_three_fields(self):
        d = {"value": "<b>628</b>", "label": "<i>到场</i>", "caption": "<u>注脚</u>"}
        out = B.render("stat-caption", d, "web")
        self.assertNotIn("<b>628</b>", out)
        self.assertNotIn("<i>到场</i>", out)
        self.assertNotIn("<u>注脚</u>", out)

    # ── stat-caption compare_to（Task 15 F3）───────────────
    def test_stat_caption_without_compare_to_unchanged(self):
        """向后兼容：不给 compare_to，行为与修复前完全一样，不出现 .cmp。"""
        d = {"value": "1", "label": "l", "caption": "c"}
        out = B.render("stat-caption", d, "web")
        self.assertNotIn("cmp", out)

    def test_stat_caption_renders_compare_to_when_present(self):
        """蓝军第7条"对比>绝对值"：给了 compare_to 就必须渲染出对比对象
        和对比数值，不能只是被解析、被无视（facts.json 的 compare_to
        字段此前就是这个下场——被 load_facts 解析进内存，从不被任何
        断言或组件读取）。"""
        d = {"value": "628", "label": "到场", "caption": "c",
             "compare_to": {"value": "297", "label": "杭州首届"}}
        out = B.render("stat-caption", d, "web")
        self.assertIn("杭州首届", out)
        self.assertIn("297", out)

    def test_stat_caption_escapes_compare_to_fields(self):
        d = {"value": "1", "label": "l", "caption": "c",
             "compare_to": {"value": "<b>x</b>", "label": "<i>y</i>"}}
        out = B.render("stat-caption", d, "web")
        self.assertNotIn("<b>x</b>", out)
        self.assertNotIn("<i>y</i>", out)

    # ── compare-bars ──────────────────────────────────────
    def test_compare_bars_web_side_longpic_top(self):
        """双向验证 S3 变体：cb-stack 只在 longpic 出现。"""
        d = {"title": "t", "legend": {"a": "A", "b": "B"},
             "pairs": [{"label": "l", "a": 1, "b": 2}]}
        web = B.render("compare-bars", d, "web")
        lp = B.render("compare-bars", d, "longpic")
        self.assertNotIn("cb-stack", web)
        self.assertIn("cb-stack", lp)

    def test_compare_bars_bar_width_reflects_relative_value(self):
        """数值必须真的按 a/b 相对当次最大值换算百分比，不是写死的宽度。
        把 _compare_bars 里的 pa/pb 计算改成常数（例如恒为 50.0），本测试变红。"""
        d = {"title": "t", "legend": {"a": "A", "b": "B"},
             "pairs": [{"label": "到场", "a": 50, "b": 100}]}
        out = B.render("compare-bars", d, "web")
        self.assertIn("width:50.0%", out)
        self.assertIn("width:100.0%", out)

    def test_compare_bars_escapes_label_and_legend(self):
        d = {"title": "<s>t</s>", "legend": {"a": "<i>A</i>", "b": "<i>B</i>"},
             "pairs": [{"label": "<b>到场</b>", "a": 1, "b": 2}]}
        out = B.render("compare-bars", d, "web")
        for bad in ("<s>t</s>", "<i>A</i>", "<i>B</i>", "<b>到场</b>"):
            self.assertNotIn(bad, out)

    # ── quote-card ──────────────────────────────────────────
    def test_quote_card_escapes_text_and_speaker(self):
        d = {"text": "<script>x()</script>", "speaker": "<i>S</i>", "link": ""}
        out = B.render("quote-card", d, "web")
        self.assertNotIn("<script>x()</script>", out)
        self.assertNotIn("<i>S</i>", out)

    def test_quote_card_web_without_link_renders_plain(self):
        """给定测试只验证了「web+有 link → 出 <a>」与「longpic → 不出 <a>」两支；
        「web+无 link」是第三条独立分支（_quote_card 里 `and d.get("link")` 那半句），
        给定测试完全没碰到。删掉这半句条件，本测试变红。"""
        d = {"text": "t", "speaker": "S", "link": ""}
        out = B.render("quote-card", d, "web")
        self.assertNotIn("<a", out)
        self.assertIn("S", out)

    # ── quote-ticker ──────────────────────────────────────
    def test_quote_ticker_escapes_lines(self):
        out = B.render("quote-ticker", {"lines": ["<script>x()</script>"]}, "web")
        self.assertNotIn("<script>x()</script>", out)

    def test_quote_ticker_duplicates_track_for_seamless_loop(self):
        """无缝滚动靠内容整体复制一份（{items}{items}）+ translateX(-50%)。
        把 render 里的 `items + items` 改回单份 `items`，本测试变红。"""
        out = B.render("quote-ticker", {"lines": ["独一无二的标记文本"]}, "web")
        self.assertEqual(out.count("独一无二的标记文本"), 2)

    # ── speaker-grid ────────────────────────────────────────
    def test_speaker_grid_longpic_is_single_column(self):
        d = {"people": [{"name": "N", "role": "R", "cover": "a", "shot": "b"}]}
        web = B.render("speaker-grid", d, "web")
        lp = B.render("speaker-grid", d, "longpic")
        self.assertNotIn("sg-1col", web)
        self.assertIn("sg-1col", lp)

    def test_speaker_grid_escapes_name_and_role(self):
        d = {"people": [{"name": "<b>N</b>", "role": "<i>R</i>",
                         "cover": "a", "shot": "b"}]}
        out = B.render("speaker-grid", d, "web")
        self.assertNotIn("<b>N</b>", out)
        self.assertNotIn("<i>R</i>", out)

    def test_speaker_grid_two_people_renders_four_images(self):
        """给定测试只喂了 1 人、断言 2 张图——一个把 img 写死成固定 2 张、
        完全不看 people 列表的实现也能骗过它。2 人必须出 4 张图才能证明
        真的在按列表循环渲染，不是凑巧对上。"""
        d = {"people": [{"name": "A", "role": "R", "cover": "a", "shot": "b"},
                        {"name": "B", "role": "R", "cover": "c", "shot": "d"}]}
        out = B.render("speaker-grid", d, "web")
        self.assertEqual(out.count("<img"), 4)

    # ── photo-mosaic ────────────────────────────────────────
    def test_photo_mosaic_longpic_is_single_column(self):
        d = {"photos": [{"src": "a", "alt": "x"}]}
        web = B.render("photo-mosaic", d, "web")
        lp = B.render("photo-mosaic", d, "longpic")
        self.assertNotIn("pm-1col", web)
        self.assertIn("pm-1col", lp)

    def test_photo_mosaic_escapes_alt(self):
        d = {"photos": [{"src": "a", "alt": "<script>x()</script>"}]}
        out = B.render("photo-mosaic", d, "web")
        self.assertNotIn("<script>x()</script>", out)

    def test_photo_mosaic_renders_one_cell_per_photo(self):
        d = {"photos": [{"src": "a", "alt": "x"}, {"src": "b", "alt": "y"},
                        {"src": "c", "alt": "z"}]}
        out = B.render("photo-mosaic", d, "web")
        self.assertEqual(out.count("pm-cell"), 3)

    # ── donut ─────────────────────────────────────────────
    def test_donut_renders_one_legend_item_per_segment_and_escapes_label(self):
        d = {"title": "t", "segments": [
            {"label": "<b>开发</b>", "pct": 40}, {"label": "产品", "pct": 30},
            {"label": "运营", "pct": 30}]}
        out = B.render("donut", d, "web")
        self.assertEqual(out.count("<li>"), 3)
        self.assertNotIn("<b>开发</b>", out)

    # ── donut sum-must-normalize guard（Task 15 F5）─────────
    def test_donut_raw_counts_not_summing_to_100_raises(self):
        """真实踩坑复现：满意度原始计数 41/27/2/1（总71）曾经会让圆环按
        41/71≈57.7% 正确画，但图例直接显示原始值"41%"——图例和圆环对不上，
        且"41%"本身是错误陈述。现在必须拒绝，不能悄悄接受。"""
        d = {"title": "t", "segments": [
            {"label": "非常满意", "pct": 41}, {"label": "满意", "pct": 27},
            {"label": "一般", "pct": 2}, {"label": "不太满意", "pct": 1}]}
        with self.assertRaises(B.ComponentError):
            B.render("donut", d, "web")

    def test_donut_normalized_percentages_accepted(self):
        """预先换算好、加起来等于100的百分比必须能正常渲染。"""
        d = {"title": "t", "segments": [
            {"label": "非常满意", "pct": 58}, {"label": "满意", "pct": 38},
            {"label": "一般", "pct": 3}, {"label": "不太满意", "pct": 1}]}
        out = B.render("donut", d, "web")
        self.assertIn("<li>", out)

    def test_donut_legend_matches_ring_computation(self):
        """图例文字必须是圆环实际使用的同一个归一化数字，不是原始输入
        直接拼接——即使输入总和已经是100（此时归一化在数学上是恒等变换），
        也要验证图例读的是 pct（归一化后），不是 s["pct"]（原始输入）。"""
        d = {"title": "t", "segments": [
            {"label": "A", "pct": 40}, {"label": "B", "pct": 60}]}
        out = B.render("donut", d, "web")
        self.assertIn("A · 40%", out)
        self.assertIn("B · 60%", out)

    def test_donut_within_rounding_tolerance_accepted(self):
        """总和 99.6-100.5 之间的浮点舍入误差应该被容忍，不是硬要求恰好100
        （真实数据换算成百分比几乎不可能刚好加总为整数100）。"""
        d = {"title": "t", "segments": [
            {"label": "A", "pct": 33.3}, {"label": "B", "pct": 33.3},
            {"label": "C", "pct": 33.3}]}  # 总和 99.9
        out = B.render("donut", d, "web")
        self.assertIn("<li>", out)

    def test_donut_segments_get_distinct_colors(self):
        """配色必须真的按下标从调色板取值，不能所有段都塞同一个颜色变量。
        把 _DONUT_PALETTE 下标计算改成恒为 0，本测试变红。"""
        d = {"title": "t", "segments": [
            {"label": "A", "pct": 40}, {"label": "B", "pct": 60}]}
        out = B.render("donut", d, "web")
        self.assertIn("stroke:var(--accent)", out)
        self.assertIn("stroke:var(--accent-2)", out)

    # ── bar-h ─────────────────────────────────────────────
    def test_bar_h_escapes_label_and_note(self):
        d = {"title": "t", "rows": [{"label": "<b>l</b>", "pct": 50, "note": "<i>n</i>"}]}
        out = B.render("bar-h", d, "web")
        self.assertNotIn("<b>l</b>", out)
        self.assertNotIn("<i>n</i>", out)

    def test_bar_h_bar_width_reflects_pct(self):
        d = {"title": "t", "rows": [{"label": "l", "pct": 73, "note": "n"}]}
        out = B.render("bar-h", d, "web")
        self.assertIn("width:73%", out)

    def test_bar_h_renders_one_row_per_entry(self):
        """用带收尾引号的 class="bh-row" 精确匹配——裸子串 "bh-row" 会连带算上
        容器自己的 class="bh-rows"（复数），3 行会被数成 4，误伤这条测试。"""
        d = {"title": "t", "rows": [{"label": "l1", "pct": 1, "note": "n"},
                                    {"label": "l2", "pct": 2, "note": "n"},
                                    {"label": "l3", "pct": 3, "note": "n"}]}
        out = B.render("bar-h", d, "web")
        self.assertEqual(out.count('class="bh-row"'), 3)

    # ── timeline-heartbeat ──────────────────────────────────
    def test_timeline_heartbeat_longpic_converts_marks_to_list(self):
        """双向验证：web 用定位轴（hb-marks-axis），longpic 转纯列表
        （hb-marks-list），不能只查其中一侧。"""
        d = {"title": "t", "buckets": [{"hour": 0, "count": 1}],
             "marks": [{"hour": 19, "label": "开场"}]}
        web = B.render("timeline-heartbeat", d, "web")
        lp = B.render("timeline-heartbeat", d, "longpic")
        self.assertIn("hb-marks-axis", web)
        self.assertNotIn("hb-marks-list", web)
        self.assertIn("hb-marks-list", lp)
        self.assertNotIn("hb-marks-axis", lp)

    def test_timeline_heartbeat_histogram_retained_in_longpic(self):
        """表格明确要求「直方图保留」——marks 退化不能连累直方图一起消失。"""
        d = {"title": "t", "buckets": [{"hour": 9, "count": 5}, {"hour": 20, "count": 88}],
             "marks": []}
        lp = B.render("timeline-heartbeat", d, "longpic")
        self.assertEqual(lp.count("hb-bar"), 2)

    def test_timeline_heartbeat_escapes_mark_label(self):
        d = {"title": "t", "buckets": [{"hour": 0, "count": 1}],
             "marks": [{"hour": 1, "label": "<script>x()</script>"}]}
        out = B.render("timeline-heartbeat", d, "web")
        self.assertNotIn("<script>x()</script>", out)

    # ── award-list ──────────────────────────────────────────
    def test_award_list_escapes_all_fields(self):
        d = {"awards": [{"category": "<b>c</b>", "winner": "<i>w</i>", "note": "<u>n</u>"}]}
        out = B.render("award-list", d, "web")
        self.assertNotIn("<b>c</b>", out)
        self.assertNotIn("<i>w</i>", out)
        self.assertNotIn("<u>n</u>", out)

    def test_award_list_renders_one_row_per_award(self):
        d = {"awards": [{"category": "c1", "winner": "w1", "note": "n1"},
                        {"category": "c2", "winner": "w2", "note": "n2"}]}
        out = B.render("award-list", d, "web")
        self.assertEqual(out.count("aw-row"), 2)

    def test_award_list_identical_in_both_modes(self):
        """表格标注「同 web」——不是「大体相似」，是同一份骨架。"""
        d = {"awards": [{"category": "c", "winner": "w", "note": "n"}]}
        self.assertEqual(B.render("award-list", d, "web"),
                          B.render("award-list", d, "longpic"))


if __name__ == "__main__":
    unittest.main()
