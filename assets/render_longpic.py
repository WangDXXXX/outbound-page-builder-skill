"""长图渲染 + 三项排版断言（含文档级溢出兜底）。全绿才出图——断言不过直接
抛，不给「凑合发」的机会。

三项断言的判定逻辑在 opb/audit.js（与本文件同目录下的 opb/ 包内），两处
踩坑（孤字行探针要走 TreeWalker 全量文本节点；absolute/overflow:hidden
容器要白名单排除）的完整说明写在那份 JS 的头注释里，这里不重复。
"""
import functools
import os
import pathlib


class LayoutError(Exception):
    pass


_HERE = pathlib.Path(__file__).resolve().parent
_AUDIT_JS_PATH = _HERE / "opb" / "audit.js"

# 与 audit.js 里逐元素溢出判定同一套 +2px 容差——亚像素舍入不算真溢出，
# 这条容差专门用来判定 docOverflow（见 _is_dirty 的说明）。
_OVERFLOW_TOLERANCE_PX = 2


@functools.lru_cache(maxsize=1)
def _audit_js() -> str:
    """惰性读取 + 缓存审计脚本。惰性是为了不让 import 这个模块本身带上 I/O
    副作用（跟 opb/config.py 的读取时机习惯一致）；缓存是因为同一进程里
    audit()/render() 可能被反复调用，没必要每次都重新读文件。"""
    return _AUDIT_JS_PATH.read_text(encoding="utf-8")


def _to_file_url(html_path: str) -> str:
    p = pathlib.Path(html_path)
    if not p.exists():
        raise FileNotFoundError(f"要渲染/审计的 HTML 不存在：{html_path}")
    return "file://" + str(p.resolve())


def _run_audit(page) -> dict:
    """在已经 goto 完成的 page 上跑审计脚本。等 900ms 是经验值——字体、懒加载、
    图片解码这些还没稳定就量，行数/末行字数都会算错（沿用C 站次脚本的既有
    做法，未改动这个数字）。"""
    page.wait_for_timeout(900)
    return page.evaluate(_audit_js())


def audit(html_path: str, width: int = 430, dsf: int = 3) -> dict:
    """只测量、不下结论——是否「脏」交给 render() 或调用方自己判断。
    独立开一个 Chromium 会话，用完即关，不依赖调用方后续是否还会调 render()。"""
    from playwright.sync_api import sync_playwright
    src = _to_file_url(html_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": 900},
                                     device_scale_factor=dsf)
            try:
                page.goto(src, wait_until="networkidle")
                return _run_audit(page)
            finally:
                page.close()
        finally:
            browser.close()


def _is_dirty(a: dict) -> bool:
    """三项数组任一非空即脏；docOverflow 超容差也算脏——这条是给原始设计
    补的漏洞（已实测验证，非猜测）：

    逐元素溢出判定会豁免 position:absolute / overflow:hidden 的容器（氛围层
    白名单，见 audit.js 头注释踩坑2）。但如果溢出源*自己*（不是它的子元素）
    的盒子就比视口宽——典型例子是氛围层用负值 inset 把自己撑到视口外，且它
    的 containing block 不是任何设了 overflow:hidden 的祖先——逐元素名单会
    正确地把这个容器排除在外（它本该被排除，它是"合法溢出"），可
    document.documentElement 的 scrollWidth 依然会因为这个容器自身的盒子
    尺寸而比 clientWidth 宽。full_page 截图按文档的可滚动宽度出图，图会因此
    整体变宽，430 画布可能出成一张几百像素更宽的图，而 out["overflow"] 全程
    是空列表——三项断言看着全绿，图已经不对了。

    实测复现过最极端的一例：<html> 自己写 overflow:hidden（逐元素判定据此
    豁免 <html>，overflow 数组全程为空），紧邻 body 下挂一个未包裹在任何
    position:relative 容器里的 position:absolute 氛围层、inset 取很大的负值
    ——docOverflow 量出 384px，实际出图从预期的 1290 宽变成 2442 宽。只看
    三个数组会漏掉这种「溢出源本身就是被白名单豁免的那个元素」的情况，
    必须把 docOverflow 也纳入硬门槛，容差跟逐元素判定同一套 +2px。"""
    return bool(a["bad"] or a["orphan"] or a["overflow"]) or a["docOverflow"] > _OVERFLOW_TOLERANCE_PX


def _fmt(a: dict) -> str:
    """把断言结果拼成人话：点名是哪一项、命中了多少处、具体是哪段文字——
    「失败要响亮」，调用方哪怕不追问异常，光看消息就知道该去改哪儿。"""
    parts = []
    if a["bad"]:
        parts.append(f"坏断行 {len(a['bad'])} 处：{a['bad'][:3]}")
    if a["orphan"]:
        parts.append(f"孤字行 {len(a['orphan'])} 处：{a['orphan'][:3]}")
    if a["overflow"]:
        parts.append(f"元素溢出 {len(a['overflow'])} 处：{a['overflow'][:3]}")
    if a["docOverflow"] > _OVERFLOW_TOLERANCE_PX and not a["overflow"]:
        parts.append(
            f"文档横向溢出 {a['docOverflow']}px（逐元素溢出名单是空的——溢出源"
            f"自己就是被 absolute/overflow:hidden 白名单豁免的容器，多半是氛围层"
            f"自己的盒子比视口还宽，不是子元素撑破了它；不拦下来出图宽度会变宽）")
    return "；".join(parts)


