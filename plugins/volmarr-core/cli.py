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
        elif memory_action == "health":
            report = probe_bifrost(ctx)
            label = "Bifröst"
        else:
            print(
                "Usage: hermes volmarr memory "
                "{health|mempalace health|openviking health|sessiondb health|"
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
    else:
        print("Usage: hermes volmarr {health|cognition|memory|world|identity} ...")
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
