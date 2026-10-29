"""全部测试：字段校验、实例化、干跑、文档一致性。零依赖 unittest。"""
import json
import os
import subprocess
import sys
import unittest
from datetime import datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from botkit import schema, render, simulate  # noqa: E402
from botkit.validate import validate  # noqa: E402

GOOD = json.load(open(os.path.join(HERE, "instances", "example_params.json"), encoding="utf-8"))
TPL = json.load(open(os.path.join(HERE, "templates", "customer_ops_bot.json"), encoding="utf-8"))


def run_py(args, cwd=None):
    """跨平台子进程调用：强制 UTF-8 管道 + 明确解码。

    踩过的坑：宿主机若设了 PYTHONIOENCODING 或 locale 是 cp936，
    子进程输出与父进程解码会错位，中文变乱码、断言全红。
    这里把编码显式钉死，测试结果不再受宿主环境影响。
    """
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run([sys.executable] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          env=env, cwd=cwd or HERE)


def p(**kw):
    d = dict(GOOD)
    d.update(kw)
    return {k: v for k, v in d.items() if v is not None}


def codes(params):
    return sorted({e["code"] for e in validate(params)})


class TestSchema(unittest.TestCase):
    def test_field_count(self):
        self.assertEqual(len(schema.FIELD_SPECS), 16)

    def test_unique_names(self):
        names = [s["name"] for s in schema.FIELD_SPECS]
        self.assertEqual(len(names), len(set(names)))

    def test_kind_known(self):
        for s in schema.FIELD_SPECS:
            self.assertIn(s["kind"], schema.KINDS, s["name"])

    def test_enum_fields_declare_enum(self):
        for s in schema.FIELD_SPECS:
            if s["kind"] == "enum":
                self.assertTrue(s.get("enum"), s["name"])

    def test_optional_fields_have_default(self):
        for s in schema.FIELD_SPECS:
            if not s["required"]:
                self.assertIn("default", s, s["name"])

    def test_each_default_passes_own_check(self):
        from botkit.validate import _check
        for s in schema.FIELD_SPECS:
            if "default" in s:
                self.assertEqual(_check(s, s["default"]), [], s["name"])

    def test_every_field_has_desc(self):
        for s in schema.FIELD_SPECS:
            self.assertGreater(len(s.get("desc", "")), 3, s["name"])


class TestValidateRequired(unittest.TestCase):
    def test_good_passes(self):
        self.assertEqual(validate(GOOD), [])

    def test_each_required_missing_reported(self):
        for s in schema.FIELD_SPECS:
            if s["required"]:
                bad = {k: v for k, v in GOOD.items() if k != s["name"]}
                self.assertIn(s["name"], [e["field"] for e in validate(bad)], s["name"])

    def test_all_missing_at_once_not_short_circuit(self):
        self.assertGreaterEqual(len(validate({})), 7)

    def test_empty_string_treated_as_missing(self):
        self.assertIn("E_REQUIRED", codes(p(business_name="")))


class TestValidateTypes(unittest.TestCase):
    def test_int_type(self):
        self.assertIn("E_TYPE", codes(p(daily_cap="3")))

    def test_bool_is_not_int(self):
        self.assertIn("E_TYPE", codes(p(daily_cap=True)))

    def test_int_range_low(self):
        self.assertIn("E_RANGE", codes(p(daily_cap=0)))

    def test_int_range_high(self):
        self.assertIn("E_RANGE", codes(p(daily_cap=51)))

    def test_str_too_long(self):
        self.assertIn("E_RANGE", codes(p(business_name="x" * 61)))

    def test_enum_reject(self):
        self.assertIn("E_ENUM", codes(p(brand_tone="casual")))

    def test_email_reject(self):
        self.assertIn("E_EMAIL", codes(p(owner_email="limin@example")))

    def test_email_ok_subdomain(self):
        self.assertEqual(validate(p(owner_email="a.b@mail.example.co")), [])

    def test_tz_reject(self):
        self.assertIn("E_TZ", codes(p(timezone="Asia/Shanghia")))

    def test_tz_ok(self):
        self.assertEqual(validate(p(timezone="Europe/Berlin")), [])

    def test_list_type(self):
        self.assertIn("E_TYPE", codes(p(stages="新客,体验")))

    def test_list_item_type(self):
        self.assertIn("E_TYPE", codes(p(stages=["新客", 2])))

    def test_list_len_exact(self):
        self.assertIn("E_LEN", codes(p(quiet_hours=[21])))

    def test_list_item_range(self):
        self.assertIn("E_RANGE", codes(p(quiet_hours=[24, 8])))

    def test_empty_stage_rejected(self):
        self.assertIn("E_EMPTY", codes(p(stages=["新客", "  "])))

    def test_duplicate_stage_rejected(self):
        self.assertIn("E_DUP", codes(p(stages=["新客", "新客"])))


