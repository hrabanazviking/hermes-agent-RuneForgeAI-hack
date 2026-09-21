# Personal Fork Customizations

This ledger records intentional differences from `NousResearch/hermes-agent`.

## Baseline

- Personal fork baseline: `214623389a37dc9608cc54cb8910d35d0ab12197`
- Baseline purpose: current upstream Hermes runtime with Volmarr-specific documentation layered
  on top.
- Runtime divergence at Milestone 0: **none**.
- Test divergence at Milestone 0: **none**.

## Intentional Differences

| Area | Difference | Reason | Upstream surface touched |
|---|---|---|---|
| Project identity | Personal `README.md` and RuneForgeAI project documents | Define the fork's purpose, culture, and roadmap | Documentation only |
| Upstream intake | `scripts/sync_upstream.py` preserves `README.md` byte-for-byte | Upstream documentation must not overwrite the fork's identity | Maintenance workflow only |
| Architecture | `ARCHITECTURE_VOLMARR.md` defines personal domain boundaries | Prevent project-specific systems from leaking into Hermes core | Documentation only |
| Licensing | Component and notice ledgers track provenance per imported system | Preserve source-specific licenses and attribution | Documentation only |

## Runtime Customizations

| Domain | Behavior | Hermes surface | Verification | Upstream-sync risk |
|---|---|---|---|---|
| Events | Opt-in `volmarr-core` plugin publishes versioned session, turn, and tool lifecycle metadata to Verðandi on Unix-socket-capable hosts; native Windows safely drops events until Verðandi gains a compatible transport | General plugin hooks only | Real discovery, privacy contract, offline-hub and unsupported-platform fail-open tests | Low; additive plugin directory, no core patch |
| Health | `hermes volmarr health [--json]` proves Verðandi responsiveness with a bounded `ping`/`pong` exchange scoped to the active profile | General plugin CLI registration | Real discovery, valid-pong and protocol-error contracts | Low; additive command owned by the plugin |
| Cognition endpoint | `hermes volmarr cognition health [--json]` validates a profile-scoped, loopback-only A.E.S.I.R. model catalog and credential file | General plugin CLI registration plus external HTTP protocol adapter | Real loopback server with A→B→A profile isolation and remote-host refusal | Low; no Hermes provider or core patch |

Every future entry must name:

- the behavior added or changed;
- its owning domain;
- the exact Hermes extension surface used;
- persistent formats or configuration keys introduced;
- verification performed;
- upstream-sync risk;
- source and license provenance when adapted from another project.
