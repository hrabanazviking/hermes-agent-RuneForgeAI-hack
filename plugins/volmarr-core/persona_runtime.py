"""Persona runtime foundations (Persona Runtime roadmap §§3-8).

The Persona Runtime roadmap defines a character by a collection
of human-editable Markdown documents whose *semantic roles* are
named in configuration — never by filename convention (§§1, 3).
This slice stands up only the foundations, reconciled against
the persona surfaces that already exist in this plugin:

- the identity store's ``persona_pack`` is a bounded *name*
  string only — it owns no persona text and is untouched here;
- persona canon (Self-Aware Agency §16) is a single YAML file
  of bounded assertions the runtime evaluates against facts —
  a different artefact from canonical persona *documents*;
- the layered self-model is runtime evidence about the entity,
  not authored persona material.

What stands here, and nothing more:

- §3 human-editable configuration: a read-only config file
  (``config/persona.yaml``) naming a persona id, a display
  name, a persona directory, and a document map of
  role -> {file, required}. The runtime cares about roles, not
  filenames; the runtime never writes this file or any
  document it names — changes are human edits only.
- §4 optional document extension: any extra role beyond the
  six core roles (``core``, ``service_bible``,
  ``memory_policy``, ``tool_policy``, ``relationship``,
  ``avatar``) is accepted as a first-class document with its
  own semantic role; adding one needs no code change here.
- §5 three-layer model, as a compiled artefact: Layer A is
  the persona kernel (sections of the ``core`` document whose
  headings name kernel material — identity, motivation,
  relationship, communication, laws, boundaries, role,
  quirks — falling back to the core document's leading
  sections; bounded to the §5 kernel token band), Layer B is
  the retrieval index (every section of every document,
  addressable by role and stable section id, with its text
  retained for a later retrieval slice), and Layer C is the
  canonical documents themselves (paths + hashes; their full
  text is compiled, never injected by this layer).
- §6 persona compiler: an explicit, deterministic compile —
  load, parse sections, normalise, derive the kernel, build
  the index, hash every document and the kernel. It runs only
  when called (startup, file change, or manual request are
  caller decisions); it never runs per message and it writes
  nothing — the compiled artefact is returned, not persisted
  (the §48 compilation cache and §49 generated directory are
  later sections, not this slice).
- §7 do not summarize blindly: the kernel, the index, and the
  IR all carry section text *verbatim* (after the §6
  whitespace normalisation only). No generated summary,
  paraphrase, or extracted prose is ever produced by this
  layer; structured representation means deterministic
  classification of whole verbatim sections, not rewriting.
- §8 PersonaIR: the compiler's explicit intermediate
  artefact. Every compiled section is classified
  deterministically into exactly one of the thirteen §8
  categories (identity, motivations, values, relationship,
  communication, behavioral_rules, preferences, boundaries,
  tools, memory, embodiment, quirks, projects) — first by
  heading keywords, then by the document's semantic role —
  and the IR carries all thirteen keys in roadmap order,
  empty where no section classifies there. The Markdown
  documents remain canonical; the IR is generated runtime
  data (``generated: True``, ``human_editable: False``),
  carries an ``ir_hash`` over its canonical form, and is
  never written to disk by this layer, so no human is ever
  asked to edit it.

Token counts are deterministic estimates (ceil(chars / 4)),
named as estimates wherever they surface. Disabled by
default. No hook and no turn-path caller compiles or injects
anything; the bounded packet item names only the persona id,
the kernel hash, and document/section counts.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

PERSONA_CONFIG_VERSION = 1
DEFAULT_CONFIG_PATH = Path("config") / "persona.yaml"
DEFAULT_DIRECTORY = Path("persona")
MAX_CONFIG_BYTES = 64 * 1024
MAX_DOCUMENT_BYTES = 512 * 1024
MAX_DOCUMENTS = 32
MAX_NAME_CHARS = 128
KERNEL_TOKEN_MIN = 500
KERNEL_TOKEN_MAX = 1500

# The six semantic roles §3 names, in roadmap order. §4 roles
# beyond these are first-class extensions, not errors.
CORE_ROLES = (
    "core",
    "service_bible",
    "memory_policy",
    "tool_policy",
    "relationship",
    "avatar",
)

# Heading words that mark a core-document section as kernel
# material (§5 Layer A: identity, core motivation, relationship
# orientation, communication style, essential behavioral laws,
# important boundaries, role, character-defining quirks).
KERNEL_HEADING_WORDS = frozenset({
    "identity", "motivation", "relationship", "communication",
    "style", "law", "laws", "boundary", "boundaries", "role",
    "quirk", "quirks", "essence", "character",
})

_SLUG = re.compile(r"^[a-z][a-z0-9_-]*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CONFIG_FIELDS = {"persona"}
_PERSONA_FIELDS = {"id", "display_name", "directory", "documents"}
_DOCUMENT_FIELDS = {"file", "required"}


class PersonaRuntimeError(RuntimeError):
    """Persona configuration or documents cannot be safely read."""


def _estimate_tokens(text: str) -> int:
    return int(math.ceil(len(text) / 4)) if text else 0


def _slugify(heading: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", heading.strip().lower()).strip("_")
    return slug or "section"


def core_roles() -> list[str]:
    return list(CORE_ROLES)


def parse_sections(text: str) -> list[dict[str, Any]]:
    """Split Markdown into sections by heading (§6 parse step).

    Content before the first heading becomes a ``preamble``
    section. Section ids are stable slugs of the heading text,
    disambiguated in document order (``name``, ``name_2``, ...).
    Section text is normalised: trailing whitespace stripped,
    runs of blank lines collapsed — the §6 normalise step; the
    wording itself is never summarised or rewritten (§7).
    """
    sections: list[dict[str, Any]] = []
    heading = "preamble"
    level = 0
    lines: list[str] = []

    def flush() -> None:
        body = "\n".join(lines).strip("\n")
        body = re.sub(r"\n{3,}", "\n\n", body).rstrip()
        if not body and heading == "preamble":
            return
        sections.append({
            "heading": heading, "level": level, "text": body,
        })

    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip()
            lines = []
        else:
            lines.append(line.rstrip())
    flush()
    seen: dict[str, int] = {}
    for section in sections:
        base = _slugify(section["heading"])
        seen[base] = seen.get(base, 0) + 1
        section["section_id"] = (
            base if seen[base] == 1 else f"{base}_{seen[base]}")
    return sections


# The thirteen PersonaIR categories §8 names, in roadmap order.
IR_CATEGORIES = (
    "identity", "motivations", "values", "relationship",
    "communication", "behavioral_rules", "preferences",
    "boundaries", "tools", "memory", "embodiment", "quirks",
    "projects",
)

# Heading-keyword classification, most specific categories
# first so a specific signal (tools, memory, embodiment, ...)
# wins over a generic one (identity). §7: classification only —
# the section text itself is carried verbatim, never rewritten.
_CATEGORY_KEYWORDS = (
    ("tools", frozenset({
        "tool", "tools", "shell", "command", "commands"})),
    ("memory", frozenset({
        "memory", "memories", "remembrance", "remembering"})),
    ("embodiment", frozenset({
        "embodiment", "avatar", "body", "appearance", "physical",
        "form"})),
    ("relationship", frozenset({
        "relationship", "relationships", "relational", "bond",
        "bonds", "companion", "devotion"})),
    ("communication", frozenset({
        "communication", "style", "voice", "speech", "language",
        "tone"})),
    ("projects", frozenset({"project", "projects"})),
    ("quirks", frozenset({
        "quirk", "quirks", "habit", "habits", "trait", "traits"})),
    ("boundaries", frozenset({
        "boundary", "boundaries", "limit", "limits", "forbidden",
        "prohibition", "prohibitions"})),
    ("preferences", frozenset({
        "preference", "preferences", "likes", "dislikes",
        "taste"})),
    ("motivations", frozenset({
        "motivation", "motivations", "purpose", "drive",
        "drives", "goal", "goals"})),
    ("values", frozenset({
        "value", "values", "virtue", "virtues", "principle",
        "principles", "ethics", "spiritual", "spirituality",
        "belief", "beliefs", "faith"})),
    ("behavioral_rules", frozenset({
        "behavior", "behaviour", "behavioral", "rule", "rules",
        "law", "laws", "execution", "conduct", "service",
        "counsel", "practice", "practices", "policy"})),
    ("identity", frozenset({
        "identity", "essence", "character", "role", "self",
        "who"})),
)

# Document-role fallback when a section heading names no
# category: the six core roles map onto the category their
# document exists for; an extension role is classified by its
# own name, and a section with no signal anywhere is
# persona-defining material by default (identity).
_ROLE_FALLBACK = {
    "core": "identity",
    "service_bible": "behavioral_rules",
    "memory_policy": "memory",
    "tool_policy": "tools",
    "relationship": "relationship",
    "avatar": "embodiment",
}


def ir_categories() -> list[str]:
    return list(IR_CATEGORIES)


def classify_section(role: str, heading: str) -> str:
    """The one §8 IR category for a section, deterministically.

    Heading keywords win (most specific first); the document
    role is the fallback. Pure function of (role, heading).
    """
    tokens = set(_slugify(heading).split("_"))
    for category, keywords in _CATEGORY_KEYWORDS:
        if tokens & keywords:
            return category
    fallback = _ROLE_FALLBACK.get(role)
    if fallback is not None:
        return fallback
    role_tokens = set(_slugify(role).split("_"))
    for category, keywords in _CATEGORY_KEYWORDS:
        if role_tokens & keywords:
            return category
    return "identity"


def build_persona_ir(persona_id: str,
                     index: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the §8 PersonaIR from the compiled section index.

    Generated runtime data: every §8 category is present in
    roadmap order (empty where nothing classifies there), each
    entry carries its section text verbatim (§7), and the
    ``ir_hash`` covers the canonical category/section/text
    form so identical documents always produce identical IR.
    """
    categories: dict[str, list[dict[str, Any]]] = {
        category: [] for category in IR_CATEGORIES}
    for entry in index:
        category = classify_section(entry["role"], entry["heading"])
        categories[category].append({
            "role": entry["role"],
            "section_id": entry["section_id"],
            "heading": entry["heading"],
            "estimated_tokens": entry["estimated_tokens"],
            "text": entry["text"],
        })
    canonical = "|".join(
        f"{category}:" + ";".join(
            f"{row['role']}/{row['section_id']}={row['text']}"
            for row in categories[category])
        for category in IR_CATEGORIES)
    return {
        "persona_id": persona_id,
        "generated": True,
        "human_editable": False,
        "categories": categories,
        "category_counts": {
            category: len(categories[category])
            for category in IR_CATEGORIES},
        "total_sections": sum(
            len(rows) for rows in categories.values()),
        "ir_hash": hashlib.sha256(
            canonical.encode("utf-8")).hexdigest(),
    }


