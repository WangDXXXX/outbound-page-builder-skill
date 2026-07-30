import sys, tempfile, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import theme as T

CIRIDAE_VARS = """:root {
  --color-ember-rust: #cc6437;
  --color-void-black: #0b0b0b;
  --color-charcoal-surface: #272a2a;
  --color-bone: #edebe7;
  --color-pure-white: #ffffff;
  --color-abyss: #050505;
  --color-steel: #484848;
  --color-ash: #cecece;
  --font-pragmatica: 'Pragmatica', sans-serif;
  --font-roboto-mono: 'Roboto Mono', monospace;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}"""

DOPE_VARS = """:root {
  --color-near-black: #090909;
  --color-almost-white: #f7f9fa;
  --color-soft-white: #f0f0f0;
  --color-steel: #828384;
  --color-graphite: #423738;
  --color-signal-violet: #af50ff;
  --color-lavender-mist: #e1bdff;
  --font-whyte-inktrap: 'Whyte Inktrap', sans-serif;
  --font-whyte-mono: 'Whyte Inktrap Mono', monospace;
  --radius-lg: 8px;
}"""

SYNTHETIC_VARS = """:root {
  --color-a: #010101;
  --color-b: #fafafa;
  --color-c: #cc3300;
  --color-d: #404040;
  --color-e: #e0e0e0;
}"""

LATIN_ONLY_VARS = """:root {
  --color-bg: #0a0a0a;
  --color-panel: #1e1e1e;
  --color-fg: #fafafa;
  --color-muted: #9a9a9a;
  --color-accent: #227744;
  --font-display: 'Helvetica Neue', Arial, sans-serif;
}"""

def _fourpack(css_text):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "Variables.css").write_text(css_text, encoding="utf-8")
    return str(d)

