#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import base64
import mimetypes

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'data' / 'fixtures' / 'client_style_kda.csv'
ENV_LOCAL = ROOT / 'secrets' / '.env.local'


def read_basic_auth() -> tuple[str, str]:
    text = ENV_LOCAL.read_text(encoding='utf-8')
    env = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        env[k] = v.strip().strip('"').strip("'")
    user = env.get('TUNDRALIS_BASIC_AUTH_USER')
    pw = env.get('TUNDRALIS_BASIC_AUTH_PASS')
    if not user or not pw:
        raise SystemExit('Missing TUNDRALIS_BASIC_AUTH_USER/PASS in secrets/.env.local')
    return user, pw


def auth_header(user: str, pw: str) -> dict[str, str]:
    token = base64.b64encode(f'{user}:{pw}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


def encode_multipart(fields: list[tuple[str, str]], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = '----TundralisSmokeBoundary7MA4YWxkTrZu0gW'
    lines: list[bytes] = []
    for name, value in fields:
        lines.extend([
            f'--{boundary}'.encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b'',
            value.encode('utf-8'),
        ])
    content_type = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'
    lines.extend([
        f'--{boundary}'.encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"'.encode(),
        f'Content-Type: {content_type}'.encode(),
        b'',
        file_path.read_bytes(),
    ])
    lines.extend([
        f'--{boundary}--'.encode(),
        b'',
    ])
    body = b'\r\n'.join(lines)
    return body, boundary


def request(url: str, *, method: str = 'GET', headers: dict[str, str] | None = None, data: bytes | None = None) -> tuple[int, str]:
    req = Request(url, method=method, headers=headers or {}, data=data)
    with urlopen(req, timeout=120) as resp:
        return resp.getcode(), resp.read().decode('utf-8', errors='replace')


def main() -> int:
    parser = argparse.ArgumentParser(description='Live smoke for recommended-run golden path.')
    parser.add_argument('--base-url', default='https://app.tundralis.com')
    parser.add_argument('--timeout-seconds', type=int, default=90)
    args = parser.parse_args()

    user, pw = read_basic_auth()
    auth = auth_header(user, pw)

    body, boundary = encode_multipart([], 'survey_file', FIXTURE)
    upload_headers = {
        **auth,
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    }
    code, upload_text = request(urljoin(args.base_url, '/upload'), method='POST', headers=upload_headers, data=body)
    if code != 200:
        raise SystemExit(f'Upload failed: {code} {upload_text[:400]}')
    payload = json.loads(upload_text)
    job_id = payload['job_id']
    filename = payload['filename']

    code, mapping_html = request(urljoin(args.base_url, f'/mapping/{job_id}'), headers=auth)
    if code != 200:
        raise SystemExit(f'Mapping page failed: {code}')
    for marker in ['Run KDA with recommended setup', 'Review your analysis setup', 'client_style_kda.csv']:
        if marker not in mapping_html:
            raise SystemExit(f'Mapping page missing marker: {marker}')

    fields = [
        ('job_id', job_id),
        ('filename', filename),
        ('target_column', 'overall_sat'),
        ('segment_columns', 'survey_wave'),
        ('segment_columns', 'region'),
        ('segment_columns', 'segment'),
        ('segment_definitions', '[]'),
        ('recode_definitions', '[]'),
        ('semantic_overrides', '{}'),
        ('display_name__overall_sat', 'Overall Sat'),
        ('display_name__product_quality_score', 'Product Quality Score'),
        ('display_name__value_for_money', 'Value For Money'),
        ('display_name__acct_mgmt_score', 'Acct Mgmt Score'),
        ('display_name__ease_use_score', 'Ease Use Score'),
        ('display_name__integration_setup', 'Integration Setup'),
        ('display_name__mobile_app_score', 'Mobile App Score'),
        ('display_name__onboarding_score', 'Onboarding Score'),
        ('display_name__reporting_tools', 'Reporting Tools'),
        ('display_name__service_reliability', 'Service Reliability'),
        ('display_name__support_experience', 'Support Experience'),
    ]
    predictors = [
        'product_quality_score', 'value_for_money', 'acct_mgmt_score', 'ease_use_score', 'integration_setup',
        'mobile_app_score', 'onboarding_score', 'reporting_tools', 'service_reliability', 'support_experience',
    ]
    fields.extend([('predictor_columns', p) for p in predictors])
    run_body, run_boundary = encode_multipart(fields, 'noop_file', FIXTURE)
    run_body = run_body.replace(
        f'name="noop_file"; filename="{FIXTURE.name}"'.encode(),
        f'name="predictor_columns"; filename="{FIXTURE.name}"'.encode(),
        1,
    )
    # rebuild correctly without accidental extra file field by using multipart helper trick-free on retry path below
    run_lines = []
    boundary = '----TundralisRunBoundary7MA4YWxkTrZu0gW'
    for name, value in fields:
        run_lines.extend([
            f'--{boundary}'.encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b'',
            value.encode('utf-8'),
        ])
    run_lines.extend([f'--{boundary}--'.encode(), b''])
    run_payload = b'\r\n'.join(run_lines)
    run_headers = {**auth, 'Content-Type': f'multipart/form-data; boundary={boundary}'}
    code, run_html = request(urljoin(args.base_url, '/run'), method='POST', headers=run_headers, data=run_payload)
    if code != 200 or 'Analysis complete' not in run_html:
        raise SystemExit(f'Run failed: code={code}')

    deadline = time.time() + args.timeout_seconds
    results_url = urljoin(args.base_url, f'/results/{job_id}')
    while time.time() < deadline:
        code, results_html = request(results_url, headers=auth)
        if code == 200 and all(x in results_html for x in ['Analysis complete', 'Decision summary', 'Download report', 'Download JSON']):
            print(json.dumps({'ok': True, 'job_id': job_id, 'results_url': results_url}))
            return 0
        time.sleep(2)

    raise SystemExit(f'Results never became ready for {job_id}')


if __name__ == '__main__':
    raise SystemExit(main())
