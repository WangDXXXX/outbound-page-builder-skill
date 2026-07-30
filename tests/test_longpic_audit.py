import json, sys, tempfile, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
import render_longpic as R
import shots as SH
from opb import build as BD

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"


def _tmp_html(content: str) -> pathlib.Path:
    """把一段 HTML 写进独立临时目录，返回路径。用于不需要落盘成 fixture 的
    一次性回归场景（踩坑1/踩坑2/docOverflow 兜底各自需要一份专门构造的最小
    HTML，塞进 audit_good.html/audit_bad.html 会让它们不再"只测一件事"）。"""
    d = pathlib.Path(tempfile.mkdtemp())
    p = d / "case.html"
    p.write_text(content, encoding="utf-8")
    return p


class TestLongpicAudit(unittest.TestCase):
    """brief 给定的 7 项基线用例。"""

    def test_good_page_passes_all_three(self):
        a = R.audit(str(FIX / "audit_good.html"))
        self.assertEqual(a["bad"], [])
        self.assertEqual(a["orphan"], [])
        self.assertEqual(a["overflow"], [])

    def test_absolute_overflow_container_not_flagged(self):
        """踩坑2：.atm 这类 absolute+overflow:hidden 容器不得误报。"""
        self.assertEqual(R.audit(str(FIX / "audit_good.html"))["overflow"], [])

    def test_bad_page_flags_bad_linebreak(self):
        self.assertTrue(R.audit(str(FIX / "audit_bad.html"))["bad"])

    def test_bad_page_flags_overflow(self):
        self.assertTrue(any("spill" in str(x)
                            for x in R.audit(str(FIX / "audit_bad.html"))["overflow"]))

    def test_render_raises_on_dirty_layout(self):
        with self.assertRaises(R.LayoutError) as e:
            R.render(str(FIX / "audit_bad.html"), "/tmp/opb_test_bad.png")
        self.assertIn("坏断行", str(e.exception))

    def test_render_writes_png_and_jpg_when_clean(self):
        png = "/tmp/opb_test_good.png"
        info = R.render(str(FIX / "audit_good.html"), png)
        self.assertTrue(pathlib.Path(png).exists())
        self.assertTrue(pathlib.Path(png.replace(".png", ".jpg")).exists())
        self.assertEqual(info["width_px"], 430 * 3)

    def test_verify_qr_degrades_gracefully_without_cv2(self):
        ok, msg = R.verify_qr("/tmp/opb_test_good.png")
        self.assertIn(ok, (True, False, None))
        if ok is None:
            self.assertIn("人工", msg)


class TestBadFixtureTriggerCounts(unittest.TestCase):
    """brief 只要求"非空"（assertTrue），这里把实测到的确切命中数钉死成
    回归断言——同时也是 REPORT 里"逐项命中数"这一节数据的来源，不是转述。"""

    def test_bad_fixture_triggers_exactly_one_bad_and_one_orphan(self):
        a = R.audit(str(FIX / "audit_bad.html"))
        self.assertEqual(len(a["bad"]), 1)
        self.assertEqual(len(a["orphan"]), 1)

    def test_bad_fixture_overflow_list_names_the_spill_element_itself(self):
        """光断言"某处字符串含 spill"不够——brief 给的原始 markup
        （<div><div class="spill"></div></div>，尺寸写在 .spill 自己身上）
        实测会导致真正撑破容器的是那个没有 class 的外层 DIV，.spill 自己
        因为 clientWidth==scrollWidth 反而不出现在名单里，spill 字样从
        未真正出现过。改成 .spill 自己是外层（尺寸写在内层匿名 div 上）后
        .spill 才是名单里的元素本身，不是命中别的字符串子串。"""
        a = R.audit(str(FIX / "audit_bad.html"))
        self.assertIn("spill", a["overflow"])


