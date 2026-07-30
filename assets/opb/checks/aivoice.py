"""层4 AI 味：humanizer 词表转正则 + 「我们」词频 + 句长方差。
这是历史 verify 脚本完全没有的一层——原来全靠肉眼。"""
import pathlib, re, statistics
import yaml

_DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "ai_patterns.yaml"
_CONTRAST_IDS = {"contrast_pair", "contrast_pair_bing_fei",
                 "contrast_pair_yushuo", "contrast_pair_bushi_shi",
                 "contrast_pair_bushi_shi_no_er", "contrast_pair_bingfei_shi_no_er"}
_SENT = re.compile(r"[。！？；]")

def load_patterns() -> dict:
    """从 YAML 文件加载 AI 味模式定义。

    Returns:
        包含 regex 和 words 列表的字典
    """
    return yaml.safe_load(_DATA.read_text(encoding="utf-8"))

def _allow_spans(allow: list[dict], text: str) -> tuple[list[tuple[int, int, str, str]], list[dict]]:
    """把 `copy.allow` 的每条豁免条目在 text 里的全部出现位置摊平成 (start, end,
    reason, text) 元组列表，供逐个命中做区间归属判断——只做精确子串查找，不支持
    正则或模糊匹配（协调者原话：正则会让一条豁免悄悄豁免掉一整个家族）。

    同一条 text 可能在页面上出现不止一次（理论上），每次出现都单独登记一个区间，
    这样"这句话的这一次出现被豁免了，另一次出现（如果真的重复）依然要按各自
    位置判断"——但更常见、也是本函数真正要防的情况是：一条豁免只精确覆盖它
    自己包住的那段字符，页面上任何其他位置的同款句式（哪怕文字很像）都不在
    这个区间列表里，命中判断会在下一步用区间包含关系自然排除掉它们。

    返回 (spans, stale)：spans 是摊平的区间列表；stale 是一个都没在 text 里
    出现过的豁免条目（用于陈旧检测，不阻断构建，只报 WARN）。"""
    spans = []
    stale = []
    for a in allow:
        t = a["text"]
        found = False
        start = 0
        while True:
            idx = text.find(t, start)
            if idx == -1:
                break
            spans.append((idx, idx + len(t), a["reason"], t))
            found = True
            start = idx + 1
        if not found:
            stale.append(a)
    return spans, stale

def _exempt_reason(start: int, end: int, spans: list[tuple[int, int, str, str]]):
    """命中区间 [start,end) 是否整段落在某条豁免区间内部——用的是"完全包含"，
    不是"有交集"：一处反差句式如果只有一半文字恰好和豁免句重叠，那不是同一句
    话，不该被放过。找到就返回那条豁免的 reason，找不到返回 None。"""
    for s, e, reason, _ in spans:
        if start >= s and end <= e:
            return reason
    return None

def check(ctx) -> list[str]:
    """检查文本中的 AI 写作特征。

    Args:
        ctx: 包含 text_noquote（去掉引用的文本）、cfg.copy 配置的上下文对象

    Returns:
        失败消息列表。空列表表示通过。WARN 前缀的消息不阻断发布。
    """
    conf = ctx.cfg.copy
    if not conf.get("humanizer", True):
        return []

    pats = load_patterns()
    text = ctx.text_noquote  # 使用去掉引用的文本，与层3一致，豁免引用区内容
    allow = conf.get("allow", [])
    allow_spans, stale = _allow_spans(allow, text)
    fails = []
    exempt_count = 0

    # 检查正则模式：用 finditer 而不是 search——豁免必须只压住"落在豁免区间
    # 内的那一次命中"，同一条正则在页面别处再犯一次必须照样抓到；只查
    # 第一个匹配会在"第一次命中恰好被豁免"时把后面真正违规的命中漏掉，
    # 这正是协调者点名"这是会悄悄出错的部分"的那个坑。
    for r in pats.get("regex", []):
        # 对比构式可以通过配置禁用
        if r["id"] in _CONTRAST_IDS and not conf.get("ban_contrast_pair", True):
            continue
        for m in re.finditer(r["pattern"], text):
            reason = _exempt_reason(m.start(), m.end(), allow_spans)
            if reason:
                exempt_count += 1
                fails.append(
                    f"WARN AI 味[{r['id']}]（已豁免，理由：{reason}）: …{m.group(0)[:30]}…")
            else:
                fails.append(f"AI 味[{r['id']}] {r['desc']}: …{m.group(0)[:30]}…")

    # 检查词表：同样枚举全部出现位置，不是只查"在不在"——原因同上。
    for w in pats.get("words", []):
        for t in w["terms"]:
            start = 0
            while True:
                idx = text.find(t, start)
                if idx == -1:
                    break
                reason = _exempt_reason(idx, idx + len(t), allow_spans)
                if reason:
                    exempt_count += 1
                    fails.append(f"WARN AI 味[{w['id']}]（已豁免，理由：{reason}）: {t}")
                else:
                    fails.append(f"AI 味[{w['id']}] {w['desc']}: {t}")
                start = idx + 1

    # 检查「我们」出现频率（WARN不阻断，允许作者和读者判断）
    limit = conf.get("max_we", 5)
    n = text.count("我们")
    if n > limit:
        fails.append(f"WARN 「我们」出现 {n} 次，超过上限 {limit}——对外页面的主语是读者")

    # 检查句长均匀度（信号：机器生成的文本通常句长很均匀）
    sents = [s.strip() for s in _SENT.split(text) if len(s.strip()) >= 4]
    if len(sents) >= 6:
        sd = statistics.pstdev([len(s) for s in sents])
        if sd < 4:
            fails.append(f"WARN 句长过于均匀（标准差 {sd:.1f} < 4），读起来像机器")

    # 陈旧豁免：allow 条目在页面里一次都没命中——不阻断构建（协调者原话：
    # "do not fail the build over a stale exemption"），但要报出来方便清理，
    # 不然一条早就不适用的豁免会一直躺在 assert.yaml 里没人知道。
    for a in stale:
        fails.append(
            f"WARN copy.allow 条目未在页面命中，可能已过期，建议清理：「{a['text'][:30]}」"
            f"（理由：{a['reason']}）")

    # 豁免汇总：单条 WARN 已经各自带了理由，这里再给一个总数，让读报告的人
    # 一眼看到"这页一共放过了几处"，不用数上面到底有几条 WARN 是豁免类型。
    if exempt_count:
        fails.append(f"WARN 本页有 {exempt_count} 处经豁免的 AI 味发现，逐条见上方")

    return fails
