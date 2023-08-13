
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import config
import random
import modules.transcription as transcription
import logging

logging.basicConfig(filename='app.log', level=logging.INFO)

app = Flask(__name__)
app.config['APPLICATION_ROOT'] = '/'+config.bot_code

#try render index.html and debug
@app.route(app.config['APPLICATION_ROOT'] + '/')
def index():
    app.logger.info("Index route accessed")
    return render_template('index.html')

# Upload audio to server /audiont/upload_audio/<user_id>
@app.route(app.config['APPLICATION_ROOT'] + '/upload_audio/<user_id>', methods=['POST'])
def upload_audio(user_id):
    try:
        # create the folder
        folder_name = user_id
        os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], folder_name))
        
        # Check if the file is present in the request
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part in the request.'}), 400
        
        # Get the file from the request
        audio = request.files['file']
        
        # Check if the file is empty
        if audio.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file.'}), 400
        
        # Check if the file is an mp3, wav, ogg (name may contain dots)
        if not audio.filename.lower().endswith(('.mp3', '.wav', '.ogg')):
            return jsonify({'status': 'error', 'message': 'File type not allowed.'}), 400
        
        # Save the audio file to the user's folder
        filename = secure_filename(audio.filename)
        audio.save(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, filename))

        
        # message for the user to download the transcription when it is ready
        message = 'La transcripción está lista. Puedes descargarla <a href="/'+config.bot_code+'/get_transcription/'+user_id+'">aquí</a>.'
        
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})

# /audiont/start_transcription/<user_id>
@app.route(app.config['APPLICATION_ROOT'] + '/start_transcription/<user_id>', methods=['POST'])
def start_transcription(user_id):
    try:
        #get folder
        folder_name = user_id

        #get audio file
        audio_file = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        # Split the audio in chunks of 30 seconds
        audio_files = transcription.split_in_chunks(audio_file)
        transcription_text = transcription.transcribe_audios(audio_files, api_key=config.openai_api_key)

        # Save the transcription to a txt file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'transcription.txt'), 'w') as f:
            f.write(transcription_text)

        # Delete the audio files
        for file in audio_files:
            os.remove(file)
    except Exception as e:
        print(e)

# get transcription from server /audiont/get_transcription/<user_id>
@app.route(app.config['APPLICATION_ROOT'] + '/get_transcription/<user_id>', methods=['GET'])
def get_transcription(user_id):
    try:
        #get folder
        folder_name = user_id

        #get transcription
        with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'transcription.txt'), 'r') as f:
            transcription_text = f.read()
        
        #return transcription
        return jsonify({'status': 'success', 'transcription': transcription_text})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})
if __name__ == '__main__':
    app.run(debug=True)