class TestCrossField(unittest.TestCase):
    def test_quiet_hours_all_day_rejected(self):
        self.assertIn("E_QUIET", codes(p(quiet_hours=[8, 8])))

    def test_weekly_below_daily_rejected(self):
        self.assertIn("E_CAP", codes(p(daily_cap=5, weekly_cap=3)))

    def test_entry_stage_must_exist(self):
        self.assertIn("E_STAGE", codes(p(entry_stage="流失")))

    def test_cadence_length_must_match_stages(self):
        self.assertIn("E_CADENCE", codes(p(cadence_hours=[24, 72])))

    def test_multiple_errors_listed_together(self):
        errs = validate(p(daily_cap=0, brand_tone="x", timezone="Bad/Zone"))
        self.assertGreaterEqual(len(errs), 3)


class TestUnknownAndDeprecated(unittest.TestCase):
    def test_typo_field_rejected_not_ignored(self):
        self.assertIn("E_UNKNOWN", codes(p(dailly_cap=3)))

    def test_deprecated_name_has_owner_hint(self):
        errs = validate(p(daily_limit=3))
        d = [e for e in errs if e["code"] == "E_DEPRECATED"]
        self.assertTrue(d)
        self.assertIn("daily_cap", d[0]["msg"])

    def test_unknown_allowed_when_not_strict(self):
        self.assertEqual(validate(p(dailly_cap=3), strict_unknown=False), [])


class TestRender(unittest.TestCase):
    def test_render_ok(self):
        inst, errs = render.render(TPL, GOOD)
        self.assertEqual(errs, [])
        self.assertTrue(inst["instance_id"].startswith("inst_"))

    def test_idempotent_same_params(self):
        a, _ = render.render(TPL, GOOD)
        b, _ = render.render(TPL, dict(reversed(list(GOOD.items()))))
        self.assertEqual(a["instance_id"], b["instance_id"])

    def test_different_params_different_id(self):
        a, _ = render.render(TPL, GOOD)
        b, _ = render.render(TPL, p(business_name="别家健身房"))
        self.assertNotEqual(a["instance_id"], b["instance_id"])

    def test_no_unknown_placeholder_in_output(self):
        inst, _ = render.render(TPL, GOOD)
        txt = json.dumps(inst["spec"], ensure_ascii=False)
        found, _ = render.check_placeholders(json.loads(txt))
        self.assertEqual([x for x in found if x in schema.spec_index()], [])

    def test_render_keeps_chinese(self):
        inst, _ = render.render(TPL, GOOD)
        self.assertIn("青柠健身", json.dumps(inst["spec"], ensure_ascii=False))

    def test_render_refuses_on_error(self):
        inst, errs = render.render(TPL, p(business_name=""))
        self.assertIsNone(inst)
        self.assertIn("E_REQUIRED", [e["code"] for e in errs])

    def test_template_unknown_placeholder_detected(self):
        bad = dict(TPL)
        bad["copy"] = {"zh": {"greeting": "{{not_a_field}}"}}
        inst, errs = render.render(bad, GOOD)
        self.assertIsNone(inst)
        self.assertIn("E_PLACEHOLDER", [e["code"] for e in errs])

    def test_instance_carries_template_version(self):
        inst, _ = render.render(TPL, GOOD)
        self.assertEqual(inst["template_version"], TPL["version"])

    def test_params_snapshot_sorted(self):
        inst, _ = render.render(TPL, GOOD)
        self.assertEqual(list(inst["params"]), sorted(inst["params"]))


