#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'app_runtime'
UPLOADS = RUNTIME / 'uploads'
MAPPINGS = RUNTIME / 'mappings'
ARTIFACTS = RUNTIME / 'artifacts'
JOB_REGISTRY = RUNTIME / 'jobs.json'


def age_days(path: Path) -> float:
    return (time.time() - path.stat().st_mtime) / 86400


def job_id_from_upload(path: Path) -> str | None:
    name = path.name
    if '_' not in name:
        return None
    return name.split('_', 1)[0]


def safe_remove(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)


def load_jobs() -> list[dict]:
    if not JOB_REGISTRY.exists():
        return []
    try:
        payload = json.loads(JOB_REGISTRY.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def save_jobs(rows: list[dict], dry_run: bool) -> None:
    if dry_run:
        return
    JOB_REGISTRY.write_text(json.dumps(rows, indent=2), encoding='utf-8')


def mark_jobs_pruned(job_ids: set[str], dry_run: bool) -> None:
    if not job_ids:
        return
    rows = load_jobs()
    updated = False
    for row in rows:
        if row.get('job_id') in job_ids:
            row['artifacts_pruned'] = True
            row['results_url'] = None
            row['status'] = 'expired'
            updated = True
    if updated:
        save_jobs(rows, dry_run=dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description='Prune stale Tundralis runtime files safely.')
    parser.add_argument('--upload-max-age-days', type=float, default=7.0)
    parser.add_argument('--empty-artifact-max-age-days', type=float, default=1.0)
    parser.add_argument('--artifact-max-age-days', type=float, default=14.0)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    uploads_removed = []
    artifact_dirs_removed = []
    successful_artifact_dirs_removed = []

    for upload in sorted(UPLOADS.glob('*')):
        if not upload.is_file():
            continue
        job_id = job_id_from_upload(upload)
        upload_age = age_days(upload)
        mapping_exists = bool(job_id and (MAPPINGS / f'{job_id}.json').exists())
        artifact_dir = ARTIFACTS / job_id if job_id else None
        artifact_exists = bool(artifact_dir and artifact_dir.exists() and any(artifact_dir.iterdir()))
        if upload_age > args.upload_max_age_days and not mapping_exists and not artifact_exists:
            uploads_removed.append(upload)

    for artifact_dir in sorted(ARTIFACTS.glob('*')):
        if not artifact_dir.is_dir():
            continue
        children = list(artifact_dir.iterdir())
        if not children:
            if age_days(artifact_dir) > args.empty_artifact_max_age_days:
                artifact_dirs_removed.append(artifact_dir)
            continue
        if age_days(artifact_dir) <= args.artifact_max_age_days:
            continue
        if (artifact_dir / 'analysis_run.json').exists():
            successful_artifact_dirs_removed.append(artifact_dir)

    print(f'dry_run={args.dry_run}')
    print(f'uploads_to_remove={len(uploads_removed)}')
    for path in uploads_removed[:50]:
        print(f'  upload {path.relative_to(ROOT)} age_days={age_days(path):.2f}')
    if len(uploads_removed) > 50:
        print(f'  ... {len(uploads_removed)-50} more uploads')

    print(f'empty_artifact_dirs_to_remove={len(artifact_dirs_removed)}')
    for path in artifact_dirs_removed[:50]:
        print(f'  artifact_dir {path.relative_to(ROOT)} age_days={age_days(path):.2f}')
    if len(artifact_dirs_removed) > 50:
        print(f'  ... {len(artifact_dirs_removed)-50} more artifact dirs')

    print(f'successful_artifact_dirs_to_remove={len(successful_artifact_dirs_removed)}')
    for path in successful_artifact_dirs_removed[:50]:
        print(f'  successful_artifact_dir {path.relative_to(ROOT)} age_days={age_days(path):.2f}')
    if len(successful_artifact_dirs_removed) > 50:
        print(f'  ... {len(successful_artifact_dirs_removed)-50} more successful artifact dirs')

    for path in uploads_removed:
        safe_remove(path, args.dry_run)
    for path in artifact_dirs_removed:
        safe_remove(path, args.dry_run)
    for path in successful_artifact_dirs_removed:
        safe_remove(path, args.dry_run)

    mark_jobs_pruned({path.name for path in successful_artifact_dirs_removed}, dry_run=args.dry_run)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
