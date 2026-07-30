"""层3 黑话：基线+体裁+项目补充+组委姓名；引用区豁免；纯英文词做词边界匹配。"""
import re

def check(ctx) -> list[str]:
    """检查文本中是否包含黑名单中的术语（组委姓名走同一套扫描，见 blacklist.build）。

    Args:
        ctx: 包含 text_noquote（去掉引用的文本）、blacklist、cfg 的上下文对象

    Returns:
        失败消息列表。空列表表示通过。
    """
    text = ctx.text_noquote
    fails = []

    # ctx.blacklist 已经是 base+genre+extra+staff_names 合并、去重、应用过 unban
    # 之后的最终词表（见 assets/opb/blacklist.py build()）——一个组委姓名如果
    # 被正确 unban（带 reason）豁免了，根本不会出现在 ctx.blacklist 里，下面
    # 这个循环自然扫不到它，不需要为"已豁免"另开分支。这里只需要知道"命中的
    # 这个词是不是姓名"，用来选一条更准确的报错文案——是姓名就说人话
    # "组委姓名出现"，不是姓名就用原来的"内部词出现"，都算硬失败，都要报。
    staff = set(ctx.cfg.blacklist.get("staff_names") or [])

    # 检查黑名单中的术语
    for w in ctx.blacklist:
        # 纯英文词（ASCII + 数字 + 空格）做词边界匹配
        if re.fullmatch(r"[A-Za-z0-9 ]+", w):
            hit = re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])", text)
        else:
            # 中文或混合词做子串匹配
            hit = w in text

        if hit:
            if w in staff:
                fails.append(f"组委姓名出现: {w}（战报页面不得出现组委个人姓名，"
                             f"确需保留请在 blacklist.unban 里带 reason 显式豁免）")
            else:
                fails.append(f"内部词出现: {w}")

    # 战报（recap）必须配置人名列表——这条 WARN 只管"名单是不是空的"，
    # 不代表名单一填就万事大吉：填了才会真正进入上面的扫描循环。
    if ctx.cfg.genre == "recap" and not ctx.cfg.blacklist.get("staff_names"):
        fails.append("WARN blacklist.staff_names 为空——战报必须把组委人名列进去，"
                     "人名是项目专属的，基线表无法预置")

    return fails
