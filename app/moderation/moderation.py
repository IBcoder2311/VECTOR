import re
import logging
from pathlib import Path

from badwords import Options, ProfanityFilter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BANNED_WORDS_PATH = PROJECT_ROOT / "core" / "banned_words" / "ru_en.txt"


profanity = ProfanityFilter()

profanity.init(
    languages=["ru", "en"],
    options=Options(
        split_on_punctuation=True,
        collapse_repeats=True,
        leetspeak=True,
    ),
)


def load_banned_words() -> list[str]:
    if not BANNED_WORDS_PATH.exists():
        raise FileNotFoundError(
            f"Не найден словарь: {BANNED_WORDS_PATH}"
        )

    words = []

    with open(BANNED_WORDS_PATH, "r", encoding="utf-8") as file:
        for line in file:
            word = line.strip().casefold()

            if not word or word.startswith("#"):
                continue

            if "*" in word:
                continue

            words.append(word)

    return words


BANNED_WORDS = load_banned_words()


def get_fragment(text: str, start: int, end: int, context: int = 50) -> str:
    left = max(0, start - context)
    right = min(len(text), end + context)

    fragment = text[left:right]

    if left > 0:
        fragment = "..." + fragment

    if right < len(text):
        fragment += "..."

    return fragment


def check_text(text: str) -> dict:
    if not text or not text.strip():
        return {
            "flagged": False,
            "matches": [],
        }

    matches = []

    # Первый источник — BadWords
    for match in profanity.find(text):
        start = text.find(match.matched_text)

        if start == -1:
            start = 0

        end = start + len(match.matched_text)

        matches.append({
            "source": "BadWords",
            "word": match.word,
            "matched_text": match.matched_text,
            "kind": match.kind,
            "fragment": get_fragment(text, start, end),
        })

    # Второй источник — собственный словарь
    normalized_text = text.casefold().replace("ё", "е")

    for word in BANNED_WORDS:
        normalized_word = word.replace("ё", "е")

        pattern = (
            r"(?<!\w)"
            + re.escape(normalized_word)
            + r"(?!\w)"
        )

        for match in re.finditer(pattern, normalized_text):
            start, end = match.span()

            matches.append({
                "source": "ru_en",
                "word": word,
                "matched_text": text[start:end],
                "kind": "custom",
                "fragment": get_fragment(text, start, end),
            })

    return {
        "flagged": bool(matches),
        "matches": matches,
    }
