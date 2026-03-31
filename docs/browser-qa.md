# Browser QA flow for app.tundralis.com

Use this when validating the live app through the Windows browser node.

## Auth

Local source of truth for automation:
- `secrets/.env.local`

Load secrets into a command:

```bash
./scripts/load-local-secrets.sh env | grep TUNDRALIS_BASIC_AUTH
```

For direct authenticated browser navigation, the current working pattern is embedding basic auth in the URL:

```text
https://<user>:<pass>@app.tundralis.com
```

## What is currently confirmed

As of 2026-03-29:
- Windows browser node can attach to Chrome successfully.
- Direct authenticated navigate works.
- Live DOM snapshot works after authenticated navigate.
- The live app shell loads with title `tundralis · KDA upload`.

## What is currently flaky

The issue appears to be browser-proxy/tooling reliability, not app auth itself.

Observed behavior on the Windows node browser proxy:
- screenshot requests can time out on the authenticated Tundralis page even when snapshot/evaluate succeed
- click actions are semi-reliable; some failures appear to be post-click wait/settling behavior rather than true click misses
- file upload path resolution requires a Windows-local OpenClaw uploads directory, not a Linux workspace path

This means:
- authenticated page-load verification is trustworthy
- DOM inspection via snapshot/evaluate is trustworthy
- full end-to-end live upload automation is not yet fully trustworthy from the current node/browser proxy path without a Windows-local upload staging step

## Action reliability notes

### Reliable now
- `snapshot`
- `evaluate`
- authenticated `navigate`

### Semi-reliable now
- `click`
  - may report timeout even when the click actually fired
  - prefer validating post-click state with `snapshot` or `evaluate`

### Least reliable now
- `screenshot` on the authenticated Tundralis page
- `upload` unless the file is staged into the Windows node's OpenClaw uploads directory first

## Recommended live QA sequence

1. Start/confirm Windows Chrome is attached via OpenClaw browser status.
2. Navigate with embedded basic auth.
3. Use snapshot or evaluate to confirm the real page title/headings loaded.
4. For click actions, verify the resulting DOM state instead of trusting the raw click return by itself.
5. For uploads, stage the file into the Windows node's OpenClaw uploads directory first, then use `browser upload` against that Windows-local path.
6. If upload/click automation still fails, treat that as a node browser tooling issue unless the app also fails in a manual browser session.

## Dependable action pattern

For remote/node browser work, prefer this sequence:

1. `navigate`
2. `snapshot` or `evaluate`
3. `click`
4. immediate `snapshot` or `evaluate` to verify post-click state

Example post-click verification signals:
- alerts/toasts appeared
- title changed
- URL changed
- expected DOM node exists
- button disabled/enabled state changed

## Upload staging note

`browser upload` must use a path local to the Windows node, not a Linux workspace path.

Observed required path shape on the node:

```text
C:\Users\ClawDaddy\AppData\Local\Temp\openclaw\uploads\...
```

So a dependable end-to-end upload flow needs a Windows-side staging step before calling `browser upload`.

## Next debugging target

If we want fully reliable automation here, debug the Windows browser proxy path separately from Tundralis:
- screenshot timeout behavior when the page is authenticated
- click return semantics vs actual click success
- Windows-local upload staging / transfer path for `browser upload`
