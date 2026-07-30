import sys, tempfile, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import report as R
from opb.facts import Fact


def _fact(key, *, public, verified, display="628万", caption="覆盖场次×人均",
          source="后台导出 20260728"):
    """按 opb.facts.load_facts() 实际产出的 dict[str, Fact] 形状构造——不用
    裸 dict 假装，用真的 Fact frozen dataclass，字段缺一个都会在构造时炸开。"""
    return Fact(key=key, value=display, display=display, caption=caption, source=source,
                decided_by=None, compare_to=None, public=public, verified=verified)


def _out():
    return str(pathlib.Path(tempfile.mkdtemp()) / "REPORT.md")


class TestReportWrite(unittest.TestCase):
    """report.py 是「降级永不静默」这条项目级承诺唯一的落地点：任何缺失的
    可选依赖（没有 opencv 就解不出二维码、没有 lark-cli 就得手工放置碎片、
    没有 magic-builder 就没法自动发布）都必须出现在「本次降级」一节。这一层
    一旦悄悄不渲染，一次降级过的交付和一次干净交付会长得一模一样，读报告
    的人没有办法察觉——"Task 14/15 会跑到它"不等于"有测试守着它"，一次零
    降级的端到端跑通样例并不会触发这一节的渲染路径。"""

    def test_degradations_are_listed(self):
        """单行依据：`lines += [f"- {d}" for d in degradations]`——删掉这行，
        三条降级消息一条都不会出现在报告里（其余逻辑不受影响，是一处
        精确失效）。"""
        p = _out()
        degs = ["lark-cli 缺失：请把碎片文件手动放进 absorb/",
                "opencv 缺失：二维码改人工扫码确认",
                "magic-builder 缺失：交付单文件 HTML，你自行发布"]
        R.write(p, degradations=degs, verify={}, facts={})
        text = pathlib.Path(p).read_text(encoding="utf-8")
        for d in degs:
            self.assertIn(d, text, f"降级消息 {d!r} 必须原样出现在报告里")

    def test_no_degradations_renders_explicit_marker_not_absent_heading(self):
        """单行依据：`lines.append("无。全部依赖就绪。")`（if/else 的 else
        分支）——删掉这一行，`degradations=[]` 时「## 本次降级」标题仍然
        存在（它是在 if/else 之前无条件加的），但正文空白，和"这一节渲染
        坏掉了"长得一模一样，人没法分辨。所以这里两条都断言：标题要在，
        且要有明确的"无"字样，不能只查其中一个。"""
        p = _out()
        R.write(p, degradations=[], verify={}, facts={})
        text = pathlib.Path(p).read_text(encoding="utf-8")
        self.assertIn("## 本次降级", text, "标题本身不能因为没有降级就消失")
        self.assertIn("无", text, "必须有明确的'无降级'字样，不能只留一个空标题")

    def test_public_unverified_fact_surfaces_under_own_heading(self):
        """单行依据：拼 unverified 事实行的那条列表推导（`- {key} = ... 出处：
        {source}` 那行）——删掉这行（或让它产出空列表），标题可能还在，但
        fact 的 key 和 source 不会出现在报告里，读者没法知道具体是哪个
        数字、出处是什么。"""
        p = _out()
        facts = {"gmv": _fact("gmv", public=True, verified=False,
                               display="628万",
                               source="财务口径表 v3 · 李默拍板未留链接")}
        R.write(p, degradations=[], verify={}, facts=facts)
        text = pathlib.Path(p).read_text(encoding="utf-8")
        self.assertIn("口径未溯源", text, "必须有单独一节标出未溯源数字")
        self.assertIn("gmv", text, "必须点名是哪个 fact key")
        self.assertIn("财务口径表 v3 · 李默拍板未留链接", text, "必须点名出处")

    def test_fully_verified_facts_produce_no_such_heading(self):
        """单行依据：`unverified = [... if f.public and not f.verified]` 里的
        `not f.verified` 子句——把它弱化成只判 f.public，上一条测试会继续
        通过（它只要求"未核实事实出现"，不要求"核实过的事实不出现"），必须
        靠这条单独锁死。没有这条，上一条测试可以被"不管三七二十一，
        所有 public 事实都塞进这一节"这种更宽松、错误的实现蒙混过关。"""
        p = _out()
        facts = {"gmv": _fact("gmv", public=True, verified=True, display="628万")}
        R.write(p, degradations=[], verify={}, facts=facts)
        text = pathlib.Path(p).read_text(encoding="utf-8")
        self.assertNotIn("口径未溯源", text)

    def test_verify_results_grouped_by_layer_with_blocking_distinguished_from_warn(self):
        """单行依据：`mark = "❌" if hard else ("⚠️" if warn else "✅")`——
        删掉这行区分逻辑（比如统一写死成某个符号），硬失败和 WARN 会长得
        一样，读者分不出哪一层真的挡发布。这里额外用字符串位置断言"分组"
        这件事本身：每层自己的消息必须出现在自己的层标题之后、下一层标题
        之前，不能被拍平成一个跟层无关的大列表——只查"两个符号都出现过"
        查不出这种拍平错误。"""
        p = _out()
        verify = {
            "层1 引用逐字": ["缺引用来源：编造的一句话"],
            "层2 数字口径": ["WARN 我们用了 6 次"],
        }
        R.write(p, degradations=[], verify=verify, facts={})
        text = pathlib.Path(p).read_text(encoding="utf-8")
        self.assertIn("❌", text, "硬失败的层必须标红叉")
        self.assertIn("⚠️", text, "只有 WARN 的层必须标警告而不是红叉")
        i_layer1 = text.index("层1 引用逐字")
        i_msg1 = text.index("缺引用来源：编造的一句话")
        i_layer2 = text.index("层2 数字口径")
        i_msg2 = text.index("WARN 我们用了 6 次")
        self.assertTrue(
            i_layer1 < i_msg1 < i_layer2 < i_msg2,
            "每层的消息必须紧跟在自己的层标题之后、下一层标题之前"
            f"（实际顺序索引 {(i_layer1, i_msg1, i_layer2, i_msg2)}）")

    def test_mode_notes_appear_when_given(self):
        """单行依据：`lines += ["## 长图说明", ""] + [f"- {n}" for n in
        mode_notes] + [""]`——删掉这行，给了的长图说明不会出现在报告里。"""
        p = _out()
        R.write(p, degradations=[], verify={}, facts={},
                mode_notes=["长图去掉了跑马灯，改成静态引言卡片"])
        text = pathlib.Path(p).read_text(encoding="utf-8")
        self.assertIn("长图去掉了跑马灯，改成静态引言卡片", text)


class TestReportWriteShapeGuards(unittest.TestCase):
    """report.py 自己就是防"静默漏报"的最后一道闸，不能自己踩同一个坑——
    调用方手滑把 degradations/verify 某层的值传成一整句字符串而不是包着它的
    列表，Python 字符串本身可迭代，若不拦截会被按字符拆散，渲染出一份
    "看起来正常、内容全错"的报告而不报错——这正是本任务要防的"安静的
    错误输出"，比崩溃更危险。"""

    def test_degradations_as_bare_string_is_rejected_not_char_split(self):
        with self.assertRaises(TypeError):
            R.write(_out(), degradations="lark-cli 缺失", verify={}, facts={})

    def test_verify_layer_value_as_bare_string_is_rejected_not_char_split(self):
        with self.assertRaises(TypeError):
            R.write(_out(), degradations=[], verify={"层1": "缺引用来源"}, facts={})


if __name__ == "__main__":
    unittest.main()
