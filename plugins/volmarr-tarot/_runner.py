"""Isolated bridge to the official RuneTarot deck subsystem."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _texts(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(2)
    engine_root = Path(sys.argv[1]).resolve(strict=True)
    seed = int(sys.argv[2])
    allow_reversals = sys.argv[3] == "1"
    sys.path.insert(0, str(engine_root))

    from src.deck import TarotDeck

    deck = TarotDeck()
    deck.load_cards()
    if deck.count() != 78:
        raise RuntimeError("official deck did not load exactly 78 cards")
    drawn = deck.draw_full_hand(
        count=1,
        allow_reversals=allow_reversals,
        seed=seed,
    )
    if len(drawn) != 1:
        raise RuntimeError("official deck did not return one card")
    card = drawn[0]
    payload = {
        "card_id": _text(card.card_id),
        "name": _text(card.display_name),
        "suit": _text(card.suit),
        "reversed": bool(card.is_reversed),
        "element": _text(card.element),
        "keywords": _texts(card.keywords),
        "meanings": _texts(card.current_meanings),
        "gd_title": _text(card.gd_title),
        "gd_meaning": _text(card.gd_meaning),
        "hebrew_letter": _text(card.hebrew_letter),
        "astrological": _text(card.astrological),
        "tree_path": card.tree_path if isinstance(card.tree_path, int) else 0,
        "number": card.number if isinstance(card.number, (int, str)) else "",
    }
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
