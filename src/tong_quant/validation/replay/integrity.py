from tong_quant.validation.replay.models import ReplayValidationSample


def validate_replay_sample(sample: ReplayValidationSample) -> None:
    validation_sample = sample.validation_sample
    if validation_sample is None:
        return
    if validation_sample.research_report.available_at > sample.decision_as_of:
        raise ValueError("replay sample contains future research data")
    if validation_sample.outcome.available_at > sample.outcome_as_of:
        raise ValueError("replay sample contains future outcome data")
    if validation_sample.outcome.observed_at < sample.decision_as_of:
        raise ValueError("replay outcome precedes decision context")


__all__ = ["validate_replay_sample"]
