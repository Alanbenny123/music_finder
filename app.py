import base64
import json
import logging
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from demucs.api import Separator
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import soundfile as sf
import torch


load_dotenv()
app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

UPLOAD_FOLDER = Path('uploads')
OUTPUT_FOLDER = Path('outputs')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav'}
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

separator = None


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_separator():
    global separator
    if separator is None:
        separator = Separator(model='htdemucs', device='cuda' if torch.cuda.is_available() else 'cpu')
    return separator


def recognize_music(input_path):
    key = os.environ.get('RAPIDAPI_KEY')
    if not key:
        return None

    try:
        # Shazam accepts base64 encoded, mono, 44.1 kHz, 16-bit PCM audio.
        sample = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(input_path), '-t', '10',
             '-ac', '1', '-ar', '44100', '-f', 's16le', '-acodec', 'pcm_s16le', '-'],
            check=True, capture_output=True,
        ).stdout
        if not sample:
            return None

        api_request = Request(
            'https://shazam.p.rapidapi.com/songs/v2/detect',
            data=base64.b64encode(sample),
            headers={
                'content-type': 'text/plain',
                'x-rapidapi-host': 'shazam.p.rapidapi.com',
                'x-rapidapi-key': key,
            },
            method='POST',
        )
        with urlopen(api_request, timeout=15) as response:
            result = json.load(response)

        track = result.get('track')
        if not track:
            return None

        metadata = {}
        for section in track.get('sections', []):
            for item in section.get('metadata', []):
                metadata[item.get('title')] = item.get('text')

        return {
            'title': track.get('title'),
            'artist': track.get('subtitle'),
            'genre': track.get('genres', {}).get('primary'),
            'album': metadata.get('Album'),
        }
    except (OSError, subprocess.CalledProcessError, URLError, ValueError, KeyError) as exc:
        logging.warning('Music recognition failed: %s', exc)
        return None


@app.errorhandler(413)
def file_too_large(_error):
    return jsonify({'error': 'File exceeds the 100 MB upload limit'}), 413


@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'torch_available': torch.cuda.is_available()})


@app.route('/api/separate', methods=['POST'])
def separate_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    job_id = str(uuid.uuid4())
    suffix = Path(file.filename).suffix.lower()
    input_path = UPLOAD_FOLDER / f'{job_id}_input{suffix}'
    output_dir = OUTPUT_FOLDER / job_id
    completed = False

    try:
        file.save(input_path)
        music_info = recognize_music(input_path)
        model = get_separator()
        _, sources = model.separate_audio_file(input_path)

        output_dir.mkdir(parents=True, exist_ok=True)
        track_paths = {}
        for source, audio in sources.items():
            output_path = output_dir / f'{source}.wav'
            sf.write(output_path, audio.cpu().numpy().T, model.samplerate)
            track_paths[source] = f'/api/download/{job_id}/{source}'

        result = {'job_id': job_id, 'tracks': track_paths}
        if music_info:
            result['music_info'] = music_info
        completed = True
        return jsonify(result)
    except Exception as exc:
        logging.exception('Separation failed for job %s', job_id)
        return jsonify({'error': str(exc)}), 500
    finally:
        input_path.unlink(missing_ok=True)
        if not completed:
            shutil.rmtree(output_dir, ignore_errors=True)


@app.route('/api/download/<job_id>/<source>')
def download_file(job_id, source):
    try:
        file_path = OUTPUT_FOLDER / job_id / f'{source}.wav'
        return send_file(file_path, as_attachment=True, download_name=f'{source}.wav')
    except Exception as exc:
        return jsonify({'error': str(exc)}), 404


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)
