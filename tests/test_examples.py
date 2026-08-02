"""example 端到端：两个虚构 demo 必须 build 通过 + verify 全绿。
example 是外部用户抄的第一个样本，坏样本比没样本严重。"""
import subprocess, sys, unittest, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "assets"))
from opb.build import build

DEMOS = ("demo-recap", "demo-campaign")

class TestExamples(unittest.TestCase):
    def test_demo_dirs_exist_with_contract_files(self):
        for d in DEMOS:
            base = ROOT / "example" / d
            for f in ("outline.json", "facts.json", "quotes.json",
                      "assert.yaml", "theme/tokens.css"):
                self.assertTrue((base / f).exists(), f"example/{d} 缺 {f}")

    def test_demos_build_both_modes(self):
        for d in DEMOS:
            base = ROOT / "example" / d
            for mode in ("web", "longpic"):
                out = build(str(base / "outline.json"), str(base / "theme"),
                            mode=mode, out=str(base / f"_test_{mode}.html"))
                self.assertTrue(pathlib.Path(out).exists(), f"{d}/{mode} 未产出")

    def test_demos_pass_verify(self):
        for d in DEMOS:
            base = ROOT / "example" / d
            r = subprocess.run(
                [sys.executable, str(ROOT / "assets" / "verify.py"),
                 str(base / "assert.yaml")],
                capture_output=True, text=True, cwd=str(base))
            self.assertEqual(r.returncode, 0,
                             f"{d} verify 未过：\n{r.stdout}\n{r.stderr}")

    def test_demo_campaign_asserts_its_real_genre(self):
        """demo-campaign 的 assert.yaml 必须写字面 `genre: campaign`，不能退回
        `genre: generic` 绕过——`campaign` 曾经不在 config.py 的 GENRES 里，
        当时用 generic 侥幸能过 verify，但那是掩盖 SKILL.md 已经承诺的
        campaign 体裁路由撞墙的一个真实缺口，不是这个 demo 该长期示范的写法。
        这条断言只锁字面配置，不重复 test_demos_pass_verify 已经做的六层校验。"""
        text = (ROOT / "example" / "demo-campaign" / "assert.yaml").read_text(encoding="utf-8")
        self.assertIn("genre: campaign", text)
