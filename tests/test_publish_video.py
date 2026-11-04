"""Stdlib tests; fixtures are generated locally, never published."""
import copy

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))


class CatalogTests(unittest.TestCase):
    def test_timestamp_matches_frontend_iso_format(self):
        from datetime import datetime, timezone
        from validate_catalog import CatalogError, timestamp
        for value in (
            '2026-11-04 12:00:00+00:00', '20261104',
            '2026-11-04T12:00Z', '2026-11-04T12:00:00+0000',
            '2026-11-04T12:00:00.1234567Z',
            '2026-11-04T12:00:00,123Z', '2026-11-04t12:00:00Z',
            '2026-11-04T12:00:00+00:60', '2026-11-04T12:00:00+24:00',
            '2026-11-04T24:00:00Z', '2026-11-04T12:60:00Z',
            '2026-11-04T12:00:60Z', '2026-02-29T12:00:00Z',
            '2026-11-04T12:00:00Z\n',
        ):
            with self.subTest(value=value), self.assertRaises(CatalogError):
                timestamp(value)
        for value in (
            '2026-11-04', '2024-02-29', '2026-11-04T12:00:00Z',
            '2026-11-04T12:00:00.1Z', '2026-11-04T12:00:00.123456Z',
            '2026-11-04T12:00:00+05:30', '2026-11-04T12:00:00-03:00',
            datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        ):
            with self.subTest(value=value):
                self.assertEqual(timestamp(value), value)

    def test_numeric_metadata_matches_frontend_caps(self):
        from validate_catalog import CatalogError, number
        for name, maximum in (('duration_seconds', 86400), ('fps', 240)):
            with self.subTest(name=name):
                number(maximum, name)
                with self.assertRaises(CatalogError):
                    number(maximum + 0.001, name)

    def test_source_metadata_matches_frontend_caps(self):
        from validate_catalog import CatalogError, probe
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            media = Path(tmp) / 'clip.mp4'
            for name, rate, accepted in (
                ('duration_seconds', '1/86400', True),
                ('duration_seconds', '1/86401', False),
                ('fps', '240', True), ('fps', '241', False),
            ):
                with self.subTest(name=name, rate=rate):
                    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi',
                                    '-i', f'color=s=16x16:r={rate}', '-frames:v', '1',
                                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                                    '-y', str(media)], check=True)
                    if accepted:
                        self.assertEqual(probe(media)[name], 86400 if name == 'duration_seconds' else 240)
                    else:
                        with self.assertRaisesRegex(CatalogError, name):
                            probe(media)

    def test_pure_slug_timestamp_path_and_budget_guards(self):
        from unittest.mock import patch
        from publish_video import slugify
        from validate_catalog import CatalogError, asset_path, number, timestamp, validate_catalog
        self.assertEqual(slugify('The Noise Outside'), 'the-noise-outside')
        self.assertEqual(slugify(' Héllo / WORLD! '), 'hello-world')
        self.assertEqual(slugify('!!!'), 'video')
        for value in (float('nan'), float('inf'), 0, -1, True, '24'):
            with self.subTest(value=value), self.assertRaises(CatalogError):
                number(value, 'fps')
        for value in ('2026-02-30', '2026-01-01T12:00:00', None):
            with self.subTest(value=value), self.assertRaises(CatalogError):
                timestamp(value)
        timestamp('2026-01-01')
        timestamp('2026-01-01T12:00:00Z')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            base = Path(tmp)
            root = base / 'public'
            root.mkdir()
            outside = base / 'outside.mp4'
            outside.write_bytes(b'outside')
            (root / 'escape.mp4').symlink_to(outside)
            with self.assertRaises(CatalogError):
                asset_path(root, 'escape.mp4')
            (root / 'escape.mp4').unlink()
            (root / 'large').write_bytes(b'12345678901')
            with patch('validate_catalog.MAX_PUBLIC_BYTES', 10), self.assertRaises(CatalogError):
                validate_catalog({'channels':[], 'videos':[]}, root)

    def test_validator_accepts_public_dir_flag_for_built_artifacts(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            (root / 'data/videos.json').write_text('{"channels":[],"videos":[]}')
            result = subprocess.run([sys.executable,str(SCRIPTS / 'validate_catalog.py'),'--public-dir',str(root)],capture_output=True,text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Catalog valid', result.stdout)

    def test_catalog_validation_rejects_unsafe_metadata_and_paths(self):
        self.assertTrue((SCRIPTS / 'validate_catalog.py').exists(), 'catalog validator is required')
        from validate_catalog import validate_catalog, CatalogError
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            assets = root / 'videos/ancestors'
            assets.mkdir(parents=True)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=16x16:r=24','-t','1','-c:v','libx264','-pix_fmt','yuv420p',str(assets / 'clip.mp4')],check=True)
            # Real JPEG produced by ffmpeg; validator must inspect it, not trust extension.
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=size=16x16', '-frames:v', '1', str(assets / 'thumb.jpg')], check=True)
            entry = dict(id='clip', channel_id='ancestors', title='Clip', description='', status='review', duration_seconds=1.0, resolution='16x16', fps=24.0, video_path='videos/ancestors/clip.mp4', thumbnail_path='videos/ancestors/thumb.jpg', generator='', style='', created_at='2026-01-01T00:00:00Z')
            catalog = {'channels':[{'id':'ancestors','name':'Ancestors'}], 'videos':[entry]}
            validate_catalog(catalog, root)
            invalid = [('id','../clip'), ('channel_id','missing'), ('status','unknown'), ('created_at','yesterday'), ('created_at','2026-99-40'), ('fps',float('nan')), ('duration_seconds',0), ('duration_seconds',10), ('fps',30), ('resolution','32x32'), ('resolution','NaNx16'), ('resolution','0x16'), ('resolution',{'width':float('nan'),'height':16}), ('video_path','/clip.mp4'), ('video_path','../clip.mp4'), ('video_path','https://site/clip.mp4'), ('video_path','missing.mp4')]
            for field, value in invalid:
                with self.subTest(field=field,value=value):
                    bad = copy.deepcopy(catalog)
                    bad['videos'][0][field] = value
                    with self.assertRaises(CatalogError):
                        validate_catalog(bad, root)
            for key in ('channels','videos'):
                bad = copy.deepcopy(catalog)
                bad[key] *= 2
                with self.assertRaises(CatalogError):
                    validate_catalog(bad, root)
            (assets / 'bad.mp4').write_bytes(b'not media')
            bad = copy.deepcopy(catalog)
            bad['videos'][0]['video_path'] = 'videos/ancestors/bad.mp4'
            with self.assertRaises(CatalogError):
                validate_catalog(bad, root)
            (assets / 'thumb.jpg').write_bytes(b'not a jpeg')
            with self.assertRaises(CatalogError):
                validate_catalog(catalog, root)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        (self.repo / 'public/data').mkdir(parents=True)
        (self.repo / 'public/data/videos.json').write_text('{"channels":[],"videos":[]}\n')
        (self.repo / 'package.json').write_text(json.dumps({'scripts':{'check':'node -e ""', 'build':'node -e ""'}}))
        self.git('init', '-q')
        # Identity exists only in the disposable fixture, never the real repository.
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.source = self.base / 'source.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=96x64:r=24','-f','lavfi','-i','sine=frequency=400','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(self.source)],check=True)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def publish(self, *extra):
        return subprocess.run([sys.executable, str(SCRIPTS / 'publish_video.py'), '--repo', str(self.repo), '--channel','curious-ancestors','--title','The Noise Outside','--file',str(self.source),'--no-push',*extra],capture_output=True,text=True)

    def test_published_asset_paths_match_frontend_before_media_io(self):
        from unittest.mock import patch
        from validate_catalog import CatalogError, validate_catalog
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.repo / 'public'
        catalog = json.loads((root / 'data/videos.json').read_text())
        validate_catalog(catalog, root)
        prefix = 'videos/curious-ancestors/'
        mutations = []
        for field, extension in (('video_path', '.mp4'), ('thumbnail_path', '.jpg')):
            for path in (
                f'videos/other/clip{extension}', f'videos/curious-ancestors-extra/clip{extension}',
                f'clip{extension}', f'/clip{extension}',
                f'{prefix}clip%20name{extension}', f'{prefix}clip name{extension}',
                f'{prefix}clíp{extension}', f'{prefix}clip+name{extension}',
                f'{prefix}clip\\name{extension}', f'{prefix}clip:name{extension}',
                f'{prefix}clip?name{extension}', f'{prefix}clip#name{extension}',
                f'{prefix}/clip{extension}', f'{prefix}./clip{extension}',
                f'{prefix}../clip{extension}', f'{prefix}clip{extension}/',
                f'{prefix}clip{extension}\n', '', None, 42,
            ):
                mutations.append((field, path))
        mutations.extend([
            ('video_path', prefix + 'clip.MP4'), ('video_path', prefix + 'clip.mov'),
            ('thumbnail_path', prefix + 'thumb.png'), ('thumbnail_path', prefix + 'thumb.JPG'),
            ('thumbnail_path', prefix + 'thumb.JPEG'), ('thumbnail_path', prefix + 'thumbjpg'),
        ])
        payloads = [catalog]
        for field, path in mutations:
            bad = copy.deepcopy(catalog)
            bad['videos'][0][field] = path
            payloads.append(bad)
        # Exercise the actual TypeScript parser, not a Python copy of its rules.
        frontend = subprocess.run([
            'node', '--experimental-strip-types', '--input-type=module', '-e',
            "import { parseCatalog } from " + json.dumps((SCRIPTS.parent / 'src/catalog.ts').as_uri()) + ";"
            "import { readFileSync } from 'node:fs';"
            "console.log(JSON.stringify(JSON.parse(readFileSync(0, 'utf8')).map(value => {"
            "try { parseCatalog(value); return true; } catch { return false; } })));",
        ], input=json.dumps(payloads), capture_output=True, text=True)
        self.assertEqual(frontend.returncode, 0, frontend.stderr)
        self.assertEqual(json.loads(frontend.stdout), [True] + [False] * len(mutations))
        for (field, path), bad in zip(mutations, payloads[1:]):
            with self.subTest(field=field, path=path):
                with patch('validate_catalog.asset_path', side_effect=AssertionError('media I/O before path validation')) as media_io:
                    with self.assertRaises(CatalogError):
                        validate_catalog(bad, root)
                    media_io.assert_not_called()

    def test_dirty_worktree_or_index_is_rejected_before_writes(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                dirty = self.repo / 'unrelated.txt'
                dirty.write_text('user work')
                if staged:
                    self.git('add', 'unrelated.txt')
                before = (self.repo / 'public/data/videos.json').read_bytes()
                result = self.publish()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('clean', result.stderr)
                self.assertEqual((self.repo / 'public/data/videos.json').read_bytes(), before)
                self.assertFalse((self.repo / 'public/videos').exists())
                if staged:
                    self.git('reset', '--', 'unrelated.txt')
                dirty.unlink()

    def test_failed_build_rolls_back_catalog_new_files_and_index(self):
        package = self.repo / 'package.json'
        package.write_text(json.dumps({'scripts':{'check':'node -e ""','build':'node -e "process.exit(2)"'}}))
        self.git('add','package.json')
        self.git('commit','-qm','failing fixture build')
        before = (self.repo / 'public/data/videos.json').read_bytes()
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.repo / 'public/data/videos.json').read_bytes(), before)
        self.assertEqual(self.git('status','--porcelain'), '')
        self.assertFalse((self.repo / 'public/videos/curious-ancestors/the-noise-outside').exists())

    def test_publisher_lock_is_exclusive(self):
        import fcntl
        lock = self.repo / '.git/videodock-publish.lock'
        with lock.open('w') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('publisher', result.stderr)
        self.assertEqual(self.git('status','--porcelain'), '')

    def test_invalid_channel_slug_is_rejected_before_writes(self):
        result = self.publish('--channel','../outside')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.repo / 'public/videos').exists())
        self.assertEqual(self.git('status','--porcelain'), '')

    def test_duplicate_hash_rejected_and_same_title_gets_hash_suffix(self):
        self.assertEqual(self.publish().returncode, 0)
        self.git('commit','-qm','first fixture publication')
        before = (self.repo / 'public/data/videos.json').read_bytes()
        duplicate = self.publish('--title','Different title')
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('duplicate', duplicate.stderr.lower())
        self.assertEqual((self.repo / 'public/data/videos.json').read_bytes(), before)
        self.assertEqual(self.git('status','--porcelain'), '')
        # Change source without touching its existing published copy.
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=96x64:r=24','-t','1','-c:v','libx264','-pix_fmt','yuv420p','-y',str(self.source)],check=True)
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads((self.repo / 'public/data/videos.json').read_text())
        self.assertEqual(len(catalog['videos']), 2)
        self.assertEqual(catalog['videos'][0], json.loads(before)['videos'][0])
        self.assertRegex(catalog['videos'][1]['id'], r'^the-noise-outside-[0-9a-f]{8}$')

    def test_unsupported_codec_requires_explicit_optimization(self):
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=96x64:r=24','-t','1','-c:v','mpeg4','-y',str(self.source)],check=True)
        original = self.source.read_bytes()
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('optimize', result.stderr)
        self.assertEqual(self.git('status','--porcelain'), '')
        optimized = self.publish('--optimize')
        self.assertEqual(optimized.returncode, 0, optimized.stderr)
        self.assertEqual(self.source.read_bytes(), original)
        catalog = json.loads((self.repo / 'public/data/videos.json').read_text())
        media = self.repo / 'public' / catalog['videos'][0]['video_path']
        info = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(media)],text=True))
        self.assertEqual(info['streams'][0]['codec_name'], 'h264')
        self.assertEqual(info['streams'][0]['pix_fmt'], 'yuv420p')

    def test_oversized_source_rejected_before_copy(self):
        with self.source.open('r+b') as stream:
            stream.truncate(50 * 1024 * 1024 + 1)
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('50 MiB', result.stderr)
        self.assertFalse((self.repo / 'public/videos').exists())

    def test_publisher_rejects_symlinked_output_parent(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.repo / 'public/videos').symlink_to(outside, target_is_directory=True)
        self.git('add','public/videos')
        self.git('commit','-qm','symlink fixture')
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_default_orchestrates_only_explicit_commit_then_origin_head_push(self):
        import publish_video
        from unittest.mock import patch
        args = publish_video.parser().parse_args(['--repo',str(self.repo),'--channel','curious-ancestors','--title','The Noise Outside','--file',str(self.source)])
        real_run = publish_video.run
        writes = []
        def intercept(command, repo=None):
            if command[:2] in (['git','commit'], ['git','push']):
                writes.append(command)
                return ''  # No commit/push side effects; verify orchestration only.
            if command[:3] == ['git','remote','get-url']:
                return 'unused-fixture-origin'
            return real_run(command, repo)
        with patch.object(publish_video, 'run', side_effect=intercept), patch('builtins.print'):
            entry = publish_video.publish(args)
        self.assertEqual(len(writes), 2)
        self.assertEqual(writes[0][:2], ['git','commit'])
        self.assertIn('--only', writes[0])
        self.assertEqual(writes[0][writes[0].index('--')+1:], ['public/data/videos.json','public/'+entry['video_path'],'public/'+entry['thumbnail_path']])
        self.assertEqual(writes[1], ['git','push','origin','HEAD'])

    def test_build_staging_unrelated_file_is_rejected_not_committed(self):
        package = self.repo / 'package.json'
        package.write_text(json.dumps({'scripts':{'check':'node -e ""','build':"node -e \"require('fs').writeFileSync('surprise.txt','user work')\" && git add surprise.txt"}}))
        self.git('add','package.json')
        self.git('commit','-qm','staging build fixture')
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unrelated', result.stderr)
        self.assertEqual((self.repo / 'surprise.txt').read_text(), 'user work')
        self.assertEqual(self.git('diff','--cached','--name-only').strip(), 'surprise.txt')
        self.assertEqual(json.loads((self.repo / 'public/data/videos.json').read_text())['videos'], [])

    def test_symlinked_catalog_parent_is_rejected_without_modification(self):
        data = self.repo / 'public/data'
        outside = self.base / 'outside-data'
        data.rename(outside)
        data.symlink_to(outside, target_is_directory=True)
        self.git('add','-A')
        self.git('commit','-qm','symlinked data fixture')
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads((outside / 'videos.json').read_text())['videos'], [])
        self.assertFalse((self.repo / 'public/videos').exists())

    def test_shell_wrapper_forwards_help(self):
        wrapper = SCRIPTS / 'publish-video.sh'
        self.assertTrue(wrapper.exists(), 'shell wrapper is required')
        result = subprocess.run(['bash',str(wrapper),'--help'],capture_output=True,text=True,cwd=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--optimize', result.stdout)

    def test_wrapper_in_clean_repository_does_not_create_bytecode_dirt(self):
        import shutil
        scripts = self.repo / 'scripts'
        scripts.mkdir()
        for name in ('publish-video.sh','publish_video.py','validate_catalog.py'):
            shutil.copy2(SCRIPTS / name, scripts / name)
        self.git('add','scripts')
        self.git('commit','-qm','publisher fixture')
        result = subprocess.run(['bash',str(scripts / 'publish-video.sh'),'--channel','ancestors','--title','Clip','--file',str(self.source),'--no-push'],capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((scripts / '__pycache__').exists())

    def test_optimization_does_not_bypass_duplicate_source_guard(self):
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git('commit','-qm','unoptimized fixture publication')
        duplicate = self.publish('--optimize','--title','Alternative title')
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('duplicate', duplicate.stderr.lower())
        self.assertEqual(self.git('status','--porcelain'), '')

    def test_default_real_commit_push_to_disposable_local_bare_remote(self):
        remote = self.base / 'remote.git'
        subprocess.run(['git','init','--bare','-q',str(remote)],check=True)
        self.git('remote','add','origin',str(remote))
        before = self.git('rev-parse','HEAD').strip()
        result = subprocess.run([sys.executable,str(SCRIPTS / 'publish_video.py'),'--repo',str(self.repo),'--channel','ancestors','--title','Real local push','--file',str(self.source),'--status','review'],capture_output=True,text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        head = self.git('rev-parse','HEAD').strip()
        self.assertNotEqual(head, before)
        branch = self.git('symbolic-ref','--short','HEAD').strip()
        remote_head = self.git('ls-remote','origin','refs/heads/'+branch).split()[0]
        self.assertEqual(remote_head, head)
        self.assertEqual(self.git('status','--porcelain'), '')
        paths = set(self.git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())
        entry = json.loads((self.repo / 'public/data/videos.json').read_text())['videos'][0]
        self.assertEqual(paths, {'public/data/videos.json','public/'+entry['video_path'],'public/'+entry['thumbnail_path']})
        # Same real file is rejected before producing another commit or asset.
        duplicate = self.publish('--channel','ancestors','--title','Different title')
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn('duplicate', duplicate.stderr.lower())
        self.assertEqual(self.git('rev-parse','HEAD').strip(), head)
        self.assertEqual(self.git('status','--porcelain'), '')

    def test_failed_push_retains_local_commit_and_assets(self):
        self.git('remote','add','origin',str(self.base / 'nonexistent.git'))
        before = self.git('rev-parse','HEAD')
        result = subprocess.run([sys.executable,str(SCRIPTS / 'publish_video.py'),'--repo',str(self.repo),'--channel','ancestors','--title','Retained commit','--file',str(self.source)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('retaining', result.stderr)
        self.assertNotEqual(self.git('rev-parse','HEAD'), before)
        self.assertEqual(self.git('status','--porcelain'), '')
        entry = json.loads((self.repo / 'public/data/videos.json').read_text())['videos'][0]
        self.assertTrue((self.repo / 'public' / entry['video_path']).is_file())

    def test_index_lock_failure_still_restores_catalog_and_new_assets(self):
        lock = self.repo / '.git/index.lock'
        lock.write_text('unrelated git operation')
        original = (self.repo / 'public/data/videos.json').read_bytes()
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.repo / 'public/data/videos.json').read_bytes(), original)
        self.assertFalse((self.repo / 'public/videos').exists())
        self.assertEqual(lock.read_text(), 'unrelated git operation')

    def test_no_push_copies_source_and_stages_valid_review_without_commit(self):
        self.assertTrue((SCRIPTS / 'publish_video.py').exists(), 'publisher is required')
        before = self.git('rev-parse','HEAD')
        original = self.source.read_bytes()
        result = self.publish('--channel-name','Curious Ancestors')
        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads((self.repo / 'public/data/videos.json').read_text())
        self.assertEqual(catalog['channels'], [{'id':'curious-ancestors','name':'Curious Ancestors'}])
        self.assertEqual(len(catalog['videos']), 1)
        entry = catalog['videos'][0]
        self.assertEqual(entry['status'], 'review')
        self.assertEqual(entry['resolution'], '96x64')
        self.assertEqual((self.repo / 'public' / entry['video_path']).read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(self.git('rev-parse','HEAD'), before)
        staged = self.git('diff','--cached','--name-only').splitlines()
        self.assertEqual(set(staged), {'public/data/videos.json', 'public/'+entry['video_path'], 'public/'+entry['thumbnail_path']})
        from validate_catalog import validate_catalog
        validate_catalog(catalog, self.repo / 'public')


if __name__ == '__main__':
    unittest.main()
