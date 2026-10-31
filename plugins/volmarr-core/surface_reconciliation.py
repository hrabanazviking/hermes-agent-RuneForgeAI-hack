"""Surface reconciliation (Self-Aware Agency roadmap §§19-21).

§§19-21 propose, for the self-aware agency line: a repository
layout (ten modules and eleven state files inside
``plugins/volmarr-core/`` and the profile ``entity/``
directory), fifteen ``plugin.yaml`` configuration keys, and a
nineteen-command operator CLI under ``hermes volmarr``. The
domain sections (§§5-18) were built slice by slice and did not
always land under the proposed names, so this module records
the reconciliation honestly and in code:

- every proposed item is classified ``exact`` (it stands under
  the proposed name), ``equivalent`` (the capability stands
  under a different, already-banked name — the proposed name
  is NOT recreated as a shim; internal paths are not API), or
  ``missing`` / ``deferred`` (named plainly, with the reason);
- the one genuine functional gap the audit found — §21's
  operator inspection commands did not exist at all — is
  implemented here as a read-only inspection service over the
  six §21 surfaces (self, awareness, reflection, motivation,
  curiosity, autonomy), wired into ``hermes volmarr`` by
  ``cli.py``. Inspection never invokes an LLM (the §21 rule),
  never writes, and reports counts, identifiers, and numeric
  state only — no claim statements, lessons, or question text.

Defaults divergence, recorded once here: several §20 keys were
suggested with ``default: false``, but the Emergent Agency
phases banked the core stores (self-model, drives,
metacognition, curiosity, autonomy) as enabled-by-default
inside an already opt-in plugin, while every Self-Aware
detail layer (§§5-18 reconciliations) is disabled by default.
The banked defaults stand; the table notes each one.

This layer is operator-facing only: it owns no persistent
file, emits no packet item, and registers no hook.
"""

from __future__ import annotations

from typing import Any

# -- §19: proposed repository additions --------------------------------

# (proposed module, status, modules it stands as)
REPOSITORY_ADDITIONS = (
    ("self_model.py", "exact", ("self_model.py",)),
    ("awareness.py", "exact", ("awareness.py",)),
    ("discrepancy.py", "equivalent",
     ("self_model_layers.py", "awareness.py", "persona_canon.py")),
    ("reflection.py", "equivalent",
     ("metacognition.py", "reflection_detail.py")),
    ("drives.py", "exact", ("drives.py",)),
    ("motivation.py", "equivalent",
     ("drives.py", "motivation_lifecycle.py")),
    ("curiosity.py", "exact", ("curiosity.py",)),
    ("autonomy.py", "exact", ("autonomy.py",)),
    ("agency.py", "exact", ("agency.py",)),
    ("epistemics.py", "exact", ("epistemics.py",)),
)

# (proposed state file, status, file it stands as)
STATE_FILES = (
    ("entity/entity.yaml", "exact", "entity/entity.yaml"),
    ("entity/relationships.yaml", "exact", "entity/relationships.yaml"),
    ("entity/goals.yaml", "exact", "entity/goals.yaml"),
    ("entity/continuity.json", "exact", "entity/continuity.json"),
    ("entity/consolidation.json", "exact", "entity/consolidation.json"),
    ("entity/self_model.yaml", "exact", "entity/self_model.yaml"),
    ("entity/awareness.json", "exact", "entity/awareness.json"),
    ("entity/drives.json", "equivalent", "entity/motivation.yaml"),
    ("entity/curiosity.yaml", "exact", "entity/curiosity.yaml"),
    ("entity/reflections.jsonl", "exact", "entity/reflections.jsonl"),
    ("entity/autonomy_policy.yaml", "exact",
     "entity/autonomy_policy.yaml"),
)

# -- §20: proposed configuration additions -----------------------------

# (proposed key, status, key it stands as, note)
CONFIGURATION_ADDITIONS = (
    ("self_model_enabled", "exact", "self_model_enabled",
     "banked default is true, not the suggested false"),
    ("self_model_path", "exact", "self_model_path", ""),
    ("awareness_enabled", "exact", "awareness_enabled",
     "banked default false, as suggested"),
    ("awareness_path", "exact", "awareness_path", ""),
    ("reflection_enabled", "equivalent", "reflection_detail_enabled",
     "the Phase 3 store's metacognition_enabled is the second half"),
    ("reflection_path", "equivalent", "reflection_detail_log_path",
     "banked default is the proposed entity/reflections.jsonl"),
    ("reflection_local_first", "missing", "",
     "no such key: reflection is local by construction — no "
     "external reflection service exists for a flag to prefer "
     "against, so the key would be inert"),
    ("motivation_enabled", "exact", "motivation_enabled",
     "banked default is true, not the suggested false"),
    ("drives_path", "equivalent", "motivation_path",
     "banked default entity/motivation.yaml, not entity/drives.json"),
    ("curiosity_enabled", "exact", "curiosity_enabled",
     "banked default is true, not the suggested false"),
    ("curiosity_path", "exact", "curiosity_path", ""),
    ("autonomy_enabled", "exact", "autonomy_enabled",
     "banked default is true, not the suggested false"),
    ("autonomy_policy_path", "exact", "autonomy_policy_path", ""),
    ("agency_cycle_max_actions", "equivalent",
     "agency_cycle_detail_max_actions",
     "banked default is 3, not the suggested 1; the Phase 6 "
     "agency_max_candidates key is the candidate-side bound"),
)

