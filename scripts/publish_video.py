#!/usr/bin/env python3
"""Publish a local MP4 into VideoDock's static catalog; defaults to review."""
import argparse
from contextlib import contextmanager
import fcntl
from datetime import datetime, timezone

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

# Importing our local validator must not dirty a clean checkout.
sys.dont_write_bytecode = True
from validate_catalog import CatalogError, MAX_VIDEO_BYTES, SLUG, STATUSES, probe, require, timestamp, validate_catalog


def run(args, repo=None):
    result = subprocess.run(args, cwd=repo, capture_output=True, text=True)
    if result.returncode:
        raise CatalogError(f'{args[0]} failed: {result.stderr or result.stdout}')
    return result.stdout


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


@contextmanager
def prepared_media(args):
    require(shutil.which('ffprobe') is not None and shutil.which('ffmpeg') is not None, 'publishing requires FFmpeg and FFprobe; install them before uploading media')
    require(args.file.is_file(), 'source file does not exist')
    if not args.optimize:
        require(0 < args.file.stat().st_size <= MAX_VIDEO_BYTES, 'source exceeds 50 MiB; use --optimize')
        probe(args.file)
        yield args.file
    else:
        gitdir = Path(run(['git', 'rev-parse', '--absolute-git-dir'], args.repo).strip())
        with tempfile.TemporaryDirectory(prefix='videodock-', dir=gitdir) as tmp:
            output = Path(tmp) / 'optimized.mp4'
            run(['ffmpeg', '-v', 'error', '-i', str(args.file), '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(output)])
            require(0 < output.stat().st_size <= MAX_VIDEO_BYTES, 'optimized media exceeds 50 MiB')
            probe(output)
            yield output


def slugify(title):
    ascii_title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().lower()
    return re.sub('[^a-z0-9]+', '-', ascii_title).strip('-')[:100].rstrip('-') or 'video'


def atomic_catalog(path, content):
    fd, name = tempfile.mkstemp(prefix='.catalog-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def publish(args):
    repo = args.repo.resolve()
    require(SLUG.fullmatch(args.channel), 'invalid channel slug')
    require(bool(args.title.strip()), 'title is required')
    for path in (repo / 'public', repo / 'public/data', repo / 'public/data/videos.json', repo / 'public/videos', repo / 'public/videos' / args.channel):
        require(not path.is_symlink(), f'publisher output must not be symlinked: {path}')
    gitdir = Path(run(['git', 'rev-parse', '--absolute-git-dir'], repo).strip())
    with (gitdir / 'videodock-publish.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CatalogError('another publisher holds the lock') from exc
        require(not run(['git', 'status', '--porcelain', '--untracked-files=all'], repo), 'repository must be clean (including index and untracked files)')
        run(['git', 'var', 'GIT_AUTHOR_IDENT'], repo)
        run(['git', 'var', 'GIT_COMMITTER_IDENT'], repo)
        starting_head = run(['git', 'rev-parse', 'HEAD'], repo).strip()
        if not args.no_push:
            run(['git', 'remote', 'get-url', 'origin'], repo)
        catalog_path = repo / 'public/data/videos.json'
        original = catalog_path.read_bytes()
        created_dirs = []
        created_files = []
        try:
            with prepared_media(args) as source:
                return publish_locked(args, created_dirs, created_files, source)
        except BaseException:
            if run(['git', 'rev-parse', 'HEAD'], repo).strip() != starting_head:
                print('HEAD changed: retaining catalog/media and commit; inspect locally before retrying git push origin HEAD.', file=sys.stderr)
                raise
            # Only remove paths that this transaction created; never broad git clean/reset.
            if created_files:
                try:
                    run(['git', 'reset', '-q', 'HEAD', '--', 'public/data/videos.json', *[str(p.relative_to(repo)) for p in created_files]], repo)
                except (OSError, CatalogError) as reset_error:
                    print(f'Could not restore publication index paths; inspect Git index: {reset_error}', file=sys.stderr)
            if catalog_path.read_bytes() != original:
                atomic_catalog(catalog_path, original)
            for path in reversed(created_files):
                path.unlink(missing_ok=True)
            for path in reversed(created_dirs):
                try:
                    path.rmdir()
                except OSError:
                    pass
            raise


def publish_locked(args, created_dirs, created_files, source):
    repo = args.repo.resolve()
    root = repo / 'public'
    catalog_path = root / 'data/videos.json'
    catalog = json.loads(catalog_path.read_text())
    validate_catalog(catalog, root)
    if args.created_at:
        timestamp(args.created_at)
    source_hash = digest(source)
    input_hash = digest(args.file)
    channel = next((c for c in catalog['channels'] if c['id'] == args.channel), None)
    if channel is None:
        catalog['channels'].append({'id': args.channel, 'name': args.channel_name or args.channel.replace('-', ' ').title()})
    for video in catalog['videos']:
        if video['channel_id'] == args.channel:
            require(digest(root / video['video_path']) not in {source_hash, input_hash}, 'duplicate video hash within channel')
    video_id = slugify(args.title)
    ids = {v['id'] for v in catalog['videos']}
    if video_id in ids or (root / 'videos' / args.channel / video_id).exists():
        video_id += '-' + source_hash[:8]
    require(video_id not in ids, 'video id/hash collision')
    destination = root / 'videos' / args.channel / video_id
    for directory in (root / 'videos', destination.parent, destination):
        if not directory.exists():
            directory.mkdir()
            created_dirs.append(directory)
        elif directory == destination:
            raise CatalogError('destination already exists')
    media = destination / 'video.mp4'
    created_files.append(media)
    shutil.copyfile(source, media)
    metadata = probe(media)
    thumbnail = destination / 'thumbnail.jpg'
    created_files.append(thumbnail)
    run(['ffmpeg', '-v', 'error', '-ss', str(metadata['duration_seconds'] * .5), '-i', str(media), '-frames:v', '1', '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2', '-q:v', '3', str(thumbnail)])
    entry = dict(id=video_id, channel_id=args.channel, title=args.title, description=args.description, status=args.status, **metadata, video_path=media.relative_to(root).as_posix(), thumbnail_path=thumbnail.relative_to(root).as_posix(), generator=args.generator, style=args.style, created_at=args.created_at or datetime.now(timezone.utc).isoformat().replace('+00:00','Z'), sha256=digest(media), size_bytes=media.stat().st_size)
    catalog['videos'].append(entry)
    validate_catalog(catalog, root)
    atomic_catalog(catalog_path, (json.dumps(catalog, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode())
    run(['npm', 'run', 'check'], repo)
    run(['npm', 'run', 'build'], repo)
    paths = ['public/data/videos.json', str(media.relative_to(repo)), str(thumbnail.relative_to(repo))]
    changed = set(filter(None, run(['git', 'diff', '--name-only', '-z', 'HEAD'], repo).split('\0')))
    changed.update(filter(None, run(['git', 'ls-files', '--others', '--exclude-standard', '-z'], repo).split('\0')))
    require(changed <= set(paths), 'unrelated changes appeared during checks/build; refusing to stage or commit')
    require(not run(['git', 'diff', '--cached', '--name-only'], repo), 'unrelated staged changes appeared during checks/build')
    require(json.loads(catalog_path.read_text()) == catalog, 'checks/build modified catalog')
    require(digest(media) == source_hash, 'media changed during publication')
    validate_catalog(catalog, root)
    run(['git', 'add', '--', *paths], repo)
    staged = set(filter(None, run(['git', 'diff', '--cached', '--name-only', '-z'], repo).split('\0')))
    require(staged == set(paths), 'staged paths differ from explicit publication assets')
    if args.no_push:
        print(f'Staged {video_id} ({args.status}); no commit or push performed.')
    else:
        run(['git', 'commit', '--only', '-m', f'Publish video: {args.title}', '--', *paths], repo)
        run(['git', 'push', 'origin', 'HEAD'], repo)
        print(f'Published {video_id} ({args.status}) via git push origin HEAD.')
    return entry


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1], help=argparse.SUPPRESS)
    result.add_argument('--channel', required=True)
    result.add_argument('--channel-name')
    result.add_argument('--title', required=True)
    result.add_argument('--file', required=True, type=Path)
    result.add_argument('--status', choices=sorted(STATUSES), default='review')
    result.add_argument('--description', default='')
    result.add_argument('--created-at')
    result.add_argument('--generator', default='')
    result.add_argument('--style', default='')
    result.add_argument('--optimize', action='store_true', help='Encode a separate H.264 CRF20/AAC128k faststart copy; never modify the source')
    result.add_argument('--no-push', action='store_true', help='Run validation/check/build and stage only; do not commit or push')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        publish(args)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f'Publication failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
