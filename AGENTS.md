# Instructions for Hermes Agent — VideoDock

VideoDock is a multichannel AI-video review dashboard. Repository: `Cognivanta-AI/videodock`.

## Protect the existing interface

Preserve the compact layout: left sidebar with channels, "Biblioteca de vídeos" header, channel selector, three KPI cards, compact recent-video list with thumbnails/status pills, and modal MP4 player. Maintain responsive behavior and the restrained white/slate visual system. Do not replace the established layout with a generic template.

## Implementation state

The current UI displays **demo data only**. No live upload API, storage, login or approval backend exists yet. Never claim a video was uploaded or approved based on sample rows. Frontend is React + TypeScript + Vite, configured for GitHub Pages under `/videodock/`.

## Hermes-to-VideoDock ingestion

Implement the backend contract in `docs/HERMES-INTEGRATION.md` before wiring automated uploads. Prefer authenticated API deployed in Coolify with private S3-compatible object storage (R2/MinIO/S3). Agent uploads go to the private backend via short-lived presigned URLs; browser receives short-lived playback URLs. Never commit MP4s to Git, embed secrets in a Vite build, or expose private videos through public GitHub Pages resources.

Each video belongs to a channel and has a review status and timestamps. Make channels configurable and searchable rather than hard-coding only sample channels. Preserve revision history and require explicit human review before marking approved.

## Operational delivery

- When changing frontend code, run `npm install`, `npm run check`, and `npm run build` before merging.
- Verify GitHub Pages configuration in repository settings; the workflow alone does not enable Pages.
- Validate mobile and desktop layout.
- Treat the dashboard as review tooling, not a public video publishing site.
- Document environment variables and API changes without adding credentials.
- Prioritize reliable upload completion, retry safety, browser seek support, and authenticated access.
