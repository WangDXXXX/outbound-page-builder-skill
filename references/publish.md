# 发布：`--id` 硬规则 + 验收 + 降级路径

## 安装与登录（第一次用之前做一次）

```bash
npm i -g magic-builder
magic-builder auth login
```

`auth login` 会打印一条授权链接并尝试自动帮你打开浏览器，用你自己的 Magic 账号登录同意后，CLI 在后台轮询直到授权完成，把 token 写进 `~/.magic-builder/magic-token`，之后 preflight 会自动检测到，不需要手动粘贴 token。`magic-builder auth show`（脱敏展示当前 token）随时确认自己是否已登录。

## `--id` 缺失即拒绝执行

```bash
magic-builder page publish page.html --title "活动名 · 邀请函" --id vpKDvxMs2oh
```

**调用 `magic-builder page publish` 时，除下方"全新页面"这一种例外，一律必须带 `--id`。缺 `--id` 就是拒绝执行这条命令，不是"提醒一下再继续"。**

### 事故背景

`magic-builder` 在本机的发布记录缓存在 `~/.magic-builder/magic-apps.json`，**这个缓存按本地文件名做键，不按项目路径做键**。如果两个不同项目里都有一个叫 `index.html` 的文件，先后各发布过一次，缓存里 `"index.html"` 这个键只会保留*最后一次*发布的那个远程 id。下一次任何项目里再发布一个也叫 `index.html` 的文件、且没传 `--id`，CLI 会按文件名去缓存里找"这个文件名上次发布到了哪个 id"，找到就当成是"更新那个 id"——**这正是C 站次曾经实锤覆盖过北京邀请函 v3（`vpKDvxMs2oh`）线上页面的机制**：不是代码 bug，是"按文件名猜你想更新哪个页面"这个设计本身，在文件名撞车时就会张冠李戴。`--id` 显式指定要覆盖谁，绕开这次"猜"。

### 从哪里拿到这个 ID

| 场景 | 怎么拿 `--id` |
|---|---|
| 这个项目之前已经发布过，本地留了记录 | 读本项目自己的 `REPORT.md`（发布成功后必须把返回的 id 写进这里，见下） |
| 手头有这个页面的线上链接，例如 `https://publish.example.com/html-box/vpf1NP4IVW1` | 链接最后一段路径就是 id：`vpf1NP4IVW1` |
| 不确定这个标题有没有发布过 | 先跑 `magic-builder page list --title "页面标题关键词"` 查一遍，命中就是已经发布过，用返回结果里的 id |
| 确认过是全新页面，从未发布过 | 唯一允许省略 `--id` 的情况——见下方"全新页面首次发布" |

**不要**从 `~/.magic-builder/magic-apps.json` 按文件名去反查 id 当作本项目的 id——那个缓存正是按文件名撞车的源头，读它等于重新踩一遍这个坑。

### 全新页面首次发布

一个页面第一次发布之前，世界上还不存在它的 id，`--id` 自然无法提前给出。这是唯一允许不带 `--id` 调用 `page publish` 的场景，前提是已经按上表"不确定这个标题有没有发布过"那一行确认过：真的没发布过。

```bash
magic-builder page publish page.html --title "活动名 · 邀请函"
```

**发布成功后，立刻把命令返回的 id 写进本项目的 `REPORT.md`。** 后续任何一次更新这同一个页面的发布，都必须显式传这个 id，不能再次省略、也不能依赖 `magic-apps.json` 按文件名去猜。

## 发布后必须做微信 UA 回拉验收

`assets/shots.py` 截的是本地构建产物（`file://` 协议打开的 HTML），不是已经发布到线上、经过 `magic-builder` 处理后实际提供服务的那个版本，也没有模拟微信内置浏览器的环境。发布成功后，用真实微信 User-Agent 重新打开线上链接过一遍：

```bash
python3 - <<'PYEOF'
from playwright.sync_api import sync_playwright
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003127) NetType/WIFI Language/zh_CN")
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, user_agent=UA,
                         is_mobile=True, has_touch=True, device_scale_factor=3)
    pg = ctx.new_page()
    pg.goto("https://publish.example.com/html-box/PAGE_ID_HERE_必填")
    pg.wait_for_load_state("networkidle")
    ov = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    print("横向溢出像素:", ov)
    pg.screenshot(path="/tmp/wechat_ua_check.png", full_page=True)
    b.close()
PYEOF
```

检查两件事：`document.documentElement.scrollWidth - clientWidth` 是否为 0（微信内置浏览器的视口行为与普通移动端浏览器不完全一致，本地构建时干净不等于线上微信里也干净）；截图肉眼过一遍，确认微信环境下没有额外的裁切或遮挡。

## 无 `magic-builder` 时的降级路径

`preflight.py` 把 `magic-builder` 列为适配器层的软能力，缺失时的降级不是"这件事做不了"，是"改成交付单文件 HTML，不做平台发布"：

1. `build.py` 产出的 `page.html` / `longpic.html` 本身就是自包含单文件（CSS 内联在 `<style>` 里，不依赖外部资源），可以直接交付给用户自行发布。
2. `REPORT.md` 里必须写明"未发布，交付单文件 HTML"，不能假装发布过。
3. 这条降级必须出现在 `REPORT.md` 的"本次降级"段——`preflight.render()` 已经会把这一项列进能力清单，写报告时原样带过去即可。

## TOS 大文件上传：>16MB 分片会失败

`magic-builder file upload <file>` 走 TOS（火山对象存储）上传资源。**大于 16MB 的文件走分片上传，这条分片逻辑在本机复现过失败（2026-07-13）**——不要指望上传大视频/大图原文件能自动分片成功。处置：上传前用 `ffmpeg` 把文件压到 16MB 以内，走单片直传；不要在没有验证过分片可用的情况下把 >16MB 的原始文件直接丢给 `file upload` 然后假设它会成功。
