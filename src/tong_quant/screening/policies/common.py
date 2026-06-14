from tong_quant.screening.policies.base import ScreeningPolicy

COMMON_RISK_FLAGS = frozenset(
    {
        "fraud_risk",
        "delisting_risk",
        "qualified_audit_opinion",
        "missing_required_data",
    }
)


def with_unvalidated_thresholds(policy: ScreeningPolicy) -> ScreeningPolicy:
    """Make missing metrics fail without inventing production thresholds."""
    return policy
