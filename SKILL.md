---
name: outbound-page-builder
description: |
  把你飞书里的复盘（活动复盘文档、campaign 数据多维表格）产出为对外战报网页 +
  微信长图，并发布成公开链接。触发场景：做战报、活动复盘做成对外页、campaign
  复盘出战报、投放战役总结对外发布、转微信长图。当用户说"把这份复盘做成战报"
  "campaign 打完了出个对外战报""这些素材做成对外页发出去"时使用。也可做活动
  邀请函网页（invite 骨架），当用户说"写一个邀请函网页""做邀请函"时使用。
  不适用于：交互式应用页、微信公众号图文排版。
---

# outbound-page-builder

把碎片信息变成对外网页（战报/邀请函）+ 微信长图，两者都移动端优先。本文件只放路由和硬规则，细节在 `references/` 里，读完本文件之后按下方"路由表"去看对应文档，不要跳过硬规则直接开始产出。碎片从哪来：读 `references/absorb-feishu.md`，两条路径（lark-cli 拉取 / 手动导出）选一条，落进 `absorb/`。

## 硬规则 0：任何产出动作之前先跑 preflight

```bash
python3 assets/preflight.py
```

把打印出来的能力清单**原样贴给用户**，缺失项列出安装命令、问一句要不要现在装。**降级永不静默**——任何一项缺失导致的能力下降（例如没有 `opencv` 只能人工扫码确认二维码），必须写进最终的 `REPORT.md`"本次降级"段，不能因为流程能跑通就不提。

## 两道人工闸门

| 闸门 | 位置 | 人要确认什么 |
|---|---|---|
| 闸门一 | `outline.json` 定稿后，开始组件拼装之前 | 数字口径、槽位取舍、原声选取、标题候选；**设计系统注入的映射表**（`theme.describe()` 输出，见 `references/design-inject.md`）也在这里过，`heuristic`/`default` 来源的令牌要重点确认；**公开性逐条确认**——台账里将出现在页面上的每个数字、人名、原声，逐条问用户"这条可以公开吗"；用户没点头的条目不进 outline。这个页面发出去是公开链接，这道确认替用户挡隐私事故。 |
| 闸门二 | 交付前 | 三视口截图 + 长图过目；`verify.py` 六层结果；`REPORT.md` 的降级声明 |

两道闸门都不能跳过。程序断言能拦住的是"引用是不是编的、数字有没有 caption、黑话有没有漏网"，拦不住的是"这个映射对不对、这张图看着顺不顺"，这部分必须有人看过。

## 体裁路由

| 碎片描述的是什么 | 骨架 | 详细文档 |
|---|---|---|
| 已经发生的活动，讲复盘/讲者/数据 | 战报（recap，11 槽位） | `references/skeleton-recap.md` |
| 一段时间的投放/营销战役，讲打法/触达/ROI | campaign（8 槽位） | `references/skeleton-campaign.md` |
| 邀请读者来参加，讲议程/门槛/报名 | 邀请函（invite，9 槽位） | `references/skeleton-invite.md` |
| 二者都不是 | 通用页（generic，4 槽位） | `references/skeleton-generic.md` |

四套骨架的槽位顺序写死在 `assets/opb/skeleton.py`，`outline.json` 不能自己重排。

## 文案层裁剪

- `vendor/humanizer-zh` 只用「内容模式」章，**不用「个性与灵魂」章**——那一章教第一人称与个人化语气，对外页面的主语是读者不是我们，用了会撞上"零内部视角"红线。
- ⛔ 调用 `vendor/wu-mengzhi-variety-copy` 时禁用它的 `Contrast pair: 不是 A，而是 B` 手法，反差改用它的三层结构（Observation→Reframe→Lift）达成。
- 正文「我们」出现次数 ≤5（超限是 WARN，不阻断，但仍要在第二轮改写里主动压）。
- **文案两轮制**：初稿写完 → 跑 `verify.py` 第 4 层 → 把命中的反模式**回灌**给自己重写第二轮 → 再跑一遍确认干净。不允许一轮直接交付。

完整规则、15 条蓝军逐条、正例反例对照见 `references/copy-layer.md`。

## 发布硬规则：缺 `--id` 拒绝执行

```bash
magic-builder page publish page.html --title "活动名 · 邀请函" --id vpKDvxMs2oh
```

`magic-builder page publish` **不带 `--id` 一律拒绝执行**，唯一例外是确认过从未发布过的全新页面（见 `references/publish.md`）。原因：这个命令的本地缓存按文件名匹配，不按项目匹配，曾经静默覆盖过另一个项目的线上页（北京邀请函 v3）。

## 品牌资产纪律

- Logo、活动贴纸一律用**官方原始文件**，不自行抠图、不改色。
- 资产自带的白色模切边当贴纸边框用，不是"没抠干净"要修掉的瑕疵。
- 内联 `<svg>` 必须显式声明 `width`——默认 300px 会挤坏顶栏/页脚。

## 冲突判例：设计系统 vs 蓝军红线，蓝军赢

设计系统的视觉偏好和文案红线冲突时（例如设计系统想用全大写英文做主视觉），**按蓝军判——中文是主角，英文字号不得超过中文**。纯视觉手法之争（阴影、圆角）才跟设计系统走。完整判例表见 `references/design-inject.md`。

## 命令速查

```bash
python3 assets/preflight.py
python3 assets/verify.py assert.yaml
python3 assets/render_longpic.py longpic.html out.png
python3 assets/shots.py page.html shots_out
```

`build` 没有独立 CLI，是库函数，同一份 `outline.json` 分别喂两次拿到 web 和 longpic：

```bash
python3 -c "
import sys; sys.path.insert(0, 'assets')
from opb.build import build
build('outline.json', 'theme', mode='web', out='page.html')
build('outline.json', 'theme', mode='longpic', out='longpic.html')
"
```

## 深入阅读路由表

| 要做什么 | 读哪份文档 |
|---|---|
| 填战报/邀请函/campaign/通用页的槽位，不知道该用哪个组件 | `references/skeleton-recap.md` / `skeleton-invite.md` / `skeleton-campaign.md` / `skeleton-generic.md` |
| 写文案、判断标题/反差合不合格 | `references/copy-layer.md` |
| 接入四件套/风格描述/前作设计系统 | `references/design-inject.md` |
| 出长图、处理断行/孤字行/溢出报错 | `references/longpic.md` |
| 配置 `assert.yaml`、读懂六层断言报错 | `references/verify.md` |
| 发布、`--id` 怎么填、TOS 大文件失败怎么办 | `references/publish.md` |
| 没有真实设计系统输入 | `assets/presets/recap-dark.css`+`.RULES.md`（战报向）或 `invite-dark.css`+`.RULES.md`（邀请函向），直接当 `theme/tokens.css` 用 |
