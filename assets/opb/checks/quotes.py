"""层1 引用逐字：「」内 ≥8 字必须是语料精确子串（空白归一）。
铁律：改引用先在语料里找到原文复制粘贴，不许手打。"""
from ..textutil import norm

def _extract_top_level_quotes(text: str) -> list[str]:
    """提取文本中所有顶层「」配对。支持嵌套引号，不支持不平衡的括号。"""
    quotes = []
    depth = 0
    start = None
    unbalanced = []

    for i, c in enumerate(text):
        if c == "「":
            if depth == 0:
                start = i + 1
            depth += 1
        elif c == "」":
            depth -= 1
            if depth < 0:
                unbalanced.append(f"不平衡的「」：位置 {i}，多出的 」")
                depth = 0
            elif depth == 0 and start is not None:
                quotes.append(text[start:i])
                start = None

    if depth > 0:
        unbalanced.append(f"不平衡的「」：缺少 {depth} 个 」")

    return quotes, unbalanced

def check(ctx) -> list[str]:
    big = norm(ctx.corpus)
    fails = []

    quotes, unbalanced = _extract_top_level_quotes(ctx.text)
    fails.extend(unbalanced)

    for q in quotes:
        # 只检查 ≥8 字的引用
        if len(q) < 8:
            continue
        n = norm(q)
        if n in big or n.rstrip("。") in big:
            continue
        fails.append(f"引用未命中语料: {q[:50]}")

    return fails
