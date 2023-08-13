
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify
from werkzeug.utils import secure_filename
import os
import config
import subprocess
import random
import openai

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
            with open(app.config['APPLICATION_ROOT'] + '/static/openai_api_key.txt', 'r') as f:

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
    app.run(debug=True)