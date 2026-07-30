# 通用对外页骨架（generic，4 槽位）

用于：不是战报、也不是邀请函的对外页面——评测页、产品介绍页这类。弱约束骨架，只固定 4 个槽位，**不预设信息架构**，但仍然继承全部文案红线（`references/copy-layer.md`）与六层程序断言（`references/verify.md`）——不体裁不代表不审核。

槽位顺序写死在 `assets/opb/skeleton.py` 的 `SKELETONS["generic"]`。

## 4 槽位

| 槽位 key | 内容 | 必备 | 规则 | 典型组件 |
|---|---|---|---|---|
| `hero` | 页面主张 + 核心信息 | ✅ | 标题给事实或情绪，禁止占位词（蓝军第 4 条），与战报/邀请函同一条红线 | `section-head` `stat-caption` `atm-layer` |
| `body` | 正文内容，槽位内容自由编排 | ✅ | 每个数字仍须带 `caption`；每条引用仍须逐字命中语料——弱约束指的是信息架构，不是指数字/引用可以降低举证标准 | 按内容形态自由选用任意已注册组件 |
| `proof` | 佐证材料 | ○ | 外链须浏览器判活 | `stat-caption` `quote-card` `compare-bars` |
| `cta` | 行动入口 | ✅ | 网页版按钮、长图版二维码的替身机制与邀请函 `cta` 槽位完全一致（见 `references/skeleton-invite.md` 的 `cta-pills` ↔ `qr-closure` 一节） | `cta-pills`(web) ↔ `qr-closure`(longpic) |

## 跨体裁通用组件

以下 5 个组件不属于任何单一体裁，`assets/opb/components/common.py` 里注册：`sysbar`（顶部信息条）、`section-head`（区块标题）、`atm-layer`（氛围光晕层）、`footer-brand`（页脚品牌区）、`reveal-wrap`（滚动渐显包裹层，longpic 模式自动关闭动效）。

## 可以借用战报与邀请函的全部组件

`body` 与 `proof` 槽位没有专属组件，因为组件注册表是全局共享的（不按体裁隔离）——`body` 槽位可以自由组合以下任意组件，只要数据槽位对得上：

- 数字/统计：`stat-caption`（战报） `compare-bars`（战报） `donut`（战报） `bar-h`（战报）
- 引用/证言：`quote-card`（战报） `quote-ticker`（战报，web 专属）
- 人物：`speaker-grid`（战报） `talk-card`（邀请函）
- 结构化列表：`terms-list`（邀请函） `agenda-rows`（邀请函） `award-list`（战报） `hook-grid`（邀请函） `info-meta`（邀请函） `keynote-block`（邀请函） `timeline-heartbeat`（战报） `photo-mosaic`（战报）

## 什么时候该用 generic 而不是硬套 recap/invite

| 情况 | 用哪个骨架 |
|---|---|
| 内容是"发生过的事"的回顾，有讲者/现场/数据 | `recap` |
| 内容是"邀请读者来参加"，有议程/门槛/报名入口 | `invite` |
| 二者都不是——例如一个持续更新的能力介绍页、一份不绑定单场活动的评测报告 | `generic` |

不确定时先看有没有"日期+地点+报名"三件套：有，走 `invite`；内容围绕"已经发生的一场活动复盘"：走 `recap`；两者都不构成，才用 `generic`。**不要因为 `generic` 约束松就默认选它**——`recap`/`invite` 的 11/9 槽位是从四份真实交付实例里蒸馏出的信息架构，能套用就套用，`generic` 是给两套骨架都不适用时的兜底，不是"偷懒选项"。
