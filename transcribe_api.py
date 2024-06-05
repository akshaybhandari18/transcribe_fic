from flask import Flask, request, jsonify, send_file
import whisper
import os
import logging
from datetime import datetime
import random
import string

app = Flask(__name__)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HARDCODED_TOKEN = 'your_hardcoded_token'

# Loading the Whisper model only once during application startup
logger.info("Loading model...")
model = whisper.load_model("large")
logger.info("Model loaded successfully.")

@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        # Checking if the hardcoded token matches
        provided_token = request.headers.get('Authorization')
        if provided_token != HARDCODED_TOKEN:
            return jsonify({'error': 'Invalid token'}), 401

        if 'audio_file' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400

        audio_file = request.files['audio_file']
        
        # Creating a folder with the --> filename_timestamp_unique_random_key 
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{os.path.splitext(audio_file.filename)[0]}_{timestamp}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(3,5)))}"
        os.makedirs(folder_name, exist_ok=True)
        
        file_path = os.path.join(folder_name, audio_file.filename)
        audio_file.save(file_path)

        # Transcribe the audio using the model
        logger.info(f"Transcribing audio file: {file_path}")
        result = model.transcribe(file_path)

 
        transcribed_text = result["text"]

        # Saving the transcribed text to a file in the created folder
        text_filename = os.path.splitext(audio_file.filename)[0] + "_transcribed.txt"
        text_file_path = os.path.join(folder_name, text_filename)
        with open(text_file_path, "w") as text_file:
            text_file.write(transcribed_text)

        # Saving the transcribed text to a VTT file in the created folder
        vtt_filename = os.path.splitext(audio_file.filename)[0] + ".vtt"
        vtt_file_path = os.path.join(folder_name, vtt_filename)
        with open(vtt_file_path, "w") as vtt_file:
            vtt_file.write("WEBVTT\n\n")
            for segment in result["segments"]:
                start = segment["start"]
                end = segment["end"]
                text = segment["text"]
                start_time = format_timestamp(start)
                end_time = format_timestamp(end)
                vtt_file.write(f"{start_time} --> {end_time}\n{text}\n\n")

        logger.info(f"Transcription completed for file: {file_path}")
        return jsonify({
            'transcribed_text': transcribed_text,
            'text_file_path': text_file_path,
            'vtt_file_path': vtt_file_path
        })

    except Exception as e:
        logger.error(f"Error during transcription: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/download_text/<path:folder_name>/<path:filename>', methods=['GET'])
def download_text(folder_name, filename):
    try:
        text_file_path = os.path.join(folder_name, filename)
        return send_file(text_file_path, as_attachment=True)
    except FileNotFoundError:
        logger.error(f"Text file not found: {text_file_path}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/download_vtt/<path:folder_name>/<path:filename>', methods=['GET'])
def download_vtt(folder_name, filename):
    try:
        vtt_file_path = os.path.join(folder_name, filename)
        return send_file(vtt_file_path, as_attachment=True)
    except FileNotFoundError:
        logger.error(f"VTT file not found: {vtt_file_path}")
        return jsonify({'error': 'File not found'}), 404

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

if __name__ == "__main__":
    app.run()