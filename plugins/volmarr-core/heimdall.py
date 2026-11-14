"""X.03 Heimdall read-only presence bridge (roadmap section 38).

Roadmap section 38 (Part VII workstream 3 of 15) names the
Heimdall Second Life Hermes Agent: a separate native bridge
process (a C# Heimdall.Core LibreMetaverse client plus a
Python Bifrost seam) that gives Hermes an optional digital
body in Second Life. The X.03 audit (docs/modernization/
X03_HEIMDALL_WORKSTREAM.md, 2026-11-14) re-measured the repo's
development branch at cee7ce679b20: real code on both sides of
the seam (Core commands login/logout/say/chat/im/group_im/
teleport/sit/stand/status/rlv_status over NDJSON Unix-socket
IPC; a Python safety governor with a 5,000-message daily cap,
kill switch, reflex-tier speech ban and payment default-deny;
two-tier presence tracking; addressed-to chat classification),
but NO LICENSE file at the audited HEAD -- the README states
the open-source license is "yet to be determined" -- so no
Heimdall source is incorporated into this fork and no pin is
taken. This module is original volmarr-core code written
against the section 38 contract, plugin-side only.

What this slice builds, honestly scoped to section 38 items
3-5, 9 and 10 (initial stage):

- a READ-ONLY presence adapter over the bridge's verified
  interface: the Core IPC command socket (/tmp/heimdall.sock)
  is queried with the single read-only "status" command, and
  the Bifrost WebSocket API listener (127.0.0.1:8765) is probed
  at TCP level only (reaching its HMAC-authenticated command
  channel is a later, separately permitted stage). When no
  bridge runs on this host the adapter reports absent /
  unconfigured truthfully -- presence is never fabricated;
- a versioned presence/context contract
  (runeforge.heimdall.presence-context.v1): every record is a
  QUALIFIED observation carrying provenance (source, location,
  time) and explicitly NOT accepted world truth (section 38
  item 5: observations feed WYRD as qualified observations);
- an action-permission gate (item 4): read actions are
  allowed; EVERY write capability -- say/chat, IM, group IM,
  movement, teleport, object interaction, spending, login,
  logout, mode changes -- is refused BY NAME in this stage.
  Write stages need distinct permissions that this slice does
  not grant;
- privacy by construction (item 9): private IM / relationship
  content can never become an observation here -- the IM kind
  is refused by name, and every recorded text passes the
  redaction rules before it is stored;
- complete disablement (item 10): HEIMDALL_BRIDGE_DISABLED=1
  makes every surface report "disabled" and nothing else in
  the fork changes.

No login is attempted, no grid session is claimed, and no
message can be sent through this module: it holds no code path
that transmits anything except the read-only status query on
an already-running local bridge.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from typing import Any, Callable

SCHEMA_PREFIX = "runeforge.heimdall"
PRESENCE_SCHEMA = f"{SCHEMA_PREFIX}.presence-context.v1"
OBSERVATION_SCHEMA = f"{SCHEMA_PREFIX}.observation.v1"
SOURCE_PROJECT = "Heimdall-SL-Hermes-Agent"
SOURCE_REPO = "hrabanazviking/Heimdall-SL-Hermes-Agent"
SOURCE_BRANCH = "development"
SOURCE_HEAD_AUDITED = "cee7ce679b2070708cee59d476bdd9397dbd9f86"
SOURCE_LICENSE = ("none - no LICENSE file at the audited "
                  "development HEAD; README states the license "
                  "is yet to be determined (X.03, 2026-11-14); "
                  "no source incorporated, no pin taken")
DEFAULT_COMMAND_SOCKET = "/tmp/heimdall.sock"
DEFAULT_EVENT_SOCKET = "/tmp/heimdall.sock.events"
DEFAULT_WS_HOST = "127.0.0.1"
DEFAULT_WS_PORT = 8765
READ_COMMANDS = ("status", "get_status", "ping", "rlv_status")
SESSION_STATES = ("logged_in", "not_logged_in", "unknown",
                  "error")
BRIDGE_STATES = ("present", "present-api-only", "absent",
                 "disabled")
OBSERVATION_KINDS = frozenset(
    {"chat", "group_chat", "region", "avatar", "object",
     "system", "presence"})
PRIVATE_KINDS = frozenset({"im", "private_im", "relationship"})

DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-heimdall",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "observe"],
    "transport": "unix-socket-ipc",
    "auth": "scoped",
    "side_effects": False,
    "privacy_classes": ["local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 5000,
}


class HeimdallError(Exception):
    """Named refusal: malformed record or policy denial."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