class TestLongpicAuditTraps(unittest.TestCase):
    """两处踩坑的专项回归 + 由此发现并修的第三个真实缺口（docOverflow 兜底）。
    每条都用最小化、只测一件事的临时 HTML，不往两份 fixture 里塞更多东西。"""

    def test_orphan_probe_does_not_misfire_on_trailing_bold_punctuation(self):
        """踩坑1：段落以 </b>。 收尾——最后一个文本节点只有"。"一个字符，
        naive「只取最后一个文本节点」实现会不管真实末行多长都report孤字。
        本例真实末行有 7 个字（"一间屋子"+句号所在行），不该被判孤字。

        已实测验证 naive 实现确实会误报（不是臆测）：同一份页面上手写一段
        只取 el.childNodes 最后一项的探针，量出该节点文本正是「。」、长度 1、
        总行数 2——满足 naive 判定的全部条件，会被判孤字。TreeWalker 版按
        rect.top 分类到「末行」的字符数是 7，不小于 3，不判孤字。"""
        html = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
body{width:430px;margin:0;font:15px/1.95 "PingFang SC",sans-serif}
.prose{line-height:2.05}
.prose b{font-weight:700}
</style></head><body>
<p class="prose">前两站证明了规模，所以这一场我们把大会改成五十个人的<b>一间屋子</b>。</p>
</body></html>"""
        p = _tmp_html(html)
        a = R.audit(str(p))
        self.assertEqual(a["orphan"], [])

    def test_overflow_whitelist_exempts_position_absolute_container_itself(self):
        """白名单的 position:absolute 这一支单独生效（不依赖同时有
        overflow:hidden）：容器自己不进溢出名单，即使它包着一个撑爆自己的
        子元素（子元素的溢出会往上冒到别的祖先——那是另一件事，不在本测试
        断言范围内；这里只认领"容器自己不被点名"这一条）。"""
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{width:430px;margin:0;font:15px/1.95 sans-serif}
.deco{position:absolute;inset:0}
</style></head><body>
<div class="deco"><div style="width:900px;height:50px"></div></div>
<h1>标题</h1>
</body></html>"""
        p = _tmp_html(html)
        a = R.audit(str(p))
        self.assertNotIn("deco", a["overflow"])

    def test_overflow_whitelist_exempts_overflow_hidden_container_completely(self):
        """白名单的 overflow:hidden 这一支单独生效（不依赖 position:absolute）：
        容器本身是正常流的 block，尺寸不会跟着子元素撑大，子元素的溢出又被
        overflow:hidden 挡住不往上冒——这种情况下整页应该彻底干净。"""
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{width:430px;margin:0;font:15px/1.95 sans-serif}
.deco{overflow:hidden}
</style></head><body>
<div class="deco"><div style="width:900px;height:50px"></div></div>
<h1>标题</h1>
</body></html>"""
        p = _tmp_html(html)
        a = R.audit(str(p))
        self.assertEqual(a["overflow"], [])
        self.assertEqual(a["docOverflow"], 0)

    def test_overflow_whitelist_does_not_exempt_plain_container(self):
        """负对照：去掉 position:absolute 和 overflow:hidden 后，同样的撑爆
        场景必须被抓到——证明上面两条"豁免"测试不是因为断言本身失效才通过。"""
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{width:430px;margin:0;font:15px/1.95 sans-serif}
.deco{}
</style></head><body>
<div class="deco"><div style="width:900px;height:50px"></div></div>
<h1>标题</h1>
</body></html>"""
        p = _tmp_html(html)
        a = R.audit(str(p))
        self.assertIn("deco", a["overflow"])

    def test_doc_overflow_alone_blocks_render_even_when_element_list_is_empty(self):
        """brief 原始 render() 只看 bad/orphan/overflow 三个数组，不看
        docOverflow。实测发现一个真能让三个数组全空、但整页确实横向溢出、
        出图会变宽的构造：<html> 自己写 overflow:hidden（逐元素判定据此把
        <html> 排除在外），紧贴 body 挂一个没有任何 position:relative 祖先
        的 position:absolute 装饰层、inset 取较大负值（它的 containing
        block 因此是初始包含块，绕过 body，直接把溢出记到 <html> 头上，
        而 <html> 恰好被白名单豁免）。

        先断言触发条件真的成立（overflow==[] 且 docOverflow 超容差），
        再断言 render() 真的拒绝——避免"断言了结果却没断言触发条件"这类
        死测试。"""
        html = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>
