import sys, unittest, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import blacklist as B

class TestBlacklist(unittest.TestCase):
    def test_base_terms_present_for_any_genre(self):
        self.assertIn("复盘", B.build("invite", [], []))
        self.assertIn("复盘", B.build("recap", [], []))

    def test_genre_terms_only_in_own_genre(self):
        self.assertIn("首届", B.build("invite", [], []))
        self.assertNotIn("首届", B.build("recap", [], []))
        self.assertIn("B1", B.build("recap", [], []))
        self.assertNotIn("B1", B.build("invite", [], []))

    def test_extra_terms_appended(self):
        self.assertIn("融中心", B.build("invite", ["融中心"], []))

    # ── staff_names（Task 15 F1）───────────────────────────
    def test_staff_names_merged_into_output(self):
        """staff_names 必须真正合并进 build() 返回的词表，不能只是被接收
        但从不出现——这是 F1 的核心修复：之前 staff_names 从未传进 build()，
        填了名单也不会出现在这里。"""
        out = B.build("recap", [], [], staff_names=["李默", "老默"])
        self.assertIn("李默", out)
        self.assertIn("老默", out)

    def test_staff_names_absent_when_not_given(self):
        """默认参数（不传 staff_names）行为不变，向后兼容。"""
        out = B.build("recap", [], [])
        self.assertNotIn("李默", out)

    def test_staff_names_share_unban_channel_with_reason(self):
        """coordinator 裁定：允许豁免一个组委姓名，但必须写 reason——和其他
        unban 条目走同一套纪律，不是姓名类目享有特殊待遇。"""
        out = B.build("invite", [], [{"term": "李默", "reason": "讲者本人姓名"}],
                      staff_names=["李默"])
        self.assertNotIn("李默", out)

    def test_staff_names_unban_without_reason_raises(self):
        """姓名走 unban 时同样必须写 reason，不能因为是姓名类目就放宽。"""
        with self.assertRaises(B.UnbanError) as e:
            B.build("recap", [], [{"term": "李默"}], staff_names=["李默"])
        self.assertIn("reason", str(e.exception))

    def test_staff_names_deduped_with_extra(self):
        """如果同一个词既出现在 extra 又出现在 staff_names（配置重复），
        去重逻辑对两者一视同仁，输出里只留一份。"""
        out = B.build("recap", ["李默"], [], staff_names=["李默"])
        self.assertEqual(out.count("李默"), 1)

    def test_unban_removes_term(self):
        out = B.build("invite", ["王李默"], [{"term": "王李默", "reason": "讲者本人姓名"}])
        self.assertNotIn("王李默", out)

    def test_unban_without_reason_raises(self):
        with self.assertRaises(B.UnbanError) as e:
            B.build("invite", [], [{"term": "复盘"}])
        self.assertIn("reason", str(e.exception))

    # 测试 unban 中 term 缺失
    def test_unban_without_term_raises(self):
        """unban 缺 term 应拒绝"""
        with self.assertRaises(B.UnbanError) as e:
            B.build("invite", [], [{"reason": "某原因"}])
        self.assertIn("term", str(e.exception))

    # 测试 unban 中 reason 为空或仅空白
    def test_unban_with_whitespace_only_reason_raises(self):
        """unban reason 为空或仅空白应拒绝"""
        with self.assertRaises(B.UnbanError) as e:
            B.build("invite", ["王李默"], [{"term": "王李默", "reason": "   "}])
        self.assertIn("reason", str(e.exception))

    # 测试 unban 中 reason 为非字符串
    def test_unban_with_non_string_reason_raises(self):
        """unban reason 应为字符串"""
        with self.assertRaises(B.UnbanError) as e:
            B.build("invite", [], [{"term": "复盘", "reason": 123}])
        self.assertIn("reason", str(e.exception))

    # 测试 unban 中 term 为非字符串
    def test_unban_with_non_string_term_raises(self):
        """unban term 应为字符串"""
        with self.assertRaises(B.UnbanError) as e:
            B.build("invite", [], [{"term": 123, "reason": "某原因"}])
        self.assertIn("term", str(e.exception))

    # 测试注释剥离：完整的四行fixture
    def test_read_with_fixture_covers_all_line_shapes(self):
        """测试 _read() 正确处理：正常词、缩进注释、词后注释、顶格注释"""
        # 创建临时目录和fixture文件
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        fixture_path = pathlib.Path(tmpdir.name) / "jargon_test.txt"
        fixture_path.write_text(
            "正常词\n"
            "  # 缩进注释\n"
            "词后注释  # 这段要被截掉\n"
            "# 顶格注释\n",
            encoding="utf-8"
        )

        # 临时替换 _DATA 指向临时目录
        orig_data = B._DATA
        try:
            B._DATA = pathlib.Path(tmpdir.name)
            result = B._read("jargon_test.txt")
        finally:
            B._DATA = orig_data

        # 验证：正常词应在列表中
        self.assertIn("正常词", result)

        # 验证：词后注释应在列表中，但没有尾部注释
        self.assertIn("词后注释", result)
        self.assertNotIn("词后注释  # 这段要被截掉", result)

        # 验证：不含任何注释文本
        self.assertNotIn("# 缩进注释", result)
        self.assertNotIn("# 顶格注释", result)
        self.assertNotIn("这段要被截掉", result)

        # 验证：不含空字符串
        self.assertNotIn("", result)

    # 测试 unban 非映射条目
    def test_unban_non_mapping_entry_raises(self):
        """unban 条目是字符串而非对象应拒绝"""
        with self.assertRaises(B.UnbanError) as e:
            B.build("invite", [], ["复盘"])
        self.assertIn("对象", str(e.exception))
        self.assertIn("str", str(e.exception))
        self.assertIn("第 0 项", str(e.exception))