class TestTheme(unittest.TestCase):
    def test_canonical_has_19_tokens(self):
        """CANONICAL 必须恰好包含 19 个令牌"""
        self.assertEqual(len(T.CANONICAL), 19)
        # 移除此行时测试变红：
        self.assertIn("--accent", T.CANONICAL)
        self.assertIn("--invert-bg", T.CANONICAL)

    def test_ciridae_bg_by_name_match(self):
        """Ciridae: void-black (#0b0b0b) 按名字线索映射到 --bg"""
        m = T.from_fourpack(_fourpack(CIRIDAE_VARS))
        # 移除此行时测试变红：
        self.assertEqual(m["--bg"].lower(), "#0b0b0b")

    def test_ciridae_bg_sunken_heuristic(self):
        """Ciridae: abyss (#050505) 映射到 --bg-sunken"""
        m = T.from_fourpack(_fourpack(CIRIDAE_VARS))
        # 移除此行时测试变红：
        self.assertEqual(m["--bg-sunken"].lower(), "#050505")

    def test_ciridae_fg3_by_name_steel(self):
        """Ciridae: steel (#484848) 按名字线索映射到 --fg-3"""
        m = T.from_fourpack(_fourpack(CIRIDAE_VARS))
        # 移除此行时测试变红：
        self.assertEqual(m["--fg-3"].lower(), "#484848")

    def test_ciridae_accent_by_name(self):
        """Ciridae: ember-rust (#cc6437) 按名字线索映射到 --accent"""
        # 移除此行时测试变红：
        self.assertEqual(T.from_fourpack(_fourpack(CIRIDAE_VARS))["--accent"].lower(), "#cc6437")

    def test_ciridae_invert_bg_by_name(self):
        """Ciridae: bone (#edebe7) 按名字线索映射到 --invert-bg"""
        # 移除此行时测试变红：
        self.assertEqual(T.from_fourpack(_fourpack(CIRIDAE_VARS))["--invert-bg"].lower(), "#edebe7")

    def test_dope_bg_by_name(self):
        """Dope: near-black (#090909) 按名字线索映射到 --bg"""
        m = T.from_fourpack(_fourpack(DOPE_VARS))
        # 移除此行时测试变红：
        self.assertEqual(m["--bg"].lower(), "#090909")

    def test_dope_accent_by_name(self):
        """Dope: signal-violet (#af50ff) 按名字线索映射到 --accent"""
        # 移除此行时测试变红：
        self.assertEqual(T.from_fourpack(_fourpack(DOPE_VARS))["--accent"].lower(), "#af50ff")

    def test_dope_fg3_by_name_steel(self):
        """Dope: steel (#828384) 按名字线索映射到 --fg-3"""
        m = T.from_fourpack(_fourpack(DOPE_VARS))
        # 移除此行时测试变红：
        self.assertEqual(m["--fg-3"].lower(), "#828384")

    def test_dope_accent2_by_name(self):
        """Dope: lavender-mist (#e1bdff) 按名字线索映射到 --accent-2"""
        m = T.from_fourpack(_fourpack(DOPE_VARS))
        # 移除此行时测试变红：
        self.assertEqual(m["--accent-2"].lower(), "#e1bdff")

    def test_synthetic_names_heuristic_fallback(self):
        """无意义名字的合成包：阶段 1 无匹配，启发式接管"""
        m = T.from_fourpack(_fourpack(SYNTHETIC_VARS))
        _, sources = T.from_fourpack_detailed(_fourpack(SYNTHETIC_VARS))
        # 移除此行时测试变红（若有色值可映射）：
        if "--bg" in m:
            self.assertEqual(sources.get("--bg"), "heuristic")

    def test_accent_collision_raises(self):
        """强调色与文字色重复 → ThemeError"""
        collision_css = """:root {
  --color-bg: #000000;
  --color-accent: #888888;
  --color-steel: #888888;
}"""
        # 移除 with self.assertRaises 时测试变红：
        with self.assertRaises(T.ThemeError):
            T.from_fourpack(_fourpack(collision_css))

    def test_describe_shows_sources(self):
        """describe() 输出包含源标签"""
        m, sources = T.from_fourpack_detailed(_fourpack(CIRIDAE_VARS))
        desc = T.describe(m, sources)
        # 移除此行时测试变红：
        self.assertIn("name", desc)
        self.assertIn("--bg", desc)

    def test_validate_reports_missing(self):
        """validate() 必须列出缺失令牌"""
        # 移除 self.assertIn 时测试变红：
        self.assertIn("--accent-2", T.validate({"--bg": "#000"}))

    def test_emit_css_contains_all_given_tokens(self):
        """emit_tokens_css() 输出必须包含给定的令牌和 :root 块"""
        css = T.emit_tokens_css({"--bg": "#000", "--accent": "#f00"})
        # 移除此两行时测试变红：
        self.assertIn("--bg: #000;", css)
        self.assertIn(":root", css)

    def test_from_prior_page_extracts_root_vars(self):
        """from_prior_page() 必须从 HTML :root 块中提取变量"""
        p = pathlib.Path(tempfile.mkdtemp()) / "prior.html"
        p.write_text("<style>:root{--bg:#090909;--accent:#af50ff}</style>", encoding="utf-8")
        m = T.from_prior_page(str(p))
        # 移除此两行时测试变红：
        self.assertEqual(m["--bg"], "#090909")
        self.assertEqual(m["--accent"], "#af50ff")

    def test_empty_fourpack_raises(self):
        """from_fourpack() 在空目录中应抛出 ThemeError"""
        # 移除 with self.assertRaises 时测试变红：
        with self.assertRaises(T.ThemeError):
            T.from_fourpack(tempfile.mkdtemp())

    def test_ciridae_font_cn_gets_cjk_fallback(self):
        """Ciridae 的 --font-pragmatica 是纯西文字体（'Pragmatica', sans-serif，
        零 CJK 覆盖），--font-cn 服务中文正文是硬规则，映射后必须包含至少
        一个具名 CJK 字体，不能只留一个 generic 关键字兜底。"""
        m = T.from_fourpack(_fourpack(CIRIDAE_VARS))
        # 移除 _ensure_cjk_fallback 的调用时测试变红：
        self.assertTrue(T._has_cjk_family(m["--font-cn"]))
        # 原字体（品牌识别度）必须保留在最前面，不是被整体替换掉：
        self.assertTrue(m["--font-cn"].startswith("'Pragmatica'"))

    def test_latin_only_pack_font_cn_gets_cjk_fallback(self):
        """合成的纯西文包（无任何 CJK 关键词）：--font-cn 映射后同样必须
        补上具名 CJK 字体——这条规则跟具体设计系统无关，任何西文包喂进来
        结果都一样。"""
        m = T.from_fourpack(_fourpack(LATIN_ONLY_VARS))
        # 移除 _ensure_cjk_fallback 的调用时测试变红：
        self.assertTrue(T._has_cjk_family(m["--font-cn"]))

    def test_cjk_fallback_is_noop_when_already_present(self):
        """源设计系统自己就带了 CJK 字体时，--font-cn 原样保留，不重复
        追加、不改写用户已经写对的值。"""
        already_cjk = """:root {
  --color-bg: #111111;
  --color-panel: #262626;
  --color-fg: #eeeeee;
  --color-dim: #bdbdbd;
  --color-accent: #a83200;
  --font-cn: "PingFang SC", "Microsoft YaHei", sans-serif;
}"""
        m = T.from_fourpack(_fourpack(already_cjk))
        # 移除此行时测试变红（沿用原值，不应该被覆盖或重复追加）：
        self.assertEqual(m["--font-cn"], '"PingFang SC", "Microsoft YaHei", sans-serif')

    def test_cjk_fallback_marks_source(self):
        """命中修复时，describe() 的复核表要如实标出这个值被程序改过
        （+cjk-fallback），不能让人误以为它是设计系统的字面原文。"""
        _, sources = T.from_fourpack_detailed(_fourpack(CIRIDAE_VARS))
        # 移除此行时测试变红：
        self.assertIn("cjk-fallback", sources["--font-cn"])
