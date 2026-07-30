"""层5 资源与链接：资源全 TOS 或内联；链接域白名单——两条硬失败，静态、
确定性判断。链接活性用真实浏览器判——curl 200 是假绿（登录墙/权限页也
200），但浏览器探测本身报的是 WARN，不是硬失败，见 check() 里的说明。"""
import re

_ASSET = re.compile(r'(?:src|poster)="([^"]+)"')
_HREF = re.compile(r'<a\s[^>]*href="(https?://[^"]+)"[^>]*>')
_BLANK_NO_NOOPENER = re.compile(
    r'<a\s[^>]*target="_blank"(?![^>]*rel="[^"]*noopener)[^>]*>')
_HOST = re.compile(r"https?://([^/]+)")

_DEAD_WORDS = ("登录", "无权限", "Not Found", "404", "Log In", "Log in", "Sign in", "Sign In")

# 2026-07-30 修复（Task 15 闸门二）：判死不能靠"死链关键词出没"，只能靠
# "死链关键词是不是支配了这条页面"。真实撞到过假阳性：一条确实在播放、有
# 698 个赞的抖音视频被判死——不是内容不可达，是抖音未登录访问时导航栏
# 本身固定带一个"登录"按钮，跟这条具体视频能不能看毫无关系；小红书/微博/
# B站同样在未登录态常驻登录入口。旧实现只看"关键词在不在前400字里"，
# 对这类站点等于把"任何未登录抓取"都判死。
#
# 支配有两种形状，缺一个都会漏判或误判——校准时用真实链接跑出来的：
#
# 1）**关键词就是标题/开头信息本身**：飞书文档的登录墙真实截图——正文
#    357 字符（"Log In With QR Code\nScan the QR code via the Feishu
#    mobile app.\n切换至Lark登录\n...多国语言切换列表...Feishu, first
#    choice for front-runners"），**纯长度阈值会把这条误判成活**——357
#    字符已经超过下面的 _ALIVE_MIN_CHARS，但这 357 字符里除了语言切换
#    列表和品牌口号，没有任何"这条内容本身"的信息，"Log In"就是第一行、
#    就是这个页面唯一的实际信息。所以先看死链词是否落在正文最开头一段
#    （_HEADING_WINDOW 字符内）——落在这里，不管后面跟了多长的语言列表
#    或品牌文案，都判死。
# 2）**关键词混在大量无关内容中间/末尾**：抖音案例——"登录"是导航栏里
#    排在中后段的一个常驻按钮，前后被"精选/推荐/关注/直播"这类无关导航项
#    和大段版权/备案信息包围，不在开头。这种情况下改看正文总量：正文
#    （含导航壳层）一旦达到 _ALIVE_MIN_CHARS，说明页面渲染出了导航壳层
#    之外的东西（文章正文/视频信息/版权页脚……），不管死链关键词出不出现，
#    都判活——协调者原话"if the page has substantial rendered body text
#    beyond the chrome, it is alive regardless of the word"这条正信号。
#
# 两条规则的顺序是"先查开头，再查总量"，不是"选一条"：开头命中优先级更高
# （飞书登录墙那 357 字符如果只跑总量检查会被误判成活），总量检查兜底
# 处理"关键词不在开头、但正文本身还是很短"的情况。
#
# 阈值来自真实观测：抖音未登录视频页刚加载时的导航壳层
# （精选/推荐/关注/直播/搜索/登录/视频数据加载中……）在 130 字符上下；
# 小红书未登录页脚壳层在 140 字符上下——两者都在 200 字符阈值之下，都还是
# "纯壳层"；真实内容（哪怕只是文章正文的头几句）几乎不可能压在 200 字符
# 以内还成篇。_HEADING_WINDOW 50 字符覆盖"Log In With QR Code"这类标题级
# 短语（20字符）留有余量，同时明显短于抖音"登录"按钮在正文里的实际位置
# （在几十到上百字符之后，视壳层加载进度而定）。
#
# 3）**开头命中，但那只是这个站点导航栏本身写得短，不代表真的是道墙**：
#    校准时又撞到一个新形状——小红书某个真实存在的帖子链接，未登录访问
#    正文全文 1672 字符（沪ICP备案号等法务页脚信息），一次都不短，但它的
#    导航栏本身只有"创作中心/业务合作/发现/RED/直播/发布/通知/登录"八个
#    词，"登录"排第八个，字符位置恰好落进前 50 字——如果只看"开头命中就
#    判死"，会把这条 1672 字符、明显不是墙的页面误判成死链，比"用总量兜底"
#    还倒退一步。区分 Feishu 登录墙（357 字符，"Log In"确实是全篇仅有的
#    实际信息）和这条小红书链接（1672 字符，"登录"只是导航栏第八项）的，
#    还是总量——所以"开头命中"这条规则本身也要有一个总量上限
#    （_HEADING_OVERRIDE_MAX）：只有正文总量本身还压在这个上限以内，开头
#    命中才优先于总量判断生效；一旦正文本身已经跑到远超"纯壳层"的量级，
#    哪怕死链词技术上还落在前 50 字，也不再改判死——总量本身已经说明这
#    不是一道墙。
_ALIVE_MIN_CHARS = 200
_HEADING_WINDOW = 50
_HEADING_OVERRIDE_MAX = 600

def _looks_alive(body: str) -> bool:
    """正文是否有实质内容，而不是死链/权限墙/纯导航壳层。"""
    stripped = body.strip()
    heading = stripped[:_HEADING_WINDOW]
    if len(stripped) <= _HEADING_OVERRIDE_MAX and any(k in heading for k in _DEAD_WORDS):
        return False
    if len(stripped) >= _ALIVE_MIN_CHARS:
        return True
    return not any(k in stripped for k in _DEAD_WORDS)

