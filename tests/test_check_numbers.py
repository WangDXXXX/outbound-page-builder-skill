import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.checks import numbers as N
from opb.facts import Fact

def _f(key, display, caption="c", public=True):
    return Fact(key=key, value=display, display=display, caption=caption,
                source="s", decided_by=None, compare_to=None,
                public=public, verified=True)

class _Ctx:
    def __init__(self, text, facts, cfg_numbers=None):
        self.text = text
        self.facts = facts
        class C: pass
        self.cfg = C()
        self.cfg.numbers = cfg_numbers or {
            "auto_whitelist_from_facts": True, "require_caption": True,
            "ignore": [r"\d{1,2}", r"\d{4}\.\d{2}\.\d{2}", r"\d{4}-\d{2}-\d{2}", r"\d{4}/\d{2}/\d{2}"]}

class TestNumberCheck(unittest.TestCase):
    def test_whitelisted_from_facts_passes(self):
        self.assertEqual(N.check(_Ctx("到场 628 人", {"a": _f("a", "628")})), [])

    def test_thousand_separator_matches(self):
        """逗号归一化：页面 1,095 应该匹配 fact 中的 1095。"""
        self.assertEqual(N.check(_Ctx("报名 1,095 人", {"a": _f("a", "1095")})), [])

    def test_thousand_separator_reverse_matches(self):
        """逗号归一化反向：页面 1095 应该匹配 fact 中的 1,095。"""
        self.assertEqual(N.check(_Ctx("报名 1095 人", {"a": _f("a", "1,095")})), [])

    def test_unlisted_number_fails(self):
        out = N.check(_Ctx("到场 999 人", {"a": _f("a", "628")}))
        self.assertEqual(len(out), 1)
        self.assertIn("999", out[0])

    def test_small_numbers_ignored(self):
        self.assertEqual(N.check(_Ctx("第 3 组，共 12 人", {})), [])

    def test_non_public_fact_on_page_fails(self):
        """非公开的长数字（超过1位数）在页面上应该拒绝。"""
        out = N.check(_Ctx("投票 600 票", {"v": _f("v", "600", public=False)}))
        self.assertTrue(any("public:false" in m for m in out))

    def test_non_public_short_number_ignored(self):
        """非公开的短数字（1-2位）被忽略列表保护，不应该拒绝。"""
        # 页面上的「3」不应该因为有非公开的「3」就被拒绝
        self.assertEqual(N.check(_Ctx("第 3 组", {"v": _f("v", "3", public=False)})), [])

    def test_missing_caption_fails_when_required(self):
        out = N.check(_Ctx("到场 628 人", {"a": _f("a", "628", caption="")}))
        self.assertTrue(any("caption" in m for m in out))

    def test_percentage_with_unit_passes(self):
        """百分比数字：fact 中是 95.8%，页面中也是 95.8%，应该通过。"""
        self.assertEqual(N.check(_Ctx("满意度 95.8%", {"a": _f("a", "95.8%")})), [])

    def test_percentage_unit_stripped_from_fact(self):
        """百分比单位去除：fact 是 95.8%，页面只有 95.8，应该通过（因为归一化了）。"""
        self.assertEqual(N.check(_Ctx("满意度 95.8", {"a": _f("a", "95.8%")})), [])

    def test_plus_sign_stripped_from_fact(self):
        """+符号去除：fact 是 106+，页面是 106+，应该通过。"""
        self.assertEqual(N.check(_Ctx("增长 106+", {"a": _f("a", "106+")})), [])

    def test_unlisted_percentage_fails(self):
        """未授权的百分比：页面 77.7% 不在 facts 中，应该拒绝。"""
        out = N.check(_Ctx("满意度 77.7%", {"a": _f("a", "95.8%")}))
        self.assertEqual(len(out), 1)
        self.assertIn("77.7", out[0])

    def test_dash_separated_date_ignored(self):
        """日期忽略规则：2026-07-29 格式应该被忽略。"""
        self.assertEqual(N.check(_Ctx("活动日期 2026-07-29", {})), [])

    def test_slash_separated_date_ignored(self):
        """日期忽略规则：2026/07/29 格式应该被忽略。"""
        self.assertEqual(N.check(_Ctx("活动日期 2026/07/29", {})), [])

    def test_bare_year_requires_whitelist(self):
        """年份要求白名单：删除 20\d{2} 规则后，2026 需要 fact 白名单授权。"""
        out = N.check(_Ctx("2026 年工作", {}))
        self.assertEqual(len(out), 1)
        self.assertIn("2026", out[0])

    def test_implausible_year_fails(self):
        """不合理的年份：9999 不是 20xx 格式，应该拒绝。"""
        out = N.check(_Ctx("年份 9999", {}))
        self.assertEqual(len(out), 1)
        self.assertIn("9999", out[0])

    def test_confidentiality_bypass_2074_fails(self):
        """回归测试：非公开的 2074（如B 站次群消息数）必须被拒绝，不能被 20xx 规则绕过。"""
        out = N.check(_Ctx("群消息 2074 条", {"msgs": _f("msgs", "2074", public=False)}))
        self.assertEqual(len(out), 1)
        self.assertIn("public:false", out[0])
        self.assertIn("2074", out[0])

    def test_confidentiality_bypass_2074_with_default_ignore(self):
        """回归测试：使用默认 ignore 规则，非公开 2074 仍然必须被拒绝。"""
        # 即使有默认的 ignore 规则，public:false 检查不应该被绕过
        out = N.check(_Ctx("群消息 2074 条", {"msgs": _f("msgs", "2074", public=False)}))
        self.assertTrue(len(out) > 0)
        self.assertTrue(any("public:false" in m for m in out))

    def test_bare_form_collision_public_wins(self):
        """回归测试：public 的 106 和 non-public 的 106% 共享裸形式 106。
        页面中的 106 应该通过（public fact 显式发布了这个数）。"""
        self.assertEqual(N.check(_Ctx("自发笔记 106 篇", {
            "notes": _f("notes", "106", public=True),
            "secret": _f("secret", "106%", public=False)
        })), [])

    def test_dot_separated_date_ignored(self):
        """日期忽略规则：2026.07.29 格式应该被忽略。"""
        self.assertEqual(N.check(_Ctx("会议日期 2026.07.29", {})), [])

    def test_full_date_tokens_not_split(self):
        """日期作为单个 token 提取：2026-07-29 不应该分裂成 2026、07、29。"""
        # 如果正确，2026-07-29 整体匹配 \d{4}-\d{2}-\d{2}，所以通过
        # 如果错误（分裂），2026 会被认为是未授权数字
        self.assertEqual(N.check(_Ctx("活动时间 2026-07-29", {})), [])

    def test_bare_4digit_without_whitelist_fails(self):
        """2074 作为独立年份，没有 fact 白名单时应该拒绝。"""
        out = N.check(_Ctx("2074 年的数据", {}))
        self.assertEqual(len(out), 1)
        self.assertIn("2074", out[0])

    def test_confidential_date_not_exempted_by_ignore(self):
        """【关键】非公开日期不应该被 ignore 规则豁免。
        这是 check() 顺序的负载承载测试：公开 → 非公开 → ignore。
        如果 ignore 在 non_public 之前运行，机密日期会被豁免而通过。"""
        out = N.check(_Ctx("下次活动 2026-07-29", {
            "event_date": _f("event_date", "2026-07-29", public=False)
        }))
        self.assertEqual(len(out), 1)
        self.assertIn("public:false", out[0])
        self.assertIn("event_date", out[0])

    def test_non_confidential_date_still_ignored(self):
        """非机密日期仍然被 ignore 规则豁免（验证规则本身有效）。
        确保 test_confidential_date_not_exempted_by_ignore 不是通过删除
        ignore 规则而通过的。"""
        # 页面中的日期，但没有任何 fact 声明
        self.assertEqual(N.check(_Ctx("下次活动 2026-07-29", {})), [])

    # ── 中文日期"N年"上下文豁免（Task 15 F4）───────────────
    def test_chinese_date_year_no_space_ignored(self):
        """核心修复：中文日期写法"2026年7月25日"（年字紧贴数字，无空格）
        不应该要求 fact 白名单——这是本次真实撞到的 bug（改成
        "2026.07.25"才不报错，但中文战报几乎必然写"2026年7月25日"）。"""
        self.assertEqual(N.check(_Ctx("活动定在 2026年7月25日 举行。", {})), [])

    def test_chinese_bare_year_no_space_ignored(self):
        """"2026年"（不接完整月日）单独出现也应该被豁免。"""
        self.assertEqual(N.check(_Ctx("这是 2026年 的第二届大会。", {})), [])

    def test_chinese_date_year_with_space_still_requires_whitelist(self):
        """精确边界：数字和"年"字之间有空格时不豁免——这不是新引入的行为，
        是既有的 test_bare_year_requires_whitelist/
        test_bare_4digit_without_whitelist_fails 已经钉死的行为（它们的
        输入都带空格），这里显式再断言一次，把"为什么没有做成 \\d{4}|
        19\\d{2}|20\\d{2} 这种全局 ignore 正则"的边界原因用一条测试锁住：
        全局正则会让任何形似年份的裸数字都免检，这条测试的场景会先变红。"""
        out = N.check(_Ctx("2026 年工作", {}))
        self.assertEqual(len(out), 1)
        self.assertIn("2026", out[0])

    def test_chinese_year_confidentiality_not_bypassed(self):
        """回归：public:false 的数字即使在文本里恰好长得像"N年"上下文，
        也必须先被 non_public 拦下，不能被这条新豁免绕过——precedence 与
        既有的 confidential_date_not_exempted_by_ignore 是同一条原则。"""
        out = N.check(_Ctx("活动办了 2074年 了。",
                           {"secret": _f("secret", "2074", public=False)}))
        self.assertEqual(len(out), 1)
        self.assertIn("public:false", out[0])
        self.assertIn("2074", out[0])

    def test_confidential_short_number_unregistered(self):
        """非公开短数字（1-2位）未被注册，所以不会被拒绝。
        这验证了 ≥3 位注册规则是正确的短数字保护（不依赖 ignore）。"""
        # 页面中的「第 7 组」，非公开 fact 有 7，但 7 因为是短数字而未注册
        self.assertEqual(N.check(_Ctx("第 7 组", {"group": _f("group", "7", public=False)})), [])