class TestTenantIsolation(unittest.TestCase):
    def test_sentinel_does_not_leak(self):
        a, _ = render.render(TPL, p(business_name="甲馆"))
        b, _ = render.render(TPL, p(business_name="乙馆"))
        self.assertNotIn("甲馆", json.dumps(b, ensure_ascii=False))

    def test_render_does_not_mutate_input(self):
        copy = dict(GOOD)
        render.render(TPL, copy)
        self.assertEqual(copy, GOOD)

    def test_template_not_mutated(self):
        before = json.dumps(TPL, ensure_ascii=False, sort_keys=True)
        render.render(TPL, GOOD)
        self.assertEqual(before, json.dumps(TPL, ensure_ascii=False, sort_keys=True))

    def test_one_tenant_bad_params_does_not_block_other(self):
        _, e1 = render.render(TPL, p(business_name=""))
        inst2, e2 = render.render(TPL, GOOD)
        self.assertTrue(e1)
        self.assertEqual(e2, [])
        self.assertIsNotNone(inst2)


class TestSimulate(unittest.TestCase):
    def sim(self, days=30, **kw):
        return simulate.simulate(p(**kw) if kw else GOOD, days=days)

    def test_runs(self):
        r = self.sim()
        self.assertTrue(r["ok"])
        self.assertGreater(r["touches"], 0)

    def test_never_touches_in_quiet_hours(self):
        for x in self.sim()["timeline"]:
            if x["action"] == "touch":
                h = datetime.fromisoformat(x["at"]).hour
                self.assertFalse(21 <= h or h < 8, x["at"])

    def test_daily_cap_respected(self):
        per = {}
        for x in self.sim(days=5)["timeline"]:
            if x["action"] == "touch":
                per[x["at"][:10]] = per.get(x["at"][:10], 0) + 1
        self.assertTrue(all(v <= GOOD["daily_cap"] for v in per.values()), per)

    def test_weekly_cap_respected(self):
        weeks = {}
        for x in self.sim(days=28)["timeline"]:
            if x["action"] == "touch":
                w = datetime.fromisoformat(x["at"]).isocalendar()[:2]
                weeks[w] = weeks.get(w, 0) + 1
        self.assertTrue(all(v <= GOOD["weekly_cap"] for v in weeks.values()), weeks)

    def test_reply_advances_stage(self):
        r = simulate.simulate(GOOD, events=[{"at": 1, "type": "reply"}], days=10)
        self.assertIn("advance", [x["action"] for x in r["timeline"]])

    def test_stage_never_goes_backwards(self):
        r = simulate.simulate(GOOD, events=[{"at": 1, "type": "reply"}] * 5, days=20)
        idx = [GOOD["stages"].index(x["stage"]) for x in r["timeline"]]
        self.assertEqual(idx, sorted(idx))

    def test_opt_out_stops_immediately(self):
        r = simulate.simulate(GOOD, events=[{"at": 1, "type": "opt_out"}], days=30)
        self.assertEqual(r["stopped"], "opt_out")
        later = [x for x in r["timeline"] if x["at"] > "2026-01-07T00:00"]
        self.assertEqual([x for x in later if x["action"] == "touch"], [])

    def test_escalates_when_no_reply(self):
        r = self.sim(days=30, escalation_days=3)
        self.assertIsNotNone(r["escalated_at"])
        self.assertIn("escalate", [x["action"] for x in r["timeline"]])

    def test_no_escalation_when_replying(self):
        ev = [{"at": d, "type": "reply"} for d in range(1, 25, 2)]
        r = simulate.simulate(GOOD, events=ev, days=25)
        self.assertIsNone(r["escalated_at"])

    def test_deterministic(self):
        a, b = self.sim(), self.sim()
        self.assertEqual(json.dumps(a["timeline"], ensure_ascii=False),
                         json.dumps(b["timeline"], ensure_ascii=False))

    def test_hash_stable_across_processes(self):
        r1 = self.sim()
        code = ("import sys,json;sys.path.insert(0,%r);from botkit import simulate;"
                "print(simulate.simulate(json.load(open(%r)),days=30)['params_hash'])"
                % (HERE, os.path.join(HERE, "instances", "example_params.json")))
        out = run_py(["-c", code])
        self.assertEqual(out.stdout.strip(), str(r1["params_hash"]))

    def test_bad_params_no_timeline(self):
        r = simulate.simulate(p(timezone="Bad/Zone"))
        self.assertFalse(r["ok"])
        self.assertEqual(r["timeline"], [])

    def test_other_timezone_shifts_hours(self):
        r = simulate.simulate(p(timezone="America/New_York"), days=3)
        hours = {datetime.fromisoformat(x["at"]).hour for x in r["timeline"]}
        self.assertTrue(all(8 <= h < 21 for h in hours), hours)


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        return run_py([os.path.join(HERE, "run.py")] + list(args))

    def test_help_exit0(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0)
        self.assertIn("validate", r.stdout)

    def test_unknown_cmd_exit2(self):
        self.assertEqual(self.run_cli("nope").returncode, 2)

    def test_validate_good_exit0(self):
        r = self.run_cli("validate", "instances/example_params.json")
        self.assertEqual(r.returncode, 0)

    def test_validate_bad_exit4(self):
        r = self.run_cli("validate", "tests/fixtures/bad_params.json")
        self.assertEqual(r.returncode, 4)
        self.assertIn("E_", r.stdout)

    def test_render_writes_file(self):
        out = os.path.join(HERE, "instances", "_t.json")
        r = self.run_cli("render", "instances/example_params.json", out)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(out))
        os.remove(out)

    def test_missing_file_exit2(self):
        r = self.run_cli("validate", "nope.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("找不到文件", r.stdout)

    def test_bad_json_exit2(self):
        bad = os.path.join(HERE, "instances", "_bad.json")
        with open(bad, "w") as f:
            f.write("{not json")
        r = self.run_cli("validate", bad)
        os.remove(bad)
        self.assertEqual(r.returncode, 2)
        self.assertIn("JSON", r.stdout)

    def test_simulate_exit0(self):
        r = self.run_cli("simulate", "instances/example_params.json", "10")
        self.assertEqual(r.returncode, 0)
        self.assertIn("触达", r.stdout)

    def test_fields_lists_all(self):
        r = self.run_cli("fields")
        for s in schema.FIELD_SPECS:
            self.assertIn(s["name"], r.stdout)


class TestFieldDocSync(unittest.TestCase):
    def test_fields_md_matches_schema(self):
        sys.path.insert(0, os.path.join(HERE, "tools"))
        from gen_fields import build
        actual = open(os.path.join(HERE, "FIELDS.md"), encoding="utf-8").read()
        self.assertEqual(actual.strip(), build().strip())

    def test_every_field_documented_in_readme(self):
        txt = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
        for s in schema.FIELD_SPECS:
            self.assertIn(s["name"], txt, s["name"])

    def test_readme_commands_exist_in_cli(self):
        cli = open(os.path.join(HERE, "botkit", "cli.py"), encoding="utf-8").read()
        for cmd in ["validate", "render", "simulate", "fields", "selftest"]:
            self.assertIn('"%s"' % cmd, cli, cmd)

    def test_guide_exit_codes_match_cli(self):
        guide = open(os.path.join(HERE, "USER_GUIDE.md"), encoding="utf-8").read()
        for code in ["0", "2", "4"]:
            self.assertIn(code, guide)

    def test_setup_commands_are_real(self):
        setup = open(os.path.join(HERE, "SETUP.md"), encoding="utf-8").read()
        for cmd in ["python3 run.py fields", "python3 test_all.py"]:
            self.assertIn(cmd, setup, cmd)


class TestRobustness(unittest.TestCase):
    """客户视角：他会用各种奇形怪状的输入试探，不能看到 Python 栈回溯。"""

    def test_non_object_root_rejected(self):
        for bad in (None, [], "x", 3):
            errs = validate(bad)
            self.assertEqual([e["code"] for e in errs], ["E_ROOT"], bad)

    def test_render_non_object_returns_errors_not_crash(self):
        for bad in (None, [], "x"):
            inst, errs = render.render(TPL, bad)
            self.assertIsNone(inst)
            self.assertTrue(errs)

    def test_simulate_non_object_no_timeline(self):
        self.assertFalse(simulate.simulate(None)["ok"])

    def test_cli_non_object_exit2(self):
        f = os.path.join(HERE, "instances", "_n.json")
        with open(f, "w") as fh:
            fh.write("[]")
        r = run_py(["run.py", "validate", f])
        os.remove(f)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_cli_no_traceback_on_directory_output(self):
        r = run_py(["run.py", "render", "instances/example_params.json", "instances"])
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


class TestSchedulingEdgeCases(unittest.TestCase):
    def test_escalation_window_must_exceed_first_cadence(self):
        self.assertIn("E_ESCALATION", codes(p(escalation_days=1)))

    def test_cross_midnight_quiet_hours(self):
        r = simulate.simulate(p(quiet_hours=[22, 6]), days=8)
        for x in r["timeline"]:
            if x["action"] == "touch":
                h = datetime.fromisoformat(x["at"]).hour
                self.assertTrue(6 <= h < 22, x["at"])

    def test_minute_alignment_keeps_cadence(self):
        r = simulate.simulate(p(), start="2026-01-05T09:30", days=3)
        ts = [x["at"] for x in r["timeline"] if x["action"] == "touch"]
        self.assertGreaterEqual(len(ts), 2)
        hhmm = {t[11:16] for t in ts}
        self.assertEqual(hhmm, {"10:30"}, hhmm)

    def test_dst_timezone_does_not_crash(self):
        r = simulate.simulate(p(timezone="America/New_York"), start="2026-03-06T09:00", days=5)
        self.assertTrue(r["ok"])
        self.assertGreater(r["touches"], 0)

    def test_daily_cap_one_and_weekly_cap_one(self):
        r = simulate.simulate(p(daily_cap=1, weekly_cap=1, cadence_hours=[1, 1, 1]),
                              days=21)
        touched = [x["at"] for x in r["timeline"] if x["action"] == "touch"]
        self.assertEqual(len(touched), len({t[:10] for t in touched}))

    def test_long_run_is_fast(self):
        import time
        t0 = time.time()
        r = simulate.simulate(p(escalation_days=90, cadence_hours=[720, 720, 720],
                                daily_cap=50, weekly_cap=200), days=3650)
        self.assertTrue(r["ok"])
        self.assertLess(time.time() - t0, 5)


class TestDocNumbers(unittest.TestCase):
    """文档里写死的数字必须与真实测试数一致——否则客户一跑就发现对不上。"""

    def total(self):
        suite = unittest.defaultTestLoader.discover(os.path.join(HERE, "tests"),
                                                    top_level_dir=HERE)
        return suite.countTestCases()

    def test_readme_count_matches(self):
        import re
        txt = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
        nums = set(re.findall(r"(\d+)\s*项测试", txt))
        self.assertEqual(nums, {str(self.total())}, nums)

    def test_setup_count_matches(self):
        import re
        txt = open(os.path.join(HERE, "SETUP.md"), encoding="utf-8").read()
        nums = set(re.findall(r"个?：(\d+) 项", txt))
        self.assertEqual(nums, {str(self.total())}, nums)

    def test_guide_count_matches(self):
        import re
        txt = open(os.path.join(HERE, "USER_GUIDE.md"), encoding="utf-8").read()
        nums = set(re.findall(r"跑 (\d+) 项测试", txt))
        self.assertEqual(nums, {str(self.total())}, nums)


class TestFormatting(unittest.TestCase):
    """文案不能把原始 JSON 塞进句子——客户读到的必须是中文人话。"""

    def spec(self):
        return render.render(TPL, GOOD)[0]["spec"]

    def test_quiet_hours_rendered_as_window(self):
        self.assertIn("21:00-次日 08:00", self.spec()["guardrails"]["quiet_hours"])

    def test_cadence_rendered_with_unit(self):
        self.assertIn("24 小时", self.spec()["playbook"][1]["trigger"])

    def test_enum_rendered_as_label(self):
        self.assertIn("亲切", self.spec()["guardrails"]["tone"])

    def test_data_scope_label(self):
        self.assertIn("仅联系方式", self.spec()["guardrails"]["data_scope"])

    def test_no_bare_list_join_in_copy(self):
        zh = self.spec()["copy"]["zh"]
        for v in zh.values():
            self.assertNotIn(" / ", v, v)

    def test_window_formatter_non_crossing(self):
        self.assertEqual(render._fmt([8, 21], "window"), "08:00-21:00")

    def test_hours_formatter(self):
        self.assertEqual(render._fmt([24, 72], "hours"), "24 小时/72 小时")

    def test_unknown_format_rejected(self):
        bad = dict(TPL)
        bad["purpose"] = "{{business_name|bogus}}"
        inst, errs = render.render(bad, GOOD)
        self.assertIsNone(inst)
        self.assertIn("E_FORMAT", [e["code"] for e in errs])


class TestInstanceIdentity(unittest.TestCase):
    def test_template_change_changes_id(self):
        a, _ = render.render(TPL, GOOD)
        tpl2 = json.loads(json.dumps(TPL))
        tpl2["copy"]["zh"]["greeting"] = "改了文案"
        b, _ = render.render(tpl2, GOOD)
        self.assertNotEqual(a["instance_id"], b["instance_id"], "只改模板也必须换 id")

    def test_template_hash_present(self):
        inst, _ = render.render(TPL, GOOD)
        self.assertEqual(len(inst["template_hash"]), 8)

    def test_version_bump_changes_id(self):
        a, _ = render.render(TPL, GOOD)
        tpl2 = json.loads(json.dumps(TPL))
        tpl2["version"] = "9.9.9"
        b, _ = render.render(tpl2, GOOD)
        self.assertNotEqual(a["instance_id"], b["instance_id"])

class TestTimezoneFallback(unittest.TestCase):
    """Windows 版 Python 不带 tzdata。若只靠 zoneinfo，测试在客户机器上会成片变红。"""

    def setUp(self):
        from botkit import tzutil
        self.tz = tzutil
        self.saved = tzutil._ZI

    def tearDown(self):
        self.tz._ZI = self.saved
        self.tz.STATE["degraded"] = False

    def test_fallback_when_zoneinfo_missing(self):
        self.tz._ZI = None
        tz = self.tz.resolve("Asia/Shanghai")
        self.assertEqual(tz.utcoffset(None).total_seconds(), 8 * 3600)

    def test_fallback_flags_degraded(self):
        self.tz._ZI = None
        self.tz.resolve("Europe/Berlin")
        self.assertTrue(self.tz.STATE["degraded"])
        self.assertIn("tzdata", self.tz.STATE["reason"])

    def test_fallback_unknown_still_rejected(self):
        self.tz._ZI = None
        self.assertFalse(self.tz.known("Mars/Olympus"))

    def test_validation_works_without_tzdata(self):
        self.tz._ZI = None
        self.assertEqual(validate(GOOD), [])

    def test_simulation_works_without_tzdata(self):
        self.tz._ZI = None
        r = simulate.simulate(GOOD, days=5)
        self.assertTrue(r["ok"])
        self.assertGreater(r["touches"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
