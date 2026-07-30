"""两套已验证的信息骨架 + 预留通用骨架。
槽位顺序即页面顺序——蓝军第10条要求按读者关心程度排序（奖状先于能用的东西，
高光先于流程），禁止按内部结构（组号/时间线/表结构）重排，所以顺序写死在这里，
不接受 outline 自己声明顺序。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    key: str
    required: bool


SKELETONS = {
    # 战报：发生了什么
    "recap": (
        Slot("hero", True), Slot("buzz", True), Slot("opening", False),
        Slot("vs_last", False), Slot("who_came", True), Slot("on_stage", True),
        Slot("off_stage", True), Slot("works", False), Slot("survey", False),
        Slot("heartbeat", False), Slot("next", True),
    ),
    # 邀请函：为什么你该来
    "invite": (
        Slot("hero", True), Slot("why_you", True), Slot("agenda", True),
        Slot("value", True), Slot("people", True), Slot("hook", False),
        Slot("proof", False), Slot("terms", True), Slot("cta", True),
    ),
    # 通用对外页：弱约束
    "generic": (
        Slot("hero", True), Slot("body", True),
        Slot("proof", False), Slot("cta", True),
    ),
}

# 本项目 23 个已注册组件里唯一一对"故意互为替身"的单模态组件。quote-ticker
# 这类没有替身的单模态组件不在这张表里——没有替身就是没有，不能靠这张表
# 硬凑一个不存在的候选（决策 D10：长图没有"时间"这个维度，quote-ticker 只能
# 删，不能退化成静态列表）。build.py 用它在报错文案里点出已知替身候选，
# 把"补一个替身"从抽象建议变成一个可以直接抄的名字。
CTA_SWAP = {"cta-pills": "qr-closure"}


def _components_registry() -> dict:
    """惰性导入：从 opb 包内部访问 .components.base 时，Python 会先跑一遍
    opb.components 包自己的 __init__（导入并注册 common/invite/recap 三个
    模块，二者共享同一个 base._REGISTRY 字典对象），所以这一次 import 就能
    拿到装满全部已注册组件的注册表——不需要在别处再补一次"确保加载"的导入，
    那种补法只是心理安慰，Python 的包导入顺序本来就保证了这件事。"""
    from .components.base import all_components
    return all_components()


def validate_outline(outline: dict, genre: str) -> list[str]:
    """校验 outline 的骨架合法性：genre 已知、槽位已知且顺序正确、必备槽位
    齐全、槽位内引用的组件（含 web/longpic 替身块）都是已注册组件。
    只返回失败信息列表，不抛异常——是否把非空列表当成硬失败、要不要在
    渲染前就拦下来，由调用方（build.build）决定。

    对形状的防御不是吹毛求疵：outline 来自人或 agent 手写的 JSON，
    slots/components 被手滑写成字符串或字典是完全可能发生的事——Python
    字符串本身可迭代、字典迭代给出的是键，如果这里不提前挡住，下面按
    列表处理的循环不会报"这里应该是列表"，而是在更深的地方冒出不知所云的
    TypeError/AttributeError。"""
    if not isinstance(outline, dict):
        return [f"outline 必须是对象，收到 {type(outline).__name__}"]
    if genre not in SKELETONS:
        return [f"未知 genre `{genre}`，只支持 {list(SKELETONS)}"]
    spec = SKELETONS[genre]
    order = [s.key for s in spec]
    known = set(order)

    raw_slots = outline.get("slots", [])
    if not isinstance(raw_slots, list):
        return [f"outline.slots 必须是列表，收到 {type(raw_slots).__name__}"]

    fails: list[str] = []
    given: list = []
    for i, s in enumerate(raw_slots):
        if not isinstance(s, dict):
            fails.append(f"outline.slots[{i}] 必须是对象，收到 {type(s).__name__}")
            continue
        key = s.get("key")
        if not isinstance(key, str):
            fails.append(f"outline.slots[{i}].key 必须是字符串，收到 {type(key).__name__}")
            continue
        given.append(key)
        if key not in known:
            fails.append(f"未知槽位 `{key}`，{genre} 只有 {order}")

    for s in spec:
        if s.required and s.key not in given:
            fails.append(f"缺必备槽位 `{s.key}`")

    valid_given = [k for k in given if k in known]
    if valid_given != sorted(valid_given, key=order.index):
        fails.append(f"槽位顺序错误，必须按 {order}")

    comps = _components_registry()
    for s in raw_slots:
        if not isinstance(s, dict):
            continue  # 形状错误已在上面报过，这里不重复报
        slot_key = s.get("key", "?")
        raw_components = s.get("components", [])
        if not isinstance(raw_components, list):
            fails.append(
                f"槽位 `{slot_key}` 的 components 必须是列表，"
                f"收到 {type(raw_components).__name__}")
            continue
        for c in raw_components:
            if not isinstance(c, dict):
                fails.append(
                    f"槽位 `{slot_key}` 的组件条目必须是对象，"
                    f"收到 {type(c).__name__}")
                continue
            name = c.get("name")
            if not isinstance(name, str):
                fails.append(
                    f"槽位 `{slot_key}` 的组件条目 `name` 必须是字符串，"
                    f"收到 {type(name).__name__}")
            elif name not in comps:
                fails.append(f"槽位 `{slot_key}` 引用未知组件 `{name}`")
            for alt in ("longpic", "web"):
                # 用「键存在且非 None」判断"是否给了替身"，不用 truthy——
                # outline 里写 "longpic": {} 是"给了一个残缺替身"，不是
                # "没给"，两者必须分开处理。truthy 判断会把空字典当成
                # falsy 悄悄放过，残缺替身要等到 build 阶段才会以一个更
                #难懂的错误炸出来，这正是"不用 if not x 判有效性"要防的事。
                if alt not in c or c[alt] is None:
                    continue
                a = c[alt]
                if not isinstance(a, dict):
                    fails.append(
                        f"槽位 `{slot_key}` 的 {alt} 替身必须是对象，"
                        f"收到 {type(a).__name__}")
                    continue
                alt_name = a.get("name")
                if not isinstance(alt_name, str):
                    fails.append(
                        f"槽位 `{slot_key}` 的 {alt} 替身缺合法的 `name` 字段，"
                        f"收到 {type(alt_name).__name__}")
                elif alt_name not in comps:
                    fails.append(f"槽位 `{slot_key}` 的 {alt} 替身 `{alt_name}` 未知")
    return fails
