"""设计系统三形态 → 统一令牌层。
19 个令牌名是四份实例的公因式：暗底 + 一个配给制强调色 + 发丝线 +
mono 只做数字 +（可选）亮色反转段 +（可选）高潮色。

三阶段映射：
  1. 按名字线索（stage='name'）
  2. 启发式后备（stage='heuristic'）
  3. 内置默认（stage='default'）

映射跑完之后还有一道不算"猜角色"的必过关卡：`--font-cn` 服务中文正文，
必须包含能渲染中文的具名字体（references/design-inject.md 的硬规则，不是
偏好）。前三阶段只按变量名/亮度猜令牌该填哪个值，从不检查猜出来的字体
认不认识中文——纯西文设计系统（如 Ciridae 的 Pragmatica Cond，官方替代
字体 Oswald/Barlow Condensed 同样不含 CJK 字形）会心安理得地把自己的西文
展示字体塞进 --font-cn，中文渲染质量全交给浏览器的 generic 关键字
（system-ui 这类）现场决定。`_ensure_cjk_fallback()` 在三阶段映射之后
补一刀：命中任一具名 CJK 字体就不动，没命中就保留原 stack 第一个字体
（保住设计系统的西文识别度）、插入四款主流 CJK 字体、末尾收一个通用
sans-serif，并把 sources 打上 `+cjk-fallback` 后缀，让 `describe()` 的
复核表如实反映这个值被程序改过，不能让人以为它是设计系统的字面原文。
"""
import colorsys, pathlib, re

class ThemeError(Exception):
    pass

CANONICAL = [
    "--bg", "--bg-2", "--bg-sunken", "--fg", "--fg-2", "--fg-3", "--hair",
    "--accent", "--accent-2", "--invert-bg", "--invert-fg",
    "--font-cn", "--font-mono",
    "--radius-s", "--radius-m", "--radius-l", "--pad", "--gap", "--maxw",
]

# 阶段 1：名字线索映射
_NAME_HINTS = {
    "--bg": ["void", "canvas", "near-black", "base", "background", "page"],
    "--bg-2": ["surface", "card", "charcoal", "iron", "graphite", "elevated", "panel"],
    "--bg-sunken": ["abyss", "sunken", "well", "deep", "inset", "trough"],
    "--fg": ["pure-white", "almost-white", "white", "ink", "foreground", "primary"],
    "--fg-2": ["soft-white", "secondary", "muted", "subdued"],
    "--fg-3": ["steel", "ash", "tertiary", "faint", "subtle", "disabled", "weak"],
    "--accent": ["ember", "signal", "brand", "accent", "rust", "violet", "primary-brand"],
    "--accent-2": ["mist", "glow", "bloom", "lavender", "highlight", "climax"],
    "--invert-bg": ["bone", "paper", "cream", "sand", "light-surface"],
    "--hair": ["hairline", "divider", "rule", "border", "stroke"],
}

_VAR = re.compile(r"(--[\w-]+)\s*:\s*([^;}\n]+)")
_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

def _hsl(hex_):
    """将十六进制颜色转换为 HSL，返回 (hue, lightness, saturation)"""
    h = hex_.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return hh, ll, ss

def _collect(text):
    """从 CSS 文本中提取所有 CSS 变量（名称和值对）"""
    return {k: v.strip() for k, v in _VAR.findall(text)}

def _match_by_name(raw: dict) -> tuple[dict, dict]:
    """阶段 1：按名字线索匹配。
    返回 (matched_mapping, sources)，sources 值为 "name" 或缺失。
    仅考虑十六进制色值或字体变量。"""
    matched = {}
    sources = {}
    used_vars = set()

    # 对每个canonical令牌，按名字线索匹配
    for canonical, hints in _NAME_HINTS.items():
        best_var = None
        best_len = 0
        for var_name in raw:
            if var_name in used_vars:
                continue
            value = raw[var_name]
            # 只考虑色值或字体变量
            is_color = _HEX.match(value)
            is_font = var_name.startswith("--font")
            is_radius = var_name.startswith("--radius")

            if not (is_color or is_font or is_radius):
                continue

            var_lower = var_name.lower()
            for hint in hints:
                if hint in var_lower:
                    if len(hint) > best_len:
                        best_var = var_name
                        best_len = len(hint)

        if best_var:
            matched[canonical] = raw[best_var]
            sources[canonical] = "name"
            used_vars.add(best_var)

    return matched, sources

