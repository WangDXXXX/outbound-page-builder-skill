"""assert.yaml 加载。路径一律相对 config 文件所在目录解析。"""
import pathlib
from dataclasses import dataclass, field
import yaml

class ConfigError(Exception):
    pass

GENRES = ("recap", "invite", "generic", "campaign")
LINK_CHECK_VALUES = ("browser", "curl", "skip")

_NUMBERS_DEFAULT = {"auto_whitelist_from_facts": True, "require_caption": True,
                    "ignore": [r"\d{1,2}", r"\d{4}\.\d{2}\.\d{2}", r"\d{4}-\d{2}-\d{2}", r"\d{4}/\d{2}/\d{2}"]}
_BLACKLIST_DEFAULT = {"base": True, "genre": True, "extra": [], "unban": [],
                      "exempt_zones": ["「」"], "staff_names": []}
_COPY_DEFAULT = {"humanizer": True, "max_we": 5, "ban_contrast_pair": True, "allow": []}

@dataclass
class Config:
    root: str; page: str; genre: str
    facts_path: str; quotes_path: str; corpus_globs: list[str]
    numbers: dict; blacklist: dict; copy: dict
    must_contain: list[str] = field(default_factory=list)
    link_hosts: list[str] = field(default_factory=list)
    asset_hosts: list[str] = field(default_factory=list)
    link_check: str = "browser"

def _validate_string(key: str, value, required: bool = True) -> str:
    """检查字符串字段。缺失/非字符串/空 分别报错。"""
    if value is None:
        if required:
            raise ConfigError(f"assert.yaml 缺必填键 `{key}`")
        return ""
    if not isinstance(value, str):
        raise ConfigError(f"assert.yaml `{key}` 期望字符串，收到 {type(value).__name__}")
    if not value:
        raise ConfigError(f"assert.yaml `{key}` 为空字符串，拒绝")
    return value

def _validate_list_of_strings(key: str, value, default=None):
    """检查字符串列表。缺失返回 default；非 list/元素非 str 报错。"""
    if value is None:
        return default if default is not None else []
    if not isinstance(value, list):
        raise ConfigError(f"assert.yaml `{key}` 期望列表，收到 {type(value).__name__}")
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ConfigError(f"assert.yaml `{key}[{i}]` 期望字符串，收到 {type(item).__name__}")
    return value

def _validate_dict(key: str, value, default: dict = None) -> dict:
    """检查映射字段。缺失返回 default；非 dict/某键为 null 报错。"""
    if value is None:
        return default if default is not None else {}
    if not isinstance(value, dict):
        raise ConfigError(f"assert.yaml `{key}` 期望映射，收到 {type(value).__name__}")
    for k, v in value.items():
        if v is None:
            raise ConfigError(f"assert.yaml `{key}.{k}` 为 null，拒绝（明确的空值易导致沉默的隐患）")
    return value

def _validate_copy_allow(value) -> list[dict]:
    """检查 `copy.allow`——第4层 AI 味豁免表，每项必须是 {text, reason} 且都非空。
    `reason` 缺失/空白直接拒绝，和 `blacklist.unban` 同一条纪律：没有理由的豁免
    是红线悄悄失效的方式，不能让人手滑或图省事就跳过这道手续。"""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"assert.yaml `copy.allow` 期望列表，收到 {type(value).__name__}")
    out = []
    for i, a in enumerate(value):
        if not isinstance(a, dict):
            raise ConfigError(
                f"copy.allow[{i}] 必须是对象（含 text 与 reason），当前是 {type(a).__name__}")
        text = a.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ConfigError(f"copy.allow[{i}].text 期望非空字符串，收到 {repr(text)}")
        reason = a.get("reason")
        if not isinstance(reason, str):
            raise ConfigError(
                f"copy.allow[{i}]（text=`{text}`）缺必填键 `reason`——没有理由的豁免不能通过")
        if not reason.strip():
            raise ConfigError(
                f"copy.allow[{i}]（text=`{text}`）的 reason 为空或仅空白，拒绝豁免")
        out.append({"text": text, "reason": reason})
    return out

def _merge(default: dict, given: dict | None) -> dict:
    """合并默认值与用户值。用户值覆盖默认值，但不递归。"""
    out = dict(default)
    if given:
        out.update(given)
    return out

def load_config(path: str) -> Config:
    p = pathlib.Path(path).resolve()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    root = p.parent

    # 必填字符串字段检查
    page = _validate_string("page", raw.get("page"), required=True)
    genre = _validate_string("genre", raw.get("genre"), required=True)
    facts = _validate_string("facts", raw.get("facts"), required=True)
    quotes = _validate_string("quotes", raw.get("quotes"), required=True)

    if genre not in GENRES:
        raise ConfigError(f"未知 genre `{genre}`，只支持 {GENRES}")

    # 可选字符串字段
    link_check = raw.get("link_check", "browser")
    if isinstance(link_check, bool):
        raise ConfigError(
            f"`link_check` 收到布尔值 {link_check}——YAML 会把 off/on/yes/no/true/false "
            f"解析成布尔量。想关闭链接检查请写 link_check: skip")
    if link_check not in LINK_CHECK_VALUES:
        raise ConfigError(f"link_check 取值 `{link_check}` 无效，只支持 {LINK_CHECK_VALUES}")

    # 列表字段检查（皆可缺省为空）
    corpus_globs = _validate_list_of_strings("corpus", raw.get("corpus"))
    must_contain = _validate_list_of_strings("must_contain", raw.get("must_contain"))
    link_hosts = _validate_list_of_strings("link_hosts", raw.get("link_hosts"))
    asset_hosts = _validate_list_of_strings("asset_hosts", raw.get("asset_hosts"))

    # 映射字段验证并合并默认值
    numbers = _validate_dict("numbers", raw.get("numbers"))
    numbers = _merge(_NUMBERS_DEFAULT, numbers)

    blacklist = _validate_dict("blacklist", raw.get("blacklist"))
    blacklist = _merge(_BLACKLIST_DEFAULT, blacklist)

    copy = _validate_dict("copy", raw.get("copy"))
    copy = _merge(_COPY_DEFAULT, copy)
    copy["allow"] = _validate_copy_allow(copy.get("allow"))

    return Config(
        root=str(root), page=str(root / page), genre=genre,
        facts_path=str(root / facts), quotes_path=str(root / quotes),
        corpus_globs=corpus_globs, numbers=numbers, blacklist=blacklist, copy=copy,
        must_contain=must_contain, link_hosts=link_hosts, asset_hosts=asset_hosts,
        link_check=link_check,
    )
