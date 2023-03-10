
# This code is used to process audio files from the telegram bot, get the text from the audio file and generate an automated response.
# Este código se usa para procesar archivos de audio del bot de telegram, obtener el texto del archivo de audio y generar una respuesta automatizada.

# import the necessary libraries // importar las librerías necesarias
import os # operating system library that allows us to access the computer's file system // librería del sistema operativo que nos permite acceder al sistema de archivos del computador
import openai # library used to access the OpenAI API // librería usada para acceder a la API de OpenAI
from typing import DefaultDict, Optional, Set # library used to define the types of variables // librería usada para definir los tipos de variables
from collections import defaultdict
from pathlib import Path # library used to handle file paths // librería usada para manejar rutas de archivos
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ExtBot,
    TypeHandler,
    InlineQueryHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode
import config # import the config file // importar el archivo de configuración
import asyncio # library used to handle asynchronous code // librería usada para manejar código asíncrono
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent # library used to communicate with the Telegram bot // librería usada para comunicarse con el bot de Telegram

# set the OpenAI API key, so the code can access the API // establecer la clave de la API de OpenAI, para que el código pueda acceder a la API
openai.api_key = config.openai_api_key

# decoding means converting the bytes (0s and 1s) into a string // la decodificación significa convertir los bytes (0s y 1s) en una cadena de texto
def decode_utf8(text: bytes) -> str: 
    # Encode the string with UTF-8 // Codificar la cadena con UTF-8
    encoded_text = text.encode('utf-8')
    # Decode the bytes with UTF-8 // Decodificar los bytes con UTF-8
    decoded_text = encoded_text.decode('utf-8')
    return decoded_text

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

# main function that handles the audio files // función principal que maneja los archivos de audio
async def handle_audio(update, context):
    # Extract the audio file from the message // Extraer el archivo de audio del mensaje
    new_file = await update.message.effective_attachment.get_file()
    await new_file.download_to_drive()
    file_path = Path(new_file.file_path).name
    # reply to the message, telling the user the audio file was received // responder al mensaje, diciendo al usuario que se recibió el archivo de audio
    await update.message.reply_text('Audio recibido. Esperá un toque que lo proceso. Te voy avisando.') 
    
    new_audio_path = convert_to_wav(file_path)
    wav_audio = open(new_audio_path,"rb")
    # call the OpenAI API to get the text from the audio file // llamar a la API de OpenAI para obtener el texto del archivo de audio
    transcription_object = openai.Audio.transcribe("whisper-1", wav_audio,language="es",prompt="esto es una nota de voz. hay momentos de silencio en el audio, cuidado con eso.")
    
    # print the text extracted from the audio file // imprimir el texto extraído del archivo de audio
    print("Transcription:\n"+transcription_object["text"])
    # reply with the text extracted from the audio file // responder con el texto extraído del archivo de audio
    await update.message.reply_text(transcription_object["text"]) 
    
    # call the OpenAI API to generate a summary of the voice note // llamar a la API de OpenAI para generar un resumen de la nota de voz
    summary_gpt_response = openai.Completion.create(
        model="text-davinci-003",
        # The prompt is the text that the model will use to generate a response. I add some things about me so that the model can generate a more personalized response // El prompt es el texto que el modelo usará para generar una respuesta. Agrego algunas cosas sobre mí para que el modelo pueda generar una respuesta más personalizada
        prompt="Me acaban de enviar una nota de voz que dice lo siguiente: \n"+transcription_object["text"] + "\n --- FIN DE LA NOTA DE VOZ --- \n Crear, en español, un resumen breve pero específico de la nota de voz.",
        # The temperature is a number between 0 and 1 that determines how random the model's response will be // La temperatura es un número entre 0 y 1 que determina qué tan aleatoria será la respuesta del modelo
        temperature=0.7,
        # Tokens is kinda like the number of words the model will use to generate a response // Tokens es como el número de palabras que el modelo usará para generar una respuesta
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # get the text from the response // obtener el texto de la respuesta
    summary_text = (summary_gpt_response.choices[0].text)
    # decode the text // decodificar el texto
    decoded_summary_text = decode_utf8(summary_text)
    # print the decoded text // imprimir el texto decodificado
    print("Summary:\n"+decoded_summary_text)
    # Send the summary to the user // Enviar el resumen al usuario
    await update.message.reply_text(decoded_summary_text)
    # call the OpenAI API to generate a reply to the voice note // llamar a la API de OpenAI para generar una respuesta a la nota de voz
    reply_gpt_response = openai.Completion.create(
        model="text-davinci-003",
        prompt="Me acaban de enviar una nota de voz que dice lo siguiente: \n"+transcription_object["text"] + "\n --- FIN DE LA NOTA DE VOZ --- \n Crear una respuesta de mi parte, "+config.my_name + ", que primero repita los puntos principales de la nota para confirmar si se entendió.\n\n Sobre mí: \n" + config.about_me_spanish,
        temperature=0.7,
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # get the text from the response // obtener el texto de la respuesta
    reply_text = (reply_gpt_response.choices[0].text)
    # decode the text // decodificar el texto
    decoded_reply_text = decode_utf8(reply_text)
    # print the decoded text // imprimir el texto decodificado
    print("Reply:\n"+decoded_reply_text)
    # Send the reply to the user // Enviar la respuesta al usuario
    await update.message.reply_text('Posible respuesta:')
    await update.message.reply_text(decoded_reply_text)
    #delete the audio files after 1 day // eliminar los archivos de audio después de 1 día
    



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Mandame audios.")

async def sendInfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="No entiendo ese comando.")


if __name__ == '__main__':
    application = Application.builder().token(config.telegram_api_key).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), sendInfo)
    application.add_handler(text_handler)

    audio_handler = MessageHandler(filters.AUDIO, handle_audio)
    application.add_handler(audio_handler)

     # Other handlers
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)
    
    application.run_polling()