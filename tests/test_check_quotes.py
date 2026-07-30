import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.checks import quotes as Q

class _Ctx:
    def __init__(self, text, corpus):
        self.text = text
        self.corpus = corpus

class TestQuoteCheck(unittest.TestCase):
    def test_exact_substring_passes(self):
        ctx = _Ctx("他说「给我们来个在线的呢也中」", "有人问 给我们来个在线的呢也中 好不好")
        self.assertEqual(Q.check(ctx), [])

    def test_whitespace_normalised_before_match(self):
        ctx = _Ctx("他说「高质量的 会议」", "这是一场\n高质量的会议")
        self.assertEqual(Q.check(ctx), [])

    def test_trailing_period_tolerated(self):
        ctx = _Ctx("他说「高质量的会议。」", "这是一场高质量的会议")
        self.assertEqual(Q.check(ctx), [])

    def test_paraphrase_fails(self):
        ctx = _Ctx("他说「这是一场质量很高的会议」", "这是一场高质量的会议")
        self.assertEqual(len(Q.check(ctx)), 1)

    def test_short_quotes_below_8_chars_skipped(self):
        ctx = _Ctx("他说「很好」", "无关语料")
        self.assertEqual(Q.check(ctx), [])

    def test_nested_quotes_fabricated_sentence_fails(self):
        """嵌套引号：页面内层「」是空的，完整引号包含编造的长句子。"""
        ctx = _Ctx("页面:  「abc「」这是一句完全编造的话没在语料里」",
                   "abc")
        failures = Q.check(ctx)
        self.assertEqual(len(failures), 1)
        self.assertIn("引用未命中语料", failures[0])

    def test_nested_quotes_legitimate_full_span_passes(self):
        """嵌套引号：完整引号在语料中。"""
        ctx = _Ctx("他说「主编说过「好文章」的话我记了很久」",
                   "主编说过「好文章」的话我记了很久")
        self.assertEqual(Q.check(ctx), [])

    def test_nested_quotes_fabricated_tail_fails(self):
        """嵌套引号：前缀在语料里，但尾部编造的内容不在。"""
        ctx = _Ctx("他说「主编说过「好文章」后来又说了很多其他的话」",
                   "主编说过「好文章」的话")
        failures = Q.check(ctx)
        self.assertEqual(len(failures), 1)

    def test_unbalanced_opening_quote_fails(self):
        """不平衡的「：缺少配对的 」。"""
        ctx = _Ctx("他说「这是一句没有结束的长引用，超过八个字", "语料无关")
        failures = Q.check(ctx)
        self.assertEqual(len(failures), 1)
        self.assertIn("不平衡", failures[0])

    def test_unbalanced_closing_quote_fails(self):
        """不平衡的 」：多出的 」。"""
        ctx = _Ctx("他说「正常的引用」还有」多出来的", "正常的引用")
        failures = Q.check(ctx)
        # 「正常的引用」通过，但 」 多出来应该报错
        self.assertTrue(any("不平衡" in m for m in failures))
