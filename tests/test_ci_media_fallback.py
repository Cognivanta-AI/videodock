import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_catalog import validate_catalog

class StaticBuildMediaTests(unittest.TestCase):
    def test_valid_public_catalog_builds_without_ffmpeg_binaries(self):
        repo=Path(__file__).resolve().parents[1]
        source=repo/'public'
        with tempfile.TemporaryDirectory() as tmp:
            public=Path(tmp)/'public'
            import shutil
            shutil.copytree(source,public)
            catalog=json.loads((public/'data/videos.json').read_text())
            def unavailable(argv,*args,**kwargs):
                if argv[0] in ('ffprobe','ffmpeg'):
                    raise FileNotFoundError(argv[0])
                return subprocess.run(argv,*args,**kwargs)
            with patch('validate_catalog.subprocess.run',side_effect=unavailable):
                result=validate_catalog(catalog,public)
            self.assertEqual(len(result['videos']),1)

    def test_corrupt_top_level_mp4_is_rejected_without_ffprobe(self):
        repo=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            public=Path(tmp)/'public'
            import shutil
            shutil.copytree(repo/'public',public)
            catalog=json.loads((public/'data/videos.json').read_text())
            path=public/catalog['videos'][0]['video_path']
            path.write_bytes(b'not an ISO BMFF video')
            def unavailable(argv,*args,**kwargs):
                if argv[0] in ('ffprobe','ffmpeg'):
                    raise FileNotFoundError(argv[0])
                return subprocess.run(argv,*args,**kwargs)
            with patch('validate_catalog.subprocess.run',side_effect=unavailable):
                with self.assertRaises(ValueError): validate_catalog(catalog,public)
