"""
Short code generation utilities.

Approach A: random base62 code generation. Collision resistance is NOT
guaranteed here — the code space is large (62^7 ≈ 3.5 trillion) but the
birthday paradox means collisions still occur at non-trivial insert volumes.
The caller (service layer) is responsible for detecting and retrying on
collision; this module's only job is to produce a random candidate.
"""

import secrets
import string

from url_shortener.core.config import settings

# base62 alphabet: 0-9, a-z, A-Z (62 characters total)
_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase

def short_code_generator() -> str:
    """
    Generate a random base62 short code.

    We use `secrets.choice` instead of `random.choice` deliberately:
    `random` is a Mersenne Twister PRNG — fast, but predictable if an
    attacker observes enough outputs. `secrets` is built on the OS's
    cryptographically secure random source (os.urandom). For a
    resource identifier that's effectively public (anyone can guess/
    enumerate short codes), using a non-predictable generator is a
    correctness/security requirement, not just a nice-to-have —
    otherwise someone could guess upcoming codes or enumerate existing
    ones.

    This function does NOT check uniqueness. It is intentionally a pure,
    stateless function — uniqueness enforcement belongs at the database
    layer (unique constraint) plus a retry loop in the service layer.
    Mixing "generate" and "check if free" here would reintroduce the
    race condition we're trying to avoid (see service layer for why).
    """

    return "".join(secrets.choice(_ALPHABET) for _ in range(settings.DEFAULT_SHORT_CODE_LENGTH))