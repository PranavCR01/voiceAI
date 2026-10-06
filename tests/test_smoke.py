import harness
import recommender


def test_packages_import() -> None:
    assert harness.__name__ == "harness"
    assert recommender.__name__ == "recommender"
