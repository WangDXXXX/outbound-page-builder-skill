import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.checks import aivoice as A
from opb.textutil import strip_quoted

class _Ctx:
    def __init__(self, text, copy=None):
        self.text = text
        self.text_noquote = strip_quoted(text)
        class C: pass
        self.cfg = C()
        self.cfg.copy = copy or {"humanizer": True, "max_we": 5, "ban_contrast_pair": True}

class TestAiVoice(unittest.TestCase):
    def test_contrast_pair_fails(self):
        out = A.check(_Ctx("这不是一场大会，而是一张桌子。"))
        self.assertTrue(any("contrast_pair" in m for m in out))

    def test_contrast_variant_bingfei_fails(self):
        self.assertTrue(A.check(_Ctx("并非规模的胜利，而是密度的胜利。")))

    def test_contrast_variant_yushuo_fails(self):
        self.assertTrue(A.check(_Ctx("与其说是发布，不如说是宣言。")))

    def test_contrast_variant_buzhishi_fails(self):
        self.assertTrue(A.check(_Ctx("这不只是工具，更是伙伴。")))

    def test_contrast_variant_bushi_shi_no_er_fails(self):
        """丢了「而」的「不是…，是…」——上海邀请函验收实测抓到的真实案例
        （AI 不是玩具，是生产工具），320 条合成测试从未产生过这个变体。"""
        out = A.check(_Ctx("AI 不是玩具，是生产工具。"))
        self.assertTrue(any("contrast_pair_bushi_shi_no_er" in m for m in out))

    def test_contrast_variant_bingfei_shi_no_er_fails(self):
        """丢了「而」的「并非…，是…」。"""
        out = A.check(_Ctx("这并非规模的胜利，是密度的胜利。"))
        self.assertTrue(any("contrast_pair_bingfei_shi_no_er" in m for m in out))

    def test_bushi_shi_no_er_requires_comma(self):
        """没有逗号分隔两半——「不是」和后面的「是」分别属于不同分句时不应该
        误伤（协调者明确要求的区分标准：逗号是构式的信号，不是巧合）。"""
        out = A.check(_Ctx("不是报名就能来：要么是定向邀请，要么通过公开招募。"))
        self.assertFalse(any("contrast_pair_bushi_shi_no_er" in m for m in out))
        out2 = A.check(_Ctx("这 50 个人不是先到先得填出来的：你被记住是因为自己，不是因为抢到了名额。"))
        self.assertFalse(any("contrast_pair_bushi_shi_no_er" in m for m in out2))

    def test_grandiose_word_fails(self):
        self.assertTrue(any("grandiose" in m for m in A.check(_Ctx("这标志着新阶段。"))))

    def test_em_dash_run_fails(self):
        self.assertTrue(any("em_dash_run" in m for m in A.check(_Ctx("他来了——带着方案——又走了"))))

    def test_we_frequency_over_limit_fails(self):
        t = "我们" * 6
        self.assertTrue(any("我们" in m for m in A.check(_Ctx(t))))

    def test_we_frequency_at_limit_passes(self):
        self.assertEqual(A.check(_Ctx("我们" * 5)), [])

    def test_uniform_sentence_length_warns(self):
        t = "。".join(["这是一个测试句子"] * 8) + "。"
        self.assertTrue(any("句长" in m for m in A.check(_Ctx(t))))

    def test_ban_contrast_pair_can_be_disabled(self):
        c = {"humanizer": True, "max_we": 5, "ban_contrast_pair": False}
        out = A.check(_Ctx("这不是大会，而是桌子。", c))
        self.assertFalse(any("contrast_pair" in m for m in out))

    # 引用区豁免测试：参与者原话不应该被标记
    def test_contrast_pair_inside_quote_is_exempt(self):
        """引用区内的对比构式（参与者原话）应该豁免。"""
        out = A.check(_Ctx("他说「这不是一场大会，而是一张桌子」。"))
        self.assertFalse(any("contrast_pair" in m for m in out))

    def test_contrast_pair_outside_quote_fails(self):
        """确保对比构式在引用外仍然会被标记。"""
        out = A.check(_Ctx("他说「没什么」。这不是大会，而是桌子。"))
        self.assertTrue(any("contrast_pair" in m for m in out))

    def test_bingfei_inside_quote_is_exempt(self):
        """并非…而是… 变体在引用内豁免。"""
        out = A.check(_Ctx("演讲者指出「并非规模的胜利，而是密度的胜利」。"))
        self.assertFalse(any("contrast_pair_bing_fei" in m for m in out))

    def test_yushuo_inside_quote_is_exempt(self):
        """与其说…不如说… 变体在引用内豁免。"""
        out = A.check(_Ctx("他说「与其说是发布，不如说是宣言」。"))
        self.assertFalse(any("contrast_pair_yushuo" in m for m in out))

    def test_buzhishi_inside_quote_is_exempt(self):
        """不只是…更是… 变体在引用内豁免。"""
        out = A.check(_Ctx("观点是「这不只是工具，更是伙伴」。"))
        self.assertFalse(any("contrast_pair_bushi_shi" in m for m in out))

    def test_bushi_shi_no_er_inside_quote_is_exempt(self):
        """丢了「而」的「不是…，是…」在引用内豁免——原声逐字优先于黑名单。"""
        out = A.check(_Ctx("他说「AI 不是玩具，是生产工具」。"))
        self.assertFalse(any("contrast_pair_bushi_shi_no_er" in m for m in out))

    def test_grandiose_word_inside_quote_is_exempt(self):
        """宏大空话在引用内豁免。"""
        out = A.check(_Ctx("参与者说「这标志着新阶段」。"))
        self.assertFalse(any("grandiose" in m for m in out))

    def test_grandiose_word_outside_quote_fails(self):
        """宏大空话在引用外仍被标记。"""
        out = A.check(_Ctx("他说「没什么」，这标志着新阶段。"))
        self.assertTrue(any("grandiose" in m for m in out))

    # 我们频率测试：验证WARN严重性与阻断行为
    def test_we_frequency_warns_not_blocks(self):
        """超过我们限制应该产生WARN（不阻断）。"""
        t = "我们" * 6
        out = A.check(_Ctx(t))
        warns = [m for m in out if m.startswith("WARN")]
        blocks = [m for m in out if not m.startswith("WARN")]
        self.assertTrue(any("我们" in m for m in warns), "应有WARN消息")
        self.assertEqual(len(blocks), 0, "不应有阻断消息（所有我们消息都是WARN）")

    def test_contrast_pair_not_warn(self):
        """对比构式应该是阻断（不是WARN）。"""
        out = A.check(_Ctx("这不是大会，而是桌子。"))
        self.assertTrue(any("contrast_pair" in m and not m.startswith("WARN") for m in out),
                        "对比构式应该是阻断消息，不是WARN")

    # copy.allow 豁免机制：闸门二协调者追加裁定——反差句式规则本身不能因为
    # 李默收官演示主线句「AI 不是玩具，是生产工具」这种人工签字确认过的
    # 句子而整体放宽，要给"具体某一句被人看过、决定保留"开一个精确的口子。
    def test_allow_entry_suppresses_to_warn_with_reason(self):
        """命中一条 allow 里的原句：降级成 WARN，理由必须出现在消息里，
        不能阻断交付。"""
        c = {"humanizer": True, "max_we": 5, "ban_contrast_pair": True,
             "allow": [{"text": "AI 不是玩具，是生产工具", "reason": "李默收官演示主线句，已上线"}]}
        out = A.check(_Ctx("AI 不是玩具，是生产工具。", c))
        hits = [m for m in out if "contrast_pair_bushi_shi_no_er" in m]
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0].startswith("WARN"))
        self.assertIn("李默收官演示主线句，已上线", hits[0])

    def test_allow_does_not_suppress_different_sentence(self):
        """协调者点名的坑：allow 里有一句被豁免的句子，页面上另一句不同的
        违规句子必须照样被拦——不能因为豁免表非空就顺带放过了别的命中。
        用 finditer 而不是 search 是这条测试存在的直接原因。"""
        c = {"humanizer": True, "max_we": 5, "ban_contrast_pair": True,
             "allow": [{"text": "AI 不是玩具，是生产工具", "reason": "李默收官演示主线句，已上线"}]}
        text = "AI 不是玩具，是生产工具。这不是一场大会，而是一张桌子。"
        out = A.check(_Ctx(text, c))
        blocking = [m for m in out if not m.startswith("WARN")]
        self.assertEqual(len(blocking), 1, f"应该恰好一条阻断消息，实际: {blocking}")
        self.assertIn("contrast_pair", blocking[0])
        self.assertNotIn("bushi_shi_no_er", blocking[0])  # 阻断的是另一句，不是被豁免的那句

    def test_stale_allow_entry_is_inert_but_warns(self):
        """allow 条目的文字在页面上根本没出现——不能因为一条过期豁免就让
        构建失败，但要报 WARN 提醒清理，不能悄悄失效。"""
        c = {"humanizer": True, "max_we": 5, "ban_contrast_pair": True,
             "allow": [{"text": "这句话页面上根本没有", "reason": "占位测试"}]}
        out = A.check(_Ctx("一句完全正常、不触发任何规则的文案。", c))
        self.assertTrue(any(m.startswith("WARN") and "过期" in m for m in out))
        # 陈旧条目本身不产生阻断消息
        self.assertFalse(any(not m.startswith("WARN") for m in out))

    def test_empty_allow_behaves_exactly_like_before(self):
        """allow 缺省/为空：行为和没有这个机制之前完全一致（回归锚点）。"""
        out_default = A.check(_Ctx("这不是一场大会，而是一张桌子。"))
        c_explicit_empty = {"humanizer": True, "max_we": 5, "ban_contrast_pair": True, "allow": []}
        out_explicit = A.check(_Ctx("这不是一场大会，而是一张桌子。", c_explicit_empty))
        self.assertEqual(out_default, out_explicit)
        self.assertTrue(any("contrast_pair" in m and not m.startswith("WARN") for m in out_default))

    def test_quoted_we_not_counted_in_limit(self):
        """引用内的我们不应计入频率限制。"""
        # 引用内10个我们 + 引用外2个我们 = 总共12个
        # 但引用外只有2个，不超过限制5
        text = ("参与者说「" + "我们" * 10 + "」。" + "我们" * 2 + "继续前进。")
        out = A.check(_Ctx(text))
        # 不应该有任何关于我们的消息（既不阻断也不WARN）
        self.assertFalse(any("我们" in m for m in out))
