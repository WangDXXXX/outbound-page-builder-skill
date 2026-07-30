"""交付报告。降级永不静默——preflight 的每个降级项都必须出现在这里；
facts 里 public 但 verified:false 的条目单独开一节标出来，防止"人工拍板过
但没留出处"的数字被后续引用当成已核实事实、悄悄被忘掉。

四个入参在动笔之前先做形状校验，不是吹毛求疵——本模块存在的唯一理由就是
"不能悄悄漏报"，如果调用方手滑把 degradations/mode_notes 传成一整句消息
字符串而不是包着它的 list[str]，Python 字符串本身可迭代，下面的列表推导会
把它按字符拆开，不会报错，只会渲染出一份看起来正常、内容全错的报告——
这比直接崩溃更危险，本模块自己不能踩这个坑。"""
import pathlib


def write(path: str, *, degradations, verify: dict, facts: dict, mode_notes=()) -> None:
    if not isinstance(degradations, (list, tuple)):
        raise TypeError(
            f"degradations 必须是 list[str]，收到 {type(degradations).__name__}"
            "（常见手滑：传了一整句消息字符串而不是包着它的列表——字符串本身"
            "可迭代，会被按字符拆散且不报错，报告会整份错但看起来没事）")
    if not isinstance(mode_notes, (list, tuple)):
        raise TypeError(f"mode_notes 必须是 list[str]，收到 {type(mode_notes).__name__}")
    if not isinstance(verify, dict):
        raise TypeError(f"verify 必须是 dict[str, list[str]]，收到 {type(verify).__name__}")
    if not isinstance(facts, dict):
        raise TypeError(f"facts 必须是 dict[str, Fact]，收到 {type(facts).__name__}")

    lines = ["# 交付报告", ""]

    lines += ["## 本次降级", ""]
    if degradations:
        lines += [f"- {d}" for d in degradations]
    else:
        lines.append("无。全部依赖就绪。")
    lines.append("")

    lines += ["## 断言结果", ""]
    for layer, msgs in verify.items():
        if not isinstance(msgs, (list, tuple)):
            raise TypeError(
                f"verify[{layer!r}] 必须是 list[str]，收到 {type(msgs).__name__}")
        hard = [m for m in msgs if not m.startswith("WARN")]
        warn = [m for m in msgs if m.startswith("WARN")]
        mark = "❌" if hard else ("⚠️" if warn else "✅")
        lines.append(f"- {mark} {layer}" + (f"（{len(hard)} 项未过）" if hard else ""))
        lines += [f"    - {m}" for m in msgs]
    lines.append("")

    # public 且 verified:false：人工拍板放上页但没留可追溯出处的数字。
    # 这条判定直接用 Fact.public/.verified 的布尔值，二者在 facts.load_facts
    # 里已经用 bool(d.get(...)) 规范化过，不存在"看起来假、实际有意义"的
    # falsy 歧义（不是那种 0/空字符串该不该算数的场景），这里判 truthy 是安全的。
    unverified = [f for f in facts.values() if f.public and not f.verified]
    if unverified:
        lines += ["## ⚠️ 口径未溯源的数字（勿在别处当已核实事实引用）", ""]
        lines += [f"- `{f.key}` = {f.display}（{f.caption}）　出处：{f.source}"
                  for f in unverified]
        lines.append("")

    if mode_notes:
        lines += ["## 长图说明", ""] + [f"- {n}" for n in mode_notes] + [""]

    pathlib.Path(path).write_text("\n".join(lines), encoding="utf-8")
