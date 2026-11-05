from pathlib import Path

from harness.env import load_env, parse_env


def test_crlf_and_bom_are_stripped(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_bytes(b"\xef\xbb\xbfDEEPGRAM_API_KEY=abc123\r\nASSEMBLYAI_API_KEY=xyz\r\n")
    env: dict[str, str] = {}
    assert load_env(p, env) == ["DEEPGRAM_API_KEY", "ASSEMBLYAI_API_KEY"]
    assert env == {"DEEPGRAM_API_KEY": "abc123", "ASSEMBLYAI_API_KEY": "xyz"}


def test_parse_rules() -> None:
    text = (
        "# comment\n\nexport A=1\nB = 'two words'\nC=\"q\"\nD=plain # trailing\n"
        "E=\nnot a line\nF=a#b\n"
    )
    assert parse_env(text) == {
        "A": "1",
        "B": "two words",
        "C": "q",
        "D": "plain",
        "E": "",
        "F": "a#b",
    }


def test_existing_environment_wins_and_empty_values_are_skipped(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("A=from_file\nB=\nC=new\n", encoding="utf-8")
    env = {"A": "from_shell"}
    assert load_env(p, env) == ["C"]
    assert env == {"A": "from_shell", "C": "new"}


def test_missing_file_is_a_noop(tmp_path: Path) -> None:
    env: dict[str, str] = {}
    assert load_env(tmp_path / "nope", env) == []
    assert env == {}
