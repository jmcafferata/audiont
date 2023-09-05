import os
import subprocess
import openai
import random
import traceback
import tempfile

# TRANSCRIPTION MODULE
# Input: audio file and API key
# Output: text transcription

def transcribe(audio_file,openai_api_key):

    # input: audio file. e.g. '/tmp/123456/testaudio.ogg'
    # output: text transcription
    
    #check if there's a tmp folder. If not, create it
    temp_dir = os.path.join(os.getcwd(), 'tmp')
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)

    random_number = str(random.randint(100000, 999999))
    os.mkdir(os.path.join(temp_dir, random_number))

    output_pattern = os.path.join(temp_dir, random_number, 'chunk-%03d.mp3')

    # Construct the ffmpeg command to split the audio file in chunks of 30 seconds
    command = ['ffmpeg', '-i', audio_file, '-vn', '-map', '0:a',
            '-f', 'segment', '-segment_time', '30', '-reset_timestamps', '1', '-b:a','192k', output_pattern]

    try:
        # log the process
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # set the API key
        openai.api_key = openai_api_key

        transcription_text = ""

        for chunk in os.listdir(os.path.join(temp_dir, random_number)):
            chunk = os.path.join(temp_dir, random_number, chunk)
            with open(chunk, "rb") as file:
                transcription_object = openai.Audio.transcribe(
                    "whisper-1", file, language='es', prompt="Esto es una nota de voz. Transcribir respetando los signos de puntuación.",
                )
                print("Transcription:\n" + transcription_object["text"])
                transcription_text += transcription_object["text"]

            # delete the chunk
            os.remove(chunk)
        # delete the folder
        os.rmdir(os.path.join(temp_dir, random_number))
        



    except Exception as e:
        traceback.print_exc()
        print(e)
        return None
    return transcription_text