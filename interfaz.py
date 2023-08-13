
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import config
import subprocess
import random
import openai
import modules.transcription as transcription

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'users/'
app.config['APPLICATION_ROOT'] = '/'+config.bot_code

#try render index.html and debug
@app.route(app.config['APPLICATION_ROOT'] + '/')
def index():
    app.logger.info("Index route accessed")
    return render_template('index.html')


# Make sure to use a secret key for your application
app.secret_key = "your-secret-key"


# This code is used to upload a file to a user's folder. It is used in the vectorizar.html file to upload the file. It is also used in the app.py file to save the file in the user's folder.
@app.route(app.config['APPLICATION_ROOT'] + '/vectorizar/<user_id>', methods=['GET', 'POST'])
def upload_file(user_id):
    if request.method == 'POST':
        # Check if the file is present in the request
        if 'file' not in request.files:
            flash('No file found')
            return redirect(request.url)
        
        file = request.files['file']

        file_info = request.form.get('file_info')


        # cehck if file is pdf or txt
        if file.filename.split('.')[-1] not in ['pdf','txt']:
            return render_template('error.html', user_id=user_id)
        
        # Check if the filename is empty
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        # Save the file to the user's folder
        filename = secure_filename(file.filename)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_id,"to_vectorize")
        # check if the user folder exists, if not create it
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)       
        
        file.save(os.path.join(user_folder, filename))
        # take the user to listo.html (in the templates folder)
        

        #store the file name and file info in a txt file in the to_vectorize folder
        # the name of the txt file is the same as the name of the pdf file
        with open(os.path.join(user_folder, 'metadata_'+filename.split('.')[0]+'.txt'), 'w') as f:
            f.write(file_info)

    

        return render_template('listo.html', user_id=user_id)


    return render_template('vectorizar.html', user_id=user_id)


# Upload audio to server
@app.route(app.config['APPLICATION_ROOT'] + '/upload_audio', methods=['POST'])
def upload_audio():
    try:
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
        
        # Save the audio file
        audio.save(audio.filename)

        # Split the audio in chunks of 30 seconds
        audio_files = transcription.split_in_chunks(audio.filename)
        transcription_text = transcription.transcribe_audios(audio_files, api_key=config.openai_api_key)
        # Delete the audio files
        for file in audio_files:
            os.remove(file)


        
        return jsonify({'status': 'success', 'message': transcription_text})
    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})



if __name__ == '__main__':
    app.run(debug=True)