# ------------------------------------------------------------ redaction

_REDACTION_RULES = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?"
                r"-----END [A-Z0-9 ]*PRIVATE KEY-----", re.S),
     "<redacted:private-key>"),
    (re.compile(r"(?i)\b(password|passwd|pwd|token|secret|"
                r"api[_-]?key|access[_-]?key|authorization)\b"
                r"(\s*[:=]\s*)\S+"),
     r"\1\2<redacted>"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-+/=]+"),
     "Bearer <redacted>"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "<redacted>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted>"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "<redacted>"),
    (re.compile(r"/home/[^/\s:'\"]+"), "/home/<user>"),
)


def redact_text(text: str) -> tuple:
    """Apply every redaction rule; return (clean_text, count)."""
    count = 0
    out = text
    for pattern, replacement in _REDACTION_RULES:
        out, n = pattern.subn(replacement, out)
        count += n
    return out, count


# ------------------------------------------------------------ permissions

READ_ACTIONS = {
    "status": "status",
    "presence": "status",
    "observe": "event stream (read-only)",
    "login_status": "status",
}

WRITE_ACTIONS = {
    "say": "say",
    "chat": "chat",
    "im": "im",
    "group_im": "group_im",
    "move": "move_to",
    "teleport": "teleport",
    "interact": "sit/stand/object touch",
    "spend": "pay/give_money/give_linden",
    "login": "login",
    "logout": "logout",
    "set_mode": "set_mode",
}


def permission_matrix() -> list:
    """Every action this bridge could ever be asked for, with
    its stage decision. Reads are allowed in this stage; every
    write is refused (section 38 item 4: distinct permissions
    for writes, none granted here)."""
    rows = []
    for action, cmd in sorted(READ_ACTIONS.items()):
        rows.append({"action": action, "bridge_command": cmd,
                     "class": "read", "allowed": True,
                     "reason": "read-only presence/context is "
                               "the initial stage (section 38)"})
    for action, cmd in sorted(WRITE_ACTIONS.items()):
        rows.append({"action": action, "bridge_command": cmd,
                     "class": "write", "allowed": False,
                     "reason": "write capabilities need distinct "
                               "permissions (section 38 item 4); "
                               "none are granted in this stage"})
    return rows


def check_action(action: Any) -> dict:
    """Gate one action by name. Read actions return an allowed
    record; write actions and unknown actions are refused by
    name -- there is no silent default in either direction."""
    if action in READ_ACTIONS:
        return {"action": action, "allowed": True,
                "class": "read", "stage": "read-only-presence",
                "bridge_command": READ_ACTIONS[action]}
    if action in WRITE_ACTIONS:
        raise HeimdallError(
            "write_action_refused",
            f"action {action!r} maps to bridge command "
            f"{WRITE_ACTIONS[action]!r}, a write capability; "
            "the X.03 stage is read-only presence/context only "
            "(section 38 item 4) and grants no write permission")
    raise HeimdallError(
        "unknown_action_refused",
        f"action {action!r} is not a known Heimdall action; "
        "unknown actions are refused, never guessed")


# ------------------------------------------------------------ bridge probe

def _env(env: Any) -> Any:
    return os.environ if env is None else env