# -- §21: proposed CLI surface ------------------------------------------

# (proposed command, status, actual command or reason)
CLI_COMMANDS = (
    ("self health", "implemented", "hermes volmarr self health"),
    ("self show", "implemented", "hermes volmarr self show"),
    ("self refresh", "deferred",
     "the self-model is evidence-merged, not refreshed on demand"),
    ("awareness health", "implemented",
     "hermes volmarr awareness health"),
    ("awareness show", "implemented", "hermes volmarr awareness show"),
    ("awareness scan", "deferred",
     "AwarenessStore.refresh exists service-side; wiring a CLI "
     "write command is a separate slice"),
    ("reflection health", "implemented",
     "hermes volmarr reflection health"),
    ("reflection run", "deferred",
     "recording a reflection is the metacognition store's "
     "explicit service call; no CLI form"),
    ("reflection recent", "implemented",
     "hermes volmarr reflection recent"),
    ("motivation show", "implemented",
     "hermes volmarr motivation show"),
    ("motivation evaluate", "deferred",
     "lifecycle evaluation needs a proposal argument; it stands "
     "service-side in motivation_lifecycle.py"),
    ("curiosity show", "implemented",
     "hermes volmarr curiosity show"),
    ("curiosity add", "deferred",
     "adding a question is the curiosity store's explicit "
     "service call; no CLI form"),
    ("curiosity select", "deferred",
     "frontier selection stands service-side (background "
     "research and the agency orchestrator)"),
    ("autonomy show", "implemented", "hermes volmarr autonomy show"),
    ("autonomy check", "deferred",
     "the Phase 5 gate's evaluate() is service-side; a CLI "
     "check needs a proposal argument shape §21 does not specify"),
    ("autonomy explain", "deferred",
     "decisions already carry their reason codes service-side"),
    ("agency status", "exact", "hermes volmarr agency status"),
    ("agency cycle", "deferred",
     "the orchestrator's run_cycle is service-side; agency run "
     "is the proposal-only routine, not the cycle"),
)

SURFACES = (
    "self", "awareness", "reflection", "motivation", "curiosity",
    "autonomy",
)


def repository_additions() -> list[dict[str, Any]]:
    return [
        {"proposed": name, "status": status, "stands_as": list(stands)}
        for name, status, stands in REPOSITORY_ADDITIONS
    ]


def state_files() -> list[dict[str, Any]]:
    return [
        {"proposed": name, "status": status, "stands_as": stands}
        for name, status, stands in STATE_FILES
    ]


def configuration_additions() -> list[dict[str, Any]]:
    return [
        {"proposed": name, "status": status, "stands_as": stands,
         "note": note}
        for name, status, stands, note in CONFIGURATION_ADDITIONS
    ]


def cli_commands() -> list[dict[str, Any]]:
    return [
        {"proposed": name, "status": status, "stands_as": stands}
        for name, status, stands in CLI_COMMANDS
    ]


def reconciliation_summary() -> dict[str, dict[str, int]]:
    """Counts per table and status. Pure and deterministic."""
    summary: dict[str, dict[str, int]] = {}
    for label, rows in (
        ("repository", repository_additions()),
        ("state_files", state_files()),
        ("configuration", configuration_additions()),
        ("cli", cli_commands()),
    ):
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        summary[label] = counts
    return summary


