import os
import subprocess
import openai
import random

# TRANSCRIPTION MODULE
# Input: audio file and API key
# Output: text transcription

# Usage:
# language = "es"
# audio_file = 'testaudio.ogg'
# audio_files = split_in_chunks(audio_file)
# print(audio_files)
# transcription = transcribe_audios(audio_files)

def split_in_chunks(audio_file):

    # input: audio file
    # output: list of audio files

    # generate random number from 1 to 1000
    random_number = str(random.randint(1, 1000))

    # output pattern
    output_pattern = random_number+'_temp_output_%03d.mp3'
    
    # Construct the ffmpeg command to split the audio file in chunks of 30 seconds
    command = ['ffmpeg', '-i', audio_file, '-vn', '-map', '0:a',
            '-f', 'segment', '-segment_time', '30', '-reset_timestamps', '1', '-b:a','192k',output_pattern]

    try:
        # log the process
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # get the list of audio files
        audio_files = [file for file in os.listdir() if file.startswith(random_number) and file.endswith(".mp3")]

        # sort the list of audio files
        audio_files.sort()
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error:\n{e.stderr.decode('utf-8')}")
        raise e
    

    return audio_files

def transcribe_audios(audio_files, language="es", prompt="", api_key=""):

    # input: list of audio files and API key
    # output: text transcription

    # set the API key
    openai.api_key = api_key
    
    text = ""

    for audio_file in audio_files:
        with open(audio_file, "rb") as file:
            transcription_object = openai.Audio.transcribe(
                "whisper-1", file, language=language, prompt=prompt
            )
            print("Transcription:\n" + transcription_object["text"])
            text += transcription_object["text"]
    
    return text

