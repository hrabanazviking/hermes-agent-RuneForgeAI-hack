# Volmarr Hermes Architecture

## Purpose

This fork turns Hermes Agent into a local-first persistent entity runtime while preserving
Hermes as the replaceable, upstream-compatible agent shell.

The **Milestone 0** foundation is complete and the first Volmarr-specific runtime slice is now
implemented as an opt-in plugin. The upstream Hermes runtime remains intact.

## Project Laws

1. `README.md` belongs to this fork. An upstream intake must never replace or rewrite it.
2. Hermes core remains a narrow waist. Personal capability enters through documented plugins,
   hooks, providers, skills, tools, MCP, CLI, or service boundaries.
3. Hermes core must not import Volmarr-specific runtime packages.
4. A plugin may use Hermes extension interfaces; it may not patch Hermes facades for its own
   convenience.
5. Memory, affect, world state, identity, events, and cognition are distinct domains with
   explicit contracts. No subsystem becomes a miscellaneous state bucket.
6. LLM providers are replaceable cognitive organs. Persistent identity and state never depend
   on one model or provider.
7. External projects remain external services or packages unless a reviewed component import
   has clear ownership, tests, provenance, and license terms.
8. Every new persistent format is versioned and has a restore or migration story.

## Ownership Map

| Domain | Owns | Must not own |
|---|---|---|
| Hermes shell | Turns, sessions, provider resolution, tools, gateways, cron, plugin contracts | Volmarr identity, affect, world truth, or project-specific policy |
| Composition plugin | Registration, lifecycle wiring, configuration validation, adapter construction | Domain logic or durable state |
| Events | Typed lifecycle signals and Verðandi transport | Memory, world truth, or business decisions |
| Present state | Small set of facts true now | Verbatim history or objective world simulation |
| Memory fabric | Retrieval, write routing, bounded memory packets | Identity authority or world-state mutation |
| Affect | Regulatory and PAD-style state transitions | Hardware telemetry collection or prompt assembly |
| World | Deterministic WYRD entities, locations, objects, and transitions | Episodic narrative memory |
| Identity | Stable entity ID, values, relationships, goals, continuity metadata | Model/provider ownership |
| Cognition | Local/cloud route selection, budgets, escalation, telemetry | Direct reimplementation of Hermes providers |
| Continuity | Snapshots, manifests, restore, backup verification | Live database operation from cloud-sync folders |
| Integrations | Translation to Kista, Verðandi, Bifröst, WYRD, A.E.S.I.R., and other services | Core domain policy |

## Dependency Law

```text
Hermes extension interfaces
          ↑
composition plugin
          ↓
application orchestration
          ↓
domain contracts
          ↑
integration adapters → external services
```

- Domain code may depend on the Python standard library and its own contracts.
- Integration adapters depend inward on domain contracts.
- The composition plugin is the only place that knows both Hermes registration APIs and the
  concrete Volmarr adapters.
- External services never call directly into Hermes facades; they enter through adapters and
  typed application operations.
- A generic Hermes extension-surface change is permitted only when a real vertical slice proves
  the existing surface insufficient.

## First Vertical Slice

The first runtime slice is a **Verðandi lifecycle bridge** implemented through existing Hermes
hooks. It publishes a small, versioned event envelope for session, turn, and tool lifecycle events
without adding an LLM call or modifying persistent memory.

This slice is first because it proves the extension boundary and provides the signal spine used
later by cognition, memory, affect, world state, health, and continuity.

**Status:** implemented as the opt-in `volmarr-core` plugin. The bridge resolves its socket from
the active profile on every event, sends metadata-only envelopes, and fails open when Verðandi is
offline or the host lacks Unix-domain-socket support. Verðandi's current hub is Unix-only, so the
transport operates on Linux/WSL and remains inert on native Windows. Hermes core does not import
the plugin.

## Verification Standard

- Run tests through `scripts/run_tests.sh`.
- Exercise plugins through real discovery against a temporary `HERMES_HOME`.
- Preserve prompt-cache stability and profile scope.
- Keep upstream Hermes behavior unchanged when the personal plugin is disabled.
- Add behavior-contract tests, not source-shape or catalog-count snapshots.
