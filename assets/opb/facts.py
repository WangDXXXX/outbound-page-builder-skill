"""facts.json / quotes.json 加载与校验。caption 与 source 必填——
蓝军第6条(数字必须自证意义)与第8条(口径精准)靠这两个字段落地。"""
import json, pathlib
from dataclasses import dataclass
from typing import Any

class FactError(Exception):
    pass

@dataclass(frozen=True)
class Fact:
    key: str; value: Any; display: str; caption: str; source: str
    decided_by: str | None; compare_to: dict | None; public: bool; verified: bool

@dataclass(frozen=True)
class Quote:
    id: str; text: str; speaker: str; source_file: str
    link: str | None; why_picked: str

_QUOTE_REQUIRED = ("id", "text", "speaker", "source_file", "why_picked")

def load_facts(path: str) -> dict[str, Fact]:
    try:
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise FactError(f"{path} 不是合法 JSON：{e}") from e

    if not isinstance(raw, dict):
        raise FactError(f"{path} 顶层必须是对象，当前是 {type(raw).__name__}")

    out = {}
    for key, d in raw.items():
        # value: 检查存在性，允许假值（0、False、""等）但不允许 None
        if "value" not in d:
            raise FactError(f"fact `{key}` 缺必填字段 value")
        if d["value"] is None:
            raise FactError(f"fact `{key}` 的 value 不能为 null")

        # display: 检查存在性，必须是字符串或数字，转换为字符串，且非空
        if "display" not in d:
            raise FactError(f"fact `{key}` 缺必填字段 display")
        if not isinstance(d["display"], (str, int, float)):
            raise FactError(f"fact `{key}` 的 display 必须是字符串或数字，当前是 {type(d['display']).__name__}")
        if not str(d["display"]).strip():
            raise FactError(f"fact `{key}` 的 display 为空")

        # caption, source: 检查存在性，必须是字符串，且非空
        for f in ("caption", "source"):
            if f not in d:
                raise FactError(f"fact `{key}` 缺必填字段 {f}")
            if not isinstance(d[f], str):
                raise FactError(f"fact `{key}` 的 {f} 必须是字符串，当前是 {type(d[f]).__name__}")
            if not d[f].strip():
                raise FactError(f"fact `{key}` 的 {f} 为空")

        out[key] = Fact(
            key=key, value=d["value"], display=str(d["display"]),
            caption=d["caption"], source=d["source"],
            decided_by=d.get("decided_by"), compare_to=d.get("compare_to"),
            public=bool(d.get("public", False)), verified=bool(d.get("verified", False)),
        )
    return out

def load_quotes(path: str) -> list[Quote]:
    try:
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise FactError(f"{path} 不是合法 JSON：{e}") from e

    if not isinstance(raw, list):
        raise FactError(f"{path} 顶层必须是数组，当前是 {type(raw).__name__}")

    out = []
    for d in raw:
        # 所有必填字段都必须是字符串且非空
        for f in _QUOTE_REQUIRED:
            if f not in d:
                raise FactError(f"quote `{d.get('id', '?')}` 缺必填字段 {f}")
            if not isinstance(d[f], str):
                raise FactError(f"quote `{d.get('id', '?')}` 的 {f} 必须是字符串，当前是 {type(d[f]).__name__}")
            if not d[f].strip():
                raise FactError(f"quote `{d.get('id', '?')}` 的 {f} 为空")

        out.append(Quote(id=d["id"], text=d["text"], speaker=d["speaker"],
                         source_file=d["source_file"], link=d.get("link"),
                         why_picked=d["why_picked"]))
    return out
