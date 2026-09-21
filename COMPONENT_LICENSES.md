# Component License Ledger

This file records the license and provenance of code or data incorporated into this repository.
It does not replace the original license text.

| Component | Source | Incorporated material | License | Attribution / notes |
|---|---|---|---|---|
| Hermes Agent | `NousResearch/hermes-agent` | Current runtime, applications, tests, documentation, and build infrastructure | MIT | Copyright 2025 Nous Research; see `LICENSE` |
| Volmarr / RuneForgeAI project documents | Authored for `hrabanazviking/hermes-agent-RuneForgeAI-hack` | Personal README, roadmap, philosophy, operating rules, and architecture records | Not separately declared | Do not infer MIT solely from repository placement; declare terms before external reuse |
| Verðandi | `hrabanazviking/Verdandi` at `dc7139416ef4bb67c9ba29c1148615d0d259b7db` | JSON-line event protocol integration; no Verðandi source copied | MIT | Copyright 2026 Volmarr Wyrd and Runa Gridweaver Freyjasdottir |
| Project A.E.S.I.R. | `hrabanazviking/RuneForgeAI-Project-Aesir` at `c1a4410ca254fa388e45936b02230999d0906a4c` | OpenAI-compatible loopback protocol integration; no A.E.S.I.R. source copied | AGPL-3.0 | Copyright 2026 Volmarr Wyrd; A.E.S.I.R. remains an external service |
| Bifröst | `hrabanazviking/bifrost` at `b66e98cc8a79d4dede22ba11d68a1a5ecd22ebd6` | Python package interface integration; no Bifröst source copied | MIT | Copyright 2025 Runa Gridweaver and Volmarr Viking; Bifröst remains an external package |
| Earlier Present State work | `hrabanazviking/hermes-agent` at `761a8559084e7f582fe4c205bfa3835c1df9df42` | Present-state data model and behavior adapted into `plugins/volmarr-core/present_state.py`; former Hermes core wiring was not copied | MIT | Original commit authored by Volmarr Wyrd in the personal Hermes fork; root MIT notice remains preserved |

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
