import os
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import torch
from demucs.pretrained import get_model
from demucs.apply import apply_model
import numpy as np
import moviepy.editor as mp
import soundfile as sf
import tempfile
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Load Demucs model
model = None

def get_demucs_model():
    global model
    if model is None:
        model = get_model('htdemucs')
        model.eval()
        if torch.cuda.is_available():
            model.cuda()
    return model

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'torch_available': torch.cuda.is_available()})

@app.route('/api/separate', methods=['POST'])
def separate_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    try:
        # Generate unique ID for this separation
        job_id = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_input.mp4")
        audio_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_audio.wav")
        output_dir = os.path.join(OUTPUT_FOLDER, job_id)
        os.makedirs(output_dir, exist_ok=True)

        # Save uploaded file
        file.save(input_path)

        # Extract audio if video file
        if file.filename.rsplit('.', 1)[1].lower() in {'mp4', 'avi', 'mov', 'mkv'}:
            video = mp.VideoFileClip(input_path)
            video.audio.write_audiofile(audio_path)
            video.close()
            os.remove(input_path)  # Clean up video file
        else:
            audio_path = input_path

        # Load audio
        model = get_demucs_model()
        
        # Process with Demucs
        with torch.no_grad():
            sources = apply_model(model, audio_path, device='cuda' if torch.cuda.is_available() else 'cpu')
            sources = sources.cpu().numpy()

        # Save separated tracks
        track_paths = {}
        for source, data in zip(['drums', 'bass', 'other', 'vocals'], sources):
            output_path = os.path.join(output_dir, f"{source}.wav")
            sf.write(output_path, data.T, 44100)
            track_paths[source] = f"/api/download/{job_id}/{source}"

        # Clean up input file
        os.remove(audio_path)

        return jsonify({
            'job_id': job_id,
            'tracks': track_paths
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<job_id>/<source>')
def download_file(job_id, source):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, job_id, f"{source}.wav")
        return send_file(file_path, as_attachment=True, download_name=f"{source}.wav")
    except Exception as e:
        return jsonify({'error': str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 