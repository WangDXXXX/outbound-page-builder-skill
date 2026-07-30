"""文档层断言：防止 Skill 文档与实现漂移。"""
import sys, re, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "assets"))
from opb.skeleton import SKELETONS
from opb.theme import CANONICAL
from opb.components import base as B
import opb.components  # noqa: F401

REFS = ROOT / "references"

class TestDocs(unittest.TestCase):
    def test_skill_md_under_200_lines(self):
        n = len((ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(n, 200, f"SKILL.md {n} 行，超出 200 行上限")

    def test_all_reference_files_exist(self):
        for f in ("skeleton-recap.md", "skeleton-invite.md", "skeleton-generic.md",
                  "copy-layer.md", "design-inject.md", "longpic.md",
                  "verify.md", "publish.md"):
            self.assertTrue((REFS / f).exists(), f"缺 references/{f}")

    def test_skill_md_states_preflight_first(self):
        t = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("preflight", t)
        self.assertRegex(t, r"任何产出动作之前")

    def test_skill_md_states_id_hard_rule(self):
        t = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("--id", t)
        self.assertIn("拒绝执行", t)

    def test_copy_layer_bans_contrast_pair_explicitly(self):
        t = (REFS / "copy-layer.md").read_text(encoding="utf-8")
        self.assertIn("不是A而是B", t.replace(" ", ""))
        self.assertIn("Contrast pair", t)
        self.assertIn("wu-mengzhi", t)

    def test_copy_layer_scopes_humanizer(self):
        t = (REFS / "copy-layer.md").read_text(encoding="utf-8")
        self.assertIn("内容模式", t)
        self.assertIn("个性与灵魂", t)

    def test_copy_layer_has_15_blueteam_items(self):
        t = (REFS / "copy-layer.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"^\s*\d+\.\s", t, re.M)), 15)

    def test_skeleton_docs_list_every_slot(self):
        for genre, fname in (("recap", "skeleton-recap.md"),
                             ("invite", "skeleton-invite.md"),
                             ("generic", "skeleton-generic.md")):
            t = (REFS / fname).read_text(encoding="utf-8")
            for s in SKELETONS[genre]:
                self.assertIn(s.key, t, f"{fname} 未记载槽位 {s.key}")

    def test_design_inject_lists_all_canonical_tokens(self):
        t = (REFS / "design-inject.md").read_text(encoding="utf-8")
        for tok in CANONICAL:
            self.assertIn(tok, t, f"design-inject.md 未记载令牌 {tok}")

    def test_longpic_doc_lists_s1_to_s8(self):
        t = (REFS / "longpic.md").read_text(encoding="utf-8")
        for i in range(1, 9):
            self.assertIn(f"S{i}", t)

    def test_presets_only_use_canonical_tokens(self):
        for f in (ROOT / "assets" / "presets").glob("*.css"):
            for tok in re.findall(r"(--[\w-]+)\s*:", f.read_text(encoding="utf-8")):
                self.assertIn(tok, CANONICAL, f"{f.name} 定义了非统一令牌 {tok}")

    def test_vendor_humanizer_keeps_license(self):
        self.assertTrue((ROOT / "vendor" / "humanizer-zh" / "LICENSE").exists(),
                        "MIT 要求保留 LICENSE")

    def test_verify_doc_documents_every_assert_yaml_key(self):
        t = (REFS / "verify.md").read_text(encoding="utf-8")
        for k in ("page", "genre", "facts", "quotes", "corpus", "numbers",
                  "blacklist", "unban", "copy", "max_we", "ban_contrast_pair",
                  "must_contain", "link_hosts", "asset_hosts", "link_check",
                  "staff_names"):
            self.assertIn(k, t, f"verify.md 未记载字段 {k}")

    def test_every_registered_component_documented(self):
        docs = "".join((REFS / f).read_text(encoding="utf-8")
                       for f in ("skeleton-recap.md", "skeleton-invite.md",
                                 "skeleton-generic.md"))
        for name in B.all_components():
            self.assertIn(name, docs, f"组件 {name} 未在任何骨架文档中记载")

    # ── 低算力可执行（Global Constraints 专节）────────────────
    HEDGES = ("可以考虑", "建议可以", "视情况", "酌情", "看情况", "尽量", "最好能")

    def test_no_hedging_language_in_skill_or_refs(self):
        """弱模型会跳过「可以考虑」这类软话。要么必须，要么删掉。"""
        for f in [ROOT / "SKILL.md"] + sorted(REFS.glob("*.md")):
            t = f.read_text(encoding="utf-8")
            for h in self.HEDGES:
                self.assertNotIn(h, t, f"{f.name} 出现模糊措辞「{h}」")

    def test_copy_layer_has_pass_fail_examples(self):
        """写不成断言的规则必须给正例/反例对照，弱模型照抄例子而非推导原则。"""
        t = (REFS / "copy-layer.md").read_text(encoding="utf-8")
        self.assertIn("✅", t)
        self.assertIn("❌", t)
        self.assertGreaterEqual(t.count("❌"), 10, "反例少于 10 条，不足以覆盖 15 条红线")

    def test_skill_md_mandates_two_round_copy(self):
        """文案两轮制：初稿 → 跑第4层 → 回灌反模式重写 → 再跑。"""
        t = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("两轮", t)
        self.assertIn("回灌", t)

    def test_skeleton_docs_have_decision_tables(self):
        """决策点必须收敛成「情况 → 做什么」的表，不留开放式判断。"""
        for f in ("skeleton-recap.md", "skeleton-invite.md"):
            t = (REFS / f).read_text(encoding="utf-8")
            self.assertRegex(t, r"\|.*\|.*\|", f"{f} 没有表格，决策点未收敛")

    def test_all_commands_are_copy_pasteable(self):
        """命令块里不许出现 <占位> 尖括号——弱模型会原样敲进去。"""
        import re as _re
        for f in [ROOT / "SKILL.md"] + sorted(REFS.glob("*.md")):
            t = f.read_text(encoding="utf-8")
            for block in _re.findall(r"```bash\n(.*?)```", t, _re.S):
                bad = _re.findall(r"<[a-zA-Z_][\w\-]*>", block)
                self.assertEqual(bad, [], f"{f.name} 命令块含未展开占位 {bad}")


if __name__ == "__main__":
    unittest.main()
