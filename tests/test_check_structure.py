import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.checks import structure as S

class _Ctx:
    def __init__(self, html, must=()):
        self.html = html
        self.text = html
        class C: pass
        self.cfg = C(); self.cfg.must_contain = list(must)

class TestStructure(unittest.TestCase):
    def test_unreplaced_placeholder_fails(self):
        self.assertTrue(any("占位符" in m for m in S.check(_Ctx("<p>{{name}}</p>"))))

    def test_missing_must_contain_fails(self):
        out = S.check(_Ctx("<p>hello</p>", ["8 月 1 日"]))
        self.assertTrue(any("必备元素缺失" in m for m in out))

    def test_present_must_contain_passes(self):
        self.assertEqual(S.check(_Ctx("<p>8 月 1 日</p>", ["8 月 1 日"])), [])

    def test_svg_without_explicit_width_fails(self):
        out = S.check(_Ctx('<svg viewBox="0 0 10 10"></svg>'))
        self.assertTrue(any("svg" in m.lower() and "width" in m for m in out))

    def test_svg_with_width_passes(self):
        self.assertEqual(S.check(_Ctx('<svg width="104" viewBox="0 0 10 10"></svg>')), [])

    def test_css_braces_do_not_trigger_placeholder_warning(self):
        # CSS 中的大括号不应该被识别为占位符
        html = '<style>body { color: red; }</style>'
        self.assertEqual(S.check(_Ctx(html)), [])

    def test_javascript_braces_do_not_trigger_placeholder_warning(self):
        # JavaScript 中的大括号不应该被识别为占位符
        html = '<script>const obj = { key: "value" };</script>'
        self.assertEqual(S.check(_Ctx(html)), [])

if __name__ == "__main__":
    unittest.main()
