from pathlib import Path
from typing import Any

import pytest
import yaml

from recommender.profile import (
    Channel,
    Profile,
    ProfileError,
    load_profile,
    parse_profile,
)
from recommender.suites import (
    REFERENCE_SUITES,
    ReferenceSuite,
    match_reference_suite,
)

PROFILES = Path(__file__).resolve().parent.parent / "configs" / "profiles"
HEALTHCARE = PROFILES / "healthcare_intake.yaml"
BILLING = PROFILES / "utility_billing_support.yaml"


def minimal() -> dict[str, Any]:
    return {
        "use_case": {
            "name": "x",
            "domain": "y",
            "channel": "telephony_8k",
            "languages": ["en"],
            "avg_call_minutes": 3,
            "agent_talk_ratio": 0.5,
        }
    }


def with_(data: dict[str, Any], dotted: str, value: Any) -> dict[str, Any]:
    *parents, leaf = dotted.split(".")
    node = data
    for key in parents:
        node = node.setdefault(key, {})
    node[leaf] = value
    return data


def write(tmp_path: Path, data: dict[str, Any]) -> Path:
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


# --- example profiles ---------------------------------------------------------


@pytest.mark.parametrize("path", [HEALTHCARE, BILLING])
def test_example_profiles_load(path: Path) -> None:
    profile = load_profile(path)
    assert profile.use_case.channel is Channel.TELEPHONY_8K
    assert profile.entities
    assert profile.keyterm_list()


def test_healthcare_profile_values() -> None:
    p = load_profile(HEALTHCARE)
    assert p.constraints.stack.require_baa is True
    assert p.constraints.llm.min_check_pass_rate["identity_before_disclosure"] == 0.99
    assert "red_flag_escalation" in p.constraints.llm.min_check_pass_rate
    assert "amlodipine" in p.keyterm_list()
    assert "# seed" not in " ".join(p.keyterm_list()).lower()


def test_minimal_profile_defaults_are_unconstrained() -> None:
    p = parse_profile(minimal(), Path("."))
    assert p.constraints.stack.max_p95_ttfa_ms is None
    assert p.constraints.stack.deployment == "either"
    assert p.entities == [] and p.audio is None and p.keyterm_list() == []


def test_explicit_keyterms_override_lexicons() -> None:
    data = with_(minimal(), "keyterms", ["Ozempic"])
    data["entities"] = [{"name": "drug", "kind": "lexicon", "lexicon_path": "nope.txt"}]
    assert parse_profile(data, Path(".")).keyterm_list() == ["Ozempic"]


def test_relative_paths_resolve_against_profile_dir(tmp_path: Path) -> None:
    (tmp_path / "lex").mkdir()
    (tmp_path / "lex" / "terms.txt").write_text("# comment\nFoo\n\n bar \n")
    data = minimal()
    data["entities"] = [{"name": "term", "kind": "lexicon", "lexicon_path": "lex/terms.txt"}]
    p = load_profile(write(tmp_path, data))
    assert p.base_dir == tmp_path
    assert p.keyterm_list() == ["bar", "foo"]


# --- validation errors (one per rule) ----------------------------------------


@pytest.mark.parametrize(
    ("dotted", "value", "message"),
    [
        ("use_case.channel", "pstn", "telephony_8k"),
        ("use_case.languages", [], "at least 1 item"),
        ("use_case.languages", ["English"], "should match pattern"),
        ("use_case.agent_talk_ratio", 1.5, "less than or equal to 1"),
        ("use_case.avg_call_minutes", 0, "greater than 0"),
        ("constraints.stack.min_task_success_rate", -0.1, "greater than or equal to 0"),
        ("constraints.stack.max_p95_ttfa_ms", 0, "greater than 0"),
        ("constraints.stack.deployment", "cloud", "managed"),
        ("constraints.stack.min_concurrency", 0, "greater than or equal to 1"),
        ("constraints.turn_taking.max_premature_endpoint_rate", 2, "less than or equal to 1"),
        ("constraints.llm.min_check_pass_rate", {"x": 1.1}, "less than or equal to 1"),
        ("constraints.tts.max_roundtrip_wer", 1.01, "less than or equal to 1"),
        ("constraints.stt.unknown", 1, "Extra inputs are not permitted"),
        ("constraints.stt.min_entity_recall", {"ghost": 0.9}, "undefined entities"),
    ],
)
def test_invalid_field(dotted: str, value: Any, message: str, tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match=message):
        load_profile(write(tmp_path, with_(minimal(), dotted, value)))


