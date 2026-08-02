# `verify.py`：六层断言与 `assert.yaml` 字段表

`python3 assets/verify.py assert.yaml` 跑六层断言，读一个项目专属的 `assert.yaml`。断言引擎本身不变，会变的是每个项目的 `assert.yaml` 配置。

## 六层检查什么

| 层 | 名字 | 检查什么 | 实现文件 |
|---|---|---|---|
| 1 | 引用逐字 | `「」`内 ≥8 字的引用必须是语料（`corpus`）的精确子串，空白归一后比对 | `checks/quotes.py` |
| 2 | 数字 | 白名单自动来自 `facts.json`；`require_caption` 卡住没有 `caption` 的数字；`public:false` 的数字一旦出现在页面直接失败 | `checks/numbers.py` |
| 3 | 黑话 | 基线词表 + 体裁词表 + 项目补充词表；`「」`引用区豁免；`unban` 必须写 `reason` | `checks/jargon.py` |
| 4 | AI 味 | humanizer 词表转正则 + 「我们」词频 + 「不是 A 而是 B」及变体；同样豁免 `「」`引用区 | `checks/aivoice.py` |
| 5 | 资源与链接 | 资源必须来自获准域名或内联（`data:`）；链接域名白名单；外链缺 `noopener`——以上三条硬失败；链接活性按 `link_check` 指定的方式判断，**结果是 `WARN`，不阻断**（原因见下节） | `checks/resources.py` |
| 6 | 结构 | 必备元素（`must_contain`）是否齐全；有没有未替换的 `{{占位符}}`；内联 `<svg>` 是否有显式 `width` | `checks/structure.py` |

**`WARN` 前缀的发现不阻断交付**，退出码只在出现非 `WARN` 消息时才是 1。当前会产出 `WARN` 的场景：第 4 层「我们」超过 `max_we`、第 4 层句长过于均匀、第 3 层战报体裁没配 `staff_names`、第 5 层链接实测不可达。`WARN` 不阻断不等于可以不管——交付前仍然要看一遍 `WARN` 列表。

## 第 5 层链接活性为什么是 `WARN`，不是硬失败（Task 15 闸门二·第三轮）

第 5 层三条检查里，资源域白名单、链接域白名单、`noopener` 三条是纯字符串匹配（正则抠 host、查表），**同一份 `page.html` 配同一份 `assert.yaml`，今天判定的结果明天不会变**，符合硬失败的前提——硬失败必须是页面本身的确定性属性，不是"这一次跑出来怎样"。

但链接活性（`probe_links_browser()`）是一次真实的浏览器网络请求，读到的是"这一次访问在这一刻观测到的结果"，**不是页面的属性**。真实测过（详见 Task 15 闸门二报告"链接实测不可达"一节）：同一条链接，间隔几分钟重新访问，会在"活"与"死"之间切换，根因是目标站点的渲染时序、限流这类外部波动，不是页面内容出了问题——三轮完整校准里，三次判定死链的分别是三条不同的链接，同一份页面内容一个字没改。

一条硬失败如果三次里有一次无缘无故变红，人会学会"红了就重跑"；这个习惯一旦养成，会连带磨掉对其他五层（真正确定性的那些）红灯的信任。所以链接活性从硬失败降级为 `WARN`——**这不是关掉这层检查**，`probe_links_browser()` 依然会真实跑、依然比只看 HTTP 状态码强得多（能抓到登录墙/权限页这类"状态码 200 但内容不可达"的情况，`curl 200 是假绿`这条判断依据完全没变），只是"更强的信号"不等于"可以单方面挡发布"——`WARN` 仍然要求闸门二把结果人工看一遍，只是不再由一次网络波动决定这一轮构建算不算通过。

`link_check: skip` 在 CI 流水线或没有出网权限的离线环境下是**正确设置**，不是偷懒不检查——网络本来就不可用时，与其让第 5 层因为连不上网而产生一堆假死链 `WARN`，不如显式关掉，把链接活性验证挪到有网络的环境里单独跑一遍。

