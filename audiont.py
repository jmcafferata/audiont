
# This code is used to process audio files from the telegram bot, get the text from the audio file and generate an automated response.
# Este código se usa para procesar archivos de audio del bot de telegram, obtener el texto del archivo de audio y generar una respuesta automatizada.

# import the necessary libraries // importar las librerías necesarias
import os  # operating system library that allows us to access the computer's file system // librería del sistema operativo que nos permite acceder al sistema de archivos del computador
import openai  # library used to access the OpenAI API // librería usada para acceder a la API de OpenAI
# library used to define the types of variables // librería usada para definir los tipos de variables
from typing import DefaultDict, Optional, Set
from collections import defaultdict
# library used to handle file paths // librería usada para manejar rutas de archivos
from pathlib import Path
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
import clean_options as clean  # import the clean_options file // importar el archivo clean_options
import re  # library used to handle regular expressions // librería usada para manejar expresiones regulares
from datetime import datetime
import csv
# library used to handle the Telegram bot // librería usada para manejar el bot de Telegram
from telegram.constants import ParseMode
import config  # import the config file // importar el archivo de configuración
import asyncio  # library used to handle asynchronous code // librería usada para manejar código asíncrono
# library used to communicate with the Telegram bot // librería usada para comunicarse con el bot de Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent

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

# store the audio message in the user's folder to be processed later // almacenar el mensaje de audio en la carpeta del usuario para ser procesado más tarde
def store_to_csv(username,sender,message):
    with open('users/'+username+'/messages.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), sender, message])

# get the last audio message sent to the user // obtener el último mensaje de audio enviado al usuario
def get_last_audio(username):
    # open the csv file users/username/messages.csv and find the last message sent by sender "other" // abrir el archivo csv users/username/messages.csv y encontrar el último mensaje enviado por el remitente "other"
    with open('users/'+username+'/messages.csv', 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reversed(list(reader)):
            if (row[1] == "other"):
                return row[2]

# use the OpenAI API to get the text from the audio file // usar la API de OpenAI para obtener el texto del archivo de audio 
async def transcribe_audio(update):
    # Extract the audio file from the message // Extraer el archivo de audio del mensaje
    new_file = await update.message.effective_attachment.get_file()
    # Download the audio file to the computer // Descargar el archivo de audio al computador
    await new_file.download_to_drive()
    # get the name of the audio file // obtener el nombre del archivo de audio
    file_path = Path(new_file.file_path).name
    # reply to the message, telling the user the audio file was received // responder al mensaje, diciendo al usuario que se recibió el archivo de audio
    await update.message.reply_text('Audio recibido. Esperá un toque que lo proceso. Te voy avisando.')
    # convert the audio file to a wav file // convertir el archivo de audio a un archivo wav
    new_audio_path = convert_to_wav(file_path)
    # open the wav file // abrir el archivo wav
    wav_audio = open(new_audio_path, "rb")
    # call the OpenAI API to get the text from the audio file // llamar a la API de OpenAI para obtener el texto del archivo de audio
    transcription_object = openai.Audio.transcribe(
        "whisper-1", wav_audio, language="es", prompt="esto es una nota de voz. hay momentos de silencio en el audio, cuidado con eso.")
    # print the text extracted from the audio file // imprimir el texto extraído del archivo de audio
    print("Transcription:\n"+transcription_object["text"])
    # store the transcription as a new line in users/username/messages.csv encoded in UTF-8 // almacenar la transcripción como una nueva línea en users/username/messages.csv codificada en UTF-8
    
    return transcription_object["text"]

# use the OpenAI API to generate answers // usar la API de OpenAI para generar respuestas
async def prompt(reason, transcription,username):
    if (reason == "summary"):
        clean.options = []
        prompt = "Yo soy un asistente virtual llamado Audion't. Mi tarea es escuchar los mensajes que mis amos reciben y ayudar a responderlos. \n\nMi amo se llama "+config.my_name+". "+config.about_me_spanish+"\n\nA mi amo le acaban de enviar un mensaje de voz. Dice lo siguiente: " + transcription + "\n\nTengo que ayudar a mi amo a responder este mensaje. Primero le voy a hacer un resumen del mensaje y luego le voy a dar 5 opciones de respuesta: las primeras 3 son contextuales y son títulos de posibles respuestas distintas (positiva, negativa, neutral) que se le podría dar al mensaje de voz (máximo 40 caracteres). la cuarta opción es -Otra respuesta-. Las opciones tienen que estar al final y con el formato 1.,2.,3.,4. y deben contener emojis que ilustren el sentimiento de la respuesta. \n\nResumen del mensaje de voz:\n"
    elif (reason == "instructions"):
        prompt = "Yo soy un asistente virtual llamado Audion't. Mi tarea es escuchar los mensajes que mis amos reciben y ayudar a responderlos. \n\nMi amo se llama "+config.my_name+". "+config.about_me_spanish+"\n\nA mi amo le acaban de enviar un mensaje de voz. Dice lo siguiente: " + get_last_audio(username) + "\n\nTengo que ayudar a mi amo a responder este mensaje. Me dio las siguientes instrucciones: \n'" + transcription + "'\n\nEscribir el mensaje de parte de mi amo hacia el remitente, usando sus instrucciones como guía.\n\nMensaje de mi amo:\n"
    # call the OpenAI API to generate a summary of the voice note // llamar a la API de OpenAI para generar un resumen de la nota de voz
    gpt_response = openai.Completion.create(
        model="text-davinci-003",
        # The prompt is the text that the model will use to generate a response. I add some things about me so that the model can generate a more personalized response // El prompt es el texto que el modelo usará para generar una respuesta. Agrego algunas cosas sobre mí para que el modelo pueda generar una respuesta más personalizada
        prompt=prompt,
        # The temperature is a number between 0 and 1 that determines how random the model's response will be // La temperatura es un número entre 0 y 1 que determina qué tan aleatoria será la respuesta del modelo
        temperature=0.7,
        # Tokens is kinda like the number of words the model will use to generate a response // Tokens es como el número de palabras que el modelo usará para generar una respuesta
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # get the text from the response // obtener el texto de la respuesta
    text = (gpt_response.choices[0].text)
    # decode the text // decodificar el texto
    decoded_text = decode_utf8(text)
    # print the decoded text // imprimir el texto decodificado
    print("Summary:\n"+decoded_text)
    return decoded_text

# function that handles the audio files // función principal que maneja los archivos de audio
async def handle_audio(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        transcription = await transcribe_audio(update)
        store_to_csv(username=update.message.from_user.username, message=transcription, sender="other")
        # reply to the message with the text extracted from the audio file // responder al mensaje con el texto extraído del archivo de audio
        await update.message.reply_text("El audio dice:")
        await update.message.reply_text(transcription)
        # call the prompt function // llamar a la función prompt
        response = await prompt("summary", transcription, update.message.from_user.username)
        # call the clean_options function // llamar a la función clean_options
        response_text, options = await clean.clean_options(response)
        # reply to the message with the summary and the 5 options // responder al mensaje con el resumen y las 5 opciones
        await update.message.reply_text(response_text, reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text=options[0], callback_data="0")
                ],
                [
                    InlineKeyboardButton(text=options[1], callback_data="1")
                ],
                [
                    InlineKeyboardButton(text=options[2], callback_data="2")
                ],
                [
                    InlineKeyboardButton(text=options[3], callback_data="3")
                ]
            ]
        ))
    else:
        await sendSubscribeMessage(update)

