"""Isolated bridge to the official Seiðr Engine composition API."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[2] == "forms":
        engine_root = Path(sys.argv[1]).resolve(strict=True)
        sys.path.insert(0, str(engine_root))
        from seidr.forms import FORMS

        canonical = []
        for key, form in FORMS.items():
            if key != form.name():
                continue
            minimum, maximum = form.syllable_range()
            canonical.append(
                {
                    "key": key,
                    "old_norse_name": form.name_on(),
                    "syllables_per_line": {"minimum": minimum, "maximum": maximum},
                    "description": form.describe(),
                }
            )
        print(json.dumps(canonical, ensure_ascii=True, separators=(",", ":")))
        return
    if len(sys.argv) == 3 and sys.argv[2] == "kennings":
        engine_root = Path(sys.argv[1]).resolve(strict=True)
        sys.path.insert(0, str(engine_root))
        from seidr.lexicon import Lexicon

        lexicon = Lexicon(seed=1)
        payload = [
            {
                "base": kenning.base,
                "expression": kenning.expression,
                "components": list(kenning.components),
                "domain": kenning.domain,
                "syllables": kenning.syllable_count,
            }
            for kenning in lexicon.kennings
        ]
        print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
        return
    if len(sys.argv) != 7:
        raise SystemExit(2)
    engine_root = Path(sys.argv[1]).resolve(strict=True)
    form = sys.argv[2]
    domain = None if sys.argv[3] == "-" else sys.argv[3]
    stanzas = int(sys.argv[4])
    use_kennings = sys.argv[5] == "1"
    seed = int(sys.argv[6])
    sys.path.insert(0, str(engine_root))

    from seidr.lexicon import Lexicon
    from seidr.poet import PoemConfig, Skald

    lexicon = Lexicon(seed=seed)
    skald = Skald(lexicon=lexicon, seed=seed)
    config = PoemConfig(
        form=form,
        domain=domain,
        num_stanzas=stanzas,
        use_kennings=use_kennings,
        seed=seed,
    )
    poem = skald.compose_poem(config)
    if len(poem.stanzas) != stanzas:
        raise RuntimeError("official engine returned the wrong stanza count")
    payload = {
        "form": form,
        "domain": domain,
        "stanza_count": stanzas,
        "use_kennings": use_kennings,
        "verse": poem.format(),
        "stanzas": [
            {
                "form": stanza.form,
                "domain": stanza.domain,
                "lines": [
                    {
                        "text": line.text,
                        "syllables": line.syllables,
                        "alliteration_group": line.alliteration_group,
                        "domain": line.domain,
                    }
                    for line in stanza.lines
                ],
            }
            for stanza in poem.stanzas
        ],
    }
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