## `assert.yaml` 全字段表

```yaml
page: page.html
genre: invite                     # recap | invite | generic | campaign
facts: facts.json
quotes: quotes.json
corpus:
  - absorb/**/*.txt
  - absorb/**/*.md
  - absorb/**/*.json
  - corpus/**/*.md
  - minutes/**/transcript.txt

numbers:
  auto_whitelist_from_facts: true
  require_caption: true
  ignore: ['\d{1,2}', '2026\.\d{2}\.\d{2}']

blacklist:
  base: true
  genre: true
  extra: []
  unban:
    - {term: 王李默, reason: 讲者本人姓名，邀请函必需}
  exempt_zones: ['「」']
  staff_names: [王李默, 老默]

copy:
  humanizer: true
  max_we: 5
  ban_contrast_pair: true
  allow:
    - text: "AI 不是玩具，是生产工具"
      reason: 活动收官演示主线句，出处 absorb/复盘.md:12，负责人已确认使用

must_contain: []
link_hosts: []
asset_hosts: [magic-builder.tos-cn-beijing.volces.com]
link_check: browser
```

**`corpus` 每个扩展名单独写一行，不要用 shell 花括号展开 `absorb/**/*.{txt,md,json}` 这种写法。** Python 标准库 `glob` 模块不支持花括号展开（这是 bash 的语法，不是 Python `glob`/`fnmatch` 的语法）——写成花括号形式会静默匹配到空列表，`corpus` 变成空字符串，所有引用会全部因为"未命中语料"而报错，而且报错信息只会指向引用本身，看不出真正原因是配置项写错了。已经用真实 Python 解释器验证过这个差异：`glob.glob("absorb/**/*.{txt,md,json}")` 返回 `[]`，拆成三行分别写 `*.txt`/`*.md`/`*.json` 才会真正匹配到文件。

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `page` | ✅ | 字符串 | 要验的 HTML 文件路径，相对 `assert.yaml` 所在目录 |
| `genre` | ✅ | 字符串 | `recap` / `invite` / `generic` / `campaign` 四选一，决定体裁词表与是否要求 `staff_names`（`staff_names` 的空名单 WARN 只在 `recap` 触发，`campaign` 没有专属体裁词表文件，走 `base`+`extra`+`staff_names`） |
| `facts` | ✅ | 字符串 | `facts.json` 路径 |
| `quotes` | ✅ | 字符串 | `quotes.json` 路径 |
| `corpus` | 可缺省 | 字符串列表 | glob 模式列表，每个扩展名单独一行（见上）；缺省则语料为空，第 1 层所有引用都会失败 |
| `numbers.auto_whitelist_from_facts` | 可缺省，默认 `true` | 布尔 | 数字白名单是否自动从 `facts.json` 的 `display` 字段生成 |
| `numbers.require_caption` | 可缺省，默认 `true` | 布尔 | 白名单里的数字是否要求对应 fact 有非空 `caption` |
| `numbers.ignore` | 可缺省 | 正则字符串列表 | 不算"需要 caption 的统计量"的数字模式，例如日期、页码；中文日期"N年"这一种写法（数字紧贴"年"字，如"2026年"）不需要写进这里，`checks/numbers.py` 内建识别，见下节 |
| `blacklist.base` | 可缺省，默认 `true` | 布尔 | 是否加载基线词表（`assets/data/jargon_base.txt`） |
| `blacklist.genre` | 可缺省，默认 `true` | 布尔 | 是否加载体裁词表（`jargon_recap.txt` / `jargon_invite.txt`） |
| `blacklist.extra` | 可缺省 | 字符串列表 | 项目专属追加词，只能加不能减 |
| `blacklist.unban` | 可缺省 | 对象列表 | 每项 `{term, reason}`，`reason` 必填且不能是空白——减词必须写理由，见下节 |
| `blacklist.exempt_zones` | 可缺省，默认 `['「」']` | 字符串列表 | 黑话检查豁免的区域标记 |
| `blacklist.staff_names` | 战报体裁强烈建议填 | 字符串列表 | 组委/工作人员姓名，会被合并进层3实际扫描的词表（`assets/opb/blacklist.py` `build()`）——**填了才真正拦人名，不是只消掉 WARN**（2026-07-30 前的实现只用这个字段判断"是不是空"，从未真正扫描过，填了名单也拦不住任何人名出现在正文里，已修复，见下节）。战报体裁不填仍然会收到 WARN；`blacklist.unban` 可以豁免某一个姓名，但和其他词一样必须写 `reason`（例如某人以讲者身份合法出现在邀请函里） |
| `copy.humanizer` | 可缺省，默认 `true` | 布尔 | 是否跑第 4 层 AI 味检查 |
| `copy.max_we` | 可缺省，默认 `5` | 整数 | 正文「我们」次数上限，超限报 WARN |
| `copy.ban_contrast_pair` | 可缺省，默认 `true` | 布尔 | 是否检查「不是 A 而是 B」及变体 |
| `copy.allow` | 可缺省，默认 `[]` | 对象列表 | 第 4 层 AI 味豁免表，每项 `{text, reason}`，`reason` 必填且不能是空白——见下节 |
| `must_contain` | 可缺省 | 字符串列表 | 页面必须包含的文本片段（例如版权信息、备案号） |
| `link_hosts` | 可缺省 | 字符串列表 | 允许出现的外链域名白名单 |
| `asset_hosts` | 可缺省 | 字符串列表 | 允许出现的资源（图片/视频）域名白名单，`data:` 内联资源不受此限制 |
| `link_check` | 可缺省，默认 `browser` | 字符串 | `browser` / `curl` / `skip` 三选一，见下节 |

