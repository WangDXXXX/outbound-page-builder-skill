# outbound-page-builder

把碎片信息做成**对外移动端网页**和**微信长图**的 Claude Code Skill。

会议纪要、群聊记录、逐字稿、问卷、往届数据 —— 这些东西散在十几个文件里。这个 Skill 把它们收敛成一份带出处的事实台账，填进三套已验证的信息骨架（战报 / 邀请函 / campaign），产出一个自包含的单文件 HTML 和一张可直接发微信的长图，中间过六层程序断言。

不是模板填空。**质量靠断言承载，不靠模型的判断力** —— 这是它能在弱模型上跑出可交付结果的原因。

---

## 它解决什么

做对外页面时，真正会出事的不是排版，是这些：

| 会出的事 | 这里怎么拦 |
|---|---|
| 引用被改写成"大意如此" | 引用必须是语料的精确子串，改一个字就报错 |
| 数字没人说得清哪来的 | 每个数字必须带 `caption`（外人为什么该在意）和 `source`（哪来的） |
| 内部口径不小心上了页 | `public: false` 的数字出现即失败 |
| 组委名字出现在对外战报里 | 分体裁黑名单，战报禁人名、邀请函允许讲者署名 |
| 满页 AI 腔 | 「不是A而是B」及变体、宏大空话、破折号连击、句长过均，程序拦 |
| 长图里一行只剩两个字 | 出图前跑三项排版断言，不绿不出图 |
| 链接看着能开其实是登录墙 | 真实浏览器判活，`curl 200` 视为假绿 |

六层断言全绿才准交付，任何一层不过 `verify.py` 退出码非零。

---

## 快速开始

### 安装

#### Claude Code

```bash
git clone https://github.com/WangDXXXX/outbound-page-builder-skill.git \
  ~/.claude/skills/outbound-page-builder

pip install -r ~/.claude/skills/outbound-page-builder/requirements.txt
playwright install chromium
```

Claude Code 下次启动就会看到这个 Skill。

#### 其他 Agent（Codex / Cursor / 任意）

clone 到任意目录，让你的 Agent 读仓库根的 `AGENTS.md` 照做即可——
skill 的全部逻辑是纯 Python + Markdown，不依赖特定 Agent 框架。

### 第一步永远是 preflight

```bash
python3 assets/preflight.py
```

它探测 9 项能力、分三档打印清单、把缺失项的安装命令列出来。**缺东西不会静默降级** —— 例如没装 OpenCV，二维码就从「程序解码验证」降为「人工扫码确认」，这条会写进最终报告。

### 跑通附带的样例

`example/demo-recap/` 是一个完整的虚构会议战报工程，可以直接跑：

```bash
cd example/demo-recap
python3 ../../assets/verify.py assert.yaml          # 六层断言
python3 ../../assets/render_longpic.py longpic.html out.png   # 长图 + 排版断言
```

预期：六层全过，长图宽 1290、高约 1.7 万像素（渲染高度依赖本机字体，具体数值以本机跑出来的为准），二维码解出 `https://example.com/report`。

想看完整链路，从 `absorb/` 里那两份虚构碎片开始，对着 `facts.json` / `quotes.json` / `outline.json` 读一遍就明白数据是怎么流的。

---

## 工作流

```
碎片（纪要/群聊/逐字稿/表格）
   ↓  preflight：报能力，缺什么说清降到什么程度
   ↓  抽取：facts.json（每个数字带口径与出处）+ quotes.json（每条带选取理由）
   ↓  填骨架：战报 11 槽位 / 邀请函 9 槽位 / campaign 8 槽位，槽位顺序即页面顺序
══ 闸门一 ══  人过：数字口径 / 槽位取舍 / 原声选取 / 标题候选
   ↓  build.py → 单文件 HTML（web 与 longpic 两态共用一份 outline）
   ↓  verify.py 六层断言
   ↓  render_longpic.py 三项排版断言 + 二维码解码
══ 闸门二 ══  人过：三视口截图 + 长图
   ↓  发布（可选适配器）
   ↓  REPORT.md，含「本次降级」段
```

两道闸门是刻意的。中间的 HTML 实现不打扰人，但**数字口径和最终观感必须人点头**。

---

## 设计要点

**视觉可换。** 组件只吃 19 个统一 CSS 令牌，零硬编码颜色 —— 契约测试会遍历注册表强制这一点，对 CSS 和渲染输出双向扫描。换设计系统 = 换一份 `tokens.css`，23 个组件一行不用动。

