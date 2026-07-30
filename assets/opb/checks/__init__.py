"""六层断言的上下文与注册表。"""
import glob, pathlib
from dataclasses import dataclass
from typing import Any
from ..textutil import strip_html, strip_quoted
from ..facts import load_facts, load_quotes
from ..blacklist import build as build_blacklist

@dataclass
class Ctx:
    html: str; text: str; text_noquote: str
    facts: dict; quotes: list; corpus: str; cfg: Any; blacklist: list

def build_ctx(cfg) -> Ctx:
    html = pathlib.Path(cfg.page).read_text(encoding="utf-8")
    text = strip_html(html)
    parts = []
    for pat in cfg.corpus_globs:
        for p in glob.glob(str(pathlib.Path(cfg.root) / pat), recursive=True):
            try:
                parts.append(pathlib.Path(p).read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                pass
    bl = build_blacklist(cfg.genre, cfg.blacklist.get("extra", []),
                         cfg.blacklist.get("unban", []),
                         cfg.blacklist.get("staff_names", []))
    return Ctx(html=html, text=text, text_noquote=strip_quoted(text),
               facts=load_facts(cfg.facts_path), quotes=load_quotes(cfg.quotes_path),
               corpus=" ".join(parts), cfg=cfg, blacklist=bl)

def layers():
    from . import quotes, numbers, jargon, aivoice, resources, structure
    return [("1 引用逐字", quotes.check), ("2 数字", numbers.check),
            ("3 黑话", jargon.check), ("4 AI 味", aivoice.check),
            ("5 资源与链接", resources.check), ("6 结构", structure.check)]