def _map_palette_heuristic(raw: dict, skip_tokens: set) -> dict:
    """阶段 2：启发式映射，仅用于未被名字线索填充的令牌"""
    colors = {k: v for k, v in raw.items() if _HEX.match(v)}
    if not colors:
        return {}

    by_light = sorted(colors.items(), key=lambda kv: _hsl(kv[1])[1])
    darks = [kv for kv in by_light if _hsl(kv[1])[1] < 0.5]
    lights = [kv for kv in by_light if _hsl(kv[1])[1] >= 0.5]
    sat = sorted(colors.items(), key=lambda kv: _hsl(kv[1])[2], reverse=True)
    accent = next((v for _, v in sat if 0.15 < _hsl(v)[1] < 0.75 and _hsl(v)[2] > 0.25), None)

    m = {}
    if "--bg" not in skip_tokens and darks:
        m["--bg"] = darks[min(1, len(darks) - 1)][1]
    if "--bg-sunken" not in skip_tokens and darks:
        m["--bg-sunken"] = darks[0][1]
    if "--bg-2" not in skip_tokens and darks:
        m["--bg-2"] = darks[min(2, len(darks) - 1)][1]
    if "--fg" not in skip_tokens and lights:
        m["--fg"] = lights[-1][1]
    if "--fg-2" not in skip_tokens and lights:
        m["--fg-2"] = lights[max(0, len(lights) - 2)][1]
    if "--fg-3" not in skip_tokens and lights:
        m["--fg-3"] = lights[0][1]
    if ("--invert-bg" not in skip_tokens or "--invert-fg" not in skip_tokens) and lights:
        pale = [v for _, v in lights if 0.75 <= _hsl(v)[1] < 0.97]
        if pale and "--invert-bg" not in skip_tokens:
            m["--invert-bg"] = pale[-1]
        if pale and "--invert-fg" not in skip_tokens:
            m["--invert-fg"] = darks[0][1] if darks else "#111111"
    if "--accent" not in skip_tokens and accent:
        m["--accent"] = accent

    return m

def _merge_mapping(name_matched: dict, heuristic: dict, raw: dict) -> tuple[dict, dict]:
    """合并三个阶段的结果并处理字体/圆角
    返回 (mapping, sources)"""
    m = dict(name_matched)
    sources = {k: "name" for k in name_matched}

    # 添加启发式结果
    for k, v in heuristic.items():
        if k not in m:
            m[k] = v
            sources[k] = "heuristic"

    # 处理字体
    fonts = {k: v for k, v in raw.items() if k.startswith("--font")}
    if "--font-mono" not in m:
        for k, v in fonts.items():
            if "mono" in k.lower():
                m["--font-mono"] = v
                sources["--font-mono"] = "name"
                break
    if "--font-cn" not in m:
        for k, v in fonts.items():
            m["--font-cn"] = v
            sources["--font-cn"] = "name"
            break

    # 处理圆角
    radius_map = {"sm": "--radius-s", "md": "--radius-m", "lg": "--radius-l"}
    for k, v in raw.items():
        if k.startswith("--radius"):
            suffix = k.rsplit("-", 1)[-1]
            canonical = radius_map.get(suffix)
            if canonical and canonical not in m:
                m[canonical] = v
                sources[canonical] = "name"

    return m, sources

_CJK_MARKERS = (
    "pingfang", "hiragino", "yahei", "simsun", "simhei", "stheiti", "stsong",
    "noto sans sc", "noto sans cjk", "source han", "wenquanyi", "cjk",
)

_CJK_FALLBACK = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC"'

def _has_cjk_family(font_stack: str) -> bool:
    """粗略但够用的检测：具名 CJK 字体的关键词是否出现在 stack 里。
    generic 关键字（system-ui/sans-serif/ui-sans-serif 这类）故意不算数——
    它们把"这个平台到底用哪个字体渲染中文"这件事完全交给浏览器现场决定，
    不是这份 tokens.css 对中文可读性的显式承诺，正是这条修复要堵住的口子。"""
    low = font_stack.lower()
    return any(marker in low for marker in _CJK_MARKERS)

def _ensure_cjk_fallback(mapping: dict, sources: dict) -> None:
    """原地修正 mapping['--font-cn']。命中任一具名 CJK 字体就什么都不做；
    没命中就保留原 stack 的第一个字体（保住设计系统的西文识别度），插入
    四款主流 CJK 字体，末尾收一个通用 sans-serif 兜底——不是简单把 CJK
    字体接在原 stack 末尾，因为原 stack 中间那些西文专属的 generic 关键字
    （ui-sans-serif/system-ui/-apple-system/BlinkMacSystemFont/...）加了
    具名 CJK 字体之后就是重复噪音，不删掉只会让 stack 越读越长却没有多
    一分中文覆盖的保证。"""
    if "--font-cn" not in mapping:
        return
    original = mapping["--font-cn"]
    if _has_cjk_family(original):
        return
    first = original.split(",")[0].strip()
    mapping["--font-cn"] = f"{first}, {_CJK_FALLBACK}, sans-serif"
    sources["--font-cn"] = sources.get("--font-cn", "default") + "+cjk-fallback"