class PersonaConfigStore:
    """Read the human-authored persona config; never write it."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return _as_bool(
            self._ctx.get_config("persona_runtime_enabled", False), False)

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "persona_config_path", str(DEFAULT_CONFIG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_CONFIG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_CONFIG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise PersonaRuntimeError(
                "persona config path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def read(self) -> dict[str, Any] | None:
        """The validated persona config, or None when absent."""
        path = self.path()
        if path.is_symlink():
            raise PersonaRuntimeError(
                "persona config file must not be a symbolic link")
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise PersonaRuntimeError(
                "persona config file exceeds its size limit")
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise PersonaRuntimeError(
                "persona config file is unreadable or malformed") from exc
        return self._validate(payload)

    def _validate(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != _CONFIG_FIELDS:
            raise PersonaRuntimeError("persona config fields are invalid")
        persona = payload.get("persona")
        if not isinstance(persona, dict) \
                or not set(persona) <= _PERSONA_FIELDS \
                or "documents" not in persona:
            raise PersonaRuntimeError("persona config fields are invalid")
        persona_id = persona.get("id")
        if not isinstance(persona_id, str) \
                or not _SLUG.match(persona_id):
            raise PersonaRuntimeError("persona id is invalid")
        display_name = persona.get("display_name", persona_id)
        if not isinstance(display_name, str) \
                or not display_name.strip() \
                or len(display_name) > MAX_NAME_CHARS:
            raise PersonaRuntimeError("persona display_name is invalid")
        directory = persona.get("directory", str(DEFAULT_DIRECTORY))
        if not isinstance(directory, str) or not directory.strip():
            raise PersonaRuntimeError("persona directory is invalid")
        documents = self._validate_documents(persona.get("documents"))
        return {
            "id": persona_id,
            "display_name": display_name.strip(),
            "directory": directory.strip(),
            "documents": documents,
        }

    @staticmethod
    def _validate_documents(raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, dict) or not raw:
            raise PersonaRuntimeError("persona documents are invalid")
        if len(raw) > MAX_DOCUMENTS:
            raise PersonaRuntimeError("persona documents exceed the limit")
        documents = []
        for role, spec in raw.items():
            if not isinstance(role, str) or not _SLUG.match(role):
                raise PersonaRuntimeError("persona document role is invalid")
            if not isinstance(spec, dict) \
                    or not set(spec) <= _DOCUMENT_FIELDS \
                    or "file" not in spec:
                raise PersonaRuntimeError(
                    "persona document fields are invalid")
            file_name = spec.get("file")
            if not isinstance(file_name, str) or not file_name.strip():
                raise PersonaRuntimeError("persona document file is invalid")
            required = spec.get("required", role == "core")
            if not isinstance(required, bool):
                raise PersonaRuntimeError(
                    "persona document required flag is invalid")
            documents.append({
                "role": role, "file": file_name.strip(),
                "required": required,
                "extension": role not in CORE_ROLES,
            })
        return documents

    def directory_path(self, config: dict[str, Any]) -> Path:
        """The persona directory, contained in the profile."""
        home = get_hermes_home().resolve()
        configured = Path(config["directory"])
        if configured.is_absolute():
            configured = DEFAULT_DIRECTORY
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise PersonaRuntimeError(
                "persona directory resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def document_path(self, config: dict[str, Any],
                      document: dict[str, Any]) -> Path:
        """One document's path, contained in the persona directory."""
        directory = self.directory_path(config)
        configured = Path(document["file"])
        if configured.is_absolute():
            raise PersonaRuntimeError(
                "persona document file must be relative")
        lexical = directory / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(directory.resolve()):
            raise PersonaRuntimeError(
                "persona document resolves outside the persona directory")
        if lexical.is_symlink():
            return lexical
        return candidate


