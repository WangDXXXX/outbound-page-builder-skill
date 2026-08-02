# 输入层：把你的飞书复盘弄进 absorb/

## 先选路径（决策表）

| 你的情况 | 走哪条 |
|---|---|
| 愿意装 CLI，数据量大/要反复跑 | 路径 A：lark-cli 拉取 |
| 不想装任何东西，或路径 A 任一步报错 | 路径 B：手动导出（100% 走得通） |

## 路径 A：lark-cli 拉取（你自己的飞书账号）

安装 CLI，用你自己的飞书账号登录：

```bash
npm i -g @larksuite/cli
lark-cli auth login --domain docs,drive
```

`lark-cli auth login` 不带 `--domain` 会直接报错「please specify the scopes to authorize」——新版本不给默认权限范围，必须显式指定。`--domain docs,drive` 覆盖下面两条导出命令要用到的权限。命令会阻塞，终端打印一行「在浏览器中打开以下链接进行认证」加一个授权链接；把链接复制进浏览器，用你自己的飞书账号登录同意后，终端会自动检测到授权完成并结束阻塞，不需要管理员，不需要建应用。登录状态存在本机 `~/.lark-cli/config.json` 里，之后不用重复登录。

建好落地目录：

```bash
mkdir -p absorb
```

复盘文档导出成 Markdown：

```bash
# 换成你自己的复盘文档链接
lark-cli drive +export --url "https://example.feishu.cn/docx/doccnExampleToken123" --file-extension markdown --output-dir absorb --file-name 复盘.md
```

多维表格导出成 CSV：

```bash
# 换成你自己的多维表格链接；table= 后面那串（tbl 开头）就是下面的 --sub-id
lark-cli drive +export --url "https://example.feishu.cn/base/bascnExampleToken123?table=tblExampleTableId" --file-extension csv --sub-id tblExampleTableId --output-dir absorb --file-name 数据.csv
```

两条命令都不用手写 `--doc-type`——传 `--url` 时 CLI 会从链接路径自动识别是 `docx` 还是 `bitable`。`--sub-id` 是必填的：一张多维表格里通常不止一张分表，CLI 需要你指定具体导出哪一张。打开你要导的那张分表页签，地址栏 `table=` 后面那一串（`tbl` 开头）就是这个值；地址栏没有 `table=` 就点一下左侧任意一张分表，它会自动补上。

跑完看一眼文件有没有落地：

```bash
ls absorb/
```

## 路径 B：手动导出

| 数据 | 在飞书里怎么导 | 放到哪 |
|---|---|---|
| 复盘文档 | 文档右上 ⋯ → 下载为 → Markdown | absorb/复盘.md |
| 多维表格 | 表格右上 ⋯ → 导出 → CSV | absorb/数据.csv |
| 群聊金句 | 逐条复制粘贴进一个 txt | absorb/原声.txt |

## 权限排错

| 症状 | 原因 | 处置 |
|---|---|---|
| `auth login` 报错「please specify the scopes to authorize」 | 没带 `--domain`，新版本不给默认权限范围 | 重新执行 `lark-cli auth login --domain docs,drive` |
| 403 / 无权限 | 文档不是你的或没开分享 | 让文档 owner 给你阅读权限，或走路径 B |
| `+export` 报缺 `--sub-id` | 多维表格默认要求指定具体分表 | 按上面「多维表格导出成 CSV」那段，从 `table=` 后面拿分表 ID 填进 `--sub-id` |
| 下载按钮灰 | 租户管理员关了导出 | 只能走路径 A；A 也不行就把内容复制成 txt 存进 absorb/ |
