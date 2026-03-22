from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tundralis.profiling import profile_dataframe
from tundralis.segments import normalize_segment_definitions, preview_segments
from tundralis.transforms import apply_recode_transforms
from tundralis.utils import load_survey_data


@dataclass
class PrepBundle:
    raw_df: object
    working_df: object
    column_profiles: dict[str, dict]
    segment_previews: list[dict]
    normalized_segments: list[dict]


def build_prep_bundle(
    data_path: str | Path,
    *,
    recode_definitions: list[dict] | None = None,
    segment_definitions: list[dict] | None = None,
) -> PrepBundle:
    raw_df = load_survey_data(data_path)
    working_df = apply_recode_transforms(raw_df, recode_definitions or [])
    normalized_segments = normalize_segment_definitions(segment_definitions or [], working_df)
    return PrepBundle(
        raw_df=raw_df,
        working_df=working_df,
        column_profiles=profile_dataframe(working_df),
        segment_previews=preview_segments(working_df, normalized_segments),
        normalized_segments=normalized_segments,
    )
