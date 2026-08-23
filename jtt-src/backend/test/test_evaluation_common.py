import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation" / "scripts"))

from common import set_value  # noqa: E402


def test_skill_aliases_are_compared_using_canonical_names():
    expected = set_value(["Vue3", "大语言模型", "自然语言处理", "C语言"])
    actual = set_value(["Vue", "LLM", "NLP", "C"])

    assert expected == actual


def test_skill_string_supports_chinese_delimiters():
    assert set_value("Python，FastAPI、Docker") == {"python", "fastapi", "docker"}
