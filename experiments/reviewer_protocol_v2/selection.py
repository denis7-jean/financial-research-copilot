"""Approved fragments of future selection; incomplete procedure fails closed."""

from experiments.reviewer_protocol_v2.common import ProtocolError
from experiments.reviewer_protocol_v2.eligibility import STRATA

SEED = 20261001
STRATUM_ORDER = STRATA
BLOCKERS = (
    "Exact protocol-version literal, delimiter, escaping and UTF-8 ranking serialization are unspecified.",
    "Candidate scan/skip and cross-stratum conflict procedure is not completely specified.",
    "Opaque packet-ID generation and packet byte serialization are unspecified.",
)


def select(*args, **kwargs):
    raise ProtocolError("selection_disabled_pending_exact_approved_procedure")
