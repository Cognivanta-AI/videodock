# Hermes Agent integration — proposed contract (not implemented)

## Goal

Hermes should be able to publish video outputs from any channel into VideoDock without SCP or Git commits containing large media. VideoDock separates channels from videos and supports browser playback/review.

## Architecture

```text
Hermes (render complete)
  -> POST /api/v1/videos/upload-intents  [agent token, metadata]
  -> PUT upload_url                  [presigned HTTPS upload to private S3/R2/MinIO]
  -> POST /api/v1/videos/{id}/complete
  -> GET /api/v1/videos               [authenticated dashboard]
  -> GET /api/v1/videos/{id}/playback [short-lived signed playback URL]
```

The static UI on GitHub Pages **cannot accept uploads or securely hold API credentials**. Build the ingestion/authentication backend separately (e.g. deployed via Coolify), and keep media in a private object-storage bucket. Access controls must apply to API data as well as media URLs. Configure API CORS to the actual approved frontend origins only.

## Data model

- `Channel`: `id`, `slug`, `name`, `created_at`
- `Video`: `id`, `channel_id`, `title`, `status`, `created_at`, `updated_at`, `duration_seconds`, `object_key`, `thumbnail_key`, `generation_cost_usd`, `source_agent`
- Status values: `rendering`, `review`, `approved`, `rejected`, `published`, `failed`

## Suggested API

### POST /api/v1/videos/upload-intents

Authenticated by a dedicated, revocable Hermes machine token (never expose in frontend).

Request:
```json
{
  "channel_slug": "curious-ancestors",
  "title": "How Humans Survived Before Fire",
  "filename": "final.mp4",
  "content_type": "video/mp4",
  "size_bytes": 150000000,
  "sha256": "<hex sha256>"
}
```

Response (201):
```json
{
  "id": "video-uuid",
  "upload_url": "https://private-object-store.example/signed-upload",
  "upload_headers": {"Content-Type":"video/mp4"},
  "expires_at": "2026-11-04T05:30:00Z"
}
```

### POST /api/v1/videos/{id}/complete

Verify object existence, expected length/hash if supported, then make the record visible in the dashboard. Reject unknown objects or unmatched channel IDs.

### GET /api/v1/channels / GET /api/v1/videos?channel_id=...

Requires dashboard session. Return paginated records; never return permanent public bucket URLs.

### GET /api/v1/videos/{id}/playback

Requires dashboard session. Returns short-lived read-only signed URL; renew on expiry.

### PATCH /api/v1/videos/{id}/status

Requires dashboard session with review permission. Prevent machine uploader from approving on behalf of a human reviewer.

## Operational requirements

1. Limit uploads by MIME/content inspection, byte size, quota, authenticated agent identity and per-channel scope.
2. Sanitize metadata and validate channel slugs (avoid path traversal and cross-channel access).
3. Rate-limit and log uploads; prefer resumable/multipart uploads for large MP4s.
4. Store secrets only as backend environment variables. Never commit keys or set `VITE_*` secrets.
5. Do not delete a local render until upload completion was verified.
6. Prefer idempotency keys and checksums so agent retries cannot duplicate videos.
7. Serve MP4 with byte-range support for seeking; private CORS and signed links must support browser playback.
8. Keep `review` distinct from `approved`; no automatic approval from Hermes.

## Future rollout

1. Implement private auth + backend + object store.
2. Wire the React UI to API endpoints, loading/error states and playback URLs.
3. Add upload jobs on Hermes and channel mapping.
4. Add human approval, comments, version history and retention rules.

The present repository only supplies the static demo and this handoff document; these endpoints are **not live**.