# function that handles the voice notes // función principal que maneja las notas de voz
async def handle_voice(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        transcription = await transcribe_audio(update)
        response = await prompt("instructions", transcription,update.message.from_user.username)
        await update.message.reply_text(response)
        print("Last audio: "+get_last_audio(update.message.from_user.username))
    else:
        await sendSubscribeMessage(update)

# sends a message when the user isn't subscribed // envía un mensaje cuando el usuario no está suscrito
async def sendSubscribeMessage(update):
    # create a row on logs.csv with the date, time and username of the user that sent the voice note // crear una fila en logs.csv con la fecha, hora y nombre de usuario del usuario que envió la nota de voz
    with open('logs.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), update.message.from_user.username])
    # send the user a message saying they are not subscribed // enviarle al usuario un mensaje diciendo que no está suscrito
    await update.message.reply_text('No estás suscrito. Para suscribirte, contactá a @jmcafferata o creá tu propio bot de Telegram usando el código de este repositorio.')
    await update.message.reply_text('github.com/jmcafferata/audiont')

# handles when the bot receives a start command // maneja cuando el bot recibe un comando de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="😊 Hola! Soy Audion't. Escucho mensajes de audio 🎧 y te ayudo a generar respuestas ✍️. Reenviame un audio o mandame un mensaje de voz!")

# handles when the bot receives a text message // maneja cuando el bot recibe un mensaje de texto
async def sendInfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

# handles when the bot receives something that is not a command // maneja cuando el bot recibe algo que no es un comando
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="No entiendo ese comando.")

# handles when the bot receives a callback query // maneja cuando el bot recibe una consulta de devolución de llamada
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the data from the callback query // obtener los datos de la consulta de devolución de llamada
    data = update.callback_query.data
    print("Data: "+clean.options[int(data)])
    # if the data is 1, edit the message to say that the user selected the first option // si los datos son 1, editar el mensaje para decir que el usuario seleccionó la primera opción
    response = await prompt("instructions", clean.options[int(data)], update.callback_query.from_user.username)
    #send a message saying that if they didn't like the response, they can send a voice note with instructions // enviar un mensaje diciendo que si no les gustó la respuesta, pueden enviar una nota de voz con instrucciones
    await update.callback_query.message.reply_text(response)
    await update.callback_query.message.reply_text("🥲 Si no te gustó la respuesta, podés mandarme una nota de voz con instrucciones 🗣️ o apretar otro botón.")


# main function // función principal
if __name__ == '__main__':
    # create the bot // crear el bot
    application = Application.builder().token(config.telegram_api_key).build()

    # add the handlers // agregar los manejadores
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), sendInfo)
    application.add_handler(text_handler)

    audio_handler = MessageHandler(filters.AUDIO, handle_audio)
    application.add_handler(audio_handler)

    voice_handler = MessageHandler(filters.VOICE, handle_voice)
    application.add_handler(voice_handler)

    # a callback query handler // un manejador de consulta de devolución de llamada
    callback_handler = CallbackQueryHandler(callback=callback)
    application.add_handler(callback_handler)

    #  add the unknown handler // agregar el manejador desconocido
    unknown_handler = MessageHandler(filters.COMMAND, unknown)
    application.add_handler(unknown_handler)

    # start the bot // iniciar el bot
    application.run_polling()
