import sys, json, tempfile, unittest, pathlib, os
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import facts as F

GOOD = {"attendance": {"value": 628, "display": "628",
        "caption": "正式名册 609 + 现场登记 19", "source": "roster/final.json",
        "public": True, "verified": True}}

def _w(obj, tc=None):
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(obj, p, ensure_ascii=False); p.close()
    if tc:
        tc.addCleanup(os.unlink, p.name)
    return p.name

class TestFacts(unittest.TestCase):
    def test_loads_good_fact(self):
        d = F.load_facts(_w(GOOD, self))
        self.assertEqual(d["attendance"].display, "628")
        self.assertTrue(d["attendance"].public)

    def test_missing_caption_raises(self):
        bad = {"a": {"value": 1, "display": "1", "source": "x", "public": True, "verified": True}}
        with self.assertRaises(F.FactError) as e:
            F.load_facts(_w(bad, self))
        self.assertIn("caption", str(e.exception))

    def test_missing_source_raises(self):
        bad = {"a": {"value": 1, "display": "1", "caption": "c", "public": True, "verified": True}}
        with self.assertRaises(F.FactError):
            F.load_facts(_w(bad, self))

    def test_public_defaults_false_when_absent(self):
        d = F.load_facts(_w({"a": {"value": 1, "display": "1", "caption": "c",
                                   "source": "s", "verified": True}}, self))
        self.assertFalse(d["a"].public)

    def test_quote_requires_why_picked(self):
        bad = [{"id": "q1", "text": "t", "speaker": "s", "source_file": "f"}]
        with self.assertRaises(F.FactError) as e:
            F.load_quotes(_w(bad, self))
        self.assertIn("why_picked", str(e.exception))

    def test_value_zero_loads_successfully(self):
        """零值是合法的——0起事故等场景"""
        good = {"incidents": {"value": 0, "display": "0", "caption": "零重大事故", "source": "log.json"}}
        d = F.load_facts(_w(good, self))
        self.assertEqual(d["incidents"].value, 0)

    def test_empty_display_raises(self):
        """display 为空字符串必须拒绝"""
        bad = {"a": {"value": 1, "display": "", "caption": "c", "source": "s"}}
        with self.assertRaises(F.FactError) as e:
            F.load_facts(_w(bad, self))
        self.assertIn("display", str(e.exception))

    def test_empty_caption_raises(self):
        """caption 为空字符串必须拒绝——数字自证意义靠它"""
        bad = {"a": {"value": 1, "display": "1", "caption": "", "source": "s"}}
        with self.assertRaises(F.FactError) as e:
            F.load_facts(_w(bad, self))
        self.assertIn("caption", str(e.exception))

    def test_empty_why_picked_raises(self):
        """why_picked 为空字符串必须拒绝"""
        bad = [{"id": "q1", "text": "t", "speaker": "s", "source_file": "f", "why_picked": ""}]
        with self.assertRaises(F.FactError) as e:
            F.load_quotes(_w(bad, self))
        self.assertIn("why_picked", str(e.exception))

    def test_malformed_json_raises_with_parse_error(self):
        """malformed JSON 必须报"不是合法 JSON"而不是顶层类型错误"""
        import shutil
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        p = tmpdir / "x.json"
        p.write_text("{bad json,,,", encoding="utf-8")
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        with self.assertRaises(F.FactError) as e:
            F.load_facts(str(p))
        self.assertIn("不是合法 JSON", str(e.exception))

    def test_facts_with_array_raises_with_shape_error(self):
        """facts.json 为数组而非对象必须报顶层类型错误"""
        import shutil
        bad = [{"value": 1}]
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        p = tmpdir / "x.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        with self.assertRaises(F.FactError) as e:
            F.load_facts(str(p))
        self.assertIn("顶层必须是对象", str(e.exception))
        self.assertNotIn("不是合法 JSON", str(e.exception))

    def test_quotes_with_object_raises_with_shape_error(self):
        """quotes.json 为对象而非数组必须报顶层类型错误"""
        import shutil
        bad = {"id": "q1"}
        tmpdir = pathlib.Path(tempfile.mkdtemp())
        p = tmpdir / "x.json"
        p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        with self.assertRaises(F.FactError) as e:
            F.load_quotes(str(p))
        self.assertIn("顶层必须是数组", str(e.exception))
        self.assertNotIn("不是合法 JSON", str(e.exception))

    def test_caption_null_raises(self):
        """caption: null 必须拒绝"""
        bad = {"a": {"value": 1, "display": "1", "caption": None, "source": "s"}}
        with self.assertRaises(F.FactError) as e:
            F.load_facts(_w(bad, self))
        self.assertIn("caption", str(e.exception))

    def test_source_as_list_raises(self):
        """source 为容器类型必须拒绝"""
        bad = {"a": {"value": 1, "display": "1", "caption": "c", "source": []}}
        with self.assertRaises(F.FactError) as e:
            F.load_facts(_w(bad, self))
        self.assertIn("source", str(e.exception))

    def test_display_as_number_loads(self):
        """display 为数字时应转换为字符串"""
        good = {"a": {"value": 1, "display": 628, "caption": "c", "source": "s"}}
        d = F.load_facts(_w(good, self))
        self.assertEqual(d["a"].display, "628")

    def test_value_null_raises(self):
        """value: null 必须拒绝——null 表示无值"""
        bad = {"a": {"value": None, "display": "1", "caption": "c", "source": "s"}}
        with self.assertRaises(F.FactError) as e:
            F.load_facts(_w(bad, self))
        self.assertIn("value", str(e.exception))

    def test_value_empty_string_loads(self):
        """value: "" 是合法的——空字符串是一个被选择的值"""
        good = {"a": {"value": "", "display": "空", "caption": "c", "source": "s"}}
        d = F.load_facts(_w(good, self))
        self.assertEqual(d["a"].value, "")

    def test_value_false_loads(self):
        """value: False 是合法的——布尔假值是被选择的值"""
        good = {"a": {"value": False, "display": "否", "caption": "c", "source": "s"}}
        d = F.load_facts(_w(good, self))
        self.assertIs(d["a"].value, False)

    def test_why_picked_null_raises(self):
        """quote why_picked: null 必须拒绝"""
        bad = [{"id": "q1", "text": "t", "speaker": "s", "source_file": "f", "why_picked": None}]
        with self.assertRaises(F.FactError) as e:
            F.load_quotes(_w(bad, self))
        self.assertIn("why_picked", str(e.exception))
