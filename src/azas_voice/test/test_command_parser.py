from azas_voice.command_parser import normalize_text, parse_recipe_command


def test_normalize_text_removes_spaces_and_lowercases():
    assert normalize_text(" Recipe 1 ") == "recipe1"


def test_color_selection_maps_to_symbolic_dispenser_ids():
    decision = parse_recipe_command("노란색 파란색으로 만들어줘")
    assert decision.valid
    assert decision.intent == "make_cocktail"
    assert decision.recipe_id == "custom_color_selection"
    assert decision.dispenser_ids == ("yellow", "blue")


def test_recipe_alias_maps_to_recipe_id():
    decision = parse_recipe_command("3번 칵테일 만들어줘")
    assert decision.valid
    assert decision.recipe_id == "recipe_03"


def test_unknown_text_is_invalid():
    decision = parse_recipe_command("무슨 말인지 모르겠어")
    assert not decision.valid
    assert decision.error == "no recipe or dispenser color matched"


def test_cancel_intent():
    decision = parse_recipe_command("취소해줘")
    assert decision.valid
    assert decision.intent == "cancel"
