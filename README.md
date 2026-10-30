# Music Source Separator

A modern web application that separates music/background music from videos into individual stems (vocals, drums, bass, and other instruments) using state-of-the-art AI technology. It also identifies the background music using Shazam's music recognition API.

## Features

- Upload video or audio files
- Identify background music/songs (title, artist, genre, album)
- Separate audio into four stems:
  - Vocals
  - Drums
  - Bass
  - Other instruments
- Modern, user-friendly interface
- Download individual stems as WAV files
- Supports various video and audio formats

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- FFmpeg installed on your system
- RapidAPI key (optional, for music recognition)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd music-source-separator
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
cd frontend
npm install
```

4. To enable music recognition, create a `.env` file in the root directory and add your RapidAPI key:

```
RAPIDAPI_KEY=your_rapidapi_key_here
```

## Running the Application

1. Start the backend server:

```bash
# From the root directory
python app.py
```

2. Start the frontend development server:

```bash
# From the frontend directory
npm start
```

3. Open your browser and navigate to `http://localhost:3000`

The frontend development server forwards API requests to the Flask server on
`127.0.0.1:5000`. For a separate frontend deployment, set
`REACT_APP_API_BASE_URL` to the backend origin when building the frontend.
When serving both behind one origin, route `/api/*` and `/health` to Flask.
The Flask development server listens only on the local machine.

## Usage

1. Click the "Select File" button to choose a video or audio file
2. Click "Start Separation" to begin the separation process
3. Wait for the processing to complete
4. View the identified music information (if available)
5. Download individual stems using the download buttons

Uploads are limited to 100 MB. If a RapidAPI key is configured, the app sends
the first 10 seconds of audio to Shazam for recognition. Stem separation still
works when recognition is unavailable or no song is found.

## Supported File Formats

- Video: MP4, AVI, MOV, MKV
- Audio: MP3, WAV

## Technical Details

- Backend: Flask (Python)
- Frontend: React with Material-UI
- Audio Processing: Demucs v4 (Facebook Research)
- Music Recognition: Shazam API (via RapidAPI)
- File Processing: FFmpeg through Demucs

## API Keys

To use the music recognition feature, you need to:

1. Sign up for a RapidAPI account
2. Subscribe to the Shazam API
3. Copy your API key to the `.env` file

## License

MIT License
