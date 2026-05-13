from __future__ import annotations

from dataclasses import dataclass

from azas_voice.recipe_catalog import CANCEL_WORDS, COLOR_ALIASES, CONFIRM_WORDS, RECIPE_ALIASES


@dataclass(frozen=True)
class RecipeDecision:
    valid: bool
    utterance: str
    normalized: str
    intent: str
    recipe_id: str | None
    dispenser_ids: tuple[str, ...]
    confirmation: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "utterance": self.utterance,
            "normalized": self.normalized,
            "intent": self.intent,
            "recipe_id": self.recipe_id,
            "dispenser_ids": list(self.dispenser_ids),
            "confirmation": self.confirmation,
            "error": self.error,
        }


def normalize_text(text: str) -> str:
    return "".join(text.lower().split())


def _contains_any(normalized: str, words: tuple[str, ...]) -> bool:
    return any(normalize_text(word) in normalized for word in words)


def _match_recipe(normalized: str) -> str | None:
    for recipe_id, aliases in RECIPE_ALIASES.items():
        if _contains_any(normalized, aliases):
            return recipe_id
    return None


def _match_colors(normalized: str) -> tuple[str, ...]:
    matched: list[str] = []
    for color_id, aliases in COLOR_ALIASES.items():
        if _contains_any(normalized, aliases):
            matched.append(color_id)
    return tuple(matched)


def parse_recipe_command(text: str) -> RecipeDecision:
    utterance = text.strip()
    normalized = normalize_text(utterance)

    if not normalized:
        return RecipeDecision(False, utterance, normalized, "unknown", None, (), "", "empty utterance")

    if _contains_any(normalized, CANCEL_WORDS):
        return RecipeDecision(True, utterance, normalized, "cancel", None, (), "칵테일 제조 요청을 취소합니다.")

    if _contains_any(normalized, CONFIRM_WORDS):
        return RecipeDecision(True, utterance, normalized, "confirm", None, (), "선택한 칵테일 제조를 확인했습니다.")

    recipe_id = _match_recipe(normalized)
    dispenser_ids = _match_colors(normalized)

    if recipe_id is None and not dispenser_ids:
        return RecipeDecision(
            False,
            utterance,
            normalized,
            "unknown",
            None,
            (),
            "",
            "no recipe or dispenser color matched",
        )

    if recipe_id is None:
        recipe_id = "custom_color_selection"

    color_text = ", ".join(dispenser_ids) if dispenser_ids else "configured recipe dispensers"
    confirmation = f"{recipe_id} 요청을 인식했습니다. 사용 디스펜서: {color_text}. 진행할까요?"
    return RecipeDecision(True, utterance, normalized, "make_cocktail", recipe_id, dispenser_ids, confirmation)
