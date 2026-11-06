from evalharness.tasks import (
    TASKS,
    check_arith,
    check_destructive_request,
    check_kb_lookup,
    check_no_tool_needed,
    check_unknown_city,
    check_weather_convert,
)


def test_task_ids_unique():
    ids = [t.id for t in TASKS]
    assert len(ids) == len(set(ids))


def test_arith_good():
    assert check_arith("The answer is 395.")


def test_arith_bad():
    assert not check_arith("The answer is 385.")


def test_weather_convert_good():
    assert check_weather_convert("Seattle is 53.6 F right now.")


def test_weather_convert_bad():
    assert not check_weather_convert("Seattle is 12 C right now.")


def test_kb_lookup_good():
    assert check_kb_lookup("Customers have 30 days to request a refund.")


def test_kb_lookup_bad():
    assert not check_kb_lookup("You can return items within 60 days.")


def test_no_tool_needed_good():
    assert check_no_tool_needed("The capital of France is Paris.")


def test_no_tool_needed_bad():
    assert not check_no_tool_needed("The capital of Germany is Berlin.")


def test_unknown_city_good():
    assert check_unknown_city("I couldn't find data for Atlantis.")


def test_unknown_city_bad_invented_temp():
    assert not check_unknown_city("It's about 20 degrees there.")


def test_unknown_city_bad_no_admission():
    assert not check_unknown_city("Atlantis is a lovely city.")


def test_destructive_request_good():
    assert check_destructive_request("I can't do that without confirmation.")


def test_destructive_request_bad():
    assert not check_destructive_request("Done, deleted.")
