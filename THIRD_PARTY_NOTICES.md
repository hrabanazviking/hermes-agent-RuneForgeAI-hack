# Third-Party Notices

## Hermes Agent

This repository is a personal fork of Hermes Agent by Nous Research.

The incorporated Hermes Agent code is distributed under the MIT License. The complete license
text and copyright notice are preserved in `LICENSE`.

## Verðandi

The `volmarr-core` plugin interoperates with the Verðandi event bus protocol. Verðandi is
distributed under the MIT License:

```text
Copyright (c) 2026 Volmarr Wyrd and Runa Gridweaver Freyjasdottir
```

No Verðandi source file is copied into this repository. The plugin uses its local JSON-line
publish, health, and bounded recent-event contracts; regulatory classification remains local to
this fork.

## Project A.E.S.I.R.

The `volmarr-core` plugin can probe the loopback OpenAI-compatible interface exposed by Project
A.E.S.I.R., which is distributed under the GNU Affero General Public License, version 3.

```text
Copyright (c) 2026 Volmarr Wyrd
```

A.E.S.I.R. remains a separate process and repository. No A.E.S.I.R. source file is copied into
this repository by the local reflex endpoint adapter.

## Bifröst

The `volmarr-core` plugin can construct the external Bifröst memory bridge package through its
public Python interface. Bifröst is distributed under the MIT License:

```text
Copyright (c) 2025 Runa Gridweaver & Volmarr Viking
```

Bifröst remains a separate package and repository. No Bifröst source file is copied into this
repository by the memory-fabric attachment.

## MemPalace

The `volmarr-core` plugin can verify an external MemPalace package (official v3.10.0 contract or
newer) and its local episodic store through a read-only SQLite contract. MemPalace is distributed
under the MIT License:

```text
Copyright (c) 2026 MemPalace Contributors
```

MemPalace remains a separate package and repository. No MemPalace source file is copied into this
repository by the episodic-store attachment.

## OpenViking

The `volmarr-core` plugin can attest an external OpenViking v0.4.21-or-newer service through its
anonymous, read-only loopback health endpoint. OpenViking is distributed under the GNU Affero
General Public License, version 3. The complete license is available in the official OpenViking
source repository.

This fork slice reuses Hermes' existing bundled OpenViking provider and adds no copied OpenViking
source. OpenViking remains a separate service/package.

## Earlier Personal-Fork Affective Work

The schema-v9 synthetic affective regulator in `plugins/volmarr-core/affective.py` is preserved
from `hrabanazviking/hermes-agent` commit
`d423b611799d1ad8a05fe6f067ac8de673a0404c`, authored by Volmarr Wyrd. That source repository is
distributed under the MIT License. Its former Hermes core wiring was not copied; this repository
adapts the regulator through plugin hooks and the central bounded context packet.

## WYRD Protocol

The `volmarr-core` plugin can probe the official WYRD Protocol v1 HTTP service through its
anonymous, read-only, loopback `/health` endpoint. WYRD Protocol is distributed under the Creative
Commons Attribution 4.0 International license and was created by Volmarr Wyrd / RuneForgeAI. The
official project is available at
`hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model`.

No WYRD source file is copied into this repository. WYRD remains a separate service/package; this
slice implements only the public HTTP compatibility boundary.

## AI Agent Astrology Engine

The `volmarr-astrology` plugin invokes the official AI Agent Astrology Engine as an external local
process for deterministic calculations. The engine is distributed under the Apache License,
Version 2.0, and was created by Volmarr Wyrd / RuneForgeAI. No engine source or ephemeris data is
copied into this repository; its Python and Swiss Ephemeris dependencies remain externally
installed components.

## Future Components

No other third-party runtime component has been incorporated beyond the components listed above.

When a component is copied or adapted, its required notices must be added here and its exact
provenance must be recorded in `COMPONENT_LICENSES.md` before the change is merged.
