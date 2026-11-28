"""Apply the Wenyi 5xx probe fix by exact text replacement (no git apply needed).

Run from the cloned Wenyi repo root:
    python apply_fix.py
"""
from pathlib import Path
import sys

CONNECTIVITY = Path("packages/core/wenyi_core/llm/connectivity.py")
TESTS = Path("packages/core/tests/test_llm_connectivity.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        print(f"ERROR [{label}]: expected exactly 1 match, found {n}", file=sys.stderr)
        sys.exit(1)
    return text.replace(old, new, 1)


# --- connectivity.py -------------------------------------------------------
c = CONNECTIVITY.read_text(encoding="utf-8")

c = replace_once(
    c,
    "from .retrying import EmptyResponseError, TruncatedResponseError",
    """from .retrying import (
    EmptyResponseError,
    RetryReporter,
    TruncatedResponseError,
    provider_retry,
)""",
    "connectivity import",
)

c = replace_once(
    c,
    "MAX_PROBE_WORKERS = 8",
    """# Connectivity checks must not hammer a shared upstream account pool in parallel.
# Some gateways reject concurrent requests with transient 5xx ("provider cooling down")
# even though each request succeeds on its own. Sequential probes avoid that false
# negative while still using the SDK's zero internal retries (no nested retries).
MAX_PROBE_WORKERS = 1
# Number of immediate retries a probe performs for transient upstream failures (5xx,
# connection resets, timeouts). Permanent errors (401/403/404) still fail fast.
PROBE_MAX_RETRIES = 2
PROBE_RETRY_WAIT_SECONDS = 0.5""",
    "probe constants",
)

c = replace_once(
    c,
    '''    """Send one minimal, non-retried request per profile; results keep the input order.

    Each probe bills a few tokens. Usage is not recorded in any run ledger, and failures are
    reduced to the provider-independent categories from ``describe_provider_failure``.
    """''',
    '''    """Send one minimal probe per profile; results keep the input order.

    Probes run sequentially and retry only transient upstream failures (bounded by
    ``PROBE_MAX_RETRIES``) so a cooling account pool does not cause false negatives.
    Each successful probe bills a few tokens. Usage is not recorded in any run ledger,
    and failures are reduced to the provider-independent categories from
    ``describe_provider_failure``.
    """''',
    "_probe_all docstring",
)

c = replace_once(
    c,
    '''        attempt_scope=nullcontext,
    )
    started = time.monotonic()
    try:
        adapter.generate(
            [dict(message) for message in PROBE_MESSAGES],
            request_model,
            json_mode=False,
            context=context,
        )
    except _REACHABLE_RESPONSES:
        return result(
            True,
            "reachable",
            "The provider accepted the request; the reply was empty or truncated.",
            latency_ms=_elapsed_ms(started),
        )
    except Exception as error:  # noqa: BLE001 - Every failure becomes a safe probe result.
        failure = describe_provider_failure(error)
        return result(
            False,
            failure.category,
            failure.message,
            status_code=failure.status_code,
            latency_ms=_elapsed_ms(started),
        )
    return result(True, "ok", "The provider replied.", latency_ms=_elapsed_ms(started))''',
    '''        attempt_scope=nullcontext,
    )
    reachable_without_text = False

    def attempt_call() -> None:
        nonlocal reachable_without_text
        # An empty or truncated reply still proves connectivity; treat it as an
        # immediate success so the retry helper never re-sends a reachable probe.
        try:
            adapter.generate(
                [dict(message) for message in PROBE_MESSAGES],
                request_model,
                json_mode=False,
                context=context,
            )
        except _REACHABLE_RESPONSES:
            reachable_without_text = True

    # Some gateways serve a shared account pool that rejects bursts with transient
    # 5xx responses. Retry those a few times with a short, bounded wait so a single
    # cooling account does not produce a false "provider unavailable" verdict.
    # Permanent errors (401/403/404/...) still fail fast via retry_reason().
    reporter = RetryReporter(
        provider=route.provider,
        profile=route.profile,
        stage=route.operation,
        max_attempts=PROBE_MAX_RETRIES + 1,
        emit=lambda event, **data: None,
    )
    guarded = provider_retry(
        PROBE_MAX_RETRIES,
        reporter,
        sleep=lambda seconds: time.sleep(min(seconds, PROBE_RETRY_WAIT_SECONDS)),
    )(attempt_call)

    started = time.monotonic()
    try:
        guarded()
    except Exception as error:  # noqa: BLE001 - Every failure becomes a safe probe result.
        failure = describe_provider_failure(error)
        return result(
            False,
            failure.category,
            failure.message,
            status_code=failure.status_code,
            latency_ms=_elapsed_ms(started),
        )
    if reachable_without_text:
        return result(
            True,
            "reachable",
            "The provider accepted the request; the reply was empty or truncated.",
            latency_ms=_elapsed_ms(started),
        )
    return result(True, "ok", "The provider replied.", latency_ms=_elapsed_ms(started))''',
    "_probe body",
)

CONNECTIVITY.write_text(c, encoding="utf-8")
print("patched", CONNECTIVITY)

# --- tests -----------------------------------------------------------------
t = TESTS.read_text(encoding="utf-8")

t = replace_once(
    t,
    """from wenyi_core.llm.connectivity import (
    PROBE_OUTPUT_TOKENS,""",
    """from wenyi_core.llm.connectivity import (
    PROBE_MAX_RETRIES,
    PROBE_OUTPUT_TOKENS,""",
    "tests import",
)

t = replace_once(
    t,
    """        if isinstance(behavior, Exception):
            raise behavior
        return behavior""",
    """        if isinstance(behavior, Exception):
            raise behavior
        # A callable behavior models a stateful/flaky endpoint across probe retries.
        if callable(behavior):
            return behavior(**kwargs)
        return behavior""",
    "tests fixture callable",
)

t = replace_once(
    t,
    """    # Probes never retry and never wait the full workflow timeout.
    assert sdk.clients == [{"timeout": 5, "max_retries": 0}] * 2""",
    """    # The SDK's internal retries stay off (no nested retry); transient failures are
    # retried by the shared probe helper instead.
    assert sdk.clients == [{"timeout": 5, "max_retries": 0}] * 2""",
    "tests client assertion",
)

t = replace_once(
    t,
    '''def test_transient_failures_are_not_retried(sdk):
    sdk.behaviors["big"] = _status_error(503)
    [result] = probe_connections(_config(), ("translation.body",))
    assert result.category == "provider_unavailable"
    assert len(sdk.calls) == 1''',
    '''def test_transient_failures_are_retried_then_reported(sdk):
    sdk.behaviors["big"] = _status_error(503)
    [result] = probe_connections(_config(), ("translation.body",))
    assert result.category == "provider_unavailable"
    assert len(sdk.calls) == PROBE_MAX_RETRIES + 1


def test_transient_5xx_then_success_is_reachable(sdk):
    """A transient 5xx burst followed by a good reply must not fail the probe."""
    state = {"n": 0}
    good = _response()

    def flaky(**kwargs):
        state["n"] += 1
        if state["n"] <= PROBE_MAX_RETRIES:
            raise _status_error(503)
        return good

    sdk.behaviors["big"] = flaky
    [result] = probe_connections(_config(), ("translation.body",))
    assert result.ok and result.category == "ok"
    assert state["n"] == PROBE_MAX_RETRIES + 1''',
    "tests 503 case",
)

TESTS.write_text(t, encoding="utf-8")
print("patched", TESTS)
print("ALL PATCHES APPLIED CLEANLY")
