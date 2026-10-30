import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import app as backend


class SeparateAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.uploads = root / 'uploads'
        self.outputs = root / 'outputs'
        self.uploads.mkdir()
        self.outputs.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(backend, 'UPLOAD_FOLDER', self.uploads).start()
        patch.object(backend, 'OUTPUT_FOLDER', self.outputs).start()
        backend.app.config['TESTING'] = True
        backend.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
        self.client = backend.app.test_client()

    def upload(self):
        return self.client.post(
            '/api/separate',
            data={'file': (io.BytesIO(b'audio'), 'example.mp3')},
        )

    def test_separation_returns_named_stems_and_recognition(self):
        model = MagicMock()
        model.samplerate = 44100
        model.separate_audio_file.return_value = (None, {
            'drums': MagicMock(),
            'bass': MagicMock(),
            'other': MagicMock(),
            'vocals': MagicMock(),
        })
        with patch.object(backend, 'get_separator', return_value=model), \
             patch.object(backend, 'recognize_music', return_value={'title': 'Song'}), \
             patch.object(backend.sf, 'write') as write:
            response = self.upload()

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['music_info'], {'title': 'Song'})
        self.assertEqual(set(payload['tracks']), {'drums', 'bass', 'other', 'vocals'})
        self.assertEqual(write.call_count, 4)
        self.assertEqual(list(self.uploads.iterdir()), [])
        self.assertEqual(model.separate_audio_file.call_args.args[0].suffix, '.mp3')

    def test_failed_separation_removes_uploaded_file_and_output_directory(self):
        model = MagicMock()
        model.separate_audio_file.side_effect = RuntimeError('processing failed')
        with patch.object(backend, 'get_separator', return_value=model), \
             patch.object(backend, 'recognize_music', return_value=None):
            response = self.upload()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(list(self.uploads.iterdir()), [])
        self.assertEqual(list(self.outputs.iterdir()), [])

    def test_failed_stem_write_removes_partial_output(self):
        model = MagicMock()
        model.samplerate = 44100
        model.separate_audio_file.return_value = (None, {'vocals': MagicMock()})

        def fail_after_write(path, _audio, _samplerate):
            path.write_bytes(b'partial')
            raise OSError('disk error')

        with patch.object(backend, 'get_separator', return_value=model), \
             patch.object(backend, 'recognize_music', return_value=None), \
             patch.object(backend.sf, 'write', side_effect=fail_after_write):
            response = self.upload()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(list(self.uploads.iterdir()), [])
        self.assertEqual(list(self.outputs.iterdir()), [])

    def test_upload_limit_returns_json_error(self):
        backend.app.config['MAX_CONTENT_LENGTH'] = 4
        response = self.upload()

        self.assertEqual(response.status_code, 413)
        self.assertIn('100 MB', response.get_json()['error'])


class RecognitionTests(unittest.TestCase):
    def test_shazam_response_is_mapped_to_music_info(self):
        response = io.BytesIO(
            b'{"track":{"title":"Song","subtitle":"Artist",'
            b'"genres":{"primary":"Pop"},"sections":[{"metadata":'
            b'[{"title":"Album","text":"Record"}]}]}}'
        )
        process = MagicMock(stdout=b'pcm')
        with patch.dict(backend.os.environ, {'RAPIDAPI_KEY': 'test-key'}), \
             patch.object(backend.subprocess, 'run', return_value=process), \
             patch.object(backend, 'urlopen', return_value=response) as open_url:
            info = backend.recognize_music(Path('example.mp3'))

        self.assertEqual(info, {
            'title': 'Song', 'artist': 'Artist', 'genre': 'Pop', 'album': 'Record'
        })
        self.assertEqual(open_url.call_args.args[0].data, b'cGNt')


if __name__ == '__main__':
    unittest.main()
