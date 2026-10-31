"""Persona runtime foundations (Persona Runtime roadmap §§3-16).

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
- §9 persona kernel generation: the kernel's source mix is
  the roadmap's formula, in roadmap order — PERSONA_CORE
  (the §5 kernel-marked core sections, with the leading-
  sections fallback) + highest-priority RELATIONSHIP_MODEL
  rules + highest-priority SERVICE_BIBLE rules + critical
  TOOL_POLICY boundaries. "Highest-priority" / "critical"
  is deterministic and explicit here: a non-core section
  enters the kernel only when its heading names a rule,
  law, principle, boundary, policy, or a critical /
  forbidden / prohibition marker (``kernel_source_kind``);
  narrative, preference, and guidance sections of those
  documents stay in the retrieval index, and no other role
  (memory policy, avatar, extensions) ever enters the
  kernel. Whole sections only, under the §5 band: a
  candidate that would overflow the ceiling is skipped, so
  a later small critical boundary can still fit. The
  kernel records its provenance (role, section id, source
  kind) and per-kind counts.
- §10 pin the kernel: the compiled artefact carries the
  kernel's pinning spec — the designated prompt order
  (system runtime rules, then the persona kernel, then
  active context, then the user message; the kernel is
  never buried in retrieved memory) and the stability this
  layer can actually guarantee (a deterministic compile:
  identical documents produce an identical kernel hash,
  and changing a non-kernel section never changes the
  kernel). Actual placement in a live prompt belongs to
  prompt assembly (§53, a later section); this layer
  injects nothing and claims no placement it does not
  perform.
- §11 section-aware Markdown parser: documents are split
  only at heading boundaries — conceptual sections, never
  arbitrary token chunks; a long section stays one whole
  section. Headings are semantic: a leading enumeration
  prefix (``37. ``) is presentation, not identity, and is
  stripped from the display heading and the slug. Every
  compiled index entry carries the §11 record shape —
  document (the semantic role), section (the bare slug),
  heading (the display heading), content (the verbatim
  section text) — plus a derived priority.
- §12 stable section ids: every section also carries a
  persistent, role-prefixed identifier
  (``relationship.when_disagreeing``) — unique across all
  documents, deterministic for identical documents, and
  unchanged when a section is merely renumbered, so
  retrieval results stay explainable across recompiles.
  The within-document bare slug remains as ``section_id``
  for the kernel and IR surfaces that already use it.
- §13 hybrid persona retrieval: an explicit, deterministic
  retrieval layer over the Layer B index — never only
  embeddings. Five of the §13 components stand here:
  keyword matching over heading + verbatim text, document
  role affinity, section tags (role + §8 category + heading /
  section tokens), current task classification (the pure
  ``classify_task`` lexicon over the query/task text), and
  the §11 derived priority, combined by the pure
  ``retrieval_score`` function into an explainable score
  whose components are returned with every result. Results
  are named by their §12 stable ids. The sixth component,
  semantic similarity, is honestly unavailable: this plugin
  owns no embedding surface, so every score records
  ``semantic: None`` and ``hybrid_components`` names it
  unavailable rather than faking a similarity value.
  Retrieval is an explicit call only — no hook, no budgeter
  (§15 is later), and nothing retrieved is injected by
  this layer.
- §14 persona router: ``PersonaRouter`` decides which
  persona sections a task *requires*, from the five §14
  inputs (user message, current task, active project, tool
  intent, conversation state — any subset may be present).
  The pure ``route_sections`` function classifies the
  combined signals with the §13 lexicon, derives a task
  label (an explicit current task wins, slugified; else a
  deterministic label from the first matching tag; else
  ``general``), and selects required sections per task tag
  — the top sections in §13 score order whose tags contact
  that tag's section keywords — filled from the §13
  retrieval ranking, capped, and ordered by score with
  stable-id tiebreaks. Every required section is named by
  its §12 stable id and carries the tags that required it
  plus its explainable §13 score. Routing is an explicit
  call only: it writes nothing, injects nothing, and no
  budgeter (§15) has trimmed its output yet.
- §15 token budgeter: ``PersonaContextBudgeter`` / the pure
  ``budget_items`` function allocate estimated tokens across
  the four §15 categories (persona kernel, dynamic persona
  retrieval, relevant memories, project state), each with
  the roadmap's suggested range. Allocations are
  configurable per category, and scale by model context
  class: a small local model receives each category's
  minimum, a standard model its suggested maximum, and a
  large-context model twice that. Trimming is whole-item
  only (a section is never cut mid-text, §7), in priority
  order (derived priority, then caller score, then id) —
  an item that does not fit is excluded with its reason
  named, and a later smaller item may still fit. Categories
  are independent: one category's overflow never spends
  another's allocation. Budgeting is an explicit call only:
  it writes nothing, injects nothing, and assembles no
  prompt (§53 is later).
- §16 priority system: persona information carries a
  priority level — P0 identity-critical, P1 strong
  behavioral rule, P2 important preference, P3
  context-specific preference, P4 aesthetic/background
  detail (``PRIORITY_LEVELS``). A level may be *authored*:
  a trailing ``[P0]``–``[P4]`` marker on a section heading
  is this layer's authored-metadata convention — the
  marker is stripped from the semantic heading (so it
  never changes a section's stable id) and recorded as
  the section's authored level. Where no marker stands,
  the level is *derived* deterministically by the pure
  ``priority_level`` function, reconciled with the §11
  bands: kernel core sections are P0, other kernel
  sections and kernel-marked rules are P1, the
  persona-defining §8 categories are P2, preference /
  project / tool / memory / communication material is
  P3, and quirks, embodiment, the preamble, and the rest
  are P4. An authored level wins over the derived one
  everywhere (index float, retrieval, kernel, budgeter).
  §16's hard rule stands in code in both places tokens
  are saved: kernel generation never skips a P0 section
  to fit the §5 ceiling (a P0-heavy kernel surfaces
  over-band, honestly), and the §15 budgeter never
  excludes a P0 item in the persona-kernel category as
  ``over_budget`` (its category may report negative
  remaining rather than evict P0 material).
- The §11 priority float is *derived* unless authored:
  the pure ``section_priority`` function bands a section
  by signals this layer already computes deterministically
  (in the kernel 0.90; kernel-marked but not selected
  0.80; identity/values/boundaries/rules/motivations/
  relationship material 0.60; everything else, including
  the unheaded preamble, 0.40); an authored §16 level
  maps to its own float (P0 1.00 … P4 0.25) instead.

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

# §9 kernel source mix, in the roadmap's formula order. Only
# these roles can enter the kernel, each under its own kind.
KERNEL_SOURCE_ORDER = (
    "core", "relationship", "service_bible", "tool_policy",
)
_KERNEL_SOURCE_KIND = {
    "core": "core",
    "relationship": "relationship_rule",
    "service_bible": "service_rule",
    "tool_policy": "tool_boundary",
}

# Heading words that mark a non-core section as highest-
# priority / critical for §9: the heading explicitly names a
# rule, law, principle, boundary, or policy, or carries a
# critical / forbidden / prohibition marker. Narrative,
# preference, and guidance headings carry none of these.
RULE_HEADING_WORDS = frozenset({
    "rule", "rules", "law", "laws", "principle", "principles",
    "boundary", "boundaries", "policy", "policies", "critical",
    "forbidden", "prohibition", "prohibitions",
})

# §10 pinning: the designated prompt order. The kernel sits
# in the highest practical persistent layer — directly under
# the system runtime rules, ahead of active context and the
# user message, never buried in retrieved memory.
PINNING_ORDER = (
    "system_runtime_rules", "persona_kernel", "active_context",
    "user_message",
)


def kernel_source_kind(role: str, heading: str) -> str | None:
    """The §9 kernel source kind for a section, or None.

    Pure function of (role, heading). The core document uses
    the §5 kernel heading words; the three other named roles
    use the rule/boundary heading words; every other role
    never enters the kernel.
    """
    kind = _KERNEL_SOURCE_KIND.get(role)
    if kind is None:
        return None
    tokens = set(_slugify(heading).split("_"))
    words = KERNEL_HEADING_WORDS if role == "core" \
        else RULE_HEADING_WORDS
    return kind if tokens & words else None


def kernel_source_kinds() -> list[str]:
    return [_KERNEL_SOURCE_KIND[role] for role in KERNEL_SOURCE_ORDER]

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


_ENUM_PREFIX = re.compile(r"^\d+(?:\.\d+)*[.)]\s+")

# §16 authored priority: a trailing [P0]-[P4] marker on a
# heading is authored metadata, not heading text.
_PRIORITY_MARKER = re.compile(r"\[(P[0-4])\]\s*$", re.IGNORECASE)


def authored_priority_level(raw: str) -> str | None:
    """The §16 level authored on a raw heading, or None.

    Pure function of the raw heading text: a trailing
    ``[P0]``–``[P4]`` marker (any case) is the authored
    level; anything else (including an out-of-range
    ``[P9]``) is ordinary heading text, not metadata.
    """
    match = _PRIORITY_MARKER.search(raw.strip())
    return match.group(1).upper() if match else None


def display_heading(raw: str) -> str:
    """The §11 semantic heading: enumeration is not identity.

    A leading enumeration prefix (``37. ``, ``11.2) ``) is
    presentation — the roadmap's own example turns
    ``37. WHEN CADUCEA DISAGREES`` into the heading
    ``WHEN CADUCEA DISAGREES``. A trailing §16 authored
    priority marker (``[P0]``–``[P4]``) is metadata, not
    identity, and is likewise stripped, so authoring a
    level never changes a section's stable id. Pure
    function of the raw heading text; a heading that is
    only a number keeps it.
    """
    cleaned = _ENUM_PREFIX.sub("", raw.strip(), count=1).strip()
    cleaned = _PRIORITY_MARKER.sub("", cleaned).strip()
    return cleaned or raw.strip()


def stable_section_id(role: str, section_id: str) -> str:
    """The §12 persistent identifier: ``role.section``.

    Role-prefixed so an id is unique across every document
    and explains which document it names; deterministic, so
    identical documents always produce identical ids.
    """
    return f"{role}.{section_id}"


def core_roles() -> list[str]:
    return list(CORE_ROLES)


def parse_sections(text: str) -> list[dict[str, Any]]:
    """Split Markdown into sections by heading (§§6, 11).

    §11: the split respects conceptual boundaries only —
    sections begin at headings and are never cut at an
    arbitrary token count, however long they run. Content
    before the first heading becomes a ``preamble`` section.
    Headings are semantic (§11): a leading enumeration
    prefix is stripped (``display_heading``), so renumbering
    a section never changes its identity. Section ids are
    stable slugs of the semantic heading, disambiguated in
    document order (``name``, ``name_2``, ...); the §12
    persistent form prefixes the document role
    (``stable_section_id``). Section text is normalised:
    trailing whitespace stripped, runs of blank lines
    collapsed — the §6 normalise step; the wording itself
    is never summarised or rewritten (§7).
    """
    sections: list[dict[str, Any]] = []
    heading = "preamble"
    level = 0
    authored: str | None = None
    lines: list[str] = []

    def flush() -> None:
        body = "\n".join(lines).strip("\n")
        body = re.sub(r"\n{3,}", "\n\n", body).rstrip()
        if not body and heading == "preamble":
            return
        sections.append({
            "heading": heading, "level": level, "text": body,
            "authored_priority": authored,
        })

    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            authored = authored_priority_level(match.group(2))
            heading = display_heading(match.group(2))
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


# §11 priority bands (derived): the kernel is
# identity-critical material; kernel-marked sections that
# did not fit are the next band; the persona-defining IR
# categories follow; the rest — preferences, background,
# the unheaded preamble — are last.
_PRIORITY_MID_CATEGORIES = frozenset({
    "identity", "values", "boundaries", "behavioral_rules",
    "motivations", "relationship",
})

# §16 priority levels, in roadmap order with the roadmap's
# own names, and the float each authored level carries.
PRIORITY_LEVELS = (
    ("P0", "identity-critical"),
    ("P1", "strong behavioral rule"),
    ("P2", "important preference"),
    ("P3", "context-specific preference"),
    ("P4", "aesthetic/background detail"),
)
_PRIORITY_LEVEL_SCORES = {
    "P0": 1.00, "P1": 0.85, "P2": 0.65, "P3": 0.45, "P4": 0.25,
}
# §8 categories whose derived level is P3; the §11 mid
# categories derive P2; quirks/embodiment and everything
# else derive P4.
_PRIORITY_P3_CATEGORIES = frozenset({
    "preferences", "projects", "tools", "memory", "communication",
})


def priority_levels() -> list[dict[str, str]]:
    return [
        {"level": level, "name": name}
        for level, name in PRIORITY_LEVELS]


def priority_level_score(level: str) -> float:
    """The float an authored §16 level carries, in [0, 1]."""
    try:
        return _PRIORITY_LEVEL_SCORES[level]
    except KeyError:
        raise PersonaRuntimeError(
            f"unknown priority level: {level!r}") from None


def priority_level(role: str, heading: str,
                   in_kernel: bool = False,
                   authored: str | None = None) -> str:
    """The §16 priority level of a section. Pure function.

    An authored level (a trailing ``[Pn]`` heading marker,
    already extracted) wins. Otherwise the level is derived
    from the signals this layer already computes: a kernel
    section of the core document is P0 (identity-critical);
    any other kernel section, and any kernel-marked (§9)
    section that did not fit, is P1 (a strong behavioral
    rule); a section classifying into a persona-defining
    §8 category is P2; preference/project/tool/memory/
    communication material is P3; quirks, embodiment, the
    unheaded preamble, and everything else are P4.
    """
    if authored is not None:
        if authored not in _PRIORITY_LEVEL_SCORES:
            raise PersonaRuntimeError(
                f"unknown priority level: {authored!r}")
        return authored
    if in_kernel:
        return "P0" if role == "core" else "P1"
    if heading == "preamble":
        return "P4"
    if kernel_source_kind(role, heading) is not None:
        return "P1"
    category = classify_section(role, heading)
    if category in _PRIORITY_MID_CATEGORIES:
        return "P2"
    if category in _PRIORITY_P3_CATEGORIES:
        return "P3"
    return "P4"


def section_priority(role: str, heading: str,
                     in_kernel: bool = False,
                     authored: str | None = None) -> float:
    """The §11 derived priority of a section, in [0, 1].

    Pure deterministic function of (role, heading, kernel
    membership) over signals this layer already computes.
    Bands: in the kernel 0.90; kernel-marked (§9) but not
    selected 0.80; sections classifying into a
    persona-defining §8 category 0.60; everything else
    0.40. An authored §16 level replaces the band with the
    level's own float (P0 1.00 … P4 0.25).
    """
    if authored is not None:
        return priority_level_score(authored)
    if in_kernel:
        return 0.90
    if heading == "preamble":
        return 0.40
    if kernel_source_kind(role, heading) is not None:
        return 0.80
    if classify_section(role, heading) in _PRIORITY_MID_CATEGORIES:
        return 0.60
    return 0.40


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
            "stable_id": entry.get(
                "stable_id",
                stable_section_id(entry["role"], entry["section_id"])),
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


# --- §13 hybrid retrieval -------------------------------------------
#
# Deterministic, explainable retrieval over the compiled
# Layer B index. Tokenisation reuses the slug vocabulary the
# parser already speaks, so a query, a heading, and a stable
# id all tokenise the same way.

RETRIEVAL_DEFAULT_LIMIT = 5
RETRIEVAL_MAX_LIMIT = 20

# Task lexicon: tag -> words in a user message / task text
# that signal the tag. Order is roadmap-example order first.
_TASK_LEXICON = (
    ("coding", frozenset({
        "code", "coding", "refactor", "debug", "bug", "implement",
        "function", "class", "python", "typescript", "compile",
        "test", "tests", "testing"})),
    ("git", frozenset({
        "git", "branch", "commit", "push", "pull", "merge",
        "rebase", "repository", "repo"})),
    ("filesystem", frozenset({
        "file", "files", "filesystem", "directory", "folder",
        "path", "rename", "move", "copy", "delete"})),
    ("external_mutation", frozenset({
        "push", "publish", "send", "post", "deploy", "release",
        "upload", "remote", "external"})),
    ("memory", frozenset({
        "memory", "remember", "recall", "forget", "contradiction",
        "history"})),
    ("relationship", frozenset({
        "relationship", "disagree", "disagrees", "counsel",
        "decision", "decisions", "trust"})),
    ("communication", frozenset({
        "write", "writing", "draft", "tone", "voice", "explain",
        "message", "speak"})),
    ("research", frozenset({
        "research", "search", "investigate", "explore", "compare",
        "documentation", "docs"})),
    ("planning", frozenset({
        "plan", "planning", "roadmap", "schedule", "organize",
        "organise", "prioritize", "prioritise"})),
)

TASK_TAGS = tuple(tag for tag, _ in _TASK_LEXICON)

# Section keywords each task tag looks for in a section's tags.
_TASK_SECTION_KEYWORDS = {
    "coding": frozenset({
        "coding", "code", "execution", "dependencies", "tests",
        "testing"}),
    "git": frozenset({"git", "remote", "reversibility"}),
    "filesystem": frozenset({
        "filesystem", "file", "files", "directory"}),
    "external_mutation": frozenset({
        "remote", "reversibility", "external", "mutation", "git"}),
    "memory": frozenset({"memory", "contradiction", "remembrance"}),
    "relationship": frozenset({
        "relationship", "disagrees", "disagreeing", "counsel",
        "decisions"}),
    "communication": frozenset({
        "communication", "voice", "tone", "style"}),
    "research": frozenset({"research", "documentation", "exploration"}),
    "planning": frozenset({"planning", "roadmap", "goals", "projects"}),
}

# Document roles each task tag has affinity for (§13's
# document-role component).
_TASK_ROLE_AFFINITY = {
    "coding": frozenset({"service_bible", "tool_policy", "core"}),
    "git": frozenset({"tool_policy", "service_bible"}),
    "filesystem": frozenset({"tool_policy", "service_bible"}),
    "external_mutation": frozenset({"tool_policy"}),
    "memory": frozenset({"memory_policy", "core"}),
    "relationship": frozenset({"relationship", "core"}),
    "communication": frozenset({"core", "relationship"}),
    "research": frozenset({"service_bible", "memory_policy"}),
    "planning": frozenset({"core", "service_bible"}),
}


# Retrieval stopwords: function words carry no topical
# signal, and counting them lets an unrelated section float
# on a shared "and"/"my" (the §13 example's core sections
# outranked tool_policy.reversibility on exactly that).
# _tokens is used only by the §13 retrieval functions, so
# the filter is scoped to retrieval.
_RETRIEVAL_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "into", "is", "it", "its", "my", "of",
    "on", "or", "the", "to", "with", "you", "your",
})


def _tokens(text: str) -> set[str]:
    return {tok for tok in _slugify(text).split("_")
            if tok and tok not in _RETRIEVAL_STOPWORDS}


def classify_task(text: str) -> list[str]:
    """The §13 task tags a message signals, in lexicon order.

    Pure function of the text: a tag is present when any of
    its lexicon words appears as a token. No model call.
    """
    tokens = _tokens(text or "")
    return [tag for tag, words in _TASK_LEXICON if tokens & words]


def task_tags() -> list[str]:
    return list(TASK_TAGS)


def section_tags(entry: dict[str, Any]) -> list[str]:
    """A compiled section's §13 tags, sorted deterministically.

    Tags are the document role, the §8 IR category, the
    role's own fallback category (the category its document
    exists for, when the heading classifies elsewhere —
    a tool_policy section headed "Git Policy" is tools
    material even though "policy" classifies it as
    behavioral rules), and the heading / section-id tokens
    — all signals this layer already computes; nothing is
    authored or stored.
    """
    tags = {entry["role"], classify_section(entry["role"], entry["heading"])}
    fallback = _ROLE_FALLBACK.get(entry["role"])
    if fallback is not None:
        tags.add(fallback)
    tags |= _tokens(entry["heading"])
    tags |= _tokens(entry["section_id"])
    return sorted(tags)


def hybrid_components() -> list[dict[str, Any]]:
    """The §13 retrieval components and their honest status."""
    return [
        {"name": "semantic_similarity", "available": False,
         "reason": "no embedding surface is owned by this plugin"},
        {"name": "keyword_matching", "available": True, "reason": ""},
        {"name": "document_role", "available": True, "reason": ""},
        {"name": "section_tags", "available": True, "reason": ""},
        {"name": "task_classification", "available": True, "reason": ""},
        {"name": "priority", "available": True, "reason": ""},
    ]


def retrieval_score(entry: dict[str, Any], query: str = "",
                    task_tags_: list[str] | None = None) -> dict[str, Any]:
    """The explainable §13 score for one section.

    Pure function. Components are each in [0, 1] except
    ``semantic``, which is None (unavailable, never faked).
    The total is the fixed weighted sum: keyword 0.35,
    heading 0.10, task 0.25, role 0.10, priority 0.20.
    """
    query_tokens = _tokens(query or "")
    heading_tokens = _tokens(entry["heading"])
    text_tokens = _tokens(entry["text"])
    if query_tokens:
        keyword = len(query_tokens & (heading_tokens | text_tokens)) \
            / len(query_tokens)
        heading_match = len(query_tokens & heading_tokens) / len(query_tokens)
    else:
        keyword = 0.0
        heading_match = 0.0
    tags = set(section_tags(entry))
    task_match = 0.0
    role_match = 0.0
    wanted = [t for t in (task_tags_ or []) if t in _TASK_SECTION_KEYWORDS]
    if wanted:
        task_match = max(
            len(_TASK_SECTION_KEYWORDS[t] & tags)
            / len(_TASK_SECTION_KEYWORDS[t]) for t in wanted)
        affinity: set[str] = set()
        for tag in wanted:
            affinity |= _TASK_ROLE_AFFINITY[tag]
        role_match = 1.0 if entry["role"] in affinity else 0.0
    priority = float(entry.get("priority", 0.40))
    total = (0.35 * keyword + 0.10 * heading_match + 0.25 * task_match
             + 0.10 * role_match + 0.20 * priority)
    return {
        "total": round(total, 6),
        "keyword": round(keyword, 6),
        "heading": round(heading_match, 6),
        "task": round(task_match, 6),
        "role": round(role_match, 6),
        "priority": priority,
        "semantic": None,
    }


def retrieve_sections(index: list[dict[str, Any]], query: str = "",
                      task_text: str | None = None,
                      limit: int = RETRIEVAL_DEFAULT_LIMIT
                      ) -> list[dict[str, Any]]:
    """Rank compiled sections for a query/task (§13).

    Deterministic: sorted by descending score, ties broken
    by stable id. Sections scoring zero are excluded, and a
    query with no tokens and no task signal retrieves
    nothing. Each result names its §12 stable id, carries
    its verbatim text (§7), its tags, and the full score
    breakdown — retrieval stays explainable.
    """
    tags_wanted = classify_task(task_text if task_text is not None else query)
    if not _tokens(query or "") and not tags_wanted:
        return []
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = RETRIEVAL_DEFAULT_LIMIT
    bounded = max(1, min(RETRIEVAL_MAX_LIMIT, bounded))
    results = []
    for entry in index:
        score = retrieval_score(entry, query=query, task_tags_=tags_wanted)
        if score["total"] <= 0.0:
            continue
        # A section must connect to the request: a bare
        # priority/role float with no keyword, heading, or
        # task contact is not a retrieval result.
        if not (score["keyword"] or score["heading"] or score["task"]):
            continue
        results.append({
            "stable_id": entry.get(
                "stable_id",
                stable_section_id(entry["role"], entry["section_id"])),
            "role": entry["role"],
            "section_id": entry["section_id"],
            "heading": entry["heading"],
            "priority": float(entry.get("priority", 0.40)),
            "task_tags": list(tags_wanted),
            "tags": section_tags(entry),
            "score": score,
            "text": entry["text"],
        })
    results.sort(key=lambda row: (-row["score"]["total"], row["stable_id"]))
    return results[:bounded]


# --- §14 persona router ---------------------------------------------
#
# The router decides which sections a task requires. It is a
# deterministic decision layer over §13 retrieval: per-tag
# coverage first (so a task's every facet names its sections),
# then the retrieval ranking as fill, under a hard cap.

ROUTER_DEFAULT_LIMIT = 8
ROUTER_MAX_LIMIT = 20
ROUTER_PER_TAG_LIMIT = 3

# The five §14 inputs, in canonical order.
ROUTER_INPUTS = (
    "user_message", "current_task", "active_project",
    "tool_intent", "conversation_state",
)

# Task labels for a derived route, in precedence order: the
# first tag present names the task when no explicit current
# task was supplied.
_TASK_LABELS = (
    ("coding", "code_generation"),
    ("git", "git_operations"),
    ("filesystem", "filesystem_operations"),
    ("external_mutation", "external_mutation"),
    ("memory", "memory_work"),
    ("relationship", "relationship_counsel"),
    ("communication", "communication"),
    ("research", "research"),
    ("planning", "planning"),
)


def router_inputs() -> list[str]:
    return list(ROUTER_INPUTS)


def route_task_label(current_task: str = "",
                     task_tags_: list[str] | None = None) -> str:
    """The §14 task label for a route. Pure function.

    An explicit current task wins, slugified (``code_generation``
    stays ``code_generation``); a placeholder (``general`` /
    ``task`` / empty) does not. Otherwise the first §13 tag in
    label precedence order names the task; no signal at all is
    ``general``.
    """
    slug = _slugify(current_task) if (current_task or "").strip() else ""
    if slug and slug not in ("general", "task", "none", "section"):
        return slug
    wanted = set(task_tags_ or [])
    for tag, label in _TASK_LABELS:
        if tag in wanted:
            return label
    return "general"


def _tag_contact(entry: dict[str, Any], tag: str) -> float:
    keywords = _TASK_SECTION_KEYWORDS.get(tag)
    if not keywords:
        return 0.0
    return len(keywords & set(section_tags(entry))) / len(keywords)


def route_sections(index: list[dict[str, Any]], user_message: str = "",
                   current_task: str = "", active_project: str = "",
                   tool_intent: str = "", conversation_state: str = "",
                   limit: int = ROUTER_DEFAULT_LIMIT
                   ) -> dict[str, Any]:
    """Decide the persona sections a task requires (§14).

    Pure deterministic function of the compiled index and the
    five §14 inputs. Selection is per-tag first — for each
    classified tag, the top ``ROUTER_PER_TAG_LIMIT`` sections
    in §13 score order whose tags contact that tag — then
    filled from the §13 retrieval ranking, capped at ``limit``
    (clamped 1–20) and ordered by descending score with
    stable-id tiebreaks. Empty signals route to ``general``
    with nothing required. The result names the task, the
    tags, which inputs were present (names only, never their
    text), and the required stable ids both as ``required``
    and in the §14 example's ``persona_context`` shape, with
    a per-section row carrying the tags that required it and
    its explainable §13 score. A row required by keyword
    retrieval alone (no tag contact) is marked
    ``via_retrieval`` rather than left reasonless.
    """
    raw = {
        "user_message": user_message, "current_task": current_task,
        "active_project": active_project, "tool_intent": tool_intent,
        "conversation_state": conversation_state,
    }
    present = [name for name in ROUTER_INPUTS
               if str(raw[name] or "").strip()]
    combined = "\n".join(str(raw[name]) for name in ROUTER_INPUTS
                         if name in present)
    tags_wanted = classify_task(combined)
    label = route_task_label(current_task, tags_wanted)
    base: dict[str, Any] = {
        "task": label,
        "task_tags": list(tags_wanted),
        "inputs_present": present,
        "required": [],
        "persona_context": [],
        "sections": [],
    }
    if not present or (not _tokens(combined) and not tags_wanted):
        return base
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = ROUTER_DEFAULT_LIMIT
    bounded = max(1, min(ROUTER_MAX_LIMIT, bounded))
    scores = {
        id(entry): retrieval_score(
            entry, query=combined, task_tags_=tags_wanted)
        for entry in index
    }

    def stable(entry: dict[str, Any]) -> str:
        return entry.get(
            "stable_id",
            stable_section_id(entry["role"], entry["section_id"]))

    selected: dict[str, dict[str, Any]] = {}

    def add(entry: dict[str, Any], reason_tags: list[str]) -> None:
        sid = stable(entry)
        row = selected.get(sid)
        if row is None:
            row = {
                "stable_id": sid, "role": entry["role"],
                "section_id": entry["section_id"],
                "heading": entry["heading"],
                "priority": float(entry.get("priority", 0.40)),
                "task_tags": [],
                "via_retrieval": False,
                "score": scores[id(entry)],
            }
            selected[sid] = row
        for tag in reason_tags:
            if tag not in row["task_tags"]:
                row["task_tags"].append(tag)

    for tag in tags_wanted:
        candidates = [
            entry for entry in index if _tag_contact(entry, tag) > 0.0]
        candidates.sort(
            key=lambda e: (-scores[id(e)]["total"], stable(e)))
        for entry in candidates[:ROUTER_PER_TAG_LIMIT]:
            add(entry, [tag])
    for row in retrieve_sections(
            index, query=combined, limit=ROUTER_MAX_LIMIT):
        entry = next(
            (e for e in index if stable(e) == row["stable_id"]), None)
        if entry is None or row["stable_id"] in selected:
            continue
        contact = [t for t in tags_wanted
                   if _tag_contact(entry, t) > 0.0]
        add(entry, contact)
        if not contact:
            # Required by keyword/heading retrieval contact,
            # not by any tag — say so, never leave the row
            # reasonless.
            selected[row["stable_id"]]["via_retrieval"] = True
    ordered = sorted(
        selected.values(),
        key=lambda r: (-r["score"]["total"], r["stable_id"]))
    ordered = ordered[:bounded]
    for row in ordered:
        row["task_tags"] = [
            t for t in tags_wanted if t in row["task_tags"]]
    ids = [row["stable_id"] for row in ordered]
    base["required"] = ids
    base["persona_context"] = list(ids)
    base["sections"] = ordered
    return base


# --- §15 token budgeter ---------------------------------------------
#
# A pure budgeting layer over the §13 retrieval / §14 router
# outputs plus caller-supplied memory and project-state items.
# It decides what fits; it assembles and injects nothing.

BUDGET_CATEGORIES = (
    "persona_kernel", "persona_retrieval", "relevant_memories",
    "project_state",
)

# The §15 suggested budgets, as (minimum, maximum) estimated
# tokens per category.
SUGGESTED_BUDGETS = {
    "persona_kernel": (500, 1500),
    "persona_retrieval": (300, 2500),
    "relevant_memories": (500, 3000),
    "project_state": (500, 3000),
}

# Model context classes: small local models receive much
# less (each category's minimum), standard models the
# suggested maximum, large-context models more (twice the
# suggested maximum).
CONTEXT_CLASSES = ("small_local", "standard", "large")


def budget_categories() -> list[str]:
    return list(BUDGET_CATEGORIES)


def context_classes() -> list[str]:
    return list(CONTEXT_CLASSES)


def suggested_budgets() -> dict[str, dict[str, int]]:
    return {
        category: {"min": low, "max": high}
        for category, (low, high) in SUGGESTED_BUDGETS.items()
    }


def budget_allocations(context_class: str = "standard",
                       overrides: dict[str, Any] | None = None
                       ) -> dict[str, int]:
    """The per-category allocations for a context class (§15).

    Pure function. ``overrides`` replaces individual category
    allocations (configurability); unknown categories,
    negative or non-integer allocations, and unknown context
    classes are refused.
    """
    if context_class not in CONTEXT_CLASSES:
        raise PersonaRuntimeError(
            f"unknown budget context class: {context_class!r}")
    allocations: dict[str, int] = {}
    for category, (low, high) in SUGGESTED_BUDGETS.items():
        if context_class == "small_local":
            allocations[category] = low
        elif context_class == "large":
            allocations[category] = 2 * high
        else:
            allocations[category] = high
    for category, value in (overrides or {}).items():
        if category not in SUGGESTED_BUDGETS:
            raise PersonaRuntimeError(
                f"unknown budget category: {category!r}")
        if isinstance(value, bool) or not isinstance(value, int) \
                or value < 0:
            raise PersonaRuntimeError(
                f"budget allocation for {category} is invalid")
        allocations[category] = value
    return allocations


def _budget_item(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PersonaRuntimeError("budget item must be a mapping")
    item_id = raw.get("id")
    category = raw.get("category")
    if not isinstance(item_id, str) or not item_id.strip():
        raise PersonaRuntimeError("budget item id is invalid")
    if category not in SUGGESTED_BUDGETS:
        raise PersonaRuntimeError(
            f"budget item category is invalid: {category!r}")
    tokens = raw.get("estimated_tokens")
    if tokens is None and isinstance(raw.get("text"), str):
        tokens = _estimate_tokens(raw["text"])
    if isinstance(tokens, bool) or not isinstance(tokens, int) \
            or tokens < 0:
        raise PersonaRuntimeError("budget item tokens are invalid")
    priority = raw.get("priority", 0.40)
    score = raw.get("score", 0.0)
    for value in (priority, score):
        if isinstance(value, bool) \
                or not isinstance(value, (int, float)) \
                or not 0.0 <= float(value) <= 1.0:
            raise PersonaRuntimeError("budget item priority/score invalid")
    level = raw.get("priority_level")
    if level is not None and level not in _PRIORITY_LEVEL_SCORES:
        raise PersonaRuntimeError(
            f"budget item priority level is invalid: {level!r}")
    return {
        "id": item_id.strip(), "category": category,
        "estimated_tokens": tokens,
        "priority": float(priority), "score": float(score),
        "priority_level": level,
    }


def budget_items(items: list[dict[str, Any]],
                 context_class: str = "standard",
                 budgets: dict[str, Any] | None = None
                 ) -> dict[str, Any]:
    """Trim candidate items to the §15 budgets. Pure function.

    Items are considered per category in priority order
    (descending derived priority, then descending score,
    then id). Whole items only: an item that does not fit
    the category's remaining allocation is excluded with
    reason ``over_budget`` and a later smaller item may
    still fit; no item is ever cut. Categories spend only
    their own allocation. Deterministic for identical input.

    §16 exception: a P0 item in the persona-kernel category
    is never excluded merely to save tokens — it is included
    even past the allocation, and the category's remaining
    count may go negative rather than evict P0 material.
    """
    allocations = budget_allocations(context_class, budgets)
    normalised = [_budget_item(raw) for raw in (items or [])]
    seen: set[tuple[str, str]] = set()
    for row in normalised:
        key = (row["category"], row["id"])
        if key in seen:
            raise PersonaRuntimeError(
                f"duplicate budget item: {row['category']}/{row['id']}")
        seen.add(key)
    categories: dict[str, Any] = {}
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for category in BUDGET_CATEGORIES:
        rows = [r for r in normalised if r["category"] == category]
        rows.sort(key=lambda r: (-r["priority"], -r["score"], r["id"]))
        remaining = allocations[category]
        kept: list[str] = []
        dropped: list[str] = []
        for row in rows:
            p0_kernel = category == "persona_kernel" \
                and row.get("priority_level") == "P0"
            if row["estimated_tokens"] <= remaining or p0_kernel:
                remaining -= row["estimated_tokens"]
                kept.append(row["id"])
                included.append(row)
            else:
                dropped.append(row["id"])
                excluded.append({**row, "reason": "over_budget"})
        categories[category] = {
            "allocation": allocations[category],
            "used": allocations[category] - remaining,
            "remaining": remaining,
            "included": kept, "excluded": dropped,
        }
    return {
        "context_class": context_class,
        "allocations": allocations,
        "categories": categories,
        "included": included,
        "excluded": excluded,
        "total_allocation": sum(allocations.values()),
        "total_used": sum(c["used"] for c in categories.values()),
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
        sections_by_role: dict[str, list[dict[str, Any]]] = {}
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
                sections_by_role.setdefault(
                    document["role"], []).append(section)
        kernel = self._kernel(sections_by_role)
        # The §11 index is built after the kernel so each
        # record's derived priority can see kernel membership.
        kernel_keys = {
            (row["role"], row["section_id"])
            for row in kernel["sources"]}
        for document in config["documents"]:
            for section in sections_by_role.get(document["role"], []):
                role = document["role"]
                index.append({
                    "role": role,
                    "document": role,
                    "section_id": section["section_id"],
                    "section": section["section_id"],
                    "stable_id": stable_section_id(
                        role, section["section_id"]),
                    "heading": section["heading"],
                    "level": section["level"],
                    "estimated_tokens": _estimate_tokens(section["text"]),
                    "text": section["text"],
                    "content": section["text"],
                    "priority": section_priority(
                        role, section["heading"],
                        in_kernel=(role, section["section_id"])
                        in kernel_keys,
                        authored=section.get("authored_priority")),
                    "priority_level": priority_level(
                        role, section["heading"],
                        in_kernel=(role, section["section_id"])
                        in kernel_keys,
                        authored=section.get("authored_priority")),
                    "priority_authored":
                        section.get("authored_priority") is not None,
                })
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
    def _kernel(
            sections_by_role: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Layer A: the §9 kernel, from the §9 source mix.

        Candidates stand in the roadmap's formula order —
        core, relationship, service bible, tool policy — in
        document order within each role. Core candidates are
        the §5 kernel-marked sections (the core document's
        leading sections when none are marked); the other
        roles contribute only their rule/boundary-marked
        sections (``kernel_source_kind``). Whole sections
        only, under the §5 ceiling: a candidate that would
        overflow is skipped so a later small critical
        boundary can still fit — except P0 material (§16),
        which is never evicted merely to save tokens and is
        picked even past the ceiling; at least one section
        is always included, so a single oversized section
        surfaces as an over-band kernel rather than an
        empty one. The kernel records its provenance and
        the §10 pinning spec it is compiled under.
        """
        candidates: list[tuple[str, str, dict[str, Any]]] = []
        for role in KERNEL_SOURCE_ORDER:
            sections = sections_by_role.get(role, [])
            marked = [
                section for section in sections
                if kernel_source_kind(role, section["heading"])
                is not None
            ]
            if role == "core" and not marked:
                marked = list(sections)
            for section in marked:
                kind = kernel_source_kind(role, section["heading"])
                candidates.append((
                    role, kind or "core", section))
        picked: list[tuple[str, str, dict[str, Any]]] = []
        total = 0
        for role, kind, section in candidates:
            tokens = _estimate_tokens(section["text"])
            # §16: P0 material is never evicted from the
            # kernel merely to save tokens — a P0 candidate
            # is picked even past the §5 ceiling, and the
            # kernel then surfaces over-band, honestly.
            level = priority_level(
                role, section["heading"], in_kernel=True,
                authored=section.get("authored_priority"))
            if picked and total + tokens > KERNEL_TOKEN_MAX \
                    and level != "P0":
                continue
            picked.append((role, kind, section))
            total += tokens
        picked_sections = [section for _, _, section in picked]
        text = "\n\n".join(
            section["text"] for section in picked_sections)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        sources = [{
            "role": role, "kind": kind,
            "section_id": section["section_id"],
        } for role, kind, section in picked]
        source_counts = {
            kind: sum(1 for row in sources if row["kind"] == kind)
            for kind in kernel_source_kinds()
        }
        return {
            "section_ids": [s["section_id"] for s in picked_sections],
            "stable_ids": [
                stable_section_id(role, section["section_id"])
                for role, _, section in picked],
            "sources": sources,
            "source_counts": source_counts,
            "text": text,
            "estimated_tokens": _estimate_tokens(text),
            "within_band": KERNEL_TOKEN_MIN <= _estimate_tokens(text)
            <= KERNEL_TOKEN_MAX,
            "sha256": digest,
            "pinning": {
                "order": list(PINNING_ORDER),
                "position": list(PINNING_ORDER).index("persona_kernel"),
                "kernel_precedes_context": True,
                "buried_in_retrieved_memory": False,
                "kernel_hash": digest,
                "stable_for_identical_documents": True,
                "enforced_by": "prompt_assembly (§53, later section)",
            },
        }

    @staticmethod
    def _persona_hash(documents: list[dict[str, Any]],
                      kernel: dict[str, Any]) -> str:
        payload = "|".join(
            f"{doc['role']}:{doc['sha256']}" for doc in documents)
        payload += f"|kernel:{kernel['sha256']}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PersonaRetriever:
    """Explicit §13 retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and ranks its index. No hook, no per-message
    call, no injection — routing (§14) and budgeting (§15)
    decide what any caller does with the results.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_sections(
            compiled["index"], query=query, task_text=task_text,
            limit=limit)


class PersonaRouter:
    """Explicit §14 routing over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and routes its index. With no persona config the
    route still names its task and tags, with nothing
    required. No hook, no per-message call, no injection —
    budgeting (§15) and prompt assembly (§53) decide what a
    caller does with the required sections.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def route(self, user_message: str = "", current_task: str = "",
              active_project: str = "", tool_intent: str = "",
              conversation_state: str = "",
              limit: int = ROUTER_DEFAULT_LIMIT) -> dict[str, Any]:
        compiled = self._compiler.compile()
        if compiled is None:
            empty = route_sections(
                [], user_message=user_message,
                current_task=current_task, active_project=active_project,
                tool_intent=tool_intent,
                conversation_state=conversation_state, limit=limit)
            empty["persona_id"] = None
            return empty
        result = route_sections(
            compiled["index"], user_message=user_message,
            current_task=current_task, active_project=active_project,
            tool_intent=tool_intent, conversation_state=conversation_state,
            limit=limit)
        result["persona_id"] = compiled["persona_id"]
        return result


