
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import config
import random
import modules.transcription as transcription
import logging
import traceback

logging.basicConfig(filename='app.log', level=logging.INFO)


app = Flask(__name__)
# uploads folder
app.config['UPLOAD_FOLDER'] = 'uploads'
# add /audiont/ to the url
app.config['APPLICATION_ROOT'] = '/audiont'

#try render index.html and debug
@app.route('/')
def index():
    app.logger.info("Index route accessed")
    return render_template('index.html')

# Upload audio to server /audiont/upload_audio/<user_id>
@app.route('/upload_audio/<user_id>', methods=['POST'])
def upload_audio(user_id):
    # check for uploads folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.mkdir(app.config['UPLOAD_FOLDER'])
    print(user_id)
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
        message = '<a href="/get_transcription/'+user_id+'">Acá</a> va a estar lista la transcripción.'
        
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        traceback.print_exc()
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})

# /audiont/start_transcription/<user_id>
@app.route('/start_transcription/<user_id>', methods=['POST'])
def start_transcription(user_id):
    print('start transcription')
    try:
        #get folder
        folder_name = user_id

        #get audio file
        audio_file = os.path.join(app.config['UPLOAD_FOLDER'], folder_name, os.listdir(os.path.join(app.config['UPLOAD_FOLDER'], folder_name))[0])
        transcription_text = transcription.transcribe(audio_file, config.openai_api_key)

        # Save the transcription to a txt file
        with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'transcription.txt'), 'w') as f:
            f.write(transcription_text)


        return None
    except Exception as e:
        traceback.print_exc()
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})


# get transcription from server /get_transcription/<user_id>
@app.route('/get_transcription/<user_id>', methods=['GET'])
def get_transcription(user_id):
    try:
        #get folder
        folder_name = user_id

        #get transcription
        with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'transcription.txt'), 'r') as f:
            transcription_text = f.read()
        
        return render_template('get_transcription.html', transcription_text=transcription_text)
        
    except Exception as e:
        print(e)
        return "La transcripción todavía no está lista. Esperá unos segundos e intentá nuevamente."
    
if __name__ == '__main__':
    app.run(debug=True)