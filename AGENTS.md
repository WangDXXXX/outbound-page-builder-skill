# 给非 Claude Code 的 Agent

本仓库是一个 agent skill。不管你是什么 Agent（Codex / Cursor / 其他），入口一律是：

1. 通读 `SKILL.md`——它是唯一路由，硬规则全在里面。
2. 按 SKILL.md 第一条硬规则先跑 `python3 assets/preflight.py`，把能力清单
   原样贴给用户。
3. 之后按 SKILL.md 的路由表读 `references/` 对应文档，照祈使句执行。
   所有质量规则都是程序断言（`assets/verify.py`），不依赖你的判断力。

两道人工闸门（SKILL.md 载明）不许跳过：闸门产物贴给用户，等确认再继续。