## `blacklist.staff_names` 真正参与扫描，不只是消掉 WARN（Task 15 F1）

`staff_names` 合并进 `blacklist.build()` 返回的词表，顺序是 `base → genre → extra → staff_names`（姓名放最后，是四层里最窄、最项目专属的一层）。合并之后它和其他黑话词走同一套逻辑：出现在正文（`「」`引用区豁免）就是硬失败，消息会明确写"组委姓名出现: X"（和普通黑话词的"内部词出现: X"分开措辞，方便一眼看出是哪一类问题）；`blacklist.unban` 可以豁免一个姓名，但必须写 `reason`，和减掉任何其他黑话词遵守同一条纪律（见下节）。

在这条修复之前，`staff_names` 只被 `checks/jargon.py` 读来判断"是否为空"（为空发 WARN），从未真正传给 `blacklist.build()`——填了名单，WARN 消失，但正文里真出现组委姓名照样零发现。真实撞到过这种情况：一位讲者自己的妙记逐字稿里恰好提到了一位组委的花名，如果不是人工发现并换用另一句发言，这处泄漏在旧实现下不会被任何断言拦住。

## `facts.json` 的 `compare_to` 字段由 `stat-caption` 渲染（Task 15 F3）

`facts.json` 每条 fact 可以带一个 `compare_to: {value, label}`，在闸门一"哪些数字要用 `compare_to`"讨论里经常被提到（蓝军第7条"对比>绝对值"）。**这个字段本身只被 `load_facts()` 解析进内存，不驱动任何断言**——真正让对比出现在页面上的，是 outline.json 里对应的 `stat-caption` 组件也带上同名的 `compare_to: {value, label}` 数据（两处手动保持一致，就像 `caption` 字段本来就需要 outline 和 facts.json 手动对齐一样）：

```json
{"name": "stat-caption", "data": {
  "value": "628", "label": "到场", "caption": "名册609+登记19",
  "compare_to": {"value": "297", "label": "杭州首届"}
}}
```

会渲染成"628 到场 ⋯ 较杭州首届 297"这样一行小字。`compare_to` 是可选槽位，不给就是老行为，历史产出（如 `sh-invite`）不需要改。

