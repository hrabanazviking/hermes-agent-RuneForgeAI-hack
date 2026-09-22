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


def _card_payload(card: object) -> dict[str, object]:
    return {
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


def main() -> None:
    if len(sys.argv) not in (4, 5):
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
    spread_key = sys.argv[4] if len(sys.argv) == 5 else None
    count = 1
    spread = None
    manager = None
    if spread_key is not None:
        from src.spreads import SpreadManager

        manager = SpreadManager()
        manager.load_spreads()
        spread = manager.get_spread(spread_key)
        if spread is None or spread.card_count < 2:
            raise RuntimeError("official multi-card spread was not found")
        if len(spread.positions) != spread.card_count:
            raise RuntimeError("official spread position count does not match card count")
        count = spread.card_count
    drawn = deck.draw_full_hand(
        count=count,
        allow_reversals=allow_reversals,
        seed=seed,
    )
    if len(drawn) != count:
        raise RuntimeError("official deck returned the wrong card count")
    if spread is None or manager is None:
        payload: object = _card_payload(drawn[0])
    else:
        placed = manager.assign_cards(spread, drawn)
        if len(placed) != count:
            raise RuntimeError("official spread did not place every card")
        payload = {
            "key": spread_key,
            "name": _text(spread.name),
            "description": _text(spread.description),
            "tradition": _text(spread.tradition),
            "card_count": count,
            "cards": [
                {
                    "position": {
                        "number": item.position.number,
                        "name": _text(item.position.name),
                        "meaning": _text(item.position.meaning),
                        "gd_meaning": _text(item.position.gd_meaning),
                        "row": item.position.row,
                        "col": item.position.col,
                        "crosses": item.position.crosses,
                    },
                    "card": _card_payload(item.card),
                }
                for item in placed
            ],
        }
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