def _tcp_connectable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def probe_bridge(*, env: Any = None, exists: Callable = None,
                 tcp_connectable: Callable = None) -> dict:
    """Detect the bridge's real state on THIS host without
    sending it anything: operator disablement flag, Core IPC
    socket presence on disk, Bifrost API listener reachability.
    Absence is a first-class, truthful result."""
    env = _env(env)
    exists = exists or os.path.exists
    tcp_connectable = tcp_connectable or _tcp_connectable
    command_socket = env.get("HEIMDALL_CORE_COMMAND_SOCKET",
                             DEFAULT_COMMAND_SOCKET)
    event_socket = env.get("HEIMDALL_CORE_EVENT_SOCKET",
                           DEFAULT_EVENT_SOCKET)
    ws_host = env.get("HEIMDALL_WS_HOST", DEFAULT_WS_HOST)
    try:
        ws_port = int(env.get("HEIMDALL_WS_PORT", DEFAULT_WS_PORT))
    except (TypeError, ValueError):
        ws_port = DEFAULT_WS_PORT
    disabled = str(env.get("HEIMDALL_BRIDGE_DISABLED", "")).lower() \
        in ("1", "true", "yes", "on")
    core = bool(exists(command_socket))
    events = bool(exists(event_socket))
    api = bool(tcp_connectable(ws_host, ws_port)) \
        if not disabled else False
    if disabled:
        state = "disabled"
    elif core:
        state = "present"
    elif api:
        state = "present-api-only"
    else:
        state = "absent"
    return {
        "state": state,
        "disabled_by_operator": disabled,
        "command_socket": command_socket,
        "command_socket_present": core,
        "event_socket": event_socket,
        "event_socket_present": events,
        "api_host": ws_host,
        "api_port": ws_port,
        "api_listening": api,
        "core_reachable": core and not disabled,
    }


# ------------------------------------------------------------ transport

Transport = Callable[[str, dict], dict]


def _default_transport(command_socket: str,
                       timeout_s: float) -> Transport:
    """NDJSON request/response over the Core command socket
    (the bridge's verified section 7.2 IPC). Only ever called
    with the read-only status command by this module."""

    def _send(cmd: str, params: dict) -> dict:
        if cmd not in READ_COMMANDS:
            raise HeimdallError(
                "write_action_refused",
                f"bridge command {cmd!r} is not a read-only "
                "command; this adapter transmits status queries "
                "only (section 38 item 4)")
        wire = {"id": "hermes-heimdall-status", "cmd": cmd}
        wire.update(params)
        line = (json.dumps(wire) + "\n").encode("utf-8")
        try:
            with socket.socket(socket.AF_UNIX,
                               socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout_s)
                sock.connect(command_socket)
                sock.sendall(line)
                data = b""
                while b"\n" not in data:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    data += chunk
        except OSError as exc:
            raise HeimdallError(
                "bridge_unreachable",
                f"Core IPC socket {command_socket} failed: "
                f"{exc.__class__.__name__}")
        text = data.split(b"\n", 1)[0].strip()
        try:
            reply = json.loads(text.decode("utf-8")) \
                if text else None
        except (ValueError, UnicodeDecodeError):
            reply = None
        if not isinstance(reply, dict):
            raise HeimdallError(
                "bridge_malformed_reply",
                "Core IPC returned no parseable NDJSON reply")
        return reply

    return _send


# ------------------------------------------------------------ presence

def _position(value: Any):
    if isinstance(value, (list, tuple)) and len(value) == 3 and \
            all(isinstance(v, (int, float)) for v in value):
        return [float(v) for v in value]
    return None


def _base_presence(*, recorded_at: str, probe: dict) -> dict:
    return {
        "schema": PRESENCE_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": "local-private",
        "bridge": {"state": probe["state"],
                   "transport": "core-ipc",
                   "command_socket_present":
                       probe["command_socket_present"],
                   "api_listening": probe["api_listening"]},
        "session": {"state": "unknown", "logged_in": None,
                    "simulated": None},
        "agent": {"name": None, "uuid": None},
        "location": {"region": None, "position": None},
        "mode": None,
        "core": {"version": None, "dotnet_runtime": None,
                 "libremetaverse_version": None},
        "qualified": True,
        "accepted_as_world_truth": False,
        "writes_performed": False,
        "provenance": {"source": "heimdall-bridge-probe",
                       "location": None,
                       "observed_at": recorded_at},
        "recorded_at": recorded_at,
    }