def _check_invariants(mapping: dict):
    """检查硬不变量，违反则抛出 ThemeError"""
    # 强调色不能等于任何文字色
    if "--accent" in mapping:
        accent_val = mapping["--accent"].lower()
        text_slots = ["--fg", "--fg-2", "--fg-3"]
        for slot in text_slots:
            if slot in mapping and mapping[slot].lower() == accent_val:
                raise ThemeError(
                    f"--accent ({accent_val}) 与 {slot} ({mapping[slot].lower()}) 重复"
                )

    # 背景不能等于前景
    if "--bg" in mapping and "--fg" in mapping:
        if mapping["--bg"].lower() == mapping["--fg"].lower():
            raise ThemeError("--bg 不能等于 --fg")

    # 反转背景必须比主背景更亮
    if "--invert-bg" in mapping and "--bg" in mapping:
        inv_light = _hsl(mapping["--invert-bg"])[1]
        bg_light = _hsl(mapping["--bg"])[1]
        if inv_light <= bg_light:
            raise ThemeError(
                f"--invert-bg 亮度 {inv_light:.3f} 必须 > --bg 亮度 {bg_light:.3f}"
            )

def _map_palette_full(raw: dict) -> tuple[dict, dict]:
    """完整三阶段映射：名字 → 启发式 → 不变量检查
    返回 (mapping, sources)"""
    # 阶段 1
    name_matched, _ = _match_by_name(raw)
    skip_tokens = set(name_matched.keys())

    # 阶段 2
    heuristic = _map_palette_heuristic(raw, skip_tokens)

    # 合并与字体/圆角处理
    m, sources = _merge_mapping(name_matched, heuristic, raw)

    # --font-cn 必须有具名 CJK 字体兜底（硬规则，不是猜角色，不计入
    # name/heuristic/default 三阶段来源统计，命中时单独打 +cjk-fallback 标记）
    _ensure_cjk_fallback(m, sources)

    # 检查不变量
    _check_invariants(m)

    return m, sources

def from_fourpack(dir_: str) -> dict:
    """形态 A：从四件套目录读取 css/json/md 文件并映射色盘"""
    text = ""
    for p in sorted(pathlib.Path(dir_).glob("*")):
        if p.suffix.lower() in (".css", ".json", ".md"):
            text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
    if not text.strip():
        raise ThemeError(f"{dir_} 下没有 css/json/md 文件")
    m, _ = _map_palette_full(_collect(text))
    return m

def from_fourpack_detailed(dir_: str) -> tuple[dict, dict]:
    """形态 A 详细版：返回 (mapping, sources)
    sources 值为 "name"、"heuristic" 或 "default"（在 emit_tokens_css 中）"""
    text = ""
    for p in sorted(pathlib.Path(dir_).glob("*")):
        if p.suffix.lower() in (".css", ".json", ".md"):
            text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
    if not text.strip():
        raise ThemeError(f"{dir_} 下没有 css/json/md 文件")
    return _map_palette_full(_collect(text))

def from_prior_page(html_path: str) -> dict:
    """形态 C：从先前页面的 HTML 中提取 :root 变量"""
    text = pathlib.Path(html_path).read_text(encoding="utf-8")
    raw = _collect(text)
    direct = {k: v for k, v in raw.items() if k in CANONICAL}
    if direct:
        return direct
    m, _ = _map_palette_full(raw)
    return m

def validate(mapping: dict) -> list[str]:
    """检查缺失的令牌，返回缺失令牌名列表"""
    return [t for t in CANONICAL if t not in mapping]

_FALLBACK = {
    "--hair": "rgba(255,255,255,.12)", "--accent-2": "var(--accent)",
    "--font-cn": '"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif',
    "--font-mono": 'ui-monospace,"SF Mono",Menlo,Consolas,monospace',
    "--radius-s": "6px", "--radius-m": "10px", "--radius-l": "16px",
    "--pad": "20px", "--gap": "56px", "--maxw": "1240px",
}

def emit_tokens_css(mapping: dict) -> str:
    """生成 :root CSS 块，使用给定映射与内置备选值填充"""
    full = dict(_FALLBACK)
    full.update(mapping)
    lines = [f"  {t}: {full[t]};" for t in CANONICAL if t in full]
    return ":root {\n" + "\n".join(lines) + "\n}\n"

def describe(mapping: dict, sources: dict) -> str:
    """生成人类可读的映射表，显示每个令牌的来源"""
    lines = []
    for token in CANONICAL:
        value = mapping.get(token, _FALLBACK.get(token, "—"))
        source = sources.get(token, "default")
        lines.append(f"{token:15} {value:20} ← {source}")
    return "\n".join(lines)
