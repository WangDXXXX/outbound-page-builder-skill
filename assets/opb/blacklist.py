"""黑名单 = 基线 + 体裁差集 + 项目补充 + 组委姓名。unban 必须写 reason，
否则该字段会被当万能豁免用滥（北京战报禁「李默」，上海邀请函必须出现「王李默」）。

2026-07-30 修复（Task 15 F1）：`staff_names` 曾经只被 `checks/jargon.py` 读来判断
"是否为空"（为空发 WARN），从未真正参与扫描——组委姓名从来没有被这个机制拦住过，
填不填名单只影响 WARN 提示消不消失，跟页面正文里有没有出现人名毫无关系（用真实
执行验证过：staff_names 填了8个真名，页面正文写「现场由李默主持」，扫描结果零发现）。
本次把 staff_names 合并进 build() 返回的词表，让它真正进入 checks/jargon.py 的扫描
循环；同时复用同一条 unban 通道——组委姓名可以被豁免（例如"王李默（老默）"作为
讲者本人姓名出现在邀请函里），但跟其他词一样，必须写 reason，不能无理由放行。"""
import pathlib

class UnbanError(Exception):
    pass

_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

def _read(name):
    """读取词表文件。逐行处理：先 strip，跳过空行和注释行，切割内联注释。"""
    p = _DATA / name
    if not p.exists():
        return []
    terms = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        # 切割内联注释（从第一个未转义 # 开始）
        if " #" in ln:
            ln = ln.split(" #")[0].strip()
        terms.append(ln)
    return terms

def _strip_inline_comment(term: str) -> str:
    """从词中切割内联注释。"""
    if " #" in term:
        return term.split(" #")[0].strip()
    return term

def build(genre: str, extra: list[str], unban: list[dict],
          staff_names: list[str] = ()) -> list[str]:
    """合并黑名单：基线 + 体裁特定 + 项目补充 + 组委姓名，去重，应用 unban。

    合并顺序是 base → genre → extra → staff_names，staff_names 放在最后：
    四层里它最窄、最项目专属——不是"一类词"，是"一个具体的人"，比 extra
    （项目专属的一般性词汇，如场馆名/环节代号）更具体一级，所以排在其后，
    顺序上是"从通用到具体"递进。这个顺序不影响去重后 build() 返回什么
    （下面 out 列表的成员集合与顺序无关，扫描时是逐词判断"是否在文本里
    出现"，谁先谁后不影响任何一次判断的结果），只影响 out 列表本身的排列，
    纯粹是给读代码/读断言输出的人一个符合直觉的顺序。

    staff_names 与 base/genre/extra 三类词共用同一条 unban 豁免通道——一个
    组委姓名可以被豁免（例如"王李默（老默）"是讲者本人姓名，出现在邀请函
    里是合法的），但必须像其他 unban 条目一样写 reason，不能无理由放行。
    这里不做任何特殊分支，staff_names 就是并进 terms 列表、走同一套
    drop/dedup 逻辑，"是不是姓名"这件事对 build() 本身不重要，只对调用方
    （checks/jargon.py 想更精确地报错时）有意义。"""
    # 处理 extra 中的内联注释
    extra_terms = [_strip_inline_comment(t) for t in extra]
    staff_terms = [_strip_inline_comment(t) for t in staff_names]
    terms = (_read("jargon_base.txt") + _read(f"jargon_{genre}.txt")
             + extra_terms + staff_terms)
    drop = set()
    for i, u in enumerate(unban):
        # unban 的每一项必须是对象（映射）
        if not isinstance(u, dict):
            raise UnbanError(f"unban 的每一项必须是对象（含 term 与 reason），当前第 {i} 项是 {type(u).__name__}")
        # term 字段必须存在
        if "term" not in u:
            raise UnbanError("unban 条目缺必填键 `term`")
        term = u["term"]
        if not isinstance(term, str) or not term.strip():
            raise UnbanError(f"unban term 期望非空字符串，收到 {repr(term)}")
        # reason 字段必须存在且非空（strip 后）
        if "reason" not in u:
            raise UnbanError(f"unban `{term}` 缺必填键 `reason`")
        reason = u["reason"]
        if not isinstance(reason, str):
            raise UnbanError(f"unban `{term}` reason 期望字符串，收到 {type(reason).__name__}")
        if not reason.strip():
            raise UnbanError(f"unban `{term}` reason 为空或仅空白，拒绝豁免")
        drop.add(term)
    seen, out = set(), []
    for t in terms:
        if t in drop or t in seen:
            continue
        seen.add(t); out.append(t)
    return out