def verify_qr(png_path: str):
    """二维码必须被解码，不能靠肉眼确认「看起来像个码」。cv2 缺失是已登记的
    可降级项（preflight.py 里是 soft 能力），降级路径必须明着返回 None + 提示
    文案，不能悄悄跳过整个校验（调用方——见 main()——必须把这个结果打印出来）。"""
    try:
        import cv2
    except ImportError:
        return None, "cv2 未装，二维码需人工扫码确认（降级项，须写进 REPORT.md）"
    img = cv2.imread(png_path)
    if img is None:
        return False, f"图片读取失败：{png_path}"
    data, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return (bool(data), data if data else "未解出二维码内容")


def render(html_path: str, out_png: str, width: int = 430, dsf: int = 3) -> dict:
    """审计与出图共用同一个 Chromium 会话：一次 goto，先测量、不脏才截图。

    没有为了"复用公开的 audit() 函数"而在这里再开一次浏览器——audit() 依旧
    是独立可调用、独立开关会话的公开入口（下面的 audit()/render() 都调用同一个
    私有的 _run_audit()，逻辑不重复；render() 只是不通过公开入口绕一圈，避免
    每次出图都完整启动 + 导航两遍 Chromium）。"""
    from playwright.sync_api import sync_playwright
    from PIL import Image

    src = _to_file_url(html_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": 900},
                                     device_scale_factor=dsf)
            try:
                page.goto(src, wait_until="networkidle")
                a = _run_audit(page)
                if _is_dirty(a):
                    raise LayoutError("三项排版断言未过，拒绝出图 —— " + _fmt(a))
                page.screenshot(path=out_png, full_page=True)
            finally:
                page.close()
        finally:
            browser.close()

    jpg_path = out_png.rsplit(".", 1)[0] + ".jpg"
    with Image.open(out_png) as im:
        width_px, height_px = im.size
        with im.convert("RGB") as rgb:
            rgb.save(jpg_path, "JPEG", quality=93, optimize=True, progressive=True)

    ratio = height_px / width_px
    notes = []
    if ratio > 15:
        notes.append(f"长图比例 1:{ratio:.1f} 偏长，可考虑按幕次切两张")
    notes.append("微信发送务必勾「原图」，否则压缩后文字会糊")
    return {
        "width_px": width_px, "height_px": height_px, "ratio": ratio,
        "png_mb": os.path.getsize(out_png) / 1048576,
        "jpg_mb": os.path.getsize(jpg_path) / 1048576,
        "notes": notes,
    }


# 2026-07-30 修复（Task 15 闸门二·第三轮）：二维码检查此前无条件跑，不管
# 这张长图的 outline 里到底有没有 qr-closure 组件——切成多张长图后，非
# 最后一张合法地没有二维码收尾（S8"尾部自带闭环"是对"一张完整长图"的
# 要求，不是对"系列里的每一张"都要求），旧实现会对着一张根本没放二维码
# 的图硬解，每次都打印"❌ 二维码解码失败"，看起来像失败，其实是预期内
# 的设计。改成先看源 HTML 里有没有 qr-closure 组件渲染出的标记
# （`class="qrc"`，见 opb/components/invite.py 的 `_qr()`），没有就不去
# 解码，只报一条 WARN 说明——不是失败，是如实告知。
def _has_qr_component(html_text: str) -> bool:
    """页面是否渲染出了 qr-closure 组件（class="qrc"）。用字符串标记判断，
    不解析 HTML 结构——跟这个文件其余部分（audit.js 走真实 DOM，Python
    侧只做轻量判断）的分工一致，没必要为了这一个布尔判断引入解析器。"""
    return 'class="qrc"' in html_text


def main():
    import sys
    if len(sys.argv) < 3:
        print("用法: python3 render_longpic.py <longpic.html> <out.png>")
        return 2
    try:
        info = render(sys.argv[1], sys.argv[2])
    except LayoutError as e:
        print("❌", e)
        return 1
    print(f"✅ 三项排版断言全绿 → {info['width_px']}×{info['height_px']} "
          f"比例 1:{info['ratio']:.1f}　PNG {info['png_mb']:.2f}MB / JPG {info['jpg_mb']:.2f}MB")
    if _has_qr_component(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")):
        ok, msg = verify_qr(sys.argv[2])
        print({True: "✅ 二维码可解码：", False: "❌ 二维码解码失败：",
               None: "⚠️ "}[ok] + msg)
    else:
        print("⚠️ WARN 这张长图没有二维码收尾组件（qr-closure）——如果这是"
              "多幕长图里的非最后一张，这是预期内的；如果这应该是收尾页，"
              "检查 outline 是不是漏放了 qr-closure。")
    for n in info["notes"]:
        print("　·", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
