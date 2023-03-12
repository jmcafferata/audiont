import os

# use ffmpeg to convert the audio file to a wav file // usar ffmpeg para convertir el archivo de audio a un archivo wav
def convert_to_wav(audio_file):
    # get the name of the audio file // obtener el nombre del archivo de audio
    audio_file_name = os.path.basename(audio_file)
    # get the name of the audio file without the extension // obtener el nombre del archivo de audio sin la extensión
    audio_file_name_without_extension = os.path.splitext(audio_file_name)[0]
    # create a new file name for the wav file // crear un nuevo nombre de archivo para el archivo wav
    new_file_name = audio_file_name_without_extension + ".wav"
    # use ffmpeg to convert the audio file to a wav file // usar ffmpeg para convertir el archivo de audio a un archivo wav
    os.system("ffmpeg -y -i "+audio_file+" "+new_file_name)
    # return the new file name // devolver el nuevo nombre de archivo
    return new_file_name
