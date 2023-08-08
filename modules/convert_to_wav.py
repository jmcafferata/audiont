import os
import subprocess

def convert_to_wav(audio_file):
    audio_file_name = os.path.basename(audio_file)
    audio_file_name_without_extension = os.path.splitext(audio_file_name)[0]
    new_file_name = audio_file_name_without_extension + ".mp3"
    
    # compress the audio
    command = ["ffmpeg", "-i", audio_file, "-b:a", "192k", new_file_name]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error:\n{e.stderr.decode('utf-8')}")
        raise e

    return new_file_name