html{overflow:hidden}
body{width:430px;margin:0;font:15px/1.95 "PingFang SC",sans-serif}
.atm{position:absolute;inset:-20%;pointer-events:none}
</style></head><body>
<div class="atm"><div style="width:900px;height:200px"></div></div>
<h1>标题</h1>
</body></html>"""
        p = _tmp_html(html)

        a = R.audit(str(p))
        self.assertEqual(a["overflow"], [], "本用例的前提是逐元素溢出名单为空")
        self.assertGreater(a["docOverflow"], 2, "本用例的前提是文档级确实横向溢出")

        out_png = str(p.parent / "out.png")
        with self.assertRaises(R.LayoutError) as e:
            R.render(str(p), out_png)
        self.assertIn("文档横向溢出", str(e.exception))
        self.assertFalse(pathlib.Path(out_png).exists())

    def test_layout_error_names_the_actual_offending_text(self):
        """"失败要响亮"不能只是叫得响的类别名——异常信息里必须能看到具体是
        哪段文字出的问题，不然排查的人还是得自己重新跑一遍审计。"""
        with self.assertRaises(R.LayoutError) as e:
            R.render(str(FIX / "audit_bad.html"), str(pathlib.Path(tempfile.mkdtemp()) / "x.png"))
        msg = str(e.exception)
        self.assertIn("这是一个非常非常长的标题", msg)  # 坏断行命中的具体标题文字
        self.assertIn("末行两字", msg)  # 孤字行命中的具体段落文字

    def test_audit_return_shape_has_doc_overflow_and_height(self):
        """接口文档承诺的 docOverflow/height 两个标量字段必须真的存在且是
        int——brief 给的 7 项用例从未直接读过这两个键，只测过 bad/orphan/
        overflow 三个数组，是形状覆盖的盲区。"""
        a = R.audit(str(FIX / "audit_good.html"))
        self.assertIsInstance(a["docOverflow"], int)
        self.assertIsInstance(a["height"], int)
        self.assertGreater(a["height"], 0)


class TestVerifyQr(unittest.TestCase):
    """verify_qr 三种返回状态各自要有真正走到该分支的测试，不能只测「返回值
    在允许的集合里」这种任何分支都能蒙混过关的弱断言。"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = pathlib.Path(tempfile.mkdtemp())

    def test_real_qr_code_is_decoded(self):
        try:
            import qrcode
        except ImportError:
            self.skipTest("本机没装 qrcode，跳过真实二维码编码回归（不影响 cv2 解码路径本身）")
        payload = "https://example.com/opb-longpic-qr-check"
        img_path = self.tmpdir / "real_qr.png"
        qrcode.make(payload).save(str(img_path))
        ok, data = R.verify_qr(str(img_path))
        self.assertTrue(ok)
        self.assertEqual(data, payload)

    def test_image_without_qr_returns_false_not_true(self):
        """cv2 在装的前提下，一张完全没有二维码的图必须解出 False，
        不能因为「没抛异常」就被误判成过了。"""
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("本机没装 cv2，走不到真实解码分支")
        no_qr_png = str(self.tmpdir / "no_qr.png")
        R.render(str(FIX / "audit_good.html"), no_qr_png)
        ok, msg = R.verify_qr(no_qr_png)
        self.assertFalse(ok)
        self.assertIsInstance(msg, str)

    def test_cv2_missing_returns_none_with_manual_check_message(self):
        """brief 给的同名测试在本机（cv2 已装）永远走不到「cv2 缺失」这个
        分支——测试名字叫「没有 cv2 时优雅降级」，但触发条件从未被满足过，
        这正是项目"死测试五种形状"里点名的一种。用 sys.modules 显式把
        cv2 钉成 None，强制 `import cv2` 在函数内部抛 ImportError，真正
        走一遍降级分支。"""
        from unittest import mock
        with mock.patch.dict(sys.modules, {"cv2": None}):
            ok, msg = R.verify_qr(str(self.tmpdir / "irrelevant.png"))
        self.assertIsNone(ok)
        self.assertIn("人工", msg)


