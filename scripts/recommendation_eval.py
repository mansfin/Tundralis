from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tundralis.app import _build_recommendation
from tundralis.prep import build_prep_bundle
CASE_PATH = ROOT / "data" / "fixtures" / "recommendation_eval_cases.json"


def evaluate_case(case: dict) -> dict:
    bundle = build_prep_bundle(ROOT / case["csv"])
    df = bundle.working_df
    recommendation = _build_recommendation(
        list(df.columns),
        bundle.column_profiles,
        df.select_dtypes(include="number").columns.tolist(),
    )
    shortlist = [item["name"] for item in recommendation["predictors"]]
    excluded = {item["name"]: item for item in recommendation["excluded"]}
    meta_candidates = {item["name"]: item for item in recommendation.get("meta_candidates", [])}
    suppressed = set(excluded) | set(meta_candidates)
    must_include = case.get("must_include", [])
    must_exclude = case.get("must_exclude", [])
    must_surface_meta = case.get("must_surface_meta", [])

    include_hits = [name for name in must_include if name in shortlist]
    include_misses = [name for name in must_include if name not in shortlist]
    exclude_hits = [name for name in must_exclude if name in suppressed]
    exclude_misses = [name for name in must_exclude if name not in suppressed]
    meta_hits = [name for name in must_surface_meta if name in meta_candidates]
    meta_misses = [name for name in must_surface_meta if name not in meta_candidates]

    return {
        "name": case["name"],
        "target": recommendation["target"],
        "expected_target": case.get("expected_target"),
        "expected_schema_clarity": case.get("expected_schema_clarity"),
        "confidence": recommendation["confidence"],
        "schema_clarity": recommendation["schema_clarity"],
        "include_recall": len(include_hits) / max(len(must_include), 1),
        "exclude_recall": len(exclude_hits) / max(len(must_exclude), 1),
        "meta_recall": len(meta_hits) / max(len(must_surface_meta), 1),
        "include_hits": include_hits,
        "include_misses": include_misses,
        "exclude_hits": exclude_hits,
        "exclude_misses": exclude_misses,
        "shortlist": shortlist,
        "meta_hits": meta_hits,
        "meta_misses": meta_misses,
        "excluded_reasons": {name: (excluded.get(name) or meta_candidates.get(name) or {}).get("reasons", []) for name in exclude_hits},
    }


def main() -> int:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]

    avg_include = sum(r["include_recall"] for r in results) / len(results)
    avg_exclude = sum(r["exclude_recall"] for r in results) / len(results)

    print("Recommendation evaluation")
    print("=" * 80)
    for result in results:
        print(f"\n[{result['name']}]")
        print(f"target: {result['target']} (expected {result['expected_target']})")
        print(f"confidence: {result['confidence']} | schema: {result['schema_clarity']}")
        print(f"include recall: {result['include_recall']:.2f} | exclude recall: {result['exclude_recall']:.2f}")
        print("shortlist:", ", ".join(result["shortlist"][:12]))
        if result["include_misses"]:
            print("missing expected drivers:", ", ".join(result["include_misses"]))
        if result["exclude_misses"]:
            print("bad survivors:", ", ".join(result["exclude_misses"]))
        if result["meta_hits"] or result["meta_misses"]:
            print(f"meta recall: {result['meta_recall']:.2f}")
            if result["meta_misses"]:
                print("missing meta candidates:", ", ".join(result["meta_misses"]))

    print("\n" + "=" * 80)
    print(f"Average include recall: {avg_include:.2f}")
    print(f"Average exclude recall: {avg_exclude:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
