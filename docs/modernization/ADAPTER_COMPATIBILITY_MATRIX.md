# Adapter compatibility matrix (W02/U2)

What the fork at the banked W01 head actually runs against, verified
2026-11-07 on purplelongship from the `yrsa/hermes-team-03` tree.
Engine pins are carried from the W00 integration lock
(`docs/modernization/integration-lock.json`, still DRAFT — its
promotion is a later wave's job); W02 verified the rows it touches
(platform, Python, uv, plugins, ravens) and corrects the ravens row,
which the draft recorded before the tree reached this machine.

## Platform & runtime

| Surface | Verified value | Source |
|---|---|---|
| Machine | purplelongship, linux x86_64 | device record |
| Fork head (banked main) | `1cd7d59015cb46775cc666655a99a44b9b0a1aa3` | git |
| Upstream pin | NousResearch hermes-agent **v0.23.0**, commit `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19` | integration lock |
| Python | 3.14.9 (tool-store build); `requires-python = ">=3.11,<3.15"` | staged env |
| uv | 0.13.5 (PM-pinned tool store) | staged env |
| Lock | 358 packages, `uv lock --check` clean | uv |
| Dependency posture | 137 exact `==` pins, 17 range-style specifiers (all in extras/groups, all upper-bounded) | pyproject audit, W02 |
| SBOM | `docs/modernization/SBOM.cdx.json`: 352 registry, 3 editable-local, 2 git, 1 archive-url | `scripts/generate_sbom.py` |
| ARM64 (Mimir) | **not yet verified** — PyYAML 6.0.3 wheel smoke on real ARM64 hardware remains an open ticket | — |

## Fork plugins (all discovered by `hermes plugins list` in the cold install)

| Plugin | Version |
|---|---|
| volmarr-core | 0.26.0 |
| volmarr-voice | 1.0.0 |
| volmarr-astrology | 0.7.0 |
| volmarr-tarot | 0.3.0 |
| volmarr-seidr | 0.4.0 |
| volmarr-rpg | 0.8.0 |
| volmarr-hamr | 0.4.0 |
| volmarr-smidja | 0.1.0 |
| kista-secret-source | 0.2.0 |

## Ravens (corrected W02)

| Package | Version | Binding | Suites |
|---|---|---|---|
| muninn | 1.0.0 | `[tool.uv.sources]` editable `../ravens/muninn`, opt-in `volmarr-ravens` extra, never PyPI | 36 passed |
| huginn | 1.0.0 | `[tool.uv.sources]` editable `../ravens/huginn`, opt-in `volmarr-ravens` extra, never PyPI | 27 passed |

Ravens tree on purplelongship: `~/ravens` at `fc761f020b39f9be875310d271aac7423239d5f8`,
byte-identical to the VM canonical tree. The integration lock's
"tree absent on purplelongship" note is stale and superseded by this row.

## External engines (pins as recorded in the DRAFT integration lock; not re-verified in W02)

| Engine | Pinned | Lock says update needed |
|---|---|---|
| Verdandi | `dc7139416ef4` | yes |
| Project A.E.S.I.R. | `c1a4410ca254` | yes |
| Bifrost | `b66e98cc8a79` | yes |
| MemPalace | v3.10.0 `22fd87f09c19` | yes |
| MemPalace mirror (hrabanazviking) | `ff1bdf03407b` | no |
| OpenViking | v0.4.21 `3fca2577520f` | yes |
| WYRD Protocol | v1.0.0 `9884ce8a9e68` | yes |
| Kista | v2.0.0 `ce6313cc3925` | yes |
| Astrology Engine | `1709fcfc1e00` | yes |
| RuneTarotEngine | no pin recorded | E0 must establish one |
| Seidr Engine | no pin recorded | E0 must establish one |
| Hamr | no pin recorded | E0 must establish one |
| Seidr-Smidja | no pin recorded | E0 must establish one |

Engine updates belong to the E-waves, not W02; this matrix records the
compatibility surface W02's deployment safety work verified.