class TestHasQrComponent(unittest.TestCase):
    """Task 15 闸门二·第三轮：切成多张长图后，非最后一张合法地没有
    qr-closure——main() 不该对着这种页面硬解二维码再报"失败"。"""

    def test_page_with_qr_closure_detected(self):
        html = '<div class="wrap"><div class="qrc"><img class="qr" src="a.png"></div></div>'
        self.assertTrue(R._has_qr_component(html))

    def test_page_without_qr_closure_not_detected(self):
        """核心回归：切分出的"非收尾页"（例如本例里只有 section-head 的
        预告性收尾）必须被判定为"没有二维码"，不能被其他组件的 class
        名字（如 "qc" 是 quote-card 的类名，字面上包含 "q" 但不是 "qrc"）
        意外命中。"""
        html = '<div class="sechead"><h2>下一张图：作品、问卷、群聊</h2></div><div class="qc"><p>引用</p></div>'
        self.assertFalse(R._has_qr_component(html))


def _missing_html_path() -> str:
    """一个保证不存在的 .html 路径：新建一个空临时目录，只拼路径、不落盘。
    不用 tempfile._get_candidate_names() 这类下划线前缀的私有接口——本项目
    自己的约定（见 build.py 里不 import theme.py 私有 _VAR/_collect 的注释）
    就是不对外承诺稳定的名字不能跨模块依赖。"""
    return str(pathlib.Path(tempfile.mkdtemp()) / "missing.html")


class TestRenderErrorHandling(unittest.TestCase):
    def test_audit_raises_clear_error_for_missing_html(self):
        missing = _missing_html_path()
        with self.assertRaises(FileNotFoundError) as e:
            R.audit(missing)
        self.assertIn(".html", str(e.exception))

    def test_render_raises_clear_error_for_missing_html(self):
        missing = _missing_html_path()
        with self.assertRaises(FileNotFoundError):
            R.render(missing, str(pathlib.Path(tempfile.mkdtemp()) / "out.png"))

    def test_render_writes_no_file_when_dirty(self):
        """脏页面必须"什么也不产出"，不能留一个半成品 PNG 在磁盘上误导人。"""
        out_png = str(pathlib.Path(tempfile.mkdtemp()) / "should_not_exist.png")
        with self.assertRaises(R.LayoutError):
            R.render(str(FIX / "audit_bad.html"), out_png)
        self.assertFalse(pathlib.Path(out_png).exists())
        self.assertFalse(pathlib.Path(out_png.replace(".png", ".jpg")).exists())


class TestShotsCapture(unittest.TestCase):
    def test_capture_returns_full_and_first_fold_for_each_viewport(self):
        outdir = tempfile.mkdtemp()
        paths = SH.capture(str(FIX / "audit_good.html"), outdir, viewports=(390, 1280, 1680))
        self.assertEqual(len(paths), 6)
        for p in paths:
            self.assertTrue(pathlib.Path(p).exists())
        names = {pathlib.Path(p).name for p in paths}
        self.assertEqual(names, {
            "v390_full.png", "v390_first.png",
            "v1280_full.png", "v1280_first.png",
            "v1680_full.png", "v1680_first.png",
        })

    def test_mobile_viewport_uses_device_scale_factor_2(self):
        """390 视口是移动端主战场，截图必须按 dsf=2 出（首屏图宽度=390*2），
        跟桌面视口（dsf=1）区分开——只查"文件存在"测不出 dsf 传没传对。"""
        from PIL import Image
        outdir = tempfile.mkdtemp()
        paths = SH.capture(str(FIX / "audit_good.html"), outdir, viewports=(390, 1280))
        first_390 = [p for p in paths if p.endswith("v390_first.png")][0]
        first_1280 = [p for p in paths if p.endswith("v1280_first.png")][0]
        with Image.open(first_390) as im:
            self.assertEqual(im.size[0], 390 * 2)
        with Image.open(first_1280) as im:
            self.assertEqual(im.size[0], 1280 * 1)

    def test_capture_raises_clear_error_for_missing_html(self):
        with self.assertRaises(FileNotFoundError):
            SH.capture(_missing_html_path(), tempfile.mkdtemp())


