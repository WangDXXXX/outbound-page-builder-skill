import sys, unittest, pathlib, shutil
from unittest.mock import patch
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

    def test_install_hints_only_point_to_existing_vendor_dirs(self):
        """回归：安装提示若指向 vendor/ 路径，该目录必须真实随仓分发。

        公开仓库因授权原因不含 vendor/wu-mengzhi-variety-copy，
        提示指向不存在的目录会让新用户照着撞墙。
        """
        for c in preflight.probe():
            if "vendor/" in c.install:
                name = c.install.split("vendor/")[1].split(" ")[0].rstrip("，。；")
                self.assertTrue(
                    (preflight.VENDOR_DIR / name / "SKILL.md").exists(),
                    f"{c.name} 的安装提示指向不存在的 vendor 目录：vendor/{name}")

    def test_render_handles_unknown_cap_name(self):
        """render() 应该优雅处理未知的能力名"""
        caps = [
            preflight.Cap("unknown-capability", "soft", False, "", "降级方案", "install something"),
        ]
        out = preflight.render(caps)
        # 应该不报错，并显示为"其他"层级
        self.assertIn("其他", out)
        self.assertIn("unknown-capability", out)

class TestCliAuthProbe(unittest.TestCase):
    """两级探测：CLI 不在 → (False, "未安装")；在但没登录 →
    (False, "已安装，未登录")；都好 → (True, "")。
    探测必须离线（只查文件，不发网络请求）——preflight 是每次产出前必跑，
    不能等网络超时。"""

    def test_cli_missing(self):
        ok, detail = preflight._cli_authed("no-such-cli-xyz", lambda: True)
        self.assertFalse(ok)
        self.assertEqual(detail, "未安装")

    def test_cli_present_but_not_authed(self):
        # python3 一定在 PATH 里，拿它冒充"装了但没登录"的 CLI
        ok, detail = preflight._cli_authed("python3", lambda: False)
        self.assertFalse(ok)
        self.assertEqual(detail, "已安装，未登录")

    def test_cli_present_and_authed(self):
        ok, detail = preflight._cli_authed("python3", lambda: True)
        self.assertTrue(ok)
        self.assertEqual(detail, "")

    def test_probe_lark_and_magic_use_two_stage(self):
        by_name = {c.name: c for c in preflight.probe()}
        for name in ("lark-cli", "magic-builder"):
            c = by_name[name]
            # 未登录时 detail 必须点名（守卫：不许静默把"没登录"当"没装"）
            if not c.ok and shutil.which(name):
                self.assertEqual(c.detail, "已安装，未登录", name)

    def test_lark_cli_install_contains_domain_flag(self):
        """lark-cli auth login 必须带 --domain docs,drive，否则新用户照裸命令敲会报错"""
        by_name = {c.name: c for c in preflight.probe()}
        lark_cap = by_name["lark-cli"]
        self.assertIn("--domain", lark_cap.install,
                     "lark-cli install 缺 --domain 参数，新用户会撞墙")

    def test_lark_authed_handles_non_dict_json(self):
        """~/.lark-cli/config.json 若不是 JSON 对象（例如被写坏成一个数组），
        .get("apps") 会抛 AttributeError——_lark_authed 必须吞掉它返回 False，
        不能让 preflight 在这种损坏配置上直接崩溃。"""
        with patch("pathlib.Path.read_text", return_value="[]"):
            self.assertFalse(preflight._lark_authed())

if __name__ == "__main__":
    unittest.main()
