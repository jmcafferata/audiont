import os
import subprocess
import shutil 
import openai
import random
import pandas as pd
from ast import literal_eval
from openai.embeddings_utils import get_embedding
from openai.embeddings_utils import cosine_similarity
import numpy as np
from io import StringIO

def convert_to_wav(audio_file):
    audio_file_name = os.path.basename(audio_file)
    audio_file_name_without_extension = os.path.splitext(audio_file_name)[0]
    # generate random number from 1 to 1000

    random_number = str(random.randint(1, 1000))

    new_file_name = audio_file_name_without_extension + random_number + ".mp3"
    
    # compress the audio 
    command = ["ffmpeg", "-i", audio_file, "-b:a", "192k", new_file_name]
    
    try:
        # log the process
        subprocess.run(command, check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error:\n{e.stderr.decode('utf-8')}")
        raise e

    return new_file_name

def split_in_chunks(audio_file):
    # generate random number from 1 to 1000

    random_number = str(random.randint(1, 1000))
    output_pattern = random_number+'_temp_output_%03d.mp3'
    
    # Construct the ffmpeg command
    command = ['ffmpeg', '-i', audio_file, '-vn', '-map', '0:a',
            '-f', 'segment', '-segment_time', '60', '-reset_timestamps', '1', '-b:a','192k',output_pattern]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # get the list of audio files
        audio_files = [file for file in os.listdir() if file.startswith(random_number) and file.endswith(".mp3")]
        audio_files.sort()
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error:\n{e.stderr.decode('utf-8')}")
        raise e

    return audio_files


def transcribe_audios(audio_files, language="es", prompt=""):

    text = ""

    for audio_file in audio_files:
        with open(audio_file, "rb") as file:
            transcription_object = openai.Audio.transcribe(
                "whisper-1", file, language=language, prompt=prompt
            )
            print("Transcription:\n" + transcription_object["text"])
            text += transcription_object["text"]

    # delete the audio files
    for file in audio_files:
        os.remove(file)
    
    return text


# openai.api_key = "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"
# language = "es"
# audio_file = 'testaudio.ogg'
# audio_files = split_in_chunks(audio_file)
# print(audio_files)
# transcription = transcribe_audios(audio_files)
# print(transcription)