def presence(*, recorded_at: str = "", transport: Transport = None,
             env: Any = None, probe: dict = None,
             timeout_s: float = 5.0) -> dict:
    """One qualified presence/context observation.

    Absent or disabled bridges produce a truthful record saying
    exactly that -- never an invented session. A present Core is
    asked only the read-only status command; its reply is
    recorded as a qualified observation, not world truth."""
    probe = probe if probe is not None else probe_bridge(env=env)
    record = _base_presence(recorded_at=recorded_at, probe=probe)
    if probe["state"] == "disabled":
        record["detail"] = (
            "bridge disabled by operator configuration "
            "(HEIMDALL_BRIDGE_DISABLED); disablement has no "
            "effect on the rest of the fork (section 38 item 10)")
        return record
    if probe["state"] == "absent":
        record["detail"] = (
            "no Heimdall bridge detected on this host: the Core "
            "IPC socket is absent and the Bifrost API is not "
            "listening; presence is not fabricated")
        return record
    if probe["state"] == "present-api-only":
        record["detail"] = (
            "Bifrost API is listening but the Core IPC socket "
            "is absent; session state is unverified and no "
            "presence is claimed")
        return record
    transport = transport or _default_transport(
        probe["command_socket"], timeout_s)
    try:
        reply = transport("status", {})
    except HeimdallError as exc:
        record["session"] = {"state": "error",
                             "logged_in": None, "simulated": None}
        record["detail"] = (
            f"bridge present but the status query failed: "
            f"{exc.name}: {exc.detail}")
        return record
    if reply.get("status") != "ok":
        record["session"] = {"state": "error",
                             "logged_in": None, "simulated": None}
        record["detail"] = (
            "Core refused the read-only status query: "
            f"{reply.get('error', 'unknown_error')}")
        return record
    result = reply.get("result") or {}
    logged_in = result.get("logged_in")
    if not isinstance(logged_in, bool):
        logged_in = result.get("state") == "logged_in"
    state = result.get("state")
    if state not in SESSION_STATES:
        state = "logged_in" if logged_in else "not_logged_in"
    region = result.get("region")
    record["provenance"] = {
        "source": "heimdall-core-ipc",
        "location": region if isinstance(region, str) else None,
        "observed_at": recorded_at}
    record["session"] = {
        "state": state, "logged_in": logged_in,
        "simulated": result.get("simulated")
        if isinstance(result.get("simulated"), bool) else None}
    record["agent"] = {
        "name": result.get("agent_name"),
        "uuid": result.get("agent_uuid")}
    record["location"] = {
        "region": region if isinstance(region, str) else None,
        "position": _position(result.get("position"))}
    record["mode"] = result.get("mode")
    record["core"] = {
        "version": result.get("core_version"),
        "dotnet_runtime": result.get("dotnet_runtime"),
        "libremetaverse_version":
            result.get("libremetaverse_version")}
    digest_src = "|".join([
        recorded_at, str(record["agent"]["uuid"]),
        str(record["location"]["region"]), state])
    record["observation_id"] = "obs-" + hashlib.sha256(
        digest_src.encode("utf-8")).hexdigest()[:16]
    record["detail"] = (
        "qualified observation from the bridge's read-only "
        "status command; not accepted world truth "
        "(section 38 item 5)")
    return record


def validate_presence(record: Any) -> dict:
    """Strict contract check. A presence record is a qualified
    observation: any claim of accepted world truth, any write
    performed, or any presence asserted for an absent/disabled
    bridge is malformed by definition."""
    if not isinstance(record, dict):
        raise HeimdallError("presence_malformed",
                            "presence record not a dict")
    if record.get("schema") != PRESENCE_SCHEMA:
        raise HeimdallError("presence_malformed", "wrong schema")
    if record.get("qualified") is not True:
        raise HeimdallError(
            "presence_malformed",
            "presence must be marked qualified (section 38.5)")
    if record.get("accepted_as_world_truth") is not False:
        raise HeimdallError(
            "presence_malformed",
            "a presence observation is never accepted world "
            "truth (section 38 item 5)")
    if record.get("writes_performed"):
        raise HeimdallError(
            "presence_malformed",
            "record claims a write was performed in a "
            "read-only stage")
    for key in ("im_text", "private_im", "im_content"):
        if key in record:
            raise HeimdallError(
                "presence_malformed",
                f"private IM content field {key!r} must never "
                "appear in a presence record (section 38.9)")
    bridge = record.get("bridge")
    if not isinstance(bridge, dict) or \
            bridge.get("state") not in BRIDGE_STATES:
        raise HeimdallError("presence_malformed", "bridge.state")
    session = record.get("session")
    if not isinstance(session, dict) or \
            session.get("state") not in SESSION_STATES:
        raise HeimdallError("presence_malformed", "session.state")
    if bridge["state"] in ("absent", "disabled") and \
            session.get("logged_in"):
        raise HeimdallError(
            "presence_malformed",
            "an absent/disabled bridge cannot assert a "
            "logged-in session")
    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or \
            not provenance.get("source") or \
            "observed_at" not in provenance:
        raise HeimdallError(
            "presence_malformed",
            "provenance must carry source and observed_at "
            "(section 38 item 5)")
    return record