## `checks/numbers.py` 对中文日期"N年"的内建豁免（Task 15 F4）

中文日期"2026年7月25日"里的"年"字会打断数字连续匹配，"2026"被单独抠出来当成待核实的统计量——默认 `numbers.ignore` 只认点/横线/斜线分隔的完整日期（`\d{4}\.\d{2}\.\d{2}` 这类），认不出这种最常见的中文写法。`checks/numbers.py` 内建了一条独立于 `ignore` 配置的豁免：只要数字后面紧跟"年"字、中间没有空格（`\d{4}年`），这个数字串本身就不需要注册进 `facts.json`。

**这不是把 `\d{4}` 或 `19\d{2}|20\d{2}` 加进默认 `ignore` 正则**——那样等于任何形似年份的裸4位数字都免检，会连累一个恰好落在1900-2099区间、但其实是真实统计量的数字（例如"2024人参与"）。豁免只认"数字紧贴年字"这个具体上下文，"2026 年"（有空格）仍然需要在 `facts.json` 里注册。`public:false` 的保护不受这条豁免影响——一个标记为非公开的数字即使在文本里恰好长得像"N年"，仍然会先被非公开检查拦下。

## `facts.json` 的 `display` 必须是裸数字，不能带单位

第 2 层的白名单机制是把 `facts.json` 每条 `display` 字段整串注册成一个"合法数字"，再去页面正文里用正则 `\d[\d,\./-]*\d|\d` 抠数字比对——**这条正则只抠数字（含逗号/点/斜杠/连字符），不认识中文单位字符**。这意味着 `display` 写成 `"628 人"` 这种"数字+单位"的复合字符串时，白名单里存的是整串 `"628 人"`，但页面正文里"628 人"这四个字被抠出来的只有 `"628"`（"人"字不在正则字符集里，永远抠不出"628 人"这个组合）——`"628"` 和 `"628 人"` 是两个不同的字符串，白名单永远命中不了，这条数字在页面上**每一处**出现都会被拒。

**正确写法：`display` 只写裸数字（或数字+`%`/`+`这类会被 `_strip_units` 处理的符号），单位、场景说明全部放进 `caption`：**

```json
{"beijing_turnout": {"value": 628, "display": "628", "caption": "B 站次实际到场人数（人）", ...}}
```

不是：

```json
{"beijing_turnout": {"value": 628, "display": "628 人", "caption": "...", ...}}
```

复合口径的数字（例如"5000 人每人 10x，组织提效或许不到 1.2x"这类一句话里有多个统计量）要拆成多条独立 fact，每条 `display` 只放其中一个裸数字——页面正文里 `"5000"` 和 `"1.2"` 是两个分开的 token，各自需要能独立命中白名单，合并成一条复合 `display` 只会让两个数字都命中不了。

这条约定目前只体现在 `tests/test_check_numbers.py` 的测试夹具里（`_f("a", "628")` 这类调用），本节是它第一次被写进文档——Task 14 验收实测：初稿把好几条 fact 的 `display` 写成了"数字+单位"，六层断言第 2 层因此在还没查文档、只读了 `references/verify.md` 字段表的情况下大面积失败，回去读测试代码才找到这条约定。

## `unban` 必须写 `reason` 的理由

黑名单可以靠 `unban` 局部解禁某个词——但这个字段一旦允许空理由，会被当成万能豁免用滥：随手把卡断言的词都塞进 `unban` 就能全部通过，断言层名存实亡。`reason` 字段被设计成必填且拒绝空白字符串，逼着每一次解禁都留下一句能审查的理由（例如"王李默"在上海邀请函里被 `unban`，理由是"讲者本人姓名，邀请函必需"——这句理由本身就在说明为什么这次解禁是合理的，而不是图省事）。

## `copy.allow`：给第 4 层开一条精确的豁免通道，不是放宽规则