@pytest.mark.parametrize(
    ("entity", "message"),
    [
        ({"name": "Drug", "kind": "builtin", "builtin": "number"}, "should match pattern"),
        ({"name": "x", "kind": "regex"}, "no pattern"),
        ({"name": "x", "kind": "regex", "pattern": "(unclosed"}, "does not compile"),
        ({"name": "x", "kind": "builtin", "builtin": "zipcode"}, "number"),
        ({"name": "x", "kind": "builtin", "builtin": "date", "pattern": "x"}, "also sets"),
        ({"name": "x", "kind": "lexicon", "lexicon_path": "missing.txt"}, "not found"),
    ],
)
def test_invalid_entity(entity: dict[str, Any], message: str, tmp_path: Path) -> None:
    data = minimal()
    data["entities"] = [entity]
    with pytest.raises(ProfileError, match=message):
        load_profile(write(tmp_path, data))


def test_duplicate_entity_names(tmp_path: Path) -> None:
    data = minimal()
    data["entities"] = [{"name": "x", "kind": "builtin", "builtin": "date"}] * 2
    with pytest.raises(ProfileError, match="duplicate entity names"):
        load_profile(write(tmp_path, data))


@pytest.mark.parametrize(
    ("dotted", "value"),
    [("conversation_scripts", "scripts.jsonl"), ("audio.manifest_path", "customer.jsonl")],
)
def test_missing_referenced_file(dotted: str, value: str, tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="referenced files not found"):
        load_profile(write(tmp_path, with_(minimal(), dotted, value)))


def test_unreadable_and_malformed_files(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="cannot read"):
        load_profile(tmp_path / "absent.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("use_case: [unclosed\n")
    with pytest.raises(ProfileError, match="cannot read"):
        load_profile(bad)


# --- reference suite matching ------------------------------------------------


def test_healthcare_is_a_direct_match() -> None:
    m = match_reference_suite(load_profile(HEALTHCARE))
    assert m.suite_id == "healthcare_intake"
    assert m.proxy is False
    assert any("direct match" in r for r in m.reasons)


def test_billing_is_a_proxy_match() -> None:
    m = match_reference_suite(load_profile(BILLING))
    assert m.suite_id == "healthcare_intake"
    assert m.proxy is True
    assert any("account_number" in r and "NOT covered" in r for r in m.reasons)
    assert "languages NOT covered: es" in m.reasons
    assert any("proxy match" in r for r in m.reasons)


def _suite(suite_id: str, **kw: Any) -> ReferenceSuite:
    fields: dict[str, Any] = {
        "suite_id": suite_id,
        "description": "",
        "channels": {Channel.TELEPHONY_8K},
        "languages": {"en"},
        "entity_signatures": set(),
    }
    fields.update(kw)
    return ReferenceSuite(**fields)


def test_matcher_ranks_by_channel_then_language_then_entities() -> None:
    p = parse_profile(minimal(), Path("."))
    wideband = _suite("a_wideband", channels={Channel.WIDEBAND_16K}, entity_signatures={"x"})
    spanish = _suite("b_spanish", languages={"es"})
    plain = _suite("c_plain")
    assert match_reference_suite(p, (wideband, spanish, plain)).suite_id == "c_plain"

    data = minimal()
    data["entities"] = [{"name": "d", "kind": "builtin", "builtin": "date"}]
    p2 = parse_profile(data, Path("."))
    dated = _suite("d_dated", entity_signatures={"date"})
    assert match_reference_suite(p2, (plain, dated)).suite_id == "d_dated"


def test_matcher_tie_breaks_alphabetically_and_is_order_independent() -> None:
    p = parse_profile(minimal(), Path("."))
    a, b = _suite("alpha"), _suite("beta")
    assert match_reference_suite(p, (b, a)).suite_id == "alpha"
    assert match_reference_suite(p, (a, b)) == match_reference_suite(p, (b, a))


def test_explicit_reference_suite() -> None:
    p = parse_profile(with_(minimal(), "reference_suite", "beta"), Path("."))
    m = match_reference_suite(p, (_suite("alpha"), _suite("beta")))
    assert m.suite_id == "beta"
    assert m.reasons[0] == "set explicitly in profile"
    with pytest.raises(ProfileError, match="not one of"):
        match_reference_suite(p, (_suite("alpha"),))


def test_language_mismatch_is_proxy() -> None:
    p = parse_profile(with_(minimal(), "use_case.languages", ["de-DE"]), Path("."))
    m = match_reference_suite(p, REFERENCE_SUITES)
    assert m.proxy is True
    assert any("no shared language" in r for r in m.reasons)


def test_partially_covered_languages_are_proxy() -> None:
    p = parse_profile(with_(minimal(), "use_case.languages", ["en-GB", "fr-FR"]), Path("."))
    m = match_reference_suite(p, REFERENCE_SUITES)
    assert m.proxy is True
    assert "languages NOT covered: fr" in m.reasons


def test_profile_is_immutable() -> None:
    p: Profile = parse_profile(minimal(), Path("."))
    with pytest.raises(ValueError):
        p.reference_suite = "x"  # type: ignore[misc]
