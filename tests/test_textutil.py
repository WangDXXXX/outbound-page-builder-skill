import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import textutil as T

class TestTextUtil(unittest.TestCase):
    def test_strip_html_removes_script_style_tags_and_unescapes(self):
        h = '<style>a{color:red}</style><script>var x=1</script><p>你好&amp;世界</p>'
        self.assertEqual(T.strip_html(h).split(), ["你好&世界"])

    def test_norm_removes_all_whitespace(self):
        self.assertEqual(T.norm(" 高质量的\n 会议 "), "高质量的会议")

    def test_strip_quoted_removes_quote_zones(self):
        out = T.strip_quoted("他说「内部口径」然后走了")
        self.assertNotIn("内部口径", out)
        self.assertIn("然后走了", out)
