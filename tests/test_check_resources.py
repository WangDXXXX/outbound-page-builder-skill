import sys, unittest, pathlib
from unittest import mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb.checks import resources as R

class _Ctx:
    def __init__(self, html, asset_hosts=(), link_hosts=()):
        self.html = html
        class C: pass
        self.cfg = C()
        self.cfg.asset_hosts = list(asset_hosts)
        self.cfg.link_hosts = list(link_hosts)
        self.cfg.link_check = "skip"

TOS = "magic-builder.tos-cn-beijing.volces.com"

class _StubFrame:
    """离线桩：模拟 Playwright frame，只提供 _combined_body_text 用到的
    inner_text(selector) 接口，不发真实网络请求。"""
    def __init__(self, text, raises=False):
        self._text = text
        self._raises = raises

    def inner_text(self, selector):
        if self._raises:
            raise RuntimeError("模拟跨域/已卸载 frame 读取失败")
        return self._text

class _StubPage:
    def __init__(self, frames):
        self.frames = frames

class TestResources(unittest.TestCase):
    def test_data_uri_asset_passes(self):
        self.assertEqual(R.check(_Ctx('<img src="data:image/png;base64,AAA">')), [])

    def test_tos_asset_passes(self):
        self.assertEqual(R.check(_Ctx(f'<img src="https://{TOS}/a.jpg">', (TOS,))), [])

    def test_foreign_asset_host_fails(self):
        out = R.check(_Ctx('<img src="https://evil.example/a.jpg">', (TOS,)))
        self.assertTrue(any("资源域未获准" in m for m in out))

    def test_link_host_whitelist(self):
        ok = _Ctx('<a href="https://ok.example/x" target="_blank" rel="noopener">x</a>',
                  (), ("ok.example",))
        self.assertEqual(R.check(ok), [])
        bad = _Ctx('<a href="https://no.example/x" target="_blank" rel="noopener">x</a>',
                   (), ("ok.example",))
        self.assertTrue(any("链接域未获准" in m for m in R.check(bad)))

    def test_blank_link_without_noopener_fails(self):
        c = _Ctx('<a href="https://ok.example/x" target="_blank">x</a>', (), ("ok.example",))
        self.assertTrue(any("noopener" in m for m in R.check(c)))

    # ── 静态两条仍是硬失败（Task 15 闸门二·第三轮）─────────────
    def test_foreign_asset_host_is_still_blocking_not_warn(self):
        """资源域白名单是纯字符串匹配，确定性判断，链接活性降级为 WARN
        不应该连累这一条——它必须继续是硬失败（不带 WARN 前缀）。"""
        out = R.check(_Ctx('<img src="https://evil.example/a.jpg">', (TOS,)))
        hard = [m for m in out if not m.startswith("WARN")]
        self.assertTrue(any("资源域未获准" in m for m in hard))

    def test_missing_noopener_is_still_blocking_not_warn(self):
        c = _Ctx('<a href="https://ok.example/x" target="_blank">x</a>', (), ("ok.example",))
        out = R.check(c)
        hard = [m for m in out if not m.startswith("WARN")]
        self.assertTrue(any("noopener" in m for m in hard))

    # ── 链接活性降级为 WARN（Task 15 闸门二·第三轮）────────────
    def test_dead_link_produces_warn_not_blocking(self):
        """核心回归：链接活性探测是一次真实网络观测，不是页面本身的确定性
        属性——真实测过同一条链接在不同次访问间"活/死"互相切换，根因是
        目标站点渲染时序/限流这类外部波动。硬失败要求确定性，这条不满足，
        必须降级成 WARN，不能再挡构建。"""
        c = _Ctx('<a href="https://ok.example/x" target="_blank" rel="noopener">x</a>',
                 (), ("ok.example",))
        c.cfg.link_check = "browser"
        with mock.patch.object(R, "probe_links_browser",
                               return_value={"https://ok.example/x": False}):
            out = R.check(c)
        self.assertTrue(out, "应该有发现，不能悄悄放行")
        self.assertTrue(all(m.startswith("WARN") for m in out),
                        f"死链发现必须全部带 WARN 前缀，实际: {out}")
        self.assertTrue(any("不可达" in m for m in out))

    def test_alive_link_produces_no_finding(self):
        c = _Ctx('<a href="https://ok.example/x" target="_blank" rel="noopener">x</a>',
                 (), ("ok.example",))
        c.cfg.link_check = "browser"
        with mock.patch.object(R, "probe_links_browser",
                               return_value={"https://ok.example/x": True}):
            out = R.check(c)
        self.assertEqual(out, [])

    def test_regular_link_without_target_blank_passes(self):
        # 没有 target="_blank" 的链接不需要 noopener
        c = _Ctx('<a href="https://ok.example/x">x</a>', (), ("ok.example",))
        self.assertEqual(R.check(c), [])

    def test_browser_check_is_skipped_when_disabled(self):
        # 当 link_check 是 skip 时，不应该调用 probe_links_browser
        c = _Ctx('<a href="https://ok.example/x" target="_blank" rel="noopener">x</a>',
                 (), ("ok.example",))
        c.cfg.link_check = "skip"
        # 应该不会尝试连接到真实网址
        self.assertEqual(R.check(c), [])

    # ── _looks_alive：死链关键词看占比不看出没（Task 15 闸门二）───
    # 全部离线：喂固定字符串给纯函数，不发真实网络请求，测试套件保持离线。
    def test_short_login_wall_body_is_dead(self):
        """真实权限墙的典型形状：正文很短，几乎全部内容就是"要求登录"
        本身——这种情况下关键词出现，判死是对的。"""
        body = "请登录后查看内容"
        self.assertFalse(R._looks_alive(body))

    def test_short_body_without_dead_words_is_alive(self):
        """短但干净（没有死链关键词）：没有"死"的证据，保守判活，
        维持旧实现里"没命中任何关键词就不算死"的默认行为。"""
        self.assertTrue(R._looks_alive("首页"))

    def test_long_body_containing_login_word_in_nav_chrome_is_alive(self):
        """核心回归：真实撞到的抖音假阳性——未登录导航栏固定带"登录"按钮，
        但正文本身（含视频信息、版权页脚等）已经积累了大量实质内容，这时候
        "登录"这个词只是导航栏的常驻按钮，不代表这条内容本身不可达。"""
        body = ("开启读屏标签\n读屏标签已关闭\n精选\n推荐\nAI抖音\n关注\n朋友\n我的\n"
                "直播\n放映厅\n短剧\n下载抖音精选\n2026 © 抖音\n京ICP备16016397号-3\n"
                "京公网安备 11000002002046号\n广播电视节目制作经营许可证\n"
                "增值电信业务经营许可证\n网络文化经营许可证\n互联网宗教信息服务许可证\n"
                "药品医疗器械网络信息服务备案\n互联网新闻信息服务许可证\n网络谣言曝光台\n"
                "网上有害信息举报\n违法和不良信息举报\n广告投放\n用户服务协议\n隐私政策\n"
                "账号找回\n联系我们\n加入我们\n营业执照\n友情链接\n站点地图\n下载抖音\n"
                "抖音电商\n搜索\n充钻石\n客户端\n壁纸\n通知\n消息\n投稿\n登录\n00:01 /")
        self.assertGreaterEqual(len(body.strip()), R._ALIVE_MIN_CHARS)
        self.assertIn("登录", body)
        self.assertTrue(R._looks_alive(body))

    def test_dead_word_as_heading_of_short_page_is_dead(self):
        """死链关键词以标题/唯一信息的形式出现在短正文里——真实的登录墙
        大多长这样，不是"混在一堆无关内容里"。"""
        body = "无权限\n您没有查看此内容的权限，请联系文档所有者。"
        self.assertLess(len(body.strip()), R._ALIVE_MIN_CHARS)
        self.assertFalse(R._looks_alive(body))

    def test_dead_word_as_heading_but_long_body_is_still_dead(self):
        """核心回归：纯长度阈值会漏掉的情况——真实撞到的飞书文档登录墙，
        正文 357 字符（超过 _ALIVE_MIN_CHARS），但除了语言切换列表和品牌
        口号，没有任何"这条内容本身"的信息，"Log In"就是第一行、就是这个
        页面唯一的实际信息。只查总量会把这条误判成活，必须先查开头。"""
        body = ("Log In With QR Code\nScan the QR code via the Feishu mobile app.\n"
                "切换至Lark登录\nScanned successfully\n\nNo account yet? Sign up now\n"
                "English\nEnglish\n简体中文\n繁體中文（中國香港）\n繁體中文（中國台灣）\n"
                "日本語\nBahasa Indonesia\nBahasa Melayu\nDeutsch\nEspañol\nFrançais\n"
                "Italiano\nPortuguês (Brasil)\nРусский\nTiếng Việt\nภาษาไทย\n한국어\n"
                "Feishu, first choice for front-runners\nAn AI work platform by ByteDance")
        self.assertGreaterEqual(len(body.strip()), R._ALIVE_MIN_CHARS)
        self.assertFalse(R._looks_alive(body))

    def test_dead_word_in_short_nav_but_long_overall_body_is_alive(self):
        """核心回归：真实撞到的第二种假阳性——小红书某帖子未登录访问，正文
        全文 1672 字符（真实的合规/备案页脚信息），但它的导航栏本身很短
        （"创作中心/业务合作/发现/RED/直播/发布/通知/登录"八项），"登录"
        排第八个，字符位置恰好落进开头 50 字窗口。只看"开头命中"会把这条
        明显不是墙、且比 Feishu 登录墙长 4 倍还多的页面误判成死链——总量
        必须对"开头命中"这条规则本身也有约束。"""
        body = ("创作中心\n业务合作\n发现\nRED\n直播\n发布\n通知\n登录\n\n" +
                "沪ICP备13030189号 备案信息与合规声明反复出现在页脚区域，" * 25)
        self.assertIn("登录", body[:R._HEADING_WINDOW])
        self.assertGreater(len(body.strip()), R._HEADING_OVERRIDE_MAX)
        self.assertTrue(R._looks_alive(body))

    def test_dead_word_deep_in_long_body_is_alive(self):
        """对照组：同一个死链词（"登录"）出现在长正文的中后段（不在开头），
        必须判活——这是区分"标题级命中"和"导航栏常驻按钮"的边界。"""
        body = "真实的文章正文内容在这里持续展开，" * 15 + "页脚还有一个登录入口。"
        self.assertGreaterEqual(len(body.strip()), R._ALIVE_MIN_CHARS)
        self.assertNotIn("登录", body[:R._HEADING_WINDOW])
        self.assertTrue(R._looks_alive(body))

    # ── 跨 frame 取正文（Task 15 闸门二·第三轮）───────────────
    def test_combined_body_text_picks_longest_frame(self):
        """核心回归：真实撞到的 iframe 盲区——本 Skill 自己发布的页面
        （publish.example.com/html-box/*）最外层 frame body 是空的，
        真实内容（8193字符）在第二个 frame 里，旧实现只读最外层，永远
        判死自己产出的每一条跨页面链接。"""
        real_content = "某系列线下活动·北京场战报\n查看大会回放\n进入大会应用\n" * 20
        page = _StubPage([_StubFrame(""), _StubFrame(real_content)])
        combined = R._combined_body_text(page)
        self.assertGreater(len(combined), R._ALIVE_MIN_CHARS)
        self.assertTrue(R._looks_alive(combined))

    def test_combined_body_text_empty_top_frame_alone_is_empty(self):
        """对照组：只有一个空 frame（没有内容 frame 可选）时返回空字符串，
        不应该报错——这种情况 _looks_alive("") 走"无死链词默认判活"分支，
        跟单 frame 页面完全空白时的既有行为一致，不是这次新增的特殊分支。"""
        page = _StubPage([_StubFrame("")])
        self.assertEqual(R._combined_body_text(page), "")

    def test_combined_body_text_skips_frame_read_errors(self):
        """跨域或已卸载的 frame 读取会抛异常——必须跳过它，不能让整个
        page 都判读取失败；剩下能读的 frame 里如果有实质内容，照常判活。"""
        real_content = "真实的文章正文内容持续展开。" * 30
        page = _StubPage([_StubFrame("", raises=True), _StubFrame(real_content)])
        combined = R._combined_body_text(page)
        self.assertTrue(R._looks_alive(combined))

    def test_combined_body_text_caps_length(self):
        d = _StubPage([_StubFrame("字" * 5000)])
        self.assertEqual(len(R._combined_body_text(d, cap=2000)), 2000)


if __name__ == "__main__":
    unittest.main()
