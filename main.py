from flask import Flask, render_template, request, jsonify
import openai
import os
import pytz
timezone = pytz.timezone('America/Argentina/Buenos_Aires')
import json
import subprocess
import random

app = Flask(__name__)

# Show index.html
@app.route('/', methods=['GET'])
def index():

    return render_template('index.html')

# Upload audio to server
@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400
        
        audio = request.files['file']
        
        # Check if the file is empty
        if audio.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file.'}), 400
        
        # Check if the file is an mp3, wav, ogg (name may contain dots)
        if not audio.filename.lower().endswith(('.mp3', '.wav', '.ogg')):
            return jsonify({'status': 'error', 'message': 'File type not allowed.'}), 400
        
        # Save the audio file
        audio.save(audio.filename)

        # Split the audio in chunks of 30 seconds
        audio_files = split_in_chunks(audio.filename)

        transcription = transcribe_audios(audio_files)


        
        return jsonify({'status': 'success', 'message': transcription})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})


def split_in_chunks(audio_file):
    # generate random number from 1 to 1000

    random_number = str(random.randint(1, 1000))
    output_pattern = random_number+'_temp_output_%03d.mp3'
    
    # Construct the ffmpeg command
    command = ['ffmpeg', '-i', audio_file, '-vn', '-map', '0:a',
            '-f', 'segment', '-segment_time', '30', '-reset_timestamps', '1', '-b:a','192k',output_pattern]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # get the list of audio files
        audio_files = [file for file in os.listdir() if file.startswith(random_number) and file.endswith(".mp3")]
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error:\n{e.stderr.decode('utf-8')}")
        raise e

    return audio_files


def transcribe_audios(audio_files, language="es", prompt=""):

    text = ""

    for audio_file in audio_files:
        with open(audio_file, "rb") as file:
            # get the openai api key from openai_api_key.txt
            with open("openai_api_key.txt", "r") as f:

                openai.api_key = f.read()
            transcription_object = openai.Audio.transcribe(
                "whisper-1", file, language=language, prompt=prompt
            )
            print("Transcription:\n" + transcription_object["text"])
            text += transcription_object["text"]

    # delete the audio files
    for file in audio_files:
        os.remove(file)
    
    return text



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)