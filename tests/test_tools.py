import pytest

from evalharness.tools import DefaultToolBox, calculator, get_weather, search_kb


def test_calculator_basic():
    assert calculator("17*23+4") == "395"


def test_calculator_rejects_import():
    with pytest.raises(ValueError):
        calculator("__import__('os').system('ls')")


def test_get_weather_case_insensitive():
    assert get_weather("Seattle") == "12 C"
    assert get_weather("AUSTIN") == "27 C"
    assert get_weather("  Oslo  ") == "-3 C"


def test_toolbox_unknown_city_is_error():
    tb = DefaultToolBox()
    result, is_error = tb.call("get_weather", {"city": "atlantis"})
    assert is_error
    assert "atlantis" in result.lower() or "no weather" in result.lower()


def test_toolbox_unknown_tool_is_error():
    tb = DefaultToolBox()
    result, is_error = tb.call("launch_missiles", {})
    assert is_error
    assert "launch_missiles" in result


def test_search_kb_no_results():
    assert search_kb("what is the meaning of life") == "no results"


def test_search_kb_hits():
    result = search_kb("I want a refund and check the warranty")
    assert "30 days" in result
    assert "2 years" in result
