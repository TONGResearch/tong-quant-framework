from dataclasses import dataclass
from math import isfinite

from tong_quant.validation.models import OutcomeDefinition


@dataclass(frozen=True, slots=True)
class OutcomeDefinitionRegistry:
    definitions: tuple[OutcomeDefinition, ...]

    def __post_init__(self) -> None:
        identifiers = [definition.outcome_id for definition in self.definitions]
        if not identifiers or len(identifiers) != len(set(identifiers)):
            raise ValueError("outcome registry requires unique definitions")

    def get(self, outcome_id: str) -> OutcomeDefinition:
        matches = [
            definition
            for definition in self.definitions
            if definition.outcome_id == outcome_id
        ]
        if len(matches) != 1:
            raise KeyError(f"unknown outcome definition: {outcome_id}")
        return matches[0]

    def evaluate(self, outcome_id: str, value: float) -> bool:
        definition = self.get(outcome_id)
        for number in (value, definition.success_threshold):
            if type(number) not in (int, float):
                raise ValueError("outcome comparisons require finite built-in numbers")
            try:
                finite = isfinite(number)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("outcome comparisons require finite built-in numbers")
        return _compare(value, definition.success_operator, definition.success_threshold)


def _compare(value: float, operator: str, threshold: float) -> bool:
    operations = {
        "<": value < threshold,
        "<=": value <= threshold,
        ">": value > threshold,
        ">=": value >= threshold,
        "==": value == threshold,
        "!=": value != threshold,
    }
    return operations[operator]


__all__ = ["OutcomeDefinitionRegistry"]