def _build_longpic_with_hero_extras(hero_components: list) -> str:
    """跑一次真实 build.build(mode="longpic")，hero 槽位内容可控——用于
    构造"含 atm-layer" / "不含 atm-layer"这两个只差一个组件的真实页面。
    其余槽位给最小合法内容，只是为了让 outline 通过 skeleton 校验。"""
    outline = {
        "genre": "invite", "title": "atm-layer 回归用例",
        "og": {"title": "og", "description": "og desc"},
        "slots": [
            {"key": "hero", "components": hero_components},
            {"key": "why_you", "components": []},
            {"key": "agenda", "components": [
                {"name": "agenda-rows", "data": {"rows": [
                    {"time": "13:00", "name": "幕零", "desc": "入局"}]}}]},
            {"key": "value", "components": []},
            {"key": "people", "components": []},
            {"key": "terms", "components": []},
            {"key": "cta", "components": [
                {"name": "cta-pills", "data": {"title": "来吗", "text": "回一个字",
                 "buttons": [{"label": "确认出席", "href": "https://example.com",
                              "variant": "primary"}]},
                 "longpic": {"name": "qr-closure",
                             "data": {"qr": "data:image/png;base64,"
                                            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
                                            "2mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
                                      "alt": "二维码", "lines": "8 月 1 日 · 上海"}}}]},
        ],
    }
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "outline.json").write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")
    th = d / "theme"
    th.mkdir()
    (th / "tokens.css").write_text(
        ":root{--bg:#0b0b0b;--fg:#fff;--accent:#cc6437;--hair:rgba(255,255,255,.12);"
        "--bg-2:#3a2a1f}", encoding="utf-8")
    out = d / "longpic.html"
    BD.build(str(d / "outline.json"), str(th), "longpic", out=str(out))
    return str(out)


class TestRealBuildAtmLayerRegression(unittest.TestCase):
    """协调者复核后指名修复的真实缺口：atm-layer（Task 8，
    assets/opb/components/common.py）在 longpic 模式下用负值 inset 把自己的
    盒子（不是子元素）撑出视口——它的 containing block 不是任何设了
    overflow:hidden 的祖先，溢出因此一路冒到 wrap/section/body/html。
    web 模式容器远比视口宽，肉眼看不出来；Task 12 第一次对本项目做真实浏览器
    渲染，才第一次有能力抓到它。

    这两条测试直接跑真实 build.build(mode="longpic") + render_longpic.audit()
    /render()，不是手写迷你 HTML 模拟——钉住的是"这个组件在真实管线里到底
    渲染成什么样"，不是"我以为它会渲染成什么样"。没有这条测试，下一个碰
    atm-layer 的人很容易在不知情的情况下把这个洞重新捅开。"""

    def test_real_longpic_build_with_atm_layer_is_clean(self):
        path = _build_longpic_with_hero_extras([
            {"name": "atm-layer", "data": {}},
            {"name": "sysbar", "data": {"text": "8 月 1 日 · 上海"}},
            {"name": "info-meta", "data": {"items": [{"k": "日期", "v": "8 月 1 日"}]}},
        ])
        a = R.audit(path)
        self.assertEqual(a["bad"], [])
        self.assertEqual(a["orphan"], [])
        self.assertEqual(a["overflow"], [],
                          "atm-layer 的负值 inset 曾经把 wrap/section/body/html 全部"
                          "撑宽——这里非空说明回归了")
        self.assertEqual(a["docOverflow"], 0)
        # 不止测 audit()：真的把 render() 跑一遍，证明画布宽度没有跑偏
        # （回归前这里会是 1818 而不是 1290）。
        info = R.render(path, str(pathlib.Path(path).parent / "out.png"))
        self.assertEqual(info["width_px"], 430 * 3)

    def test_real_longpic_build_without_atm_layer_stays_clean(self):
        """负对照：防止"修好了含 atm-layer 的场景，却弄坏了不含它的场景"
        这类此消彼长——两个场景除了这一个组件，其余 outline 完全一致。"""
        path = _build_longpic_with_hero_extras([
            {"name": "sysbar", "data": {"text": "8 月 1 日 · 上海"}},
            {"name": "info-meta", "data": {"items": [{"k": "日期", "v": "8 月 1 日"}]}},
        ])
        a = R.audit(path)
        self.assertEqual(a["bad"], [])
        self.assertEqual(a["orphan"], [])
        self.assertEqual(a["overflow"], [])
        self.assertEqual(a["docOverflow"], 0)


if __name__ == "__main__":
    unittest.main()
