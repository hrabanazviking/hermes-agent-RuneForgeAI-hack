# Component License Ledger

This file records the license and provenance of code or data incorporated into this repository.
It does not replace the original license text.

| Component | Source | Incorporated material | License | Attribution / notes |
|---|---|---|---|---|
| Hermes Agent | `NousResearch/hermes-agent` | Current runtime, applications, tests, documentation, and build infrastructure | MIT | Copyright 2025 Nous Research; see `LICENSE` |
| Volmarr / RuneForgeAI project documents | Authored for `hrabanazviking/hermes-agent-RuneForgeAI-hack` | Personal README, roadmap, philosophy, operating rules, and architecture records | Not separately declared | Do not infer MIT solely from repository placement; declare terms before external reuse |
| Verðandi | `hrabanazviking/Verdandi` at `dc7139416ef4bb67c9ba29c1148615d0d259b7db` | JSON-line publish, health, and bounded recent-event protocol integration; no Verðandi source copied | MIT | Copyright 2026 Volmarr Wyrd and Runa Gridweaver Freyjasdottir |
| Project A.E.S.I.R. | `hrabanazviking/RuneForgeAI-Project-Aesir` at `c1a4410ca254fa388e45936b02230999d0906a4c` | OpenAI-compatible loopback protocol integration; no A.E.S.I.R. source copied | AGPL-3.0 | Copyright 2026 Volmarr Wyrd; A.E.S.I.R. remains an external service |
| Bifröst | `hrabanazviking/bifrost` at `b66e98cc8a79d4dede22ba11d68a1a5ecd22ebd6` | Python package interface integration; no Bifröst source copied | MIT | Copyright 2025 Runa Gridweaver and Volmarr Viking; Bifröst remains an external package |
| Earlier Present State work | `hrabanazviking/hermes-agent` at `761a8559084e7f582fe4c205bfa3835c1df9df42` | Present-state data model and behavior adapted into `plugins/volmarr-core/present_state.py`; former Hermes core wiring was not copied | MIT | Original commit authored by Volmarr Wyrd in the personal Hermes fork; root MIT notice remains preserved |
| Earlier Affective Nervous System work | `hrabanazviking/hermes-agent` at `d423b611799d1ad8a05fe6f067ac8de673a0404c` | Schema-v9 deterministic regulator copied into `plugins/volmarr-core/affective.py`; former core wiring replaced by `affective_bridge.py` plugin hooks and central packet contribution | MIT | Original commit authored by Volmarr Wyrd in the personal Hermes fork; source repository's MIT terms and the root MIT notice remain preserved |
| MemPalace | Official `MemPalace/mempalace` v3.10.0 at `22fd87f09c19d5ffb2d6966486483353937931c0`; mirrored by `hrabanazviking/mempalace` at `ff1bdf03407bc5d6c571fa85f8c621d7177de616` | Python package identity and read-only Chroma SQLite contract integration; no MemPalace source copied | MIT | Copyright 2026 MemPalace Contributors; MemPalace remains an external package |
| OpenViking | Official `volcengine/OpenViking` v0.4.21 at `3fca2577520f00b7f580d85d4ac6ae42bb9ba6f1` | Anonymous loopback `/health` protocol attestation; existing Hermes provider reused and no OpenViking source copied by this fork slice | AGPL-3.0 | Copyright belongs to OpenViking contributors; OpenViking remains an external service/package |
| WYRD Protocol | Official `hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model` v1.0.0 at `9884ce8a9e683dc20f372a91eb66ba5b02561300` | Anonymous loopback `/health` protocol compatibility probe; no WYRD source copied | CC BY 4.0 | Created by Volmarr Wyrd / RuneForgeAI; WYRD remains an external world-model service/package |
| Kista | Official `hrabanazviking/kista` v2.0.0 at `ce6313cc392589abd43a5fcf614e0e272663961f` | Read-only `kista get <service>` JSON protocol integration through the Hermes Secret Source plugin API; no Kista source copied | MIT | Authored by Runa Gridweaver; Kista remains an external encrypted-vault CLI |

## Import Rule

Before copying or adapting another project into this repository, add an entry containing:

- source repository and exact commit;
- original author or organization;
- files or data copied or adapted;
- original license and required notices;
- local destination;
- summary of modifications.

When terms are unclear, integrate through an external CLI, MCP, REST, or package boundary instead
of copying source code.
