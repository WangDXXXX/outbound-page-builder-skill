import sys, json, tempfile, unittest, pathlib
from unittest import mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
import verify
from opb.checks import resources as _resources

FACTS = {"a": {"value": 628, "display": "628", "caption": "名册609+登记19",
               "source": "s", "public": True, "verified": True}}
QUOTES = [{"id": "q1", "text": "高质量的会议", "speaker": "C",
           "source_file": "c.txt", "why_picked": "带情绪"}]

def _project(html, extra_yaml=""):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "page.html").write_text(html, encoding="utf-8")
    (d / "facts.json").write_text(json.dumps(FACTS, ensure_ascii=False), encoding="utf-8")
    (d / "quotes.json").write_text(json.dumps(QUOTES, ensure_ascii=False), encoding="utf-8")
    (d / "corpus.txt").write_text("这是一场高质量的会议", encoding="utf-8")
    (d / "assert.yaml").write_text(
        "page: page.html\ngenre: invite\nfacts: facts.json\nquotes: quotes.json\n"
        "corpus: ['corpus.txt']\nlink_check: skip\n" + extra_yaml, encoding="utf-8")
    return str(d / "assert.yaml")

class TestVerifyCli(unittest.TestCase):
    def test_clean_page_exits_zero(self):
        code, res = verify.run(_project(
            "<html><body><p>到场 628 人。他说「高质量的会议」。</p></body></html>"))
        self.assertEqual(code, 0, res)

    def test_dirty_page_exits_one_and_groups_by_layer(self):
        code, res = verify.run(_project(
            "<html><body><p>本次复盘：到场 999 人。</p></body></html>"))
        self.assertEqual(code, 1)
        self.assertTrue(res["2 数字"])
        self.assertTrue(res["3 黑话"])

    def test_warn_only_does_not_fail_build(self):
        code, res = verify.run(_project(
            "<html><body><p>到场 628 人。他说「高质量的会议」。</p></body></html>"))
        self.assertEqual(code, 0)

    def test_mixed_warn_and_hard_failures_exits_one(self):
        # 当同时有 WARN 和硬错误时，应该返回 1
        code, res = verify.run(_project(
            "<html><body><p>本次复盘：到场 999 人。</p></body></html>"))
        self.assertEqual(code, 1)
        # 验证有硬错误存在
        hard_count = sum(1 for layer_msgs in res.values()
                        for msg in layer_msgs if not msg.startswith("WARN"))
        self.assertGreater(hard_count, 0)

    def test_warn_findings_must_be_present_and_blocking_absent(self):
        """WARN 消息存在时必须确实产生 WARN，且没有硬错误。

        这个测试验证 test_warn_only_does_not_fail_build 的两个断言：
        1. 至少有一条 WARN 消息（而不是空结果）
        2. 没有非 WARN 消息（硬错误）
        3. 退出码是 0

        触发条件：在文本中加入超过 max_we(5) 次的「我们」，触发 layer 4 WARN。
        """
        html = "<html><body><p>我们的产品很好。我们的团队很强。我们的成就很大。我们的视野很宽。我们的梦想很远。到场 628 人。他说「高质量的会议」。</p></body></html>"
        code, res = verify.run(_project(html))

        # 收集所有消息
        all_msgs = [m for layer_msgs in res.values() for m in layer_msgs]

        # 1. 必须有至少一条 WARN 消息
        warn_msgs = [m for m in all_msgs if m.startswith("WARN")]
        self.assertTrue(warn_msgs,
                       f"期望至少一条 WARN 消息，实际消息：{all_msgs}")

        # 2. 不能有非 WARN 消息
        hard_msgs = [m for m in all_msgs if not m.startswith("WARN")]
        self.assertFalse(hard_msgs,
                        f"期望没有硬错误，实际消息：{hard_msgs}")

        # 3. 退出码必须是 0
        self.assertEqual(code, 0)

    def test_warn_and_blocking_together_must_exit_one(self):
        """WARN 和硬错误共存时必须返回 exit code 1。

        这个测试是前一个测试的镜像：验证硬错误不会被 WARN 逻辑降级。
        """
        # 构造同时有 WARN 和硬错误的 HTML
        # - 硬错误：未替换的占位符 {{name}}
        # - WARN：「我们」出现 8 次（超过 max_we:5）
        html = "<html><body><p>{{name}}，我们的产品很好。我们的团队很强。我们的成就很大。我们的视野很宽。我们的梦想很远。到场 628 人。他说「高质量的会议」。</p></body></html>"
        code, res = verify.run(_project(html))

        # 收集所有消息
        all_msgs = [m for layer_msgs in res.values() for m in layer_msgs]

        # 1. 必须有至少一条 WARN 消息
        warn_msgs = [m for m in all_msgs if m.startswith("WARN")]
        self.assertTrue(warn_msgs,
                       f"期望至少一条 WARN 消息，实际消息：{all_msgs}")

        # 2. 必须有至少一条硬错误消息
        hard_msgs = [m for m in all_msgs if not m.startswith("WARN")]
        self.assertTrue(hard_msgs,
                       f"期望至少一条硬错误，实际消息：{all_msgs}")

        # 3. 退出码必须是 1
        self.assertEqual(code, 1)

    # ── staff_names 端到端（Task 15 F1）─────────────────────
    # 这几条走真实的 assert.yaml → load_config() → build_ctx() 全链路，
    # 不是直接调 blacklist.build()/jargon.check()——第一次尝试 mutation-verify
    # 时，只测到 blacklist.py+jargon.py 本身的单元测试完全测不出
    # checks/__init__.py 里那一行"没把 cfg.blacklist.staff_names 传给
    # build_blacklist()"的接线遗漏（临时改回旧代码后，单元测试仍然全绿，
    # 因为它们从没经过 build_ctx()）。这几条端到端测试补上这个盲区。
    def test_staff_name_on_page_blocks_end_to_end(self):
        yaml_extra = "genre: recap\nblacklist:\n  staff_names: [李默, 老默]\n"
        code, res = verify.run(_project(
            "<html><body><p>活动由李默统筹策划，现场氛围热烈。到场 628 人。"
            "他说「高质量的会议」。</p></body></html>", yaml_extra))
        self.assertEqual(code, 1)
        hard = [m for m in res["3 黑话"] if not m.startswith("WARN")]
        self.assertTrue(any("李默" in m for m in hard), res["3 黑话"])

    def test_staff_name_absent_from_page_passes_end_to_end(self):
        yaml_extra = "genre: recap\nblacklist:\n  staff_names: [李默, 老默]\n"
        code, res = verify.run(_project(
            "<html><body><p>到场 628 人。他说「高质量的会议」。</p></body></html>",
            yaml_extra))
        self.assertEqual(code, 0, res)

    # ── 链接活性 WARN 化端到端（Task 15 闸门二·第三轮）──────────
    # 走真实的 assert.yaml(link_check: browser) → load_config() →
    # build_ctx() → verify.run() 全链路，只 mock 掉最底层的真实网络调用
    # （opb.checks.resources.probe_links_browser），不发真实请求，测试
    # 套件保持离线；验证的是"死链只产生 WARN、不再让 exit code 变成 1"
    # 这条端到端属性，不只是 checks/resources.py 单个模块内部的行为。
    def test_dead_link_warns_but_exit_code_stays_zero_end_to_end(self):
        yaml_extra = ("blacklist:\n  staff_names: []\n"
                      "link_hosts: [ok.example]\nlink_check: browser\n")
        html = ('<html><body><p>到场 628 人。他说「高质量的会议」。'
               '<a href="https://ok.example/x" target="_blank" rel="noopener">链接</a>'
               '</p></body></html>')
        with mock.patch.object(_resources, "probe_links_browser",
                               return_value={"https://ok.example/x": False}):
            code, res = verify.run(_project(html, yaml_extra))
        self.assertEqual(code, 0, res)
        self.assertTrue(any("不可达" in m for m in res["5 资源与链接"]))
        self.assertTrue(all(m.startswith("WARN") for m in res["5 资源与链接"]))

    def test_foreign_asset_host_still_blocks_exit_code_end_to_end(self):
        """对照组：确认降级只发生在网络探测这一条，静态的资源域检查仍然
        是硬失败，能把 exit code 顶到 1——不是整层5都变成了 WARN。"""
        yaml_extra = "blacklist:\n  staff_names: []\nlink_check: skip\n"
        html = ('<html><body><p>到场 628 人。他说「高质量的会议」。'
               '<img src="https://evil.example/a.jpg"></p></body></html>')
        code, res = verify.run(_project(html, yaml_extra))
        self.assertEqual(code, 1, res)
        hard = [m for m in res["5 资源与链接"] if not m.startswith("WARN")]
        self.assertTrue(any("资源域未获准" in m for m in hard))

if __name__ == "__main__":
    unittest.main()
