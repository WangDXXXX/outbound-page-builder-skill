# vendor 授权边界

`vendor/` 下的两份副本仅供本人跨机自用，**不随本 Skill 对外分发**。分享 Skill 前必须按下表处置，否则会带着授权不明的内容一起分发出去。

| 目录 | 授权 | 能不能对外分发 | 分享前必须做的事 |
|---|---|---|---|
| `humanizer-zh/` | MIT（歸藏，译自 [blader/humanizer](https://github.com/blader/humanizer)）| 能——只要保留 `LICENSE` 与署名 | 不用做任何事，原样带走即可 |
| `wu-mengzhi-variety-copy/` | 无 LICENSE 文件、无确认可达的公开仓库 | **不能** | **先整个删除这个目录** |

## humanizer-zh

MIT 协议，版权人歸藏，翻译自 [blader/humanizer](https://github.com/blader/humanizer)（原始英文版）。`LICENSE` 文件已原样复制到 `vendor/humanizer-zh/LICENSE`，`README.md` 保留了完整署名声明。MIT 协议要求"在软件的所有副本或实质性部分中包含上述版权声明和本许可声明"——只要 `LICENSE` 文件和 `README.md` 里的署名段跟着目录一起走，这份 vendor 副本就是合规的，可以随 Skill 一起对外分发。

## wu-mengzhi-variety-copy

`vendor/wu-mengzhi-variety-copy/` 目录里没有 `LICENSE` 文件——不是遗漏，是源头本来就没有。它的来源是 `~/.codex/skills/wu-mengzhi-variety-copy`，在复制前是一个指向 `~/.codex/skills/` 的**软链**；`cp -RL`（大写 `-L`）把软链解引用成了真实文件——如果漏掉 `-L`，复制出来的会是一个指向另一个工具目录的死链，换一台机器就直接读不到内容。

它的 `README.md` 里出现过一个 GitHub 地址（`AAAAAAAJ/wu-mengzhi-variety-copy`），但本地目录既没有 `LICENSE` 文件，也没有任何可独立确认该地址内容、可达性与授权条款的证据——**按无授权处理**，不去猜测那个地址背后是什么条款。

**若要把本 Skill 分享出去，先整个删除 `vendor/wu-mengzhi-variety-copy/` 目录**，再检查 `assets/preflight.py` 的能力清单会如实报告这项软能力缺失（本就是设计要求，见 `references/publish.md` 的降级路径）。删除这一步不影响 Skill 能否正常运行：`references/copy-layer.md` 已经把 wu-mengzhi 的三招（三层结构 / 具象锚点 / 呼吸单位）与 Contrast pair 禁令蒸馏成独立小节，删除 vendor 目录后这份文档仍然独立可用、仍然是完整的写作依据。