第 4 层（AI 味）的正则/词表是按"这类句式几乎总是 AI 腔"这个统计判断写的，但"几乎总是"不等于"永远"——一句话可能恰好撞上了黑名单模式，却是团队里的人认认真真写出来、并且已经签字确认要用的（例如：某场活动的收官演示主线句「AI 不是玩具，是生产工具」——团队认真写出、签字确认要用，却恰好命中黑名单模式）。这种时候不能靠"改宽正则"解决——放宽一条正则是全局生效的，会让**所有项目、所有页面**里长得像的句子一起免检，红线名存实亡。`copy.allow` 解决的是另一件事：**精确豁免这一句话，其他任何地方的同款句式继续拦**。

```yaml
copy:
  allow:
    - text: "AI 不是玩具，是生产工具"
      reason: 活动收官演示主线句，出处 absorb/复盘.md:12，负责人已确认使用
```

几条硬规则：

1. **`reason` 必填，缺失或空白直接 `ConfigError`**——和 `blacklist.unban` 同一条纪律（见上节）。没有理由的豁免是红线悄悄失效的方式。
2. **`text` 是精确子串，不是正则，不支持模糊匹配。** 只豁免这一段字符完全一致的文本，不会连带放过意思相近、写法不同的句子——这是"豁免一句话"和"放宽一条规则"的本质区别。
3. **只压住"命中范围完全落在这段豁免文字内部"的发现，页面别处的同款句式照样拦。** 实现上不能用"找到第一个匹配就看它是否被豁免"这种写法——如果第一个匹配恰好被豁免，用 `re.search` 式的"只找第一个"会让后面真正违规的命中被漏检。`aivoice.py` 用 `re.finditer`/全量位置扫描逐个判断，就是为了避免这个坑。
4. **命中一条豁免时不是silently消失，是降级成 `WARN` 并带上理由**，例如 `WARN AI 味[contrast_pair_bushi_shi_no_er]（已豁免，理由：活动收官演示主线句…）: …`。多条豁免命中时还会有一条汇总——`WARN 本页有 N 处经豁免的 AI 味发现，逐条见上方`，让读报告的人一眼看到这页放过了几处、各自为什么。
5. **`allow` 条目的文字如果在页面上根本没出现（陈旧豁免），不阻断构建，但会报 `WARN` 提示清理**——设计系统、文案改版之后，一条早就不适用的豁免不该继续静静地留在 `assert.yaml` 里没人知道。
6. **默认空列表，不写这个字段的项目行为和没有这个机制之前完全一样。**

**经验法则：豁免一句人已经看过、点头认可的具体句子；永远不要为了让某句话过审而放宽正则本身。** 前者是给一次人工判断留痕迹，后者是让判断权从人手里转移到正则手里——这个 Skill 的六层断言存在的意义就是替代不了人工判断的地方绝不冒充能替代，`copy.allow` 是这条原则在第 4 层的具体落地。

## `link_check` 三个取值，别写成 `off`

| 取值 | 行为 |
|---|---|
| `browser`（默认） | 用真实 Chromium 打开每个链接，读正文判断是否命中"登录"/"无权限"/"Not Found"/"404"这类死链特征 |
| `curl` | 只检查 HTTP 状态码 |
| `skip` | 完全不检查链接活性（本地测试、没有网络访问时用） |

**关闭链接检查要写 `skip`，不能写 `off`。** YAML 1.1 规范会把裸词 `off`/`on`/`yes`/`no`/`true`/`false` 全部解析成布尔量，`link_check: off` 读进来的不是字符串 `"off"`，是布尔 `False`——不在 `browser`/`curl`/`skip` 这三个合法取值里，`load_config` 会直接拒绝并报错点破这个 YAML 陷阱。

`curl 200` 是假绿：登录墙、无权限页面对任何请求都会返回 200，`curl` 只看状态码看不出这些。`browser` 模式会真正打开页面读正文内容，这是唯一能抓到"页面打得开但内容是登录墙"这种情况的判法。**没有特殊理由，不要把 `link_check` 从默认的 `browser` 改成 `curl`。**
