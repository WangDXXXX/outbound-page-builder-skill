import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
import preflight

class TestPreflight(unittest.TestCase):
    def test_probe_returns_all_known_caps(self):
        names = {c.name for c in preflight.probe()}
        self.assertEqual(names, {
            "python3", "playwright", "Pillow", "PyYAML", "opencv",
            "humanizer-zh", "wu-mengzhi-variety-copy",
            "lark-cli", "magic-builder",
        })

    def test_every_cap_has_kind_and_fallback(self):
        for c in preflight.probe():
            self.assertIn(c.kind, ("hard", "soft", "adapter"), c.name)
            if c.kind != "hard":
                self.assertTrue(c.fallback, f"{c.name} 缺降级说明")
            self.assertTrue(c.install, f"{c.name} 缺安装命令")

    def test_degradations_lists_only_missing_non_hard(self):
        caps = [
            preflight.Cap("a", "soft", False, "", "用内置", "pip install a"),
            preflight.Cap("b", "soft", True, "", "用内置", "pip install b"),
            preflight.Cap("hard_missing", "hard", False, "", "", "install hard"),
        ]
        self.assertEqual(preflight.degradations(caps), ["a：用内置"])

    def test_render_marks_missing(self):
        caps = [
            preflight.Cap("lark-cli", "adapter", False, "", "手动放文件", "npm i -g lark-cli"),
            preflight.Cap("python3", "hard", False, "", "", "brew install python"),
        ]
        out = preflight.render(caps)
        # 缺失的能力都应该被标记
        self.assertIn("✗", out)
        self.assertIn("手动放文件", out)
        # hard 能力的安装命令应该出现在列表中
        self.assertIn("brew install python", out)

    def test_render_counts_all_missing_caps(self):
        """混合 hard/soft/adapter，验证计数和完整性"""
        caps = [
            preflight.Cap("python3", "hard", False, "", "", "brew install python3"),
            preflight.Cap("opencv", "soft", False, "", "降级说明", "pip install opencv-python"),
            preflight.Cap("lark-cli", "adapter", False, "", "手动安装", "npm i -g lark-cli"),
            preflight.Cap("playwright", "hard", True, "", "", "pip install playwright"),
        ]
        out = preflight.render(caps)
        # 计数应该包括所有缺失的能力（3 个）
        self.assertIn("缺 3 项", out)
        # 所有缺失能力的安装命令都应该出现
        self.assertIn("brew install python3", out)
        self.assertIn("pip install opencv-python", out)
        self.assertIn("npm i -g lark-cli", out)
        # 正常的能力不应该在缺失清单中
        self.assertNotIn("pip install playwright", out)

    def test_render_handles_unknown_cap_name(self):
        """render() 应该优雅处理未知的能力名"""
        caps = [
            preflight.Cap("unknown-capability", "soft", False, "", "降级方案", "install something"),
        ]
        out = preflight.render(caps)
        # 应该不报错，并显示为"其他"层级
        self.assertIn("其他", out)
        self.assertIn("unknown-capability", out)

if __name__ == "__main__":
    unittest.main()