class PersonaContextBudgeter:
    """Explicit §15 budgeting over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and budgets: the compiled kernel as the single
    persona-kernel item, the §14 route's required sections
    (or an explicit §13 retrieval result list) as persona
    retrieval items, and caller-supplied memory / project
    items under their own categories. With no persona config
    the caller items are still budgeted and ``persona_id``
    is None. No hook, no per-message call, no injection, no
    prompt assembly (§53).
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def budget(self, route: dict[str, Any] | None = None,
               retrieval: list[dict[str, Any]] | None = None,
               memories: list[dict[str, Any]] | None = None,
               project_state: list[dict[str, Any]] | None = None,
               context_class: str = "standard",
               budgets: dict[str, Any] | None = None
               ) -> dict[str, Any]:
        compiled = self._compiler.compile()
        items: list[dict[str, Any]] = []
        persona_id = None
        if compiled is not None:
            persona_id = compiled["persona_id"]
            kernel = compiled["kernel"]
            by_id = {
                entry.get(
                    "stable_id",
                    stable_section_id(entry["role"], entry["section_id"])):
                entry for entry in compiled["index"]
            }
            # §16: the kernel item carries P0 when any kernel
            # section is P0, so the budgeter never evicts it
            # merely to save tokens.
            kernel_level = "P0" if any(
                by_id[sid].get("priority_level") == "P0"
                for sid in kernel["stable_ids"] if sid in by_id
            ) else "P1"
            items.append({
                "id": "persona_kernel",
                "category": "persona_kernel",
                "estimated_tokens": kernel["estimated_tokens"],
                "priority": 0.90, "score": 0.90,
                "priority_level": kernel_level,
            })
            rows: list[dict[str, Any]] = []
            if route is not None:
                rows = list(route.get("sections") or [])
            elif retrieval is not None:
                rows = list(retrieval)
            for row in rows:
                stable_id = row.get("stable_id")
                entry = by_id.get(stable_id or "")
                if entry is None:
                    continue
                score = row.get("score") or {}
                items.append({
                    "id": stable_id,
                    "category": "persona_retrieval",
                    "estimated_tokens": entry["estimated_tokens"],
                    "priority": float(
                        row.get("priority", entry["priority"])),
                    "score": float(score.get("total", 0.0))
                    if isinstance(score, dict) else 0.0,
                    "priority_level": entry.get("priority_level"),
                })
        for raw, category in (
                (memories, "relevant_memories"),
                (project_state, "project_state")):
            for entry in (raw or []):
                if not isinstance(entry, dict):
                    raise PersonaRuntimeError(
                        "budget item must be a mapping")
                items.append({**entry, "category": category,
                              "id": entry.get("id")})
        result = budget_items(
            items, context_class=context_class, budgets=budgets)
        result["persona_id"] = persona_id
        return result


class PersonaRuntimeBridge:
    """Surface the compiled persona's identity, counts only.

    No session hook — compilation is an explicit call (§6).
    The packet item is content-bearing only and carries no
    persona text: Layer A injection into prompt assembly,
    Layer B retrieval, and Layer C use are later roadmap
    sections (§15, §53), not this slice.
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
        counts = kernel["source_counts"]
        content = (
            f"Persona runtime (§§3-16): persona "
            f"{compiled['persona_id']} compiled from "
            f"{len(compiled['documents'])} documents / "
            f"{len(compiled['index'])} sections; kernel "
            f"{kernel['sha256'][:12]} "
            f"({kernel['estimated_tokens']} estimated tokens, "
            f"{'within' if kernel['within_band'] else 'outside'} "
            f"the §5 band) from the §9 mix — core "
            f"{counts['core']}, relationship rules "
            f"{counts['relationship_rule']}, service rules "
            f"{counts['service_rule']}, tool boundaries "
            f"{counts['tool_boundary']} — pinned at position "
            f"{kernel['pinning']['position']} of the §10 order; "
            f"PersonaIR hash "
            f"{compiled['ir']['ir_hash'][:12]} with {populated} "
            f"of {len(compiled['ir']['categories'])} categories "
            f"populated; persona hash "
            f"{compiled['persona_hash'][:12]}. Every section "
            f"carries a §12 stable id (role.section) and a "
            f"derived §11 priority. §13 hybrid retrieval is "
            f"explicit-only over those stable ids (keyword, "
            f"role, tags, task classification, priority; the "
            f"semantic component is unavailable — no embedding "
            f"surface is owned). §14 routing is explicit-only: "
            f"PersonaRouter decides the required sections for a "
            f"task from its five inputs, named by stable id. "
            f"§15 budgeting is explicit-only: "
            f"PersonaContextBudgeter trims kernel, retrieval, "
            f"memory, and project items to configurable "
            f"per-category allocations scaled by model context "
            f"class, whole items only in priority order. "
            f"§16 priority: every section carries a P0-P4 "
            f"level (authored by a trailing heading marker "
            f"where present, otherwise derived), and P0 "
            f"material is never evicted from the kernel or "
            f"the kernel budget merely to save tokens. "
            f"Canonical document "
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
    "KERNEL_SOURCE_ORDER",
    "KERNEL_TOKEN_MIN",
    "KERNEL_TOKEN_MAX",
    "PINNING_ORDER",
    "RULE_HEADING_WORDS",
    "PersonaRuntimeError",
    "PersonaConfigStore",
    "PersonaCompiler",
    "PersonaRetriever",
    "PersonaRouter",
    "PersonaContextBudgeter",
    "BUDGET_CATEGORIES",
    "CONTEXT_CLASSES",
    "SUGGESTED_BUDGETS",
    "PersonaRuntimeBridge",
    "ROUTER_DEFAULT_LIMIT",
    "ROUTER_INPUTS",
    "ROUTER_MAX_LIMIT",
    "ROUTER_PER_TAG_LIMIT",
    "TASK_TAGS",
    "build_persona_ir",
    "classify_section",
    "classify_task",
    "core_roles",
    "display_heading",
    "ir_categories",
    "kernel_source_kind",
    "kernel_source_kinds",
    "hybrid_components",
    "parse_sections",
    "retrieval_score",
    "retrieve_sections",
    "route_sections",
    "route_task_label",
    "router_inputs",
    "budget_allocations",
    "budget_categories",
    "budget_items",
    "context_classes",
    "suggested_budgets",
    "section_priority",
    "PRIORITY_LEVELS",
    "authored_priority_level",
    "priority_level",
    "priority_level_score",
    "priority_levels",
    "section_tags",
    "stable_section_id",
    "task_tags",
]
