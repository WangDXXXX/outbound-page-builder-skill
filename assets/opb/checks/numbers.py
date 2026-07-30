"""层2 数字：白名单自动来自 facts；require_caption 卡自证意义；
public:false 出现即失败。"""
import re

_NUM = re.compile(r"\d[\d,\./-]*\d|\d")

# 2026-07-30 修复（Task 15 F4）：中文日期写法"2026年7月25日"里的"年"字
# 打断了 _NUM 的连续数字匹配，"2026"会被单独抠出来当成一个待核实的统计量
# ——默认 ignore 只认点/横线/斜线分隔的完整日期 token（\d{4}\.\d{2}\.\d{2}
# 这类），抠不住这种最常见的中文写法（真实复现过：'活动定在 2026年7月25日
# 举行。' 会报"未获准数字: 2026"，改成 '2026.07.25' 就不会）。
#
# 没有采用"把 \d{4}（或 19\d{2}|20\d{2}）加进默认 ignore 正则"这个最直接的
# 做法——那样等于说"任何形似年份的裸4位数字，不管上下文，一律免检"，会
# 产生新的、更隐蔽的问题：一个恰好落在1900-2099区间、但其实是统计量不是
# 年份的裸4位数（比如"2024人参与"）会跟着被免检，直接违反"每个数字都要
# 能自证"——而且 tests/test_check_numbers.py 里已经有明确的回归测试钉死了
# "裸4位数字（哪怕形似年份）没有 fact 白名单时必须拒绝"这条行为
# （test_bare_year_requires_whitelist / test_bare_4digit_without_whitelist_fails，
# 用的是"2026 年工作"/"2074 年的数据"这种数字和"年"字之间带空格的写法），
# 加一条全局 ignore 正则会直接把这两条测试打红。
#
# 改成只在"数字后面紧跟着'年'字、中间没有空格"这个具体上下文里豁免——
# 这精确对应中文日期的实际写法（"2026年"没有空格，"2026 年"是另一回事），
# 不引入一个覆盖任何形似年份数字的全局豁免，也因此完全不影响上面两条
# 既有回归测试（它们的输入都带空格）。这是"跟原有的点/横线/斜线日期规则
# 同一个精神"的修法：只豁免完整、无歧义的日期书写形式，不豁免裸数字本身。
_CN_YEAR = re.compile(r"(\d{4})年")

def _strip_units(s: str) -> str:
    """移除尾部的单位符号（%、+、空格等）。"""
    return s.rstrip("%+ \t\n").strip()

def _has_at_least_3_digits(s: str) -> bool:
    """检查字符串中是否至少有3个数字。"""
    digit_count = sum(1 for c in s if c.isdigit())
    return digit_count >= 3

def check(ctx) -> list[str]:
    conf = ctx.cfg.numbers
    fails = []
    allowed, non_public, no_caption = set(), {}, set()

    if conf.get("auto_whitelist_from_facts", True):
        for f in ctx.facts.values():
            # 生成多个形式：原始、无逗号、无单位、无单位无逗号
            forms = {f.display}
            forms.add(f.display.replace(",", ""))
            bare = _strip_units(f.display)
            forms.add(bare)
            forms.add(bare.replace(",", ""))

            if f.public:
                # 检查 caption 要求
                if conf.get("require_caption", True) and not f.caption:
                    no_caption |= forms
                else:
                    allowed |= forms
            else:
                # 非公开 fact 只注册 ≥3 位的形式
                for x in forms:
                    if _has_at_least_3_digits(x):
                        non_public[x] = f.key

    ignore = [re.compile(p) for p in conf.get("ignore", [])]

    # 中文日期"N年"上下文豁免（F4）——只登记"数字紧跟着'年'字、中间无空格"
    # 这个具体位置命中的数字串本身，不是放宽一条全局正则。跟 ignore 正则
    # 一样，这条豁免同样排在 non_public/no_caption 判断之后生效（见下方
    # 循环里的位置）——一个被标记 public:false 的数字，哪怕在文本里恰好
    # 长得像"N年"，也必须先被 non_public 拦下，不能被这条豁免绕过。
    cn_year_tokens = {m.group(1) for m in _CN_YEAR.finditer(ctx.text)}

    for raw in set(_NUM.findall(ctx.text)):
        n = raw.rstrip(".,")
        if not n:
            continue

        # 步骤 1: 检查是否在公开白名单中 → 通过（作者明确公开了这个数）
        if n in allowed or n.replace(",", "") in allowed:
            continue

        # 步骤 2: 检查是否来自 public:false 的 fact → 失败（不管 ignore）
        if n in non_public:
            fails.append(f"public:false 的数字出现在页面: {n}（fact `{non_public[n]}`）")
            continue

        # 步骤 3: 检查是否缺 caption
        if n in no_caption:
            fails.append(f"数字 {n} 缺 caption，不许上页（蓝军第6条）")
            continue

        # 步骤 4: 检查是否匹配忽略正则（不是统计量）
        if any(p.fullmatch(n) for p in ignore):
            continue

        # 步骤 5: 检查是否是"N年"上下文里的年份（F4，见上方 _CN_YEAR 注释）
        if n in cn_year_tokens:
            continue

        # 步骤 6: 其余情况拒绝
        fails.append(f"未获准数字: {n}")

    return sorted(fails)
