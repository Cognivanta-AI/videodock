#!/usr/bin/env python3
"""Validate the static VideoDock catalog and local asset safety (stdlib only)."""
import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_PUBLIC_BYTES = 900 * 1024 * 1024
MAX_THUMBNAIL_BYTES = 250 * 1024
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
STATUSES = {'review', 'rendering', 'approved', 'rejected', 'published', 'failed'}


class CatalogError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CatalogError(message)


def timestamp(value):
    require(isinstance(value, str), 'created_at must be an ISO date or timestamp')
    require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9]))?', value), 'invalid created_at')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(len(value) == 10 or parsed.tzinfo is not None, 'timestamp requires a timezone')
    except ValueError as exc:
        raise CatalogError('invalid created_at') from exc
    return value


def number(value, name):
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0, f'{name} must be finite and positive')
    maximum = {'duration_seconds': 86400, 'fps': 240}.get(name)
    if maximum is not None:
        require(value <= maximum, f'{name} must not exceed {maximum}')


def safe_path(value):
    require(isinstance(value, str) and bool(value), 'asset path must be a nonempty string')
    require(re.fullmatch(r'[a-zA-Z0-9_./-]+', value) and not value.startswith('/') and all(p not in ('', '.', '..') for p in value.split('/')), f'unsafe asset path: {value}')
    return value


def asset_path(root, value):
    safe_path(value)
    target = root / value
    require(target.resolve().is_relative_to(root.resolve()), f'asset escapes public: {value}')
    require(target.is_file(), f'missing asset: {value}')
    return target


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True)
    require(result.returncode == 0, f'invalid media: {result.stderr}')
    try:
        info = json.loads(result.stdout)
        stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
        if stream is None:
            raise CatalogError('no video stream')
        require(stream['codec_name'] == 'h264' and stream.get('pix_fmt') == 'yuv420p' and all(s.get('codec_name') == 'aac' for s in info['streams'] if s['codec_type'] == 'audio') and all(s['codec_type'] in ('video', 'audio') for s in info['streams']), 'unsupported media: use --optimize for H.264/yuv420p with AAC audio')
        require('mp4' in info['format']['format_name'].split(','), 'input must be MP4')
        metadata = {'duration_seconds': float(info['format']['duration']), 'resolution': f"{stream['width']}x{stream['height']}", 'fps': float(Fraction(stream['avg_frame_rate']))}
        for name in ('duration_seconds', 'fps'):
            number(metadata[name], name)
        for name in ('width', 'height'):
            number(stream[name], name)
        return metadata
    except (KeyError, TypeError, ZeroDivisionError, ValueError) as exc:
        raise CatalogError(f'invalid media metadata: {exc}') from exc


def validate_thumbnail(path):
    require(0 < path.stat().st_size <= MAX_THUMBNAIL_BYTES, 'thumbnail exceeds 250 KiB or is empty')
    data = path.read_bytes()
    require(data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9'), 'thumbnail must be a JPEG')
    result = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path), '-frames:v', '1', '-f', 'null', '-'], capture_output=True, text=True)
    require(result.returncode == 0, 'thumbnail is not a decodable JPEG')


def validate_catalog(catalog, public_root):
    root = Path(public_root)
    require(isinstance(catalog, dict) and isinstance(catalog.get('channels'), list) and isinstance(catalog.get('videos'), list), 'catalog requires channels and videos arrays')
    channels = set()
    for channel in catalog['channels']:
        require(isinstance(channel, dict), 'channel must be an object')
        ident = channel.get('id')
        require(isinstance(ident, str) and SLUG.fullmatch(ident), 'invalid channel id')
        require(ident not in channels, 'duplicate channel id')
        require(isinstance(channel.get('name'), str) and bool(channel['name'].strip()), 'channel name required')
        channels.add(ident)
    ids = set()
    for video in catalog['videos']:
        require(isinstance(video, dict), 'video must be an object')
        ident = video.get('id')
        require(isinstance(ident, str) and SLUG.fullmatch(ident), 'invalid video id')
        require(ident not in ids, 'duplicate video id')
        ids.add(ident)
        require(video.get('channel_id') in channels, 'unknown channel')
        for field in ('title', 'description', 'generator', 'style'):
            require(isinstance(video.get(field), str), f'{field} must be a string')
        require(bool(video['title'].strip()), 'title is required')
        require(video.get('status') in STATUSES, 'invalid status')
        timestamp(video.get('created_at'))
        number(video.get('duration_seconds'), 'duration_seconds')
        number(video.get('fps'), 'fps')
        resolution = video.get('resolution')
        require(isinstance(resolution, str) and re.fullmatch(r'[1-9][0-9]*x[1-9][0-9]*', resolution), 'resolution must be WIDTHxHEIGHT positive integer dimensions')
        video_path = safe_path(video.get('video_path'))
        thumbnail_path = safe_path(video.get('thumbnail_path'))
        prefix = f"videos/{video['channel_id']}/"
        require(video_path.startswith(prefix) and video_path.endswith('.mp4'), 'video must be a channel-local .mp4')
        require(thumbnail_path.startswith(prefix) and thumbnail_path.endswith(('.jpg', '.jpeg')), 'thumbnail must be a channel-local .jpg or .jpeg')
        media = asset_path(root, video_path)
        require(0 < media.stat().st_size <= MAX_VIDEO_BYTES, 'video exceeds 50 MiB or is empty')
        metadata = probe(media)
        require(metadata['resolution'] == resolution, 'resolution does not match media')
        require(math.isclose(metadata['fps'], video['fps'], abs_tol=0.01), 'fps does not match media')
        require(math.isclose(metadata['duration_seconds'], video['duration_seconds'], abs_tol=0.25), 'duration does not match media')
        validate_thumbnail(asset_path(root, thumbnail_path))
        if 'size_bytes' in video:
            require(type(video['size_bytes']) is int and video['size_bytes'] == media.stat().st_size, 'size_bytes mismatch')
        if 'sha256' in video:
            require(isinstance(video['sha256'], str) and re.fullmatch('[0-9a-f]{64}', video['sha256']), 'invalid sha256')
            with media.open('rb') as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == video['sha256'], 'sha256 mismatch')
    total = 0
    for path in root.rglob('*'):
        require(not path.is_symlink() or path.resolve().is_relative_to(root.resolve()), 'public symlink escapes root')
        if path.is_file():
            total += path.stat().st_size
    require(total <= MAX_PUBLIC_BYTES, 'public exceeds 900 MiB budget')
    return catalog


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-dir', '--public-root', dest='public_root', type=Path, default=Path(__file__).resolve().parents[1] / 'public', help='Asset/catalog root (default: repository public/)')
    args = parser.parse_args(argv)
    try:
        data = json.loads((args.public_root / 'data/videos.json').read_text())
        validate_catalog(data, args.public_root)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print(f'Catalog validation failed: {exc}', file=sys.stderr)
        return 1
    print(f'Catalog valid: {len(data["videos"])} videos, {len(data["channels"])} channels')
    return 0


if __name__ == '__main__':
    sys.exit(main())