class PersonaCompiler:
    """The §6 compiler: config + documents -> three-layer artefact.

    Explicit calls only; deterministic for identical inputs;
    writes nothing. A missing optional document is reported in
    ``missing_optional``; a missing required document, an
    unreadable or oversized document, and a symlinked document
    are errors — the compile fails closed rather than standing
    up a partial persona silently.
    """

    def __init__(self, ctx) -> None:
        self._store = PersonaConfigStore(ctx)

    def compile(self) -> dict[str, Any] | None:
        config = self._store.read()
        if config is None:
            return None
        documents: list[dict[str, Any]] = []
        missing_optional: list[str] = []
        index: list[dict[str, Any]] = []
        kernel_source: list[dict[str, Any]] = []
        for document in config["documents"]:
            path = self._store.document_path(config, document)
            if path.is_symlink():
                raise PersonaRuntimeError(
                    "persona document must not be a symbolic link")
            if not path.is_file():
                if document["required"]:
                    raise PersonaRuntimeError(
                        f"required persona document is missing: "
                        f"{document['role']}")
                missing_optional.append(document["role"])
                continue
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                raise PersonaRuntimeError(
                    "persona document exceeds its size limit")
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise PersonaRuntimeError(
                    "persona document is unreadable") from exc
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            sections = parse_sections(text)
            documents.append({
                "role": document["role"], "file": document["file"],
                "required": document["required"],
                "extension": document["extension"],
                "sha256": digest, "sections": len(sections),
                "estimated_tokens": _estimate_tokens(text),
            })
            for section in sections:
                index.append({
                    "role": document["role"],
                    "section_id": section["section_id"],
                    "heading": section["heading"],
                    "estimated_tokens": _estimate_tokens(section["text"]),
                    "text": section["text"],
                })
                if document["role"] == "core":
                    kernel_source.append(section)
        kernel = self._kernel(kernel_source)
        return {
            "persona_id": config["id"],
            "display_name": config["display_name"],
            "documents": documents,
            "missing_optional": missing_optional,
            "kernel": kernel,
            "index": index,
            "ir": build_persona_ir(config["id"], index),
            "persona_hash": self._persona_hash(documents, kernel),
        }

    @staticmethod
    def _kernel(core_sections: list[dict[str, Any]]) -> dict[str, Any]:
        """Layer A: kernel sections of the core document (§5).

        Sections whose headings name kernel material come
        first, in document order; if none do, the leading
        sections stand as the kernel. Whole sections are taken
        until the §5 kernel ceiling (1,500 estimated tokens);
        at least one section is always included, so a single
        oversized section surfaces as an over-band kernel
        rather than an empty one.
        """
        marked = [
            section for section in core_sections
            if KERNEL_HEADING_WORDS & set(
                _slugify(section["heading"]).split("_"))
        ]
        chosen = marked or list(core_sections)
        picked: list[dict[str, Any]] = []
        total = 0
        for section in chosen:
            tokens = _estimate_tokens(section["text"])
            if picked and total + tokens > KERNEL_TOKEN_MAX:
                break
            picked.append(section)
            total += tokens
        text = "\n\n".join(section["text"] for section in picked)
        return {
            "section_ids": [s["section_id"] for s in picked],
            "text": text,
            "estimated_tokens": _estimate_tokens(text),
            "within_band": KERNEL_TOKEN_MIN <= _estimate_tokens(text)
            <= KERNEL_TOKEN_MAX,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    @staticmethod
    def _persona_hash(documents: list[dict[str, Any]],
                      kernel: dict[str, Any]) -> str:
        payload = "|".join(
            f"{doc['role']}:{doc['sha256']}" for doc in documents)
        payload += f"|kernel:{kernel['sha256']}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PersonaRuntimeBridge:
    """Surface the compiled persona's identity, counts only.

    No session hook — compilation is an explicit call (§6).
    The packet item is content-bearing only and carries no
    persona text: Layer A injection into prompt assembly,
    Layer B retrieval, and Layer C use are later roadmap
    sections (§§13-15, §53), not this slice.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._compiler = PersonaCompiler(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str,
                     user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("persona_runtime_enabled", False), False
        ):
            return []
        try:
            compiled = self._compiler.compile()
        except (IdentityError, PersonaRuntimeError, OSError):
            return []
        if compiled is None:
            return []
        kernel = compiled["kernel"]
        populated = sum(
            1 for count in compiled["ir"]["category_counts"].values()
            if count)
        content = (
            f"Persona runtime (§§3-8): persona "
            f"{compiled['persona_id']} compiled from "
            f"{len(compiled['documents'])} documents / "
            f"{len(compiled['index'])} sections; kernel "
            f"{kernel['sha256'][:12]} "
            f"({kernel['estimated_tokens']} estimated tokens, "
            f"{'within' if kernel['within_band'] else 'outside'} "
            f"the §5 band); PersonaIR hash "
            f"{compiled['ir']['ir_hash'][:12]} with {populated} "
            f"of {len(compiled['ir']['categories'])} categories "
            f"populated; persona hash "
            f"{compiled['persona_hash'][:12]}. Canonical document "
            f"text is compiled, not injected by this layer."
        )
        return [ContextItem(
            section="current_state",
            content=content,
            source="persona_runtime",
            record_id=compiled["persona_hash"],
            priority=0.4,
            updated_at=0.0,
        )]


__all__ = [
    "PERSONA_CONFIG_VERSION",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_DIRECTORY",
    "CORE_ROLES",
    "IR_CATEGORIES",
    "KERNEL_TOKEN_MIN",
    "KERNEL_TOKEN_MAX",
    "PersonaRuntimeError",
    "PersonaConfigStore",
    "PersonaCompiler",
    "PersonaRuntimeBridge",
    "build_persona_ir",
    "classify_section",
    "core_roles",
    "ir_categories",
    "parse_sections",
]
