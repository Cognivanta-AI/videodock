# VideoDock

**Private, multi-channel video review workspace for AI-assisted production.**

VideoDock is a lightweight dashboard for reviewing videos produced by agents such as Hermes. Organize productions by channel, inspect thumbnails and metadata, play MP4s in your browser, and track review status without downloading files over SCP.

## Status

Initial UI foundation (static demo). The interface is ready for GitHub Pages deployment after Pages is configured; **video ingestion, authentication, approvals and storage are not implemented yet**. Demo entries are clearly identified as sample data.

## Stack

- React + TypeScript + Vite
- Responsive, compact dashboard with per-channel filters, status and video playback
- GitHub Actions workflow to publish static assets to GitHub Pages
- External secure video storage anticipated (S3/R2/MinIO), not Git/GitHub Pages

## Quick start

```bash
npm install
npm run dev
npm run build
```

## GitHub Pages

The project is configured with base path `/videodock/`. In **Settings > Pages > Build and deployment**, select **GitHub Actions**. Pushes to `main` should trigger the deployment workflow.

> **Privacy warning:** GitHub Pages is not a private-video platform. Do not store private MP4 files, signing keys, access tokens or confidential production metadata in this repository or the static `public/` directory. Public Pages URLs must not be treated as authenticated.

## Hermes integration

The desired workflow is `Hermes -> authenticated ingestion API -> private object storage + database -> VideoDock`.

The ingestion API is **not implemented in this repository**. See [docs/HERMES-INTEGRATION.md](docs/HERMES-INTEGRATION.md) for a proposed versioned API contract and security requirements. A future backend can be deployed on Coolify without modifying the static page build.

## Repository structure

- `src/`: UI and demo data
- `docs/HERMES-INTEGRATION.md`: future upload/metadata/approval contract
- `.github/workflows/deploy-pages.yml`: Pages deployment
- `public/`: only public, non-sensitive static frontend assets

## Guiding principles

One workspace, many channels; explicit review states; readable desktop/mobile design; no upload via GitHub commits; do not pretend demo videos are real.
