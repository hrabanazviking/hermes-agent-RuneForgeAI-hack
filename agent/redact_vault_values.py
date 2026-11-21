"""Exact-value redaction of secrets that transited a server-side vault fill (browser_vault)
or a Secret Source apply pass.

Re-exported by ``agent.redact``; moved out of it by upstream, with the fork's
scope-aware registry (f286e20000) ported in at the v0.23.3 intake (2026-11-21).
"""

from __future__ import annotations

import threading

# ---------------------------------------------------------------------------
# Vault-value redaction registry (profile-scoped, bounded)
# ---------------------------------------------------------------------------
# Exact secret values that transited a server-side vault fill (browser_vault) or a Secret
# Source apply pass. Generic credential-shaped regexes cannot catch arbitrary values, so the
# acquisition path registers the exact bytes before they can reach model or user output, and
# every browser_* tool result (including browser_cdp Runtime.evaluate passthrough) is scrubbed
# against them before it can reach the model. Memory only: never persisted or logged. Keyed by
# profile home so a multiplex gateway never scrubs profile B's output with profile A's secrets
# (which would also confirm to B that the bytes exist), and bounded per profile: a fill-heavy
# session evicts its oldest entries rather than growing forever.
_VAULT_REDACTION_MAX_PER_PROFILE = 64
_VAULT_REDACTION_VALUES: dict = {}  # profile home → ordered {value: None}
_VAULT_REDACTION_LOCK = threading.Lock()


def _vault_scope(scope=None) -> str:
    from hermes_constants import hermes_home_key
    return hermes_home_key(scope)


def register_vault_redaction_value(value, *, scope=None) -> None:
    """Register an exact vault secret value for model-facing redaction.

    Called by the vault fill path BEFORE the injection happens, so no later browser tool result
    can echo the value back into model context. Also registers the form a text input normalizes
    it to (CR/LF stripped), since that is what the page holds.
    """
    if not isinstance(value, str) or not value:
        return
    normalized = value.replace("\r", "").replace("\n", "")
    with _VAULT_REDACTION_LOCK:
        bucket = _VAULT_REDACTION_VALUES.setdefault(_vault_scope(scope), {})
        for v in (value, normalized):
            if v:
                bucket.pop(v, None)  # re-registering refreshes recency
                bucket[v] = None
        while len(bucket) > _VAULT_REDACTION_MAX_PER_PROFILE:
            del bucket[next(iter(bucket))]


def clear_vault_redaction_values(*, scope=None) -> None:
    """Drop the current profile's registered values (profile teardown / explicit lock)."""
    with _VAULT_REDACTION_LOCK:
        _VAULT_REDACTION_VALUES.pop(_vault_scope(scope), None)


def redact_registered_vault_values(text: str, *, scope=None) -> str:
    """Exact-substring scrub of every vault secret value registered for the current profile."""
    if not isinstance(text, str) or not text:
        return text
    with _VAULT_REDACTION_LOCK:
        bucket = _VAULT_REDACTION_VALUES.get(_vault_scope(scope))
        values = sorted(bucket, key=len, reverse=True) if bucket else ()  # longest first: a substring never shadows its superstring
    for value in values:
        if value in text:
            text = text.replace(value, "«redacted-vault-secret»")
    return text