# 2026-07-30 修复（Task 15 闸门二·第三轮）：`pg.inner_text("body")` 只读
# 最外层 frame——本 Skill 自己发布的页面（`build.py` 写的
# `<meta name="use-iframe" content="true">` 就是明证）内容全部在 iframe
# 里，最外层 frame 的 body 是空的。真实复现过：`publish.example.com`
# 上的北京战报页，最外层 frame body 长度 0，真实内容（"某系列线下活动·北京场
# 战报...628人全部带着电脑上场..."，8193 字符）在 `page.frames` 的第二个
# frame 里。这不是边缘情况——这个 Skill 产出的页面互相引用是常态（上海
# 邀请函链接北京战报），所以层5 会稳定地把这个 Skill 自己产出的每一条
# 跨页面链接都判死。
#
# 改成取全部 frame 里文本最长的那一个，不是拼接全部——拼接会把多个不
# 相关文档的文本接在一起，"死链词是否落在开头"这个判断对着拼接文本就
# 失去意义了（拼接后的"开头"到底是谁的开头？）；取最长的那个 frame，
# `_looks_alive()` 还是在对着"一份连贯的文档"做判断，跟单 frame 页面走
# 的是同一条判断路径，不需要为多 frame 场景另外发明一套逻辑。
def _combined_body_text(page, cap: int = 2000) -> str:
    """跨 page 全部 frame 取正文，返回文本最长的那个 frame 的内容
    （截到 cap 字符）。frame 读取失败（跨域权限、已卸载等）跳过，不中断。"""
    texts = []
    for fr in page.frames:
        try:
            t = fr.inner_text("body")
        except Exception:
            continue
        if t:
            texts.append(t)
    if not texts:
        return ""
    return max(texts, key=len)[:cap]

def probe_links_browser(urls: list[str]) -> dict:
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        for u in urls:
            try:
                # networkidle，不是 domcontentloaded：iframe 结构的页面
                # （本 Skill 自己的产物就是）需要等内层 frame 的网络请求
                # 完成才会有真实内容，domcontentloaded 只保证最外层文档
                # 解析完毕，内层 iframe 大概率还没加载完。
                r = pg.goto(u, wait_until="networkidle", timeout=15000)
                # 很多平台（含抖音）是 SPA：即使 networkidle 触发，首次渲染
                # 到真实内容之间可能还有一小段异步延迟——多等一小段再取
                # 正文，不然"正文有没有实质内容"这个判断永远只能看到壳层。
                pg.wait_for_timeout(3000)
                body = _combined_body_text(pg)
                out[u] = bool(r and r.status < 400 and _looks_alive(body))
            except Exception:
                out[u] = False
        b.close()
    return out

def check(ctx) -> list[str]:
    fails = []
    for a in _ASSET.findall(ctx.html):
        if a.startswith("data:"):
            continue
        m = _HOST.match(a)
        if not m:
            continue
        if m.group(1) not in ctx.cfg.asset_hosts:
            fails.append(f"资源域未获准（须 TOS 或内联）: {a[:70]}")
    links = _HREF.findall(ctx.html)
    for u in links:
        h = _HOST.match(u).group(1)
        if h not in ctx.cfg.link_hosts:
            fails.append(f"链接域未获准: {u[:70]}")
    for m in _BLANK_NO_NOOPENER.finditer(ctx.html):
        fails.append(f"外链缺 noopener: {m.group(0)[:60]}")
    # 2026-07-30 降级（Task 15 闸门二·第三轮）：链接活性探测从硬失败改成
    # WARN，上面两条（资源域白名单、链接域白名单）保持硬失败不变。
    #
    # 原因：硬失败必须是确定性的——同一份 page.html、同一份 assert.yaml，
    # 今天判定失败，明天不该在内容一个字没改的情况下自己变绿。资源域/
    # 链接域两条断言是纯字符串匹配（正则抠 host，查表），符合这个要求。
    # 但 `probe_links_browser()` 是一次真实网络请求+浏览器渲染，读到的
    # 是"这一次访问在这一刻观测到的结果"，不是页面本身的属性——真实测过
    # （见闸门二报告"链接实测不可达"一节）：同一条链接，间隔几分钟重查，
    # 会在"活"和"死"之间切换，根因是目标站点的渲染时序/限流这类外部
    # 波动，不是我们的页面出了问题。一条硬失败如果三次里有一次无缘无故
    # 变红，人会学会"红了就重跑"，这个习惯一旦养成，会连带磨掉对其他
    # 五层（真正确定性的那些）红灯的信任——所以非确定性信号不能是闸门，
    # 只能是提醒。
    #
    # `curl 200 是假绿`这条判断依据没有变：浏览器探测依然比只看状态码
    # 强得多（能抓到登录墙/权限页这类"状态码 200 但内容不可达"的情况），
    # 只是"更强的信号"不等于"可以当硬门"——WARN 仍然要求人在闸门二把
    # 结果看一遍，不是关掉了这层检查，只是不让它单方面挡发布。
    #
    # `link_check: skip` 在 CI/离线环境下是正确设置，不是"偷懒不检查"——
    # 见 references/verify.md 对应小节。
    if getattr(ctx.cfg, "link_check", "browser") == "browser" and links:
        for u, alive in probe_links_browser(sorted(set(links))).items():
            if not alive:
                fails.append(f"WARN 链接实测不可达（浏览器判定，可能是网络/渲染时序波动，"
                             f"不代表页面一定有问题——发布前人工点开确认）: {u[:70]}")
    return fails
