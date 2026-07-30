"""能力检测：任何产出动作之前先跑，把清单贴给用户。降级永不静默。"""
import importlib.util, shutil, sys, pathlib, unicodedata
from typing import NamedTuple

class Cap(NamedTuple):
    name: str; kind: str; ok: bool; detail: str; fallback: str; install: str

SKILLS_DIR = pathlib.Path.home() / ".claude" / "skills"

# 能力名到显示层级的映射（独立于 kind 的关键性）
_LAYER = {
    "python3": "渲染层",
    "playwright": "渲染层",
    "Pillow": "渲染层",
    "PyYAML": "渲染层",
    "opencv": "渲染层",
    "humanizer-zh": "文案层",
    "wu-mengzhi-variety-copy": "文案层",
    "lark-cli": "输入层",
    "magic-builder": "输出层",
}

def _mod(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False

def _skill(name):
    p = SKILLS_DIR / name
    return p.exists() and (p / "SKILL.md").exists()

def probe():
    py_ok = sys.version_info >= (3, 10)
    return [
        Cap("python3", "hard", py_ok, sys.version.split()[0], "", "brew install python@3.14"),
        Cap("playwright", "hard", _mod("playwright"), "", "",
            "pip install playwright && playwright install chromium"),
        Cap("Pillow", "hard", _mod("PIL"), "", "", "pip install pillow"),
        Cap("PyYAML", "hard", _mod("yaml"), "", "", "pip install pyyaml"),
        Cap("opencv", "soft", _mod("cv2"), "", "二维码改人工扫码确认", "pip install opencv-python"),
        Cap("humanizer-zh", "soft", _skill("humanizer-zh"), "",
            "用内置 references/copy-layer.md 的 AI 味词表", "从 vendor/humanizer-zh 复制并软链"),
        Cap("wu-mengzhi-variety-copy", "soft", _skill("wu-mengzhi-variety-copy"), "",
            "用内置三层法，标题候选少一套产出路径",
            "从 vendor/wu-mengzhi-variety-copy 复制并软链"),
        Cap("lark-cli", "adapter", bool(shutil.which("lark-cli")), "",
            "请把碎片文件手动放进 absorb/",
            "npm i -g @larksuite/cli && lark-cli auth login"),
        Cap("magic-builder", "adapter", bool(shutil.which("magic-builder")), "",
            "交付单文件 HTML，你自行发布", "npm i -g magic-builder"),
    ]

def degradations(caps):
    return [f"{c.name}：{c.fallback}" for c in caps if not c.ok and c.kind != "hard"]

def _display_width(s):
    """计算字符串的显示宽度（CJK 字符宽度为 2）。"""
    width = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width

def _pad_to_width(s, width):
    """填充字符串到指定显示宽度。"""
    current_width = _display_width(s)
    if current_width >= width:
        return s
    padding = width - current_width
    return s + " " * padding

def render(caps):
    lines = ["能力清单", "─" * 34]
    for c in caps:
        layer = _LAYER.get(c.name, "其他")
        mark = "✓" if c.ok else "✗"
        tail = f" → {c.fallback}" if not c.ok and c.fallback else ""
        # 使用显示宽度感知的填充
        layer_part = _pad_to_width(layer, 6)
        name_part = _pad_to_width(c.name, 24)
        lines.append(f"{layer_part} {name_part} {mark}{tail}")
    lines.append("─" * 34)
    miss = [c for c in caps if not c.ok]
    if miss:
        lines.append(f"缺 {len(miss)} 项。要我现在装吗？")
        for i, c in enumerate(miss, 1):
            name_part = _pad_to_width(c.name, 24)
            lines.append(f"  [{i}] {name_part} {c.install}")
    else:
        lines.append("全部就绪。")
    return "\n".join(lines)

if __name__ == "__main__":
    print(render(probe()))
