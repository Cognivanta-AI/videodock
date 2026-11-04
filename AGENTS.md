# Instructions for agents — VideoDock

VideoDock is the **static, public multichannel review library** for agent-generated videos. Repo: `Cognivanta-AI/videodock`. The owner's current static-public direction supersedes the earlier proposed private-backend architecture.

## Preserve the interface and scope

Keep the existing React + TypeScript + Vite layout: channel sidebar, compact library header, search/channel selector, three KPI cards, thumbnail list, review-status pills and modal MP4 player. Preserve the white/slate identity and mobile behavior. Do not replace the design or install a template. No database, server, upload API, custom authentication, new rendering framework or YouTube embedding in this version. Do not modify the video-generation pipeline.

## Static catalog and media

- `public/data/videos.json` contains `{channels: [{id,name}], videos: [...]}`; every video refers to a configured channel. Never mix demos into live records.
- Media live at `public/videos/<channel>/<safe-unique-slug>/preview.mp4` and `thumbnail.jpg`.
- Catalog paths are relative to Vite's public base. Resolve with `import.meta.env.BASE_URL`; never bake an origin or `/videodock/` into media URLs. Vite's deployment base remains `/videodock/`.
- Use `scripts/publish-video.sh` for subsequent publications. It validates MP4s, preserves production originals, avoids duplicate hashes/overwrites, updates the catalog, builds and commits/pushes the publication. Read `docs/HERMES-INTEGRATION.md` for flags and recovery.
- Never stage unrelated work or secrets. A `.env` or a `VITE_*` secret must not enter the repository/build. Do not use Git LFS for Pages media.

## Review and privacy

Publication in this library is **not editorial approval**. New videos default to `review` (Em revisão). Never set `approved` based on a successful render, upload, build, playback or deploy. Only the owner approves image, voice, rhythm and continuation. No UI action automatically approves a production.

The owner authorized exposing this repository and its media publicly for GitHub Pages. Pages is not private storage, including when a source repository is private under a compatible paid plan. Warn before publishing sensitive content; public URLs, git history and downloaded copies cannot be made confidential by adding frontend authentication.

## Verification and limits

Before push: run `npm run check`, `npm test`, `npm run build`; validate JSON and exact media files. Check browser playback, pause, forward/back seek, thumbnail, channel/search filtering, deep link, loading/error feedback and desktop/mobile overflow. Confirm the original production file hash remains unchanged.

GitHub warns above50MiB and blocks above100MiB per ordinary Git file. This project adopts a stricter50MiB per-video cap and900MiB public-directory cap. Pages published site limit1GB; soft bandwidth100GB/month. History grows even after deleting a file. Propose external storage rather than forcing long/heavy videos into Git. Record source docs and revisit platform limits before scaling.

GitHub Pages must be enabled in repository settings with GitHub Actions source. Organization Free requires a public repository. If the GitHub App lacks administration/Pages permission, report the exact owner-side settings; never claim a deploy exists based only on a workflow file. Verify the remote commit, Actions outcome and live catalog/media URLs after every publication.
