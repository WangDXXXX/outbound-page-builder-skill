import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
from opb import skeleton as S


def _outline(keys, genre="invite"):
    return {"genre": genre, "title": "t",
            "slots": [{"key": k, "components": []} for k in keys]}


INVITE_ALL = ["hero", "why_you", "agenda", "value", "people", "hook", "proof", "terms", "cta"]
RECAP_ALL = ["hero", "buzz", "opening", "vs_last", "who_came", "on_stage",
             "off_stage", "works", "survey", "heartbeat", "next"]
CAMPAIGN_ALL = ["hero", "context", "playbook", "reach", "results",
                "voices", "lessons", "next"]


class TestSkeleton(unittest.TestCase):
    def test_invite_has_9_slots(self):
        self.assertEqual(len(S.SKELETONS["invite"]), 9)

    def test_recap_has_11_slots(self):
        self.assertEqual(len(S.SKELETONS["recap"]), 11)

    def test_generic_has_4_slots(self):
        self.assertEqual(len(S.SKELETONS["generic"]), 4)

    def test_complete_outline_passes(self):
        self.assertEqual(S.validate_outline(_outline(INVITE_ALL), "invite"), [])

    def test_missing_required_slot_fails(self):
        out = S.validate_outline(_outline([k for k in INVITE_ALL if k != "cta"]), "invite")
        self.assertTrue(any("cta" in m for m in out))

    def test_missing_optional_slot_passes(self):
        self.assertEqual(S.validate_outline(_outline([k for k in INVITE_ALL if k != "hook"]),
                                            "invite"), [])

    def test_unknown_slot_fails(self):
        out = S.validate_outline(_outline(INVITE_ALL + ["bogus"]), "invite")
        self.assertTrue(any("bogus" in m for m in out))

    def test_slot_order_must_match_skeleton(self):
        bad = _outline(["cta"] + [k for k in INVITE_ALL if k != "cta"])
        self.assertTrue(any("顺序" in m for m in S.validate_outline(bad, "invite")))

    def test_unknown_component_name_fails(self):
        o = _outline(INVITE_ALL)
        o["slots"][0]["components"] = [{"name": "no-such", "data": {}}]
        self.assertTrue(any("no-such" in m for m in S.validate_outline(o, "invite")))

    def test_recap_requires_its_own_slots(self):
        self.assertEqual(S.validate_outline(_outline(RECAP_ALL, "recap"), "recap"), [])

    def test_campaign_has_8_slots(self):
        self.assertEqual(len(S.SKELETONS["campaign"]), 8)

    def test_campaign_complete_outline_passes(self):
        self.assertEqual(
            S.validate_outline(_outline(CAMPAIGN_ALL, "campaign"), "campaign"), [])

    def test_campaign_missing_results_fails(self):
        out = S.validate_outline(
            _outline([k for k in CAMPAIGN_ALL if k != "results"], "campaign"),
            "campaign")
        self.assertTrue(any("results" in m for m in out))

    def test_campaign_optional_slots_can_be_omitted(self):
        keys = [k for k in CAMPAIGN_ALL if k not in ("reach", "voices", "lessons")]
        self.assertEqual(
            S.validate_outline(_outline(keys, "campaign"), "campaign"), [])

    def test_campaign_slot_order_must_match_skeleton(self):
        bad = _outline(["next"] + [k for k in CAMPAIGN_ALL if k != "next"],
                       "campaign")
        self.assertTrue(any("顺序" in m for m in S.validate_outline(bad, "campaign")))


class TestSkeletonShapeRobustness(unittest.TestCase):
    """踩坑清单点名的那一条：outline["slots"] 与 components 是列表，调用方
    传成字典或字符串必须被明确拒绝，不能被当成列表悄悄迭代。Python 字符串
    本身可迭代、字典迭代给出的是键——不提前拦截的话，这些错误形状不会让
    validate_outline 干净地返回一条"这里应该是列表"的消息，而是在更深的
    地方冒出不知所云的 TypeError/AttributeError（甚至更糟：如果调用点不小心
    用 try/except 兜住了泛化异常，会被当成"验证通过"悄悄放行）。"""

    def test_outline_top_level_must_be_dict(self):
        out = S.validate_outline(["not", "a", "dict"], "invite")
        self.assertTrue(any("对象" in m for m in out))

    def test_slots_as_string_is_rejected_not_char_split(self):
        bad = {"genre": "invite", "title": "t", "slots": "hero"}
        out = S.validate_outline(bad, "invite")
        self.assertTrue(any("列表" in m for m in out),
                         f"字符串形式的 slots 必须被拒绝且不崩溃，实际返回 {out}")

    def test_slots_as_dict_is_rejected(self):
        bad = {"genre": "invite", "title": "t", "slots": {"hero": {}}}
        out = S.validate_outline(bad, "invite")
        self.assertTrue(any("列表" in m for m in out),
                         f"字典形式的 slots 必须被拒绝且不崩溃，实际返回 {out}")

    def test_components_as_string_is_rejected_not_char_split(self):
        bad = {"genre": "invite", "title": "t",
               "slots": [{"key": "hero", "components": "sysbar"}]}
        out = S.validate_outline(bad, "invite")
        self.assertTrue(any("列表" in m for m in out),
                         f"字符串形式的 components 必须被拒绝且不崩溃，实际返回 {out}")

    def test_slot_entry_that_is_not_an_object_is_rejected(self):
        bad = {"genre": "invite", "title": "t", "slots": ["hero", "why_you"]}
        out = S.validate_outline(bad, "invite")
        self.assertTrue(any("对象" in m for m in out))

    def test_component_name_wrong_type_is_rejected(self):
        bad = {"genre": "invite", "title": "t",
               "slots": [{"key": "hero", "components": [{"name": 123, "data": {}}]}]}
        out = S.validate_outline(bad, "invite")
        self.assertTrue(any("字符串" in m for m in out))

    def test_empty_substitute_block_is_rejected(self):
        """outline 写 "longpic": {} 是"给了一个残缺替身"，不是"没给"——两者
        必须分开处理。brief 原实现用 `if a and a.get("name") not in comps`
        这种 truthy 判断，空字典是 falsy，会被当成"没给"悄悄放过校验，
        残缺替身要等到 build() 更深处才会以更难懂的错误炸出来。这里直接
        证明校验层本身就会拦住它。"""
        o = _outline(INVITE_ALL)
        o["slots"][-1]["components"] = [
            {"name": "cta-pills", "data": {}, "longpic": {}}]
        out = S.validate_outline(o, "invite")
        self.assertTrue(any("longpic" in m and "替身" in m for m in out),
                         f"空字典替身块必须被拦住，实际返回 {out}")


if __name__ == "__main__":
    unittest.main()
