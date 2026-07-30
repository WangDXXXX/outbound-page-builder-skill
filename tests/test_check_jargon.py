import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.checks import jargon as J
from opb.blacklist import build as build_blacklist
from opb.textutil import strip_quoted

class _Ctx:
    def __init__(self, text, bl, genre="invite", staff=None):
        self.text = text
        self.text_noquote = strip_quoted(text)
        self.blacklist = bl
        class C: pass
        self.cfg = C(); self.cfg.genre = genre
        self.cfg.blacklist = {"staff_names": staff or []}

def _staff_ctx(text, genre, staff_names, unban=None):
    """构造一个"staff_names 真的走过 blacklist.build() 合并"的 ctx——
    不能像 _Ctx 默认那样把 ctx.blacklist 和 cfg.blacklist.staff_names 分开
    手写，那样测的是"如果它们碰巧一致会怎样"，测不出 F1 那种"填了名单
    但从未真正合并进扫描词表"的回归。"""
    bl = build_blacklist(genre, [], unban or [], staff_names)
    return _Ctx(text, bl, genre=genre, staff=staff_names)

class TestJargon(unittest.TestCase):
    def test_blacklisted_term_fails(self):
        out = J.check(_Ctx("本次复盘结论如下", ["复盘"]))
        self.assertTrue(any("复盘" in m for m in out))

    def test_term_inside_quote_zone_is_exempt(self):
        self.assertEqual(J.check(_Ctx("他说「我们内部复盘过」", ["复盘"])), [])

    def test_clean_text_passes(self):
        self.assertEqual(J.check(_Ctx("8 月 1 日，上海见。", ["复盘"])), [])

    def test_recap_without_staff_names_warns(self):
        out = J.check(_Ctx("现场很热闹", [], genre="recap", staff=[]))
        self.assertTrue(any("staff_names" in m and m.startswith("WARN") for m in out))

    # ── staff_names 真实入扫描（Task 15 F1）────────────────
    def test_staff_name_on_page_is_blocking_finding_naming_it(self):
        """核心回归：组委姓名出现在正文里必须是硬失败（非 WARN），且消息里
        点名是哪个姓名——这是 F1 的关键测试，见下方 mutation-verify。"""
        ctx = _staff_ctx("活动由李默统筹策划，现场氛围热烈。", "recap", ["李默", "老默"])
        out = J.check(ctx)
        hard = [m for m in out if not m.startswith("WARN")]
        self.assertTrue(any("李默" in m for m in hard),
                        f"页面正文含组委姓名「李默」，必须产生一条点名它的非 WARN 发现，实际: {out}")

    def test_staff_name_inside_quote_zone_is_exempt(self):
        """与层3既有的引用豁免规则一致：「」内的姓名不拦（例如参会者原声
        里恰好提到组委，逐字引用不能因为撞上人名黑名单就被拦或被迫改写）。"""
        ctx = _staff_ctx("参会者说：「感谢李默团队的努力」", "recap", ["李默", "老默"])
        self.assertEqual(J.check(ctx), [])

    def test_staff_name_unban_with_reason_is_allowed(self):
        """unban 带 reason 可以豁免一个组委姓名（例如邀请函里的讲者本人）。"""
        ctx = _staff_ctx("主持人王李默（老默）压轴登场。", "invite", ["李默"],
                         unban=[{"term": "李默", "reason": "讲者本人姓名，邀请函必需"}])
        self.assertEqual(J.check(ctx), [])

    def test_empty_staff_names_on_recap_is_warn_only(self):
        """空 staff_names 在 recap 体裁下仍然只报 WARN，不因为 F1 修复
        变成硬失败——这条规则本来就该是提醒性质，不是靠"名单必须非空"
        这件事本身去拦页面。"""
        ctx = _staff_ctx("现场很热闹，大家都很开心。", "recap", [])
        out = J.check(ctx)
        self.assertTrue(all(m.startswith("WARN") for m in out), out)
        self.assertTrue(any("staff_names" in m for m in out))