设计系统有三种进法：四件套文件（`.md` + `tokens.json` + `theme.css` + `variables.css`）、一段风格描述、或指一个前作页面反抽。规约器**先按语义变量名匹配**（`steel` 是弱文字、`abyss` 是凹陷、`ember-rust` 是强调色），名字解析不出的才退回亮度/饱和度启发式，并把每个令牌的来源（`name` / `heuristic` / `default`）列成表交人确认 —— 因为没有任何启发式能覆盖你随手拿来的设计系统。

**长图是独立媒介，不是网页截图。** 交互归零、左右改上下、手动断行、两端对齐、画布放宽到 430px、品牌元素重新称重、尾部自带闭环。这八条不是要 agent 记住的规则，而是**每个组件自带的模式变体** —— `cta-pills` 声明只支持 web，`qr-closure` 只支持长图，build 时自动换件；换不到又不支持就抛错，绝不静默丢内容。

**失败要响亮。** 缺料、模式不支持、断言不过一律抛异常并写清怎么修。设计前提是使用者可能是弱模型：它不会推理，不会权衡，会跳过一切写成"建议"的东西 —— 所以文档全是祈使句和可直接复制的命令，决策点收敛成表格。

---

## 目录

```
SKILL.md              路由与硬规则，只放这些
AGENTS.md             给非 Claude Code 的 Agent
references/
  skeleton-recap.md     战报 11 槽位
  skeleton-invite.md    邀请函 9 槽位
  skeleton-generic.md   通用对外页 4 槽位
  skeleton-campaign.md   campaign 骨架 8 槽位文档
  absorb-feishu.md      Feishu 碎片拉取清单与工程结构
  copy-layer.md         对外文案红线 + 去 AI 腔 + 标题三层法
  design-inject.md      三形态 → 19 统一令牌 + 冲突判例
  longpic.md            长图八条转换规则 + 三项断言 + 踩坑
  verify.md             assert.yaml 全字段 + 六层说明
  publish.md            发布纪律与降级路径
assets/
  preflight.py          能力检测
  verify.py             六层断言 CLI
  render_longpic.py     长图渲染 + 排版断言 + 二维码解码
  shots.py              三视口截图
  opb/                  引擎：数据契约 / 配置 / 断言层 / 设计系统 / 23 组件 / build
  presets/              两套兜底设计系统（战报向暗色 / 邀请函向）
example/demo-recap/  可直接跑的完整样例（虚构数据）
example/demo-campaign/  campaign 骨架的完整样例（虚构数据）
tests/                全量测试套件（含真实浏览器渲染，约 50s）
vendor/humanizer-zh/  去 AI 腔词表（MIT，归藏，译自 blader/humanizer）
```

---

## 依赖

**硬依赖**：Python ≥ 3.10、Playwright（+ chromium）、Pillow、PyYAML。

**软依赖**：OpenCV（二维码解码，缺则降级人工）。

**可选适配器**：拉碎片的 CLI、发布用的 CLI。都没有也能跑完整条链路 —— 碎片你手动放进 `absorb/`，产出的单文件 HTML 你自己发。

测试零联网、零外部依赖：

```bash
python3 -m unittest discover -s tests
```

---

## 已知边界

- 长图管线没有「系列」概念。超过 1:15 建议切成多张，但要自己写多份 outline，工具不会自动切。
- `link_hosts` 是精确主机名匹配，不做子域归一。
- 链接活性检查有网络时序波动，因此是 `WARN` 而非阻断 —— **一个三次里失败一次的阻断断言，会训练人「再跑一遍」，其他五层的可信度一起陪葬**。CI 或离线环境用 `link_check: skip`。
- `timeline-heartbeat` 假设 24 小时时间轴，跨天活动表达不了。
- 第 2 层（数字）不共享第 1/3/4 层的 `「」` 引用豁免。
- 手动 `<br>` 在 `section-head` / `talk-card` / `hook-grid` 的标题里不生效（会被 HTML 转义中和）。长图里标题太长就缩短它，让自然断行落在语义边界上。

---

## 出处

方法论蒸馏自连续多场线下活动的对外页面实践 —— 文案红线来自真实编辑的多轮返工意见，长图规则来自「长图不是网页截图」这个教训本身，断言层的每一条都对应一次真实事故（引用被拼接、内部口径上页、27 条死链通过了 `curl` 检查）。

`vendor/humanizer-zh/` 为 MIT 授权，原作者归藏，译自 [blader/humanizer](https://github.com/blader/humanizer)，保留原 LICENSE 与署名。

本仓库 MIT。
