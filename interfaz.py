
from flask import Flask, flash, request, redirect, url_for, render_template, jsonify, Blueprint
from werkzeug.utils import secure_filename
import os
import config
import random
import modules.transcription as transcription
import logging
import traceback

logging.basicConfig(filename='app.log', level=logging.INFO)


# bp = Blueprint('audiont', __name__, template_folder='templates')

# FOR DEBUG 👇
bp = Blueprint('audiont', __name__, template_folder='templates', static_folder='static', static_url_path='/static')


#try render index.html and debug
@bp.route('/')
def index():
    return render_template('index.html')

# Upload audio to server /audiont/upload_audio/<user_id>
@bp.route('/upload_audio/<user_id>', methods=['POST'])
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
        if not audio.filename.lower().endswith(('.mp3', '.wav', '.ogg','.opus','.m4a','.mp4','.oga')):
            return jsonify({'status': 'error', 'message': 'File type not allowed.'}), 400
        
        # Save the audio file to the user's folder
        filename = secure_filename(audio.filename)
        audio.save(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, filename))

        
        # message for the user to download the transcription when it is ready
        message = '<a href="/audiont/get_transcription/'+user_id+'">Acá</a> va a estar lista la transcripción.'
        
        return jsonify({'status': 'success', 'message': message})
    except Exception as e:
        traceback.print_exc()
        print(e)
        return jsonify({'status': 'error', 'error': str(e)})

# /audiont/start_transcription/<user_id>
@bp.route('/start_transcription/<user_id>', methods=['POST'])
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
@bp.route('/get_transcription/<user_id>', methods=['GET'])
def get_transcription(user_id):
    try:
        #get folder
        folder_name = user_id

        #get transcription
        with open(os.path.join(app.config['UPLOAD_FOLDER'], folder_name, 'transcription.txt'), 'r') as f:
            transcription_text = f.read()
        
        return render_template('get_transcription.html', transcription_text=transcription_text, is_ready=True)
        
    except Exception as e:
        print(e)
        return render_template('get_transcription.html', transcription_text='Todavía no está lista la transcripción. Tarda 5 segundos por cada 30 segundos de audio.',is_ready=False)    

@bp.route('/vectorizar/<user_id>', methods=['GET', 'POST'])
def upload_file(user_id):
    if request.method == 'POST':
        # Check if the file zis present in the request
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



app = Flask(__name__)
app.register_blueprint(bp, url_prefix='/audiont')
# uploads folder
app.config['UPLOAD_FOLDER'] = 'uploads'


if __name__ == '__main__':
    app.run(debug=True)