# ------------------------------------------------------------ observations

def build_observation(*, kind: str, summary: str, source: str,
                      location: Any = None,
                      recorded_at: str = "") -> dict:
    """One qualified observation for WYRD-style consumers.

    Private IM / relationship content is refused by name: it
    never becomes an observation, so it can never leak into
    telemetry or shared knowledge (section 38 item 9). All
    recorded text is redacted first."""
    if kind in PRIVATE_KINDS:
        raise HeimdallError(
            "private_content_refused",
            f"observation kind {kind!r} is private IM/"
            "relationship content; it stays out of telemetry "
            "and shared knowledge by default "
            "(section 38 item 9) and is never recorded")
    if kind not in OBSERVATION_KINDS:
        raise HeimdallError(
            "observation_malformed",
            f"kind {kind!r} is not a classified observation kind")
    if not summary or not source:
        raise HeimdallError(
            "observation_malformed",
            "summary and source are required (provenance)")
    clean, _ = redact_text(summary)
    return {
        "schema": OBSERVATION_SCHEMA,
        "source_project": SOURCE_PROJECT,
        "privacy_zone": "local-private",
        "kind": kind,
        "summary": clean,
        "provenance": {"source": source, "location": location,
                       "observed_at": recorded_at},
        "qualified": True,
        "accepted_as_world_truth": False,
        "telemetry_shareable": False,
        "recorded_at": recorded_at,
    }


def validate_observation(record: Any) -> dict:
    if not isinstance(record, dict):
        raise HeimdallError("observation_malformed",
                            "observation not a dict")
    if record.get("schema") != OBSERVATION_SCHEMA:
        raise HeimdallError("observation_malformed",
                            "wrong schema")
    if record.get("kind") in PRIVATE_KINDS:
        raise HeimdallError(
            "observation_malformed",
            "private IM/relationship kind in an observation "
            "(section 38 item 9)")
    if record.get("kind") not in OBSERVATION_KINDS:
        raise HeimdallError("observation_malformed", "kind")
    if record.get("qualified") is not True or \
            record.get("accepted_as_world_truth") is not False:
        raise HeimdallError(
            "observation_malformed",
            "observations are qualified, never world truth "
            "(section 38 item 5)")
    if record.get("telemetry_shareable"):
        raise HeimdallError(
            "observation_malformed",
            "Heimdall observations are not telemetry-shareable "
            "by default (section 38 item 9)")
    provenance = record.get("provenance")
    if not isinstance(provenance, dict) or \
            not provenance.get("source"):
        raise HeimdallError("observation_malformed",
                            "provenance.source required")
    return record


# ------------------------------------------------------------ status

def heimdall_status(*, recorded_at: str = "", env: Any = None,
                    probe: dict = None) -> dict:
    probe = probe if probe is not None else probe_bridge(env=env)
    return {
        "schema": f"{SCHEMA_PREFIX}.status.v1",
        "service": DESCRIPTOR["service"],
        "version": DESCRIPTOR["version"],
        "availability": "contract-implemented",
        "source_repo": SOURCE_REPO,
        "source_branch": SOURCE_BRANCH,
        "source_head_audited": SOURCE_HEAD_AUDITED,
        "source_license": SOURCE_LICENSE,
        "bridge": probe,
        "stage": "read-only presence/context only "
                 "(section 38 item 4)",
        "write_actions_refused": sorted(WRITE_ACTIONS),
        "read_actions_allowed": sorted(READ_ACTIONS),
        "live_grid_session_claimed": False,
        "login_attempted": False,
        "recorded_at": recorded_at,
    }