class SurfaceInspectionService:
    """Read-only §21 inspection over the six proposed surfaces.

    Each surface reports ``ok`` (read), ``disabled`` (its store
    is not enabled), ``not_created`` (enabled but its state
    file does not exist yet), or ``unreadable`` (the store
    refused the read; only the error type is named). Detail is
    counts, identifiers, and numeric state only. This service
    writes nothing and invokes no model.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def surfaces(self) -> list[str]:
        return list(SURFACES)

    def inspect(self, surface: str) -> dict[str, Any]:
        if surface not in SURFACES:
            return {
                "surface": str(surface), "status": "unknown_surface",
                "enabled": None, "detail": {},
            }
        try:
            return getattr(self, f"_inspect_{surface}")()
        except Exception as exc:  # the store refused the read
            return {
                "surface": surface, "status": "unreadable",
                "enabled": None, "detail": {},
                "error_type": type(exc).__name__,
            }

    def inspect_all(self) -> dict[str, Any]:
        return {name: self.inspect(name) for name in SURFACES}

    # -- surfaces -------------------------------------------------------

    def _inspect_self(self) -> dict[str, Any]:
        from .self_model import SelfModelStore

        store = SelfModelStore(self._ctx)
        if not store.enabled():
            return self._report("self", "disabled", False)
        if not store.path().is_file():
            return self._report("self", "not_created", True)
        claims = store.claims()
        domains: dict[str, int] = {}
        for claim in claims:
            domains[claim.domain] = domains.get(claim.domain, 0) + 1
        contradicted = sum(
            1 for row in store.records() if row["contradictions"])
        return self._report("self", "ok", True, {
            "claims": len(claims),
            "domains": domains,
            "contradicted_claims": contradicted,
        })

    def _inspect_awareness(self) -> dict[str, Any]:
        from .awareness import AwarenessStore

        store = AwarenessStore(self._ctx)
        if not store.enabled():
            return self._report("awareness", "disabled", False)
        if not store.path().is_file():
            return self._report("awareness", "not_created", True)
        snap = store.read()
        return self._report("awareness", "ok", True, {
            "attention_target": snap["attention_target"],
            "current_goals": len(snap["current_goal_ids"]),
            "uncertainty": snap["uncertainty"],
            "cognitive_load": snap["cognitive_load"],
            "salient_discrepancies": len(snap["salient_discrepancies"]),
            "known_blind_spots": len(snap["known_blind_spots"]),
            "reflection_recommended": snap["reflection_recommended"],
            "observed_at": snap["observed_at"],
        })

    def _inspect_reflection(self) -> dict[str, Any]:
        from .metacognition import MetacognitionStore

        store = MetacognitionStore(self._ctx)
        if not store.enabled():
            return self._report("reflection", "disabled", False)
        if not store.summary_path().is_file():
            return self._report("reflection", "not_created", True)
        summary = store.summary()
        return self._report("reflection", "ok", True, {
            "total_reflections": summary["total_reflections"],
            "last_reflection_at": summary["last_reflection_at"],
            "recent_lessons": len(summary["recent_lessons"]),
            "recent_strategy_changes":
                len(summary["recent_strategy_changes"]),
        })

    def _inspect_motivation(self) -> dict[str, Any]:
        from .drives import DriveStore, tension_of

        store = DriveStore(self._ctx)
        if not store.enabled():
            return self._report("motivation", "disabled", False)
        if not store.path().is_file():
            return self._report("motivation", "not_created", True)
        drives = store.drives()
        top_id, top_tension = "", 0.0
        for drive in drives:
            tension = tension_of(drive)
            if tension > top_tension:
                top_id, top_tension = drive.drive_id, tension
        return self._report("motivation", "ok", True, {
            "drives": len(drives),
            "enabled_drives": sum(1 for d in drives if d.enabled),
            "top_drive": top_id,
            "top_tension": round(top_tension, 4),
        })

    def _inspect_curiosity(self) -> dict[str, Any]:
        from .curiosity import CuriosityStore

        store = CuriosityStore(self._ctx)
        if not store.enabled():
            return self._report("curiosity", "disabled", False)
        if not store.path().is_file():
            return self._report("curiosity", "not_created", True)
        questions = store.questions()
        by_status: dict[str, int] = {}
        for question in questions:
            by_status[question.status] = \
                by_status.get(question.status, 0) + 1
        return self._report("curiosity", "ok", True, {
            "questions": len(questions),
            "by_status": by_status,
            "frontier": len(store.frontier()),
        })

    def _inspect_autonomy(self) -> dict[str, Any]:
        from .autonomy import AutonomyStore

        store = AutonomyStore(self._ctx)
        if not store.enabled():
            return self._report("autonomy", "disabled", False)
        if not store.policy_path().is_file() \
                or not store.state_path().is_file():
            return self._report("autonomy", "not_created", True)
        policy = store.policy()
        state = store.state()
        return self._report("autonomy", "ok", True, {
            "mode": policy["mode"],
            "capabilities": len(policy["capabilities"]),
            "proposals_considered": state["proposals_considered"],
            "decisions_allow": state["decisions_allow"],
            "decisions_confirmation": state["decisions_confirmation"],
            "decisions_deny": state["decisions_deny"],
            "actions_executed": state["actions_executed"],
            "actions_failed": state["actions_failed"],
            "circuit_breaker_tripped":
                state["circuit_breaker_tripped"],
            "paused": state["paused"],
        })

    @staticmethod
    def _report(surface: str, status: str, enabled: bool | None,
                detail: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "surface": surface, "status": status,
            "enabled": enabled, "detail": detail or {},
        }


__all__ = [
    "REPOSITORY_ADDITIONS",
    "STATE_FILES",
    "CONFIGURATION_ADDITIONS",
    "CLI_COMMANDS",
    "SURFACES",
    "SurfaceInspectionService",
    "repository_additions",
    "state_files",
    "configuration_additions",
    "cli_commands",
    "reconciliation_summary",
]
