"""Operator CLI for the opt-in Volmarr composition plugin."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agency_routines import (
    AgencyRoutineError,
    AgencyRoutineManager,
    AgencyRoutineService,
)
from .cognition import probe_aesir
from .consolidation import (
    ConsolidationService,
    probe_consolidation,
    sleep_routine_manager,
)
from .execution import CognitionExecutionRequest, CognitionExecutor
from .health import probe_verdandi
from .heartbeat import HeartbeatError, HeartbeatService, probe_heartbeat
from .identity import IdentityError, probe_identity
from .memory_fabric import probe_bifrost, probe_bifrost_muninn
from .ravens import probe_ravens
from .ravens_writes import (
    consolidate_memories,
    decay_memories,
    ingest_memory,
    reinforce_memories,
)
from .mempalace import probe_mempalace
from .openviking import probe_openviking
from .routing import CognitionRequest, CognitionRouter, RoutingRequestError
from .routines import RoutineError, RoutineManager, RoutineService
from .sessiondb import probe_sessiondb
from .surface_reconciliation import SurfaceInspectionService
from .telemetry import CognitionTelemetry
from .wyrd import probe_wyrd


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="volmarr_action")
    health = subcommands.add_parser(
        "health",
        help="Probe the active profile's Verðandi transport",
    )
    health.add_argument("--json", action="store_true", dest="json_output")
    cognition = subcommands.add_parser(
        "cognition",
        help="Inspect the local reflex-cognition endpoint",
    )
    cognition_subcommands = cognition.add_subparsers(dest="cognition_action")
    cognition_health = cognition_subcommands.add_parser(
        "health",
        help="Probe the configured A.E.S.I.R. model catalog",
    )
    cognition_health.add_argument("--json", action="store_true", dest="json_output")
    cognition_route = cognition_subcommands.add_parser(
        "route",
        help="Choose a cognition tier from a metadata-only JSON request",
    )
    cognition_route.add_argument(
        "--request",
        default="-",
        help="JSON request file, or - for standard input",
    )
    cognition_execute = cognition_subcommands.add_parser(
        "execute",
        help="Execute an admitted local reflex request or return a route directive",
    )
    cognition_execute.add_argument(
        "--request",
        default="-",
        help="JSON execution request file, or - for standard input",
    )
    memory = subcommands.add_parser(
        "memory",
        help="Inspect the Bifröst memory-fabric attachment",
    )
    memory_subcommands = memory.add_subparsers(dest="memory_action")
    memory_health = memory_subcommands.add_parser(
        "health",
        help="Validate Bifröst and the active profile's Mímir store",
    )
    memory_health.add_argument("--json", action="store_true", dest="json_output")
    corpus = memory_subcommands.add_parser(
        "corpus",
        help="Inspect the W06 unbounded MEMORY.md / USER.md corpus",
    )
    corpus_subcommands = corpus.add_subparsers(dest="corpus_action")
    corpus_status = corpus_subcommands.add_parser(
        "status",
        help="Show full-store vs hot-view sizes, corpus generation and index state (read-only)",
    )
    corpus_status.add_argument("--json", action="store_true", dest="json_output")
    mempalace = memory_subcommands.add_parser(
        "mempalace",
        help="Inspect the profile-scoped MemPalace episodic store",
    )
    mempalace_subcommands = mempalace.add_subparsers(dest="mempalace_action")
    mempalace_health = mempalace_subcommands.add_parser(
        "health",
        help="Validate the MemPalace package and Chroma SQLite store read-only",
    )
    mempalace_health.add_argument("--json", action="store_true", dest="json_output")
    openviking = memory_subcommands.add_parser(
        "openviking",
        help="Inspect the local OpenViking context service",
    )
    openviking_subcommands = openviking.add_subparsers(dest="openviking_action")
    openviking_health = openviking_subcommands.add_parser(
        "health",
        help="Validate the bundled provider and official server contract read-only",
    )
    openviking_health.add_argument("--json", action="store_true", dest="json_output")
    sessiondb = memory_subcommands.add_parser(
        "sessiondb",
        help="Inspect Hermes' canonical profile session store",
    )
    sessiondb_subcommands = sessiondb.add_subparsers(dest="sessiondb_action")
    sessiondb_health = sessiondb_subcommands.add_parser(
        "health",
        help="Audit SessionDB integrity and transcript ownership read-only",
    )
    sessiondb_health.add_argument("--json", action="store_true", dest="json_output")
    muninn = memory_subcommands.add_parser(
        "muninn",
        help="Inspect the profile-scoped Bifröst Muninn association store",
    )
    muninn_subcommands = muninn.add_subparsers(dest="muninn_action")
    muninn_health = muninn_subcommands.add_parser(
        "health",
        help="Validate the Muninn association store read-only, importing no package",
    )
    muninn_health.add_argument("--json", action="store_true", dest="json_output")
    ravens = memory_subcommands.add_parser(
        "ravens",
        help="Inspect the installed muninn + huginn ravens packages",
    )
    ravens_subcommands = ravens.add_subparsers(dest="ravens_action")
    ravens_health = ravens_subcommands.add_parser(
        "health",
        help="Attest the ravens package contract import-only, constructing nothing",
    )
    ravens_health.add_argument("--json", action="store_true", dest="json_output")
    ravens_reinforce = ravens_subcommands.add_parser(
        "reinforce",
        help="Muninn reinforcement for the given memory ids (write; flag-gated)",
    )
    ravens_reinforce.add_argument(
        "--ids",
        required=True,
        help="Comma-separated positive memory ids to activate and wire",
    )
    ravens_reinforce.add_argument("--valence", type=float, default=0.0)
    ravens_reinforce.add_argument("--json", action="store_true", dest="json_output")
    ravens_decay = ravens_subcommands.add_parser(
        "decay",
        help="Run Muninn decay over the profile store (write; flag-gated)",
    )
    ravens_decay.add_argument("--days", type=float, default=1.0)
    ravens_decay.add_argument("--json", action="store_true", dest="json_output")
    ravens_consolidate = ravens_subcommands.add_parser(
        "consolidate",
        help="Run Muninn consolidation on the profile store (write; flag-gated)",
    )
    ravens_consolidate.add_argument("--json", action="store_true", dest="json_output")
    ravens_ingest = ravens_subcommands.add_parser(
        "ingest",
        help="Ingest one memory into the profile's Huginn store (write; flag-gated)",
    )
    ravens_ingest.add_argument("--content", required=True)
    ravens_ingest.add_argument("--category", default="general")
    ravens_ingest.add_argument("--importance", type=int, default=5)
    ravens_ingest.add_argument(
        "--tags", default="", help="Comma-separated tags (may be empty)"
    )
    ravens_ingest.add_argument("--valence", type=float, default=0.0)
    ravens_ingest.add_argument("--json", action="store_true", dest="json_output")
    world = subcommands.add_parser(
        "world",
        help="Inspect the WYRD world-model attachment",
    )
    world_subcommands = world.add_subparsers(dest="world_action")
    world_health = world_subcommands.add_parser(
        "health",
        help="Validate the official WYRD loopback liveness contract read-only",
    )
    world_health.add_argument("--json", action="store_true", dest="json_output")
    identity = subcommands.add_parser(
        "identity",
        help="Inspect the active profile's stable entity identity",
    )
    identity_subcommands = identity.add_subparsers(dest="identity_action")
    identity_health = identity_subcommands.add_parser(
        "health",
        help="Validate the structured entity identity read-only",
    )
    identity_health.add_argument("--json", action="store_true", dest="json_output")
    heartbeat = subcommands.add_parser(
        "heartbeat",
        help="Inspect or pulse the active entity's continuity heartbeat",
    )
    heartbeat_subcommands = heartbeat.add_subparsers(dest="heartbeat_action")
    heartbeat_status = heartbeat_subcommands.add_parser(
        "status",
        help="Report current continuity freshness read-only",
    )
    heartbeat_status.add_argument("--json", action="store_true", dest="json_output")
    heartbeat_pulse = heartbeat_subcommands.add_parser(
        "pulse",
        help="Record one pulse; recurring cadence remains owned by Hermes cron",
    )
    heartbeat_pulse.add_argument(
        "--source",
        choices=("manual", "cron"),
        default="manual",
    )
    heartbeat_pulse.add_argument("--json", action="store_true", dest="json_output")
    routines = subcommands.add_parser(
        "routines",
        help="Manage entity routines backed by Hermes cron",
    )
    routines_subcommands = routines.add_subparsers(dest="routines_action")
    routines_status = routines_subcommands.add_parser(
        "status",
        help="Inspect the installed routine definition read-only",
    )
    routines_status.add_argument("--json", action="store_true", dest="json_output")
    routines_install = routines_subcommands.add_parser(
        "install",
        help="Idempotently install the routine paused unless --activate is supplied",
    )
    routines_install.add_argument("--activate", action="store_true")
    routines_install.add_argument("--json", action="store_true", dest="json_output")
    routines_run = routines_subcommands.add_parser(
        "run",
        help="Run one deterministic routine (used by the installed cron script)",
    )
    routines_run.add_argument("--kind", choices=("frequent",), required=True)
    routines_run.add_argument("--json", action="store_true", dest="json_output")
    sleep = subcommands.add_parser(
        "sleep",
        help="Manage non-destructive entity consolidation",
    )
    sleep_subcommands = sleep.add_subparsers(dest="sleep_action")
    sleep_status = sleep_subcommands.add_parser(
        "status",
        help="Inspect the latest consolidation checkpoint read-only",
    )
    sleep_status.add_argument("--json", action="store_true", dest="json_output")
    sleep_install = sleep_subcommands.add_parser(
        "install",
        help="Install the daily Hermes cron job paused unless --activate is supplied",
    )
    sleep_install.add_argument("--activate", action="store_true")
    sleep_install.add_argument("--json", action="store_true", dest="json_output")
    sleep_run = sleep_subcommands.add_parser(
        "run",
        help="Record one non-destructive consolidation checkpoint",
    )
    sleep_run.add_argument(
        "--source",
        choices=("manual", "cron"),
        default="manual",
    )
    sleep_run.add_argument("--json", action="store_true", dest="json_output")
    persona = subcommands.add_parser(
        "persona",
        help="Live persona operations (W07/P6): the section 12 command table",
    )
    persona_subcommands = persona.add_subparsers(dest="persona_action")
    for _verb, _help in (
        ("status", "Persona status from live reads (honest-empty aware)"),
        ("files", "Manifest inventory, hash-verified live"),
        ("validate", "Section 70 catalogue + on-disk checks"),
        ("diff", "Active generation vs fresh compile (section 74)"),
        ("test", "Measured scenario battery against this profile"),
        ("diagnostics", "Read-only diagnostics bundle (P.020)"),
        ("watchdog", "Bounded read-only drift diagnostics run"),
    ):
        _vp = persona_subcommands.add_parser(_verb, help=_help)
        _vp.add_argument("--json", action="store_true", dest="json_output")
    _search = persona_subcommands.add_parser("search", help="W04 retrieval over the real index")
    _search.add_argument("query")
    _search.add_argument("--limit", type=int, default=5)
    _search.add_argument("--json", action="store_true", dest="json_output")
    _inspect = persona_subcommands.add_parser("inspect", help="Section 71 inspect over the live compile")
    _inspect.add_argument("section", nargs="?", default=None)
    _inspect.add_argument("--json", action="store_true", dest="json_output")
    _explain = persona_subcommands.add_parser("explain", help="Section 72 explain over a stored receipt")
    _explain.add_argument("turn_id")
    _explain.add_argument("--json", action="store_true", dest="json_output")
    _reload = persona_subcommands.add_parser("reload", help="Reload: --dry-run (default) or --activate")
    _reload.add_argument("--activate", action="store_true")
    _reload.add_argument("--json", action="store_true", dest="json_output")
    _export = persona_subcommands.add_parser("export", help="Write a section 75 bundle file")
    _export.add_argument("--dest", default=None)
    _export.add_argument("--json", action="store_true", dest="json_output")
    _import = persona_subcommands.add_parser("import", help="Section 76 import plan (dry-run only in W07)")
    _import.add_argument("bundle")
    _import.add_argument("--json", action="store_true", dest="json_output")
    _backup = persona_subcommands.add_parser("backup", help="Integrity-checked backup (labelled unencrypted-local)")
    _backup.add_argument("--dest", required=True)
    _backup.add_argument("--json", action="store_true", dest="json_output")
    _restore = persona_subcommands.add_parser("restore", help="Restore a verified backup into a non-live profile")
    _restore.add_argument("backup_dir")
    _restore.add_argument("--target", required=True)
    _restore.add_argument("--json", action="store_true", dest="json_output")
    _read = persona_subcommands.add_parser("read", help="Paged read of one document (P.013 pager)")
    _read.add_argument("document_id")
    _read.add_argument("--cursor", type=int, default=0)
    _read.add_argument("--max-bytes", type=int, default=None)
    _read.add_argument("--json", action="store_true", dest="json_output")
    _page = persona_subcommands.add_parser("page", help="Continue a retrieval/read handle")
    _page.add_argument("handle")
    _page.add_argument("--max-bytes", type=int, default=None)
    _page.add_argument("--json", action="store_true", dest="json_output")
    _edit = persona_subcommands.add_parser("edit", help="Bounded section editor (dry-run unless --confirm)")
    _edit.add_argument("stable_id")
    _edit.add_argument("--text", required=True)
    _edit.add_argument("--confirm", action="store_true")
    _edit.add_argument("--approved", action="store_true")
    _edit.add_argument("--json", action="store_true", dest="json_output")
    engines = subcommands.add_parser(
        "engines",
        help="E0 integration ledger (W08): promoted lock status, read-only",
    )
    engines_subcommands = engines.add_subparsers(dest="engines_action")
    engines_status = engines_subcommands.add_parser(
        "status",
        help="Full E0 ledger status from the promoted lock (no network)",
    )
    engines_status.add_argument("--json", action="store_true", dest="json_output")
    engines_show = engines_subcommands.add_parser(
        "show", help="One engine row from the promoted lock, by name"
    )
    engines_show.add_argument("name")
    engines_show.add_argument("--json", action="store_true", dest="json_output")
    engines_validate = engines_subcommands.add_parser(
        "validate", help="Validate the promoted lock against this tree"
    )
    engines_validate.add_argument("--json", action="store_true", dest="json_output")
    capabilities = subcommands.add_parser(
        "capabilities",
        help="N1 capability bus (W09): seed descriptors, read-only",
    )
    capabilities_subcommands = capabilities.add_subparsers(dest="capabilities_action")
    capabilities_list = capabilities_subcommands.add_parser(
        "list", help="List the built-in capability descriptors"
    )
    capabilities_list.add_argument("--json", action="store_true", dest="json_output")
    capabilities_show = capabilities_subcommands.add_parser(
        "show", help="One built-in capability descriptor, by service name"
    )
    capabilities_show.add_argument("name")
    capabilities_show.add_argument("--json", action="store_true", dest="json_output")
    capabilities_validate = capabilities_subcommands.add_parser(
        "validate", help="Validate the built-in descriptors against this tree"
    )
    capabilities_validate.add_argument("--json", action="store_true", dest="json_output")
    capabilities_authorize = capabilities_subcommands.add_parser(
        "authorize", help="Run the N1 permission policy for one built-in service"
    )
    capabilities_authorize.add_argument("--service", required=True)
    capabilities_authorize.add_argument("--caller", required=True)
    capabilities_authorize.add_argument("--action", required=True)
    capabilities_authorize.add_argument("--data-owner", required=True)
    capabilities_authorize.add_argument("--data-class", required=True)
    capabilities_authorize.add_argument("--destination", required=True)
    capabilities_authorize.add_argument("--device", default=None)
    capabilities_authorize.add_argument("--approved", action="store_true")
    capabilities_authorize.add_argument("--json", action="store_true", dest="json_output")
    productivity = subcommands.add_parser(
        "productivity",
        help="N2/N3 productivity (W10): project packets, publish guard, bridge status; read-only",
    )
    productivity_subcommands = productivity.add_subparsers(dest="productivity_action")
    productivity_packet = productivity_subcommands.add_parser(
        "packet", help="Build a live project-context packet for a local repo (read-only)")
    productivity_packet.add_argument("--repo", required=True)
    productivity_packet.add_argument("--json", action="store_true", dest="json_output")
    productivity_publish = productivity_subcommands.add_parser(
        "publish-check", help="Resolve a publish action through the capability policy")
    productivity_publish.add_argument("--caller", required=True)
    productivity_publish.add_argument("--data-owner", required=True)
    productivity_publish.add_argument("--data-class", default="local-private")
    productivity_publish.add_argument("--destination", default="local")
    productivity_publish.add_argument("--approved", action="store_true")
    productivity_publish.add_argument("--json", action="store_true", dest="json_output")
    productivity_bridge = productivity_subcommands.add_parser(
        "bridge-status", help="Samtal bridge + Samkoma contract status (no live connection)")
    productivity_bridge.add_argument("--json", action="store_true", dest="json_output")
    world_bridge = subcommands.add_parser(
        "world-bridge",
        help="N4 embodiment/world (W11): interchange, presence, HUD status; read-only",
    )
    world_bridge_subcommands = world_bridge.add_subparsers(dest="world_bridge_action")
    world_bridge_status = world_bridge_subcommands.add_parser(
        "status", help="World bridge descriptor + availability status (no live connection)")
    world_bridge_status.add_argument("--json", action="store_true", dest="json_output")
    world_bridge_presence = world_bridge_subcommands.add_parser(
        "presence-check", help="Authorize a remote-presence read through the W09 policy")
    world_bridge_presence.add_argument("--caller", required=True)
    world_bridge_presence.add_argument("--data-owner", required=True)
    world_bridge_presence.add_argument("--data-class", default="local-private")
    world_bridge_presence.add_argument("--approved", action="store_true")
    world_bridge_presence.add_argument("--json", action="store_true", dest="json_output")
    edge_research = subcommands.add_parser(
        "edge-research",
        help="N5 edge+research (W12): resource meter, allocator gate, mesh fixtures, repair proposals; read/propose only",
    )
    edge_research_subcommands = edge_research.add_subparsers(dest="edge_research_action")
    edge_research_status = edge_research_subcommands.add_parser(
        "status", help="Edge/research descriptor + honest availability status (no live connection)")
    edge_research_status.add_argument("--json", action="store_true", dest="json_output")
    edge_research_meter = edge_research_subcommands.add_parser(
        "meter", help="Read the local machine resource meter (private, no transmission)")
    edge_research_meter.add_argument("--json", action="store_true", dest="json_output")
    edge_research_propose = edge_research_subcommands.add_parser(
        "propose", help="Record a Lif-thrasir self-repair proposal (never applied)")
    edge_research_propose.add_argument("--title", required=True)
    edge_research_propose.add_argument("--detail", default="")
    edge_research_propose.add_argument("--json", action="store_true", dest="json_output")
    yggdrasil = subcommands.add_parser(
        "yggdrasil",
        help="X.01 Yggdrasil local (section 36): local-host discovery + placement records; no mesh claimed",
    )
    yggdrasil_subcommands = yggdrasil.add_subparsers(dest="yggdrasil_action")
    ygg_status = yggdrasil_subcommands.add_parser(
        "status", help="Yggdrasil local status + audited source facts (no live mesh)")
    ygg_status.add_argument("--json", action="store_true", dest="json_output")
    ygg_discover = yggdrasil_subcommands.add_parser(
        "discover", help="Read-only local-host node discovery (unknown stays unknown)")
    ygg_discover.add_argument("--json", action="store_true", dest="json_output")
    ygg_place = yggdrasil_subcommands.add_parser(
        "place", help="Place one task request JSON against this host (local only)")
    ygg_place.add_argument("--request", required=True)
    ygg_place.add_argument("--caller", required=True)
    ygg_place.add_argument("--json", action="store_true", dest="json_output")
    production = subcommands.add_parser(
        "production",
        help="Q0-Q4 production (W13): status, release scorecard, boundary/threat audit; read-only",
    )
    production_subcommands = production.add_subparsers(dest="production_action")
    production_status_p = production_subcommands.add_parser(
        "status", help="Production status from disk + W08 ledger + W09 registry (no live connection)")
    production_status_p.add_argument("--json", action="store_true", dest="json_output")
    production_scorecard = production_subcommands.add_parser(
        "scorecard", help="Section 32 release scorecard (honest: releasable only when every item is met)")
    production_scorecard.add_argument("--json", action="store_true", dest="json_output")
    production_audit_p = production_subcommands.add_parser(
        "audit", help="Q0 policy + Q1 threat gaps + Q2 unmeasured performance record")
    production_audit_p.add_argument("--json", action="store_true", dest="json_output")
    agency = subcommands.add_parser(
        "agency",
        help="Manage the proposal-only agency review routine (Phase 7)",
    )
    agency_subcommands = agency.add_subparsers(dest="agency_action")
    agency_status = agency_subcommands.add_parser(
        "status",
        help="Inspect the installed agency routine definition read-only",
    )
    agency_status.add_argument("--json", action="store_true", dest="json_output")
    agency_install = agency_subcommands.add_parser(
        "install",
        help="Idempotently install the agency routine paused unless --activate is supplied",
    )
    agency_install.add_argument("--activate", action="store_true")
    agency_install.add_argument("--json", action="store_true", dest="json_output")
    agency_run = agency_subcommands.add_parser(
        "run",
        help="Run one proposal-only agency review (executes nothing)",
    )
    agency_run.add_argument("--json", action="store_true", dest="json_output")
    agency_evaluation = agency_subcommands.add_parser(
        "evaluation",
        help="Report agency routine evaluation counts read-only",
    )
    agency_evaluation.add_argument("--json", action="store_true", dest="json_output")
    # §21 inspection surface (Slice 117): read-only, no LLM.
    for surface, verbs in (
        ("self", ("health", "show")),
        ("awareness", ("health", "show")),
        ("reflection", ("health", "recent")),
        ("motivation", ("show",)),
        ("curiosity", ("show",)),
        ("autonomy", ("show",)),
    ):
        surface_parser = subcommands.add_parser(
            surface,
            help=f"Inspect the {surface} surface read-only (§21)",
        )
        surface_subcommands = surface_parser.add_subparsers(
            dest=f"{surface}_action")
        for verb in verbs:
            verb_parser = surface_subcommands.add_parser(
                verb, help=f"Report the {surface} surface ({verb})")
            verb_parser.add_argument(
                "--json", action="store_true", dest="json_output")


def _load_json_request(source: str, *, max_bytes: int) -> dict:
    if source == "-":
        raw = sys.stdin.read(max_bytes + 1)
    else:
        with Path(source).open("rb") as stream:
            encoded = stream.read(max_bytes + 1)
        if len(encoded) > max_bytes:
            raise RoutingRequestError("JSON request exceeds its size limit")
        raw = encoded.decode("utf-8")
    if len(raw.encode("utf-8")) > max_bytes:
        raise RoutingRequestError("JSON request exceeds its size limit")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RoutingRequestError("routing request is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RoutingRequestError("routing request must be a JSON object")
    return payload


def health_command(args: argparse.Namespace, *, ctx) -> int:
    action = getattr(args, "volmarr_action", None)
    if action == "cognition":
        cognition_action = getattr(args, "cognition_action", None)
        if cognition_action == "execute":
            try:
                execution_request = CognitionExecutionRequest.from_mapping(
                    _load_json_request(
                        getattr(args, "request", "-"),
                        max_bytes=256 * 1024,
                    )
                )
                result = CognitionExecutor(ctx).execute(execution_request)
            except (OSError, UnicodeError, RoutingRequestError) as exc:
                print(
                    json.dumps(
                        {"error": "invalid_execution_request", "detail": str(exc)},
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 2
            print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
            return 1 if result.status in {"blocked", "failed"} else 0
        if cognition_action == "route":
            try:
                request = CognitionRequest.from_mapping(
                    _load_json_request(
                        getattr(args, "request", "-"),
                        max_bytes=64 * 1024,
                    )
                )
                decision = CognitionRouter.from_plugin_context(ctx).decide(request)
            except (OSError, UnicodeError, RoutingRequestError) as exc:
                print(
                    json.dumps(
                        {"error": "invalid_routing_request", "detail": str(exc)},
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 2
            CognitionTelemetry().record_decision(ctx, decision)
            print(json.dumps(decision.as_dict(), sort_keys=True))
            return 0
        if cognition_action != "health":
            print("Usage: hermes volmarr cognition {health|route|execute} [options]")
            return 2
        report = probe_aesir(ctx)
        label = "A.E.S.I.R."
    elif action == "memory":
        memory_action = getattr(args, "memory_action", None)
        if memory_action == "mempalace":
            if getattr(args, "mempalace_action", None) != "health":
                print("Usage: hermes volmarr memory mempalace health [--json]")
                return 2
            report = probe_mempalace(ctx)
            label = "MemPalace"
        elif memory_action == "openviking":
            if getattr(args, "openviking_action", None) != "health":
                print("Usage: hermes volmarr memory openviking health [--json]")
                return 2
            report = probe_openviking(ctx)
            label = "OpenViking"
        elif memory_action == "sessiondb":
            if getattr(args, "sessiondb_action", None) != "health":
                print("Usage: hermes volmarr memory sessiondb health [--json]")
                return 2
            report = probe_sessiondb(ctx)
            label = "Hermes SessionDB"
        elif memory_action == "muninn":
            if getattr(args, "muninn_action", None) != "health":
                print("Usage: hermes volmarr memory muninn health [--json]")
                return 2
            report = probe_bifrost_muninn(ctx)
            label = "Bifröst Muninn"
        elif memory_action == "ravens":
            ravens_action = getattr(args, "ravens_action", None)
            if ravens_action == "health":
                report = probe_ravens(ctx)
                label = "Ravens"
            elif ravens_action in {"reinforce", "decay", "consolidate", "ingest"}:
                if ravens_action == "reinforce":
                    tokens = [
                        token.strip()
                        for token in str(getattr(args, "ids", "")).split(",")
                    ]
                    try:
                        memory_ids = [int(token) for token in tokens]
                    except ValueError:
                        memory_ids = tokens
                    result = reinforce_memories(
                        ctx, memory_ids, getattr(args, "valence", 0.0)
                    )
                elif ravens_action == "decay":
                    result = decay_memories(ctx, getattr(args, "days", 1.0))
                elif ravens_action == "consolidate":
                    result = consolidate_memories(ctx)
                else:
                    raw_tags = str(getattr(args, "tags", "") or "")
                    result = ingest_memory(
                        ctx,
                        getattr(args, "content", ""),
                        category=getattr(args, "category", "general"),
                        importance=getattr(args, "importance", 5),
                        tags=[tag.strip() for tag in raw_tags.split(",") if tag.strip()],
                        emotional_valence=getattr(args, "valence", 0.0),
                    )
                if getattr(args, "json_output", False):
                    print(json.dumps(result.as_dict(), sort_keys=True))
                else:
                    print(f"Ravens {result.operation}: {result.status}")
                return 0 if result.healthy else 1
            else:
                print(
                    "Usage: hermes volmarr memory ravens "
                    "{health|reinforce|decay|consolidate|ingest} [--json]"
                )
                return 2
        elif memory_action == "corpus":
            if getattr(args, "corpus_action", None) != "status":
                print("Usage: hermes volmarr memory corpus status [--json]")
                return 2
            from .memory_corpus import corpus_from_plugin_context
            from . import memory_digest as _md
            _corpus = corpus_from_plugin_context(ctx)
            _status = _corpus.status()
            _status["digest"] = _md.digest_status(
                _corpus, _md.load_digest(_corpus))
            if getattr(args, "json_output", False):
                print(json.dumps(_status, sort_keys=True))
            else:
                print(
                    "Memory corpus: generation "
                    f"{_status['generation']}, index "
                    f"{_status['index']['status']}, digest "
                    f"{_status['digest']['state']}")
                for _t in ("memory", "user"):
                    _row = _status["targets"][_t]
                    print(
                        f"  {_t}: full store {_row['full_store_bytes']} "
                        f"bytes; hot view {_row.get('snapshot_chars', 0)}/"
                        f"{_row['hot_cap_chars']} chars"
                        + (" (over cap -- full store only)"
                           if _row.get("snapshot_over_cap") else ""))
            return 0
        elif memory_action == "health":
            report = probe_bifrost(ctx)
            label = "Bifröst"
        else:
            print(
                "Usage: hermes volmarr memory "
                "{health|corpus status|mempalace health|openviking health|sessiondb health|"
                "muninn health|ravens health} [--json]"
            )
            return 2
    elif action == "health":
        report = probe_verdandi(ctx)
        label = "Verðandi"
    elif action == "world":
        if getattr(args, "world_action", None) != "health":
            print("Usage: hermes volmarr world health [--json]")
            return 2
        report = probe_wyrd(ctx)
        label = "WYRD"
    elif action == "identity":
        if getattr(args, "identity_action", None) != "health":
            print("Usage: hermes volmarr identity health [--json]")
            return 2
        report = probe_identity(ctx)
        label = "Entity identity"
    elif action == "heartbeat":
        heartbeat_action = getattr(args, "heartbeat_action", None)
        if heartbeat_action == "status":
            report = probe_heartbeat(ctx)
        elif heartbeat_action == "pulse":
            try:
                report = HeartbeatService(ctx).pulse(getattr(args, "source", "manual"))
            except (IdentityError, HeartbeatError, OSError) as exc:
                print(
                    json.dumps(
                        {"error": "heartbeat_failed", "detail": str(exc)},
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 1
        else:
            print("Usage: hermes volmarr heartbeat {status|pulse} [options]")
            return 2
        label = "Entity heartbeat"
    elif action == "routines":
        routines_action = getattr(args, "routines_action", None)
        try:
            if routines_action == "status":
                report = RoutineManager(ctx).status()
                exit_code = 0 if report.status.startswith("installed_") else 1
            elif routines_action == "install":
                report = RoutineManager(ctx).install(
                    activate=bool(getattr(args, "activate", False))
                )
                exit_code = 0
            elif routines_action == "run":
                report = RoutineService(ctx).run_frequent()
                exit_code = 0
            else:
                print("Usage: hermes volmarr routines {status|install|run} [options]")
                return 2
        except (IdentityError, HeartbeatError, RoutineError, OSError) as exc:
            print(
                json.dumps(
                    {"error": "routine_failed", "detail": str(exc)},
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 1
        if getattr(args, "json_output", False):
            print(json.dumps(report.as_dict(), sort_keys=True))
        else:
            print(f"Entity routines: {getattr(report, 'status', 'completed')}")
        return exit_code
    elif action in {"self", "awareness", "reflection", "motivation",
                    "curiosity", "autonomy"}:
        verbs = {
            "self": ("health", "show"),
            "awareness": ("health", "show"),
            "reflection": ("health", "recent"),
            "motivation": ("show",),
            "curiosity": ("show",),
            "autonomy": ("show",),
        }[action]
        verb = getattr(args, f"{action}_action", None)
        if verb not in verbs:
            print(
                f"Usage: hermes volmarr {action} "
                f"{{{'|'.join(verbs)}}} [--json]"
            )
            return 2
        payload = SurfaceInspectionService(ctx).inspect(action)
        payload = {"command": verb, **payload}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, sort_keys=True, default=str))
        else:
            print(f"{action.capitalize()} surface: {payload['status']}")
            for key, value in payload["detail"].items():
                print(f"{key}: {value}")
        if verb == "health":
            return 0 if payload["status"] == "ok" else 1
        return 1 if payload["status"] == "unreadable" else 0
    elif action == "agency":
        agency_action = getattr(args, "agency_action", None)
        try:
            if agency_action == "status":
                report = AgencyRoutineManager(ctx).status()
                exit_code = 0 if report.status.startswith("installed_") else 1
                payload = report.as_dict()
            elif agency_action == "install":
                report = AgencyRoutineManager(ctx).install(
                    activate=bool(getattr(args, "activate", False))
                )
                exit_code = 0
                payload = report.as_dict()
            elif agency_action == "run":
                report = AgencyRoutineService(ctx).run_once(trigger="manual")
                exit_code = 0
                payload = report.as_dict()
            elif agency_action == "evaluation":
                payload = AgencyRoutineService(ctx).evaluation()
                exit_code = 0
            else:
                print("Usage: hermes volmarr agency {status|install|run|evaluation} [options]")
                return 2
        except (IdentityError, AgencyRoutineError, RoutineError, OSError) as exc:
            print(
                json.dumps(
                    {"error": "agency_routine_failed", "detail": str(exc)},
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 1
        if getattr(args, "json_output", False):
            print(json.dumps(payload, sort_keys=True, default=str))
        else:
            print(f"Agency routine: {payload.get('status', 'completed')}")
        return exit_code
    elif action == "sleep":
        sleep_action = getattr(args, "sleep_action", None)
        try:
            if sleep_action == "status":
                report = probe_consolidation(ctx)
                exit_code = 0 if report.healthy else 1
            elif sleep_action == "install":
                report = sleep_routine_manager(ctx).install(
                    activate=bool(getattr(args, "activate", False))
                )
                exit_code = 0
            elif sleep_action == "run":
                report = ConsolidationService(ctx).run(
                    getattr(args, "source", "manual")
                )
                exit_code = 0
            else:
                print("Usage: hermes volmarr sleep {status|install|run} [options]")
                return 2
        except (RuntimeError, OSError) as exc:
            print(
                json.dumps(
                    {"error": "consolidation_failed", "detail": str(exc)},
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 1
        if getattr(args, "json_output", False):
            print(json.dumps(report.as_dict(), sort_keys=True))
        else:
            print(f"Entity consolidation: {getattr(report, 'status', 'completed')}")
        return exit_code
    elif action == "engines":
        from .integration_ledger import (
            IntegrationLedgerError,
            find_engine,
            integration_status,
            load_lock,
        )
        _eaction = getattr(args, "engines_action", None)
        try:
            if _eaction == "status":
                _record = integration_status()
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(
                        f"Engines: {_record['engine_count']} rows, "
                        f"lock {_record['status']}"
                    )
                    for _row in _record["engines"]:
                        print(
                            f"{_row['name']}: {_row['verification']} / "
                            f"{_row['evidence_stage']} / "
                            f"adapter {_row['adapter_mode']}"
                        )
                return 0 if _record["status"] == "ok" else 1
            elif _eaction == "show":
                _row = find_engine(load_lock(), getattr(args, "name", ""))
                if _row is None:
                    print(
                        json.dumps(
                            {
                                "error": "engine_not_found",
                                "detail": getattr(args, "name", ""),
                            },
                            sort_keys=True,
                        ),
                        file=sys.stderr,
                    )
                    return 1
                print(json.dumps(_row, sort_keys=True, default=str))
                return 0
            elif _eaction == "validate":
                _record = integration_status()
                if getattr(args, "json_output", False):
                    print(
                        json.dumps(
                            {
                                "status": _record["status"],
                                "problems": _record["problems"],
                            },
                            sort_keys=True,
                        )
                    )
                elif _record["problems"]:
                    for _problem in _record["problems"]:
                        print(_problem)
                else:
                    print(
                        "Integration lock: valid, all rows verified "
                        "against this tree"
                    )
                return 0 if _record["status"] == "ok" else 1
            else:
                print("Usage: hermes volmarr engines {status|show|validate} [--json]")
                return 2
        except IntegrationLedgerError as exc:
            print(
                json.dumps(
                    {"error": exc.name, "detail": exc.detail}, sort_keys=True
                ),
                file=sys.stderr,
            )
            return 1
    elif action == "capabilities":
        from .capability_bus import BUILTIN_DESCRIPTORS, authorize as _cb_authorize, builtin_status as _cb_status
        _caction = getattr(args, "capabilities_action", None)
        if _caction == "list":
            _record = _cb_status()
            if getattr(args, "json_output", False):
                print(json.dumps(_record, sort_keys=True, default=str))
            else:
                print(f"Capabilities: {_record['service_count']} built-in services, bus {_record['status']}")
                for _row in _record["services"]:
                    print(f"{_row['service']} {_row['version']}: {', '.join(_row['actions'])} / {_row['availability']}")
            return 0 if _record["status"] == "ok" else 1
        elif _caction == "show":
            _found = next((d for d in BUILTIN_DESCRIPTORS if d["service"] == getattr(args, "name", "")), None)
            if _found is None:
                print(json.dumps({"error": "service_not_found", "detail": getattr(args, "name", "")}, sort_keys=True), file=sys.stderr)
                return 1
            print(json.dumps(_found, sort_keys=True, default=str))
            return 0
        elif _caction == "validate":
            _record = _cb_status()
            if getattr(args, "json_output", False):
                print(json.dumps({"status": _record["status"], "problems": _record["problems"]}, sort_keys=True))
            elif _record["problems"]:
                for _problem in _record["problems"]:
                    print(_problem)
            else:
                print("Capability bus: valid, all built-in descriptors verified against this tree")
            return 0 if _record["status"] == "ok" else 1
        elif _caction == "authorize":
            _found = next((d for d in BUILTIN_DESCRIPTORS if d["service"] == getattr(args, "service", "")), None)
            _decision = _cb_authorize(_found, caller=getattr(args, "caller", ""), action=getattr(args, "action", ""), data_owner=getattr(args, "data_owner", ""), data_class=getattr(args, "data_class", ""), destination=getattr(args, "destination", ""), device=getattr(args, "device", None), approved=bool(getattr(args, "approved", False)))
            print(json.dumps(_decision, sort_keys=True))
            return 0 if _decision["allowed"] else 1
        else:
            print("Usage: hermes volmarr capabilities {list|show|validate|authorize} [--json]")
            return 2
    elif action == "productivity":
        from datetime import datetime as _dt, timezone as _tz
        from .project_context import ProjectContextError, build_project_packet
        from .samtal_bridge import SAMKOMA_DESCRIPTOR, SAMTAL_DESCRIPTOR
        from .task_handoff import guard_publish
        _paction = getattr(args, "productivity_action", None)
        _now = _dt.now(_tz.utc).isoformat()
        try:
            if _paction == "packet":
                _record = build_project_packet(getattr(args, "repo", ""), recorded_at=_now)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Project packet: {_record['repo_path']} head {_record['head']}")
                    for _row in _record["sources"]:
                        print(f"{_row['kind']}: {_row['path']} {_row['size_bytes']}B sha256 {_row['sha256'][:12]}")
                    if _record["missing"]:
                        print(f"Missing: {', '.join(_record['missing'])}")
                return 0
            elif _paction == "publish-check":
                _decision = guard_publish(caller=getattr(args, "caller", ""), data_owner=getattr(args, "data_owner", ""), data_class=getattr(args, "data_class", "local-private"), destination=getattr(args, "destination", "local"), approved=bool(getattr(args, "approved", False)))
                print(json.dumps(_decision, sort_keys=True))
                return 0 if _decision["allowed"] else 1
            elif _paction == "bridge-status":
                _record = {"samtal": {"service": SAMTAL_DESCRIPTOR["service"], "availability": SAMTAL_DESCRIPTOR["availability"], "actions": SAMTAL_DESCRIPTOR["actions"]}, "samkoma": {"service": SAMKOMA_DESCRIPTOR["service"], "availability": SAMKOMA_DESCRIPTOR["availability"], "actions": SAMKOMA_DESCRIPTOR["actions"]}, "live_connection": "not-claimed"}
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Samtal bridge: {SAMTAL_DESCRIPTOR['service']} / {SAMTAL_DESCRIPTOR['availability']} / live connection not-claimed")
                    print(f"Samkoma: {SAMKOMA_DESCRIPTOR['service']} / {SAMKOMA_DESCRIPTOR['availability']}")
                return 0
            else:
                print("Usage: hermes volmarr productivity {packet|publish-check|bridge-status} [--json]")
                return 2
        except ProjectContextError as exc:
            print(json.dumps({"error": exc.name, "detail": exc.detail}, sort_keys=True), file=sys.stderr)
            return 1
    elif action == "world-bridge":
        from .world_bridge import HEIMDALL_DESCRIPTOR, RUNMAL_DESCRIPTOR, authorize_presence, availability as _wb_availability
        _waction = getattr(args, "world_bridge_action", None)
        if _waction == "status":
            _record = {"runmal": {"service": RUNMAL_DESCRIPTOR["service"], "availability": RUNMAL_DESCRIPTOR["availability"]}, "heimdall": {"service": HEIMDALL_DESCRIPTOR["service"], "availability": HEIMDALL_DESCRIPTOR["availability"]}, "availability": _wb_availability(None), "live_connection": "not-claimed"}
            if getattr(args, "json_output", False):
                print(json.dumps(_record, sort_keys=True, default=str))
            else:
                print(f"Runmal interchange: {RUNMAL_DESCRIPTOR['service']} / {RUNMAL_DESCRIPTOR['availability']}")
                print(f"Heimdall presence: {HEIMDALL_DESCRIPTOR['service']} / {HEIMDALL_DESCRIPTOR['availability']} / live connection not-claimed")
            return 0
        elif _waction == "presence-check":
            _decision = authorize_presence(caller=getattr(args, "caller", ""), action="read", data_owner=getattr(args, "data_owner", ""), data_class=getattr(args, "data_class", "local-private"), approved=bool(getattr(args, "approved", False)))
            print(json.dumps(_decision, sort_keys=True))
            return 0 if _decision["allowed"] else 1
        else:
            print("Usage: hermes volmarr world-bridge {status|presence-check} [--json]")
            return 2
    elif action == "edge-research":
        from datetime import datetime as _dt2, timezone as _tz2
        from .edge_research import EdgeError, ProposalBook, edge_status, read_resource_meter
        _eaction = getattr(args, "edge_research_action", None)
        _now2 = _dt2.now(_tz2.utc).isoformat()
        try:
            if _eaction == "status":
                _record = edge_status(recorded_at=_now2)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Edge research: {_record['edge_research']['service']} / {_record['edge_research']['availability']} / live connection not-claimed")
                    print(f"Lifthrasir: {_record['lifthrasir']['mode']} / auto-apply off")
                return 0
            elif _eaction == "meter":
                _record = read_resource_meter(recorded_at=_now2)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    _mem = _record["outputs"]["memory"]
                    print(f"Resource meter: memory {_mem.get('status')} / telemetry local-private, transmission none")
                return 0
            elif _eaction == "propose":
                _book = ProposalBook()
                _record = _book.propose(getattr(args, "title", ""), getattr(args, "detail", ""), recorded_at=_now2)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Proposal recorded: {_record['proposal_id']} / {_record['status']} / never applied automatically")
                return 0
            else:
                print("Usage: hermes volmarr edge-research {status|meter|propose} [--json]")
                return 2
        except EdgeError as exc:
            print(json.dumps({"error": exc.name, "detail": exc.detail}, sort_keys=True), file=sys.stderr)
            return 1
    elif action == "yggdrasil":
        from datetime import datetime as _dt_y, timezone as _tz_y
        from .yggdrasil_local import (
            YggdrasilLocalError, build_task_request, discover_local_node,
            place_task, yggdrasil_status)
        _yaction = getattr(args, "yggdrasil_action", None)
        _now_y = _dt_y.now(_tz_y.utc).isoformat()
        try:
            if _yaction == "status":
                _record = yggdrasil_status(recorded_at=_now_y)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Yggdrasil local: {_record['service']} / {_record['availability']} / mesh not claimed, live peers 0")
                return 0
            elif _yaction == "discover":
                _record = discover_local_node(recorded_at=_now_y)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Node {_record['node_id']}: {_record['architecture']} / accelerator {_record['accelerator']} / models {_record['models']}")
                return 0
            elif _yaction == "place":
                _payload = _load_json_request(getattr(args, "request"), max_bytes=64 * 1024)
                _req = build_task_request(recorded_at=_now_y, **_payload)
                _cap = discover_local_node(recorded_at=_now_y)
                _record = place_task(_cap, _req, caller=getattr(args, "caller"), recorded_at=_now_y)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Placement {_record['request_id']}: {_record['decision']} on {_record['node_id']}")
                return 0
            else:
                print("Usage: hermes volmarr yggdrasil {status|discover|place} [--json]")
                return 2
        except (YggdrasilLocalError, RoutingRequestError) as exc:
            _name = getattr(exc, "name", "request_invalid")
            _detail = getattr(exc, "detail", str(exc))
            print(json.dumps({"error": _name, "detail": _detail}, sort_keys=True), file=sys.stderr)
            return 1
    elif action == "production":
        from datetime import datetime as _dt3, timezone as _tz3
        from .production import KNOWN_DEFERRED, ProductionError, evaluate_scorecard, production_audit, production_status
        _paction = getattr(args, "production_action", None)
        _now3 = _dt3.now(_tz3.utc).isoformat()
        try:
            if _paction == "status":
                _record = production_status(recorded_at=_now3)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Production: {_record['service']} {_record['version']} / {_record['availability']} / live connection not-claimed")
                    print(f"Engines: {_record['engines']['engine_count']} rows, {_record['engines']['working_count']} end-to-end working")
                    print(f"Docs: {_record['docs_present']}/{len(_record['docs'])} present; next: {_record['next_required_action']}")
                return 0
            elif _paction == "scorecard":
                _record = evaluate_scorecard({}, deferred=dict(KNOWN_DEFERRED))
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    print(f"Release scorecard: {_record['met_count']}/15 met; releasable: {_record['releasable']}")
                    for _item in _record["items"]:
                        if _item["status"] != "met":
                            print(_item["verdict"])
                return 0 if _record["releasable"] else 1
            elif _paction == "audit":
                _record = production_audit(recorded_at=_now3)
                if getattr(args, "json_output", False):
                    print(json.dumps(_record, sort_keys=True, default=str))
                else:
                    _threat = _record["outputs"]["threat"]
                    print(f"Threat checklist: {_threat['present_count']}/12 with evidence; gaps: {', '.join(_threat['gaps'])}")
                    print("Performance: structure only, all fields unmeasured (no benchmark run)")
                return 0
            else:
                print("Usage: hermes volmarr production {status|scorecard|audit} [--json]")
                return 2
        except ProductionError as exc:
            print(json.dumps({"error": exc.name, "detail": exc.detail}, sort_keys=True), file=sys.stderr)
            return 1
    elif action == "persona":
        from pathlib import Path as _Path
        from .persona_ops import PersonaOps, PersonaOpsError
        _paction = getattr(args, "persona_action", None)
        _ops = PersonaOps(ctx)
        try:
            if _paction == "status":
                _record = _ops.status()
            elif _paction == "files":
                _record = _ops.files()
            elif _paction == "search":
                _record = _ops.search(getattr(args, "query", ""), limit=int(getattr(args, "limit", 5)))
            elif _paction == "inspect":
                _record = _ops.inspect(getattr(args, "section", None))
            elif _paction == "explain":
                _record = _ops.explain(getattr(args, "turn_id", ""))
            elif _paction == "validate":
                _record = _ops.validate()
            elif _paction == "diff":
                _record = _ops.diff()
            elif _paction == "reload":
                _record = _ops.reload_activate() if getattr(args, "activate", False) else _ops.reload_dry_run()
            elif _paction == "export":
                _dest = getattr(args, "dest", None)
                _record = _ops.export_bundle(_Path(_dest) if _dest else None)
            elif _paction == "import":
                _record = _ops.import_dry_run(_Path(getattr(args, "bundle", "")))
            elif _paction == "backup":
                _record = _ops.backup(_Path(getattr(args, "dest", "")))
            elif _paction == "restore":
                _record = _ops.restore(_Path(getattr(args, "backup_dir", "")), _Path(getattr(args, "target", "")))
            elif _paction == "read":
                _record = _ops.read_page(getattr(args, "document_id", ""), int(getattr(args, "cursor", 0)), getattr(args, "max_bytes", None))
            elif _paction == "page":
                _record = _ops.continue_read(getattr(args, "handle", ""), getattr(args, "max_bytes", None))
            elif _paction == "edit":
                _record = _ops.edit_section(getattr(args, "stable_id", ""), getattr(args, "text", ""), confirm=bool(getattr(args, "confirm", False)), approved=bool(getattr(args, "approved", False)))
            elif _paction == "watchdog":
                _record = _ops.watchdog()
            elif _paction == "test":
                _record = _ops.test_battery()
            elif _paction == "diagnostics":
                _record = _ops.diagnostics()
            else:
                print("Usage: hermes volmarr persona {status|files|search|inspect|explain|validate|diff|reload|export|import|backup|restore|read|page|edit|watchdog|test|diagnostics} [--json]")
                return 2
        except PersonaOpsError as exc:
            print(json.dumps({"error": exc.name, "detail": exc.detail}, sort_keys=True), file=sys.stderr)
            return 1
        if getattr(args, "json_output", False):
            print(json.dumps(_record, sort_keys=True, default=str))
        else:
            print(f"Persona {_paction}: {_record.get('status', 'ok')}")
            for _key in ("persona_id", "active_generation", "activation_scope", "document_count", "path", "generation"):
                if _record.get(_key) is not None:
                    print(f"{_key}: {_record[_key]}")
        return 0 if _record.get("status") in {"ok", "dry_run"} else 1
    else:
        print("Usage: hermes volmarr {health|cognition|memory|world|identity|self|awareness|reflection|motivation|curiosity|autonomy|agency|persona|engines|capabilities|productivity|world-bridge|edge-research|production|yggdrasil} ...")
        return 2

    if getattr(args, "json_output", False):
        print(json.dumps(report.as_dict(), sort_keys=True))
    else:
        mark = "healthy" if report.healthy else report.status.replace("_", " ")
        print(f"{label}: {mark}")
        location = (
            getattr(report, "socket_path", None)
            or getattr(report, "base_url", None)
            or getattr(report, "mimir_db_path", "")
            or getattr(report, "muninn_db_path", "")
            or getattr(report, "palace_path", "")
            or getattr(report, "state_db_path", "")
            or getattr(report, "identity_path", "")
            or getattr(report, "continuity_path", "")
        )
        print(f"Endpoint: {location}")
        if getattr(report, "latency_ms", None) is not None:
            print(f"Latency: {report.latency_ms} ms")
        if getattr(report, "sequence", None) is not None:
            print(f"Sequence: {report.sequence}")
        if getattr(report, "uptime_seconds", None) is not None:
            print(f"Uptime: {report.uptime_seconds} s")
        if getattr(report, "models", ()):
            print(f"Models: {', '.join(report.models)}")
        if getattr(report, "memory_count", None) is not None:
            print(f"Memories: {report.memory_count}")
        if getattr(report, "connection_count", None) is not None:
            print(f"Connections: {report.connection_count}")
        if getattr(report, "activation_count", None) is not None:
            print(f"Activations: {report.activation_count}")
        if getattr(report, "package_version", None):
            print(f"Package version: {report.package_version}")
        if getattr(report, "server_version", None):
            print(f"Server version: {report.server_version}")
        if getattr(report, "schema_version", None) is not None:
            print(f"Schema version: {report.schema_version}")
        if getattr(report, "session_count", None) is not None:
            print(f"Sessions: {report.session_count}")
        if getattr(report, "message_count", None) is not None:
            print(f"Messages: {report.message_count}")
        if report.error_type:
            print(f"Error type: {report.error_type}")
    return 0 if report.healthy else 1
