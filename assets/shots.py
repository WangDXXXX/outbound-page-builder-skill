"""三视口截图，交给人肉眼过。移动端是主战场，390 排第一。"""
import pathlib


def capture(html_path: str, outdir: str, viewports=(390, 1280, 1680)) -> list:
    from playwright.sync_api import sync_playwright
    src_path = pathlib.Path(html_path)
    if not src_path.exists():
        raise FileNotFoundError(f"要截图的 HTML 不存在：{html_path}")
    src = "file://" + str(src_path.resolve())
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for w in viewports:
                page = browser.new_page(viewport={"width": w, "height": 900},
                                         device_scale_factor=2 if w == 390 else 1,
                                         is_mobile=(w == 390))
                try:
                    page.goto(src, wait_until="networkidle")
                    # 慢滚触发懒加载与计数动画，截图前必须走一遍
                    page.evaluate("""async () => {
                      const step = innerHeight * .8;
                      for (let y = 0; y < document.body.scrollHeight; y += step) {
                        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120));
                      }
                      window.scrollTo(0, 0);
                    }""")
                    page.wait_for_timeout(600)
                    f1 = str(out / f"v{w}_full.png")
                    page.screenshot(path=f1, full_page=True)
                    f2 = str(out / f"v{w}_first.png")
                    page.screenshot(path=f2)
                    paths += [f1, f2]
                finally:
                    page.close()
        finally:
            browser.close()
    return paths


if __name__ == "__main__":
    import sys
    for p in capture(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "shots"):
        print(p)
