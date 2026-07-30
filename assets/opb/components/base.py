"""组件注册表。三条铁律：
1) 零硬编码颜色，只吃统一令牌；
2) 长图变体是组件自带属性，不是转换步骤；
3) 每个组件声明所需 facts 槽位，缺料立即报而不是等断言阶段。"""
import html as _html
from dataclasses import dataclass, field
from typing import Callable

class ComponentError(Exception):
    pass

class ModeUnsupported(ComponentError):
    pass

class SlotMissing(ComponentError):
    pass

@dataclass(frozen=True)
class Component:
    name: str
    slots: tuple
    css: str
    render: Callable
    modes: tuple = ("web", "longpic")

_REGISTRY: dict = {}

def register(c: Component) -> None:
    if c.name in _REGISTRY:
        raise ComponentError(f"组件 `{c.name}` 重复注册")
    _REGISTRY[c.name] = c

def get(name: str) -> Component:
    if name not in _REGISTRY:
        raise ComponentError(f"未知组件 `{name}`，已注册：{sorted(_REGISTRY)}")
    return _REGISTRY[name]

def all_components() -> dict:
    return dict(_REGISTRY)

def esc(s) -> str:
    return _html.escape(str(s), quote=True)

def render(name: str, data: dict, mode: str = "web") -> str:
    c = get(name)
    if mode not in c.modes:
        raise ModeUnsupported(f"组件 `{name}` 不支持 {mode} 模式（声明为 {c.modes}）")
    missing = [s for s in c.slots if s not in data]
    if missing:
        raise SlotMissing(f"组件 `{name}` 缺槽位 {missing}")
    return c.render(data, mode)

def collect_css(names) -> str:
    seen, out = set(), []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        css = get(n).css.strip()
        if css:
            out.append(f"/* {n} */\n{css}")
    return "\n".join(out)
