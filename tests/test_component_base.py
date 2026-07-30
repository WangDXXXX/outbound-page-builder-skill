import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.components import base as B

def _mk(name="demo", modes=("web", "longpic")):
    return B.Component(
        name=name, slots=("title",), css=".demo{color:var(--fg)}",
        render=lambda d, m: f'<p class="demo">{B.esc(d["title"])}·{m}</p>', modes=modes)

class TestComponentBase(unittest.TestCase):
    def setUp(self):
        self._saved_registry = dict(B._REGISTRY)
        B._REGISTRY.clear()

    def tearDown(self):
        B._REGISTRY.clear()
        B._REGISTRY.update(self._saved_registry)

    def test_register_and_get(self):
        c = _mk(); B.register(c)
        self.assertIs(B.get("demo"), c)

    def test_duplicate_registration_raises(self):
        B.register(_mk())
        with self.assertRaises(B.ComponentError):
            B.register(_mk())

    def test_unknown_component_raises(self):
        with self.assertRaises(B.ComponentError):
            B.get("nope")

    def test_render_passes_mode(self):
        B.register(_mk())
        self.assertIn("·longpic", B.render("demo", {"title": "x"}, "longpic"))

    def test_missing_slot_raises_before_render(self):
        B.register(_mk())
        with self.assertRaises(B.SlotMissing) as e:
            B.render("demo", {}, "web")
        self.assertIn("title", str(e.exception))

    def test_unsupported_mode_raises(self):
        B.register(_mk(modes=("web",)))
        with self.assertRaises(B.ModeUnsupported):
            B.render("demo", {"title": "x"}, "longpic")

    def test_escapes_user_data(self):
        B.register(_mk())
        out = B.render("demo", {"title": "<script>x</script>"}, "web")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_collect_css_dedupes_and_preserves_order(self):
        B.register(_mk("a")); B.register(_mk("b"))
        css = B.collect_css(["b", "a", "b"])
        self.assertEqual(css.count(".demo{color:var(--fg)}"), 2)
