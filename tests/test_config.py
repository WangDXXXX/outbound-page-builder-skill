import sys, tempfile, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import config as C

YAML = """
page: page.html
genre: invite
facts: facts.json
quotes: quotes.json
corpus: ["absorb/**/*.txt"]
numbers:
  require_caption: true
blacklist:
  extra: ["融中心"]
copy:
  max_we: 5
must_contain: ["8 月 1 日"]
asset_hosts: ["magic-builder.tos-cn-beijing.volces.com"]
"""

def _w(text, name="assert.yaml"):
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / name
    p.write_text(text, encoding="utf-8")
    return str(p)

class TestConfig(unittest.TestCase):
    def test_loads_and_resolves_paths_relative_to_config(self):
        c = C.load_config(_w(YAML))
        self.assertEqual(c.genre, "invite")
        self.assertTrue(c.facts_path.endswith("facts.json"))
        self.assertTrue(pathlib.Path(c.facts_path).is_absolute())

    def test_defaults_applied(self):
        c = C.load_config(_w(YAML))
        self.assertEqual(c.link_check, "browser")
        self.assertTrue(c.numbers["auto_whitelist_from_facts"])
        self.assertTrue(c.copy["humanizer"])
        self.assertTrue(c.copy["ban_contrast_pair"])
        self.assertEqual(c.blacklist["exempt_zones"], ["「」"])

    def test_campaign_genre_accepted(self):
        """genre: campaign 必须被接受——campaign 是 build/skeleton.py 里已注册的
        体裁（SKILL.md 体裁路由表已经在文档层承诺了这条路径），verify 层的
        GENRES 若不同步收录，外部用户照着文档给 campaign 复盘跑 verify 会
        在这里直接 ConfigError 撞墙，例子见 example/demo-campaign。"""
        c = C.load_config(_w(YAML.replace("genre: invite", "genre: campaign")))
        self.assertEqual(c.genre, "campaign")

    def test_unknown_genre_raises(self):
        with self.assertRaises(C.ConfigError):
            C.load_config(_w(YAML.replace("genre: invite", "genre: poster")))

    def test_missing_required_key_raises(self):
        with self.assertRaises(C.ConfigError):
            C.load_config(_w(YAML.replace("page: page.html\n", "")))

    # 测试 null 值拒绝
    def test_null_in_numbers_dict_raises(self):
        """numbers 某键为 null 应拒绝"""
        bad_yaml = YAML.replace("require_caption: true", "auto_whitelist_from_facts: null")
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("null", str(e.exception))

    def test_null_in_blacklist_dict_raises(self):
        """blacklist 某键为 null 应拒绝"""
        bad_yaml = YAML.replace("extra: [\"融中心\"]", "base: null")
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("null", str(e.exception))

    def test_null_in_copy_dict_raises(self):
        """copy 某键为 null 应拒绝"""
        bad_yaml = YAML.replace("max_we: 5", "humanizer: null")
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("null", str(e.exception))

    # 测试非列表值作为列表字段
    def test_corpus_as_string_raises(self):
        """corpus 给字符串而非列表应拒绝"""
        bad_yaml = YAML.replace('corpus: ["absorb/**/*.txt"]', 'corpus: absorb/notes.txt')
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望列表", str(e.exception))

    def test_must_contain_as_string_raises(self):
        """must_contain 给字符串而非列表应拒绝"""
        bad_yaml = YAML.replace('must_contain: ["8 月 1 日"]', 'must_contain: 8月1日')
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望列表", str(e.exception))

    def test_link_hosts_as_string_raises(self):
        """link_hosts 给字符串而非列表应拒绝"""
        bad_yaml = YAML + "link_hosts: example.com"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望列表", str(e.exception))

    # 测试列表中非字符串元素
    def test_corpus_with_non_string_elements_raises(self):
        """corpus 列表包含非字符串元素应拒绝"""
        bad_yaml = YAML.replace('corpus: ["absorb/**/*.txt"]', 'corpus: [1, 2]')
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望字符串", str(e.exception))

    def test_must_contain_with_non_string_elements_raises(self):
        """must_contain 列表包含非字符串元素应拒绝"""
        bad_yaml = YAML.replace('must_contain: ["8 月 1 日"]', 'must_contain: [8, 月, 1]')
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望字符串", str(e.exception))

    # 测试非映射作为映射字段
    def test_numbers_as_string_raises(self):
        """numbers 给字符串而非映射应拒绝"""
        bad_yaml = YAML.replace("numbers:\n  require_caption: true", "numbers: oops")
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望映射", str(e.exception))

    def test_blacklist_as_list_raises(self):
        """blacklist 给列表而非映射应拒绝"""
        bad_yaml = YAML.replace("blacklist:\n  extra: [\"融中心\"]", "blacklist: []")
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("期望映射", str(e.exception))

    # 测试 link_check 取值约束
    def test_link_check_invalid_value_raises(self):
        """link_check 取值不在 {browser, curl, skip} 应拒绝"""
        bad_yaml = YAML + "link_check: banana"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("无效", str(e.exception))
        # 确保不含 YAML 布尔提示（这是未知字符串，不是布尔）
        self.assertNotIn("YAML", str(e.exception))

    # 测试 link_check: skip 有效
    def test_link_check_skip_loads(self):
        """link_check: skip 应加载成功"""
        c = C.load_config(_w(YAML + "link_check: skip"))
        self.assertEqual(c.link_check, "skip")

    # 测试 link_check: off 被解析为布尔 False
    def test_link_check_off_boolean_coercion_raises(self):
        """link_check: off 被 YAML 解析为布尔 False，应拒绝并提示用 skip"""
        bad_yaml = YAML + "link_check: off"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("布尔值", str(e.exception))
        self.assertIn("skip", str(e.exception))

    # 测试 link_check: on 被解析为布尔 True
    def test_link_check_on_boolean_coercion_raises(self):
        """link_check: on 被 YAML 解析为布尔 True，应拒绝并提示用 skip"""
        bad_yaml = YAML + "link_check: on"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        self.assertIn("布尔值", str(e.exception))
        self.assertIn("skip", str(e.exception))

    # copy.allow 豁免表：reason 必填，和 blacklist.unban 同一条纪律
    def test_copy_allow_defaults_to_empty(self):
        """没写 copy.allow 时默认空列表——机制默认关闭，行为和今天完全一样。"""
        c = C.load_config(_w(YAML))
        self.assertEqual(c.copy["allow"], [])

    def test_copy_allow_valid_entry_loads(self):
        """text + reason 都给全，应该正常加载并保留字段。"""
        y = YAML + "copy:\n  allow:\n    - text: \"AI 不是玩具，是生产工具\"\n      reason: 李默收官演示主线句\n"
        c = C.load_config(_w(y))
        self.assertEqual(len(c.copy["allow"]), 1)
        self.assertEqual(c.copy["allow"][0]["reason"], "李默收官演示主线句")

    def test_copy_allow_missing_reason_raises(self):
        """allow 条目缺 reason——必须拒绝，不能让豁免悄悄没有理由地生效。"""
        y = YAML + "copy:\n  allow:\n    - text: \"AI 不是玩具，是生产工具\"\n"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(y))
        self.assertIn("reason", str(e.exception))

    def test_copy_allow_blank_reason_raises(self):
        """reason 给了但是空白字符串——同样拒绝，不能用空字符串糊弄过去。"""
        y = YAML + "copy:\n  allow:\n    - text: \"AI 不是玩具，是生产工具\"\n      reason: \"   \"\n"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(y))
        self.assertIn("reason", str(e.exception))

    def test_copy_allow_missing_text_raises(self):
        """allow 条目缺 text——同样拒绝，豁免必须精确指向一句话。"""
        y = YAML + "copy:\n  allow:\n    - reason: 某个理由\n"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(y))
        self.assertIn("text", str(e.exception))

    def test_copy_allow_as_string_raises(self):
        """copy.allow 给字符串而非列表——拒绝。"""
        y = YAML + "copy:\n  allow: \"AI 不是玩具\"\n"
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(y))
        self.assertIn("期望列表", str(e.exception))

    # 测试 link_check: "off" (quoted，所以是字符串)
    def test_link_check_off_quoted_string_raises(self):
        """link_check: "off" (引用后是字符串，但不在允许值中)"""
        bad_yaml = YAML + 'link_check: "off"'
        with self.assertRaises(C.ConfigError) as e:
            C.load_config(_w(bad_yaml))
        # 这应该是"无效"错误，不是布尔错误
        self.assertIn("无效", str(e.exception))
        self.assertNotIn("布尔值", str(e.exception))
