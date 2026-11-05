import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEX = ROOT / "data" / "lexicons"


def _builder():  # data/ is not a package
    spec = importlib.util.spec_from_file_location("openfda", LEX / "fetch_openfda_generics.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_boost_list_is_what_the_builder_makes_from_the_snapshot() -> None:
    builder = _builder()
    snapshot = json.loads((LEX / "openfda_ndc_rx_counts.json").read_text())
    assert builder.render(snapshot) == (LEX / "openfda_rx_generics.txt").read_text()


def test_base_name_strips_salts_and_drops_combinations() -> None:
    b = _builder()
    assert b.base_name("ATORVASTATIN CALCIUM") == "atorvastatin"
    assert b.base_name("Metformin Hydrochloride Extended Release") == "metformin"
    assert b.base_name("Amoxicillin and Clavulanate Potassium") is None
    assert b.base_name("Potassium Chloride") is None  # nothing left once salts are stripped


def test_rank_merges_case_and_salt_variants_and_adds_uk_names() -> None:
    b = _builder()
    results = [
        {"term": "Albuterol Sulfate", "count": 3},
        {"term": "ALBUTEROL", "count": 2},
        {"term": "Gabapentin", "count": 4},
        {"term": "Oxygen", "count": 99},
    ]
    ranked = b.rank(results)
    assert ranked == [("albuterol", 5), ("gabapentin", 4)]
    assert b.terms(ranked) == ["albuterol", "salbutamol", "gabapentin"]
    assert b.terms(ranked, limit=2) == ["albuterol", "salbutamol"]
