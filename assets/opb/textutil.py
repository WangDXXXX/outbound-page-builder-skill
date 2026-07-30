import re, html as _html

_SCRIPT = re.compile(r"<script.*?</script>", re.S)
_STYLE = re.compile(r"<style.*?</style>", re.S)
_TAG = re.compile(r"<[^>]+>")
_QUOTED = re.compile(r"「[^」]*」")
_WS = re.compile(r"\s+")

def strip_html(html: str) -> str:
    t = _SCRIPT.sub(" ", html)
    t = _STYLE.sub(" ", t)
    t = _TAG.sub(" ", t)
    return _html.unescape(t)

def norm(s: str) -> str:
    return _WS.sub("", s)

def strip_quoted(text: str) -> str:
    return _QUOTED.sub(" ", text)
