"""Ablation configuration and standard experiment profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping


@dataclass(frozen=True)
class AblationConfig:
    cognitive_detection: bool = True
    layer_diagnosis: bool = True
    ternary_feedback: bool = True
    adaptive_episodes: bool = True
    runtime_verification: bool = True
    knowledge_hints: bool = True
    comprehension_check: bool = True

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "AblationConfig":
        if values is None:
            return cls()
        unknown = set(values) - set(cls.__dataclass_fields__)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown ablation mechanisms: {names}")
        normalized = {}
        for name, value in values.items():
            if not isinstance(value, bool):
                raise TypeError(f"Ablation value for {name} must be a boolean")
            normalized[name] = value
        return cls(**normalized)

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)

    def with_disabled(self, *mechanisms: str) -> "AblationConfig":
        unknown = set(mechanisms) - set(self.__dataclass_fields__)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown ablation mechanisms: {names}")
        return replace(self, **dict.fromkeys(mechanisms, False))

    def process_guidance_enabled(self) -> bool:
        return any(
            (
                self.cognitive_detection,
                self.layer_diagnosis,
                self.ternary_feedback,
                self.adaptive_episodes,
            )
        )


MECHANISM_NAMES = tuple(AblationConfig.__dataclass_fields__)


def standard_ablation_profiles(
    include_additive: bool = False,
) -> dict[str, AblationConfig]:
    full = AblationConfig()
    base = AblationConfig(**dict.fromkeys(MECHANISM_NAMES, False))
    profiles = {"base": base, "full": full}
    for mechanism in MECHANISM_NAMES:
        profiles[f"full-minus-{mechanism.replace('_', '-')}"] = full.with_disabled(
            mechanism
        )
    if include_additive:
        for mechanism in MECHANISM_NAMES:
            profiles[f"base-plus-{mechanism.replace('_', '-')}"] = replace(
                base, **{mechanism: True}
            )
    return profiles


def resolve_ablation_profile(name: str) -> AblationConfig:
    profiles = standard_ablation_profiles(include_additive=True)
    try:
        return profiles[name]
    except KeyError as exc:
        choices = ", ".join(profiles)
        raise ValueError(
            f"Unknown ablation profile {name!r}; choose one of: {choices}"
        ) from exc
