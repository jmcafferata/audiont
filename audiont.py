
# This code is used to process audio files from the telegram bot, get the text from the audio file and generate an automated response.
# Este código se usa para procesar archivos de audio del bot de telegram, obtener el texto del archivo de audio y generar una respuesta automatizada.

# import the necessary libraries // importar las librerías necesarias
from typing import DefaultDict, Optional, Set # library used to define the types of variables // librería usada para definir los tipos de variables
from collections import defaultdict # library used to handle dictionaries // librería usada para manejar diccionarios
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
import modules.clean_options as clean  # import the clean_options file // importar el archivo clean_options
import re  # library used to handle regular expressions // librería usada para manejar expresiones regulares
from datetime import datetime # library used to handle dates // librería usada para manejar fechas
import csv # library used to handle csv files // librería usada para manejar archivos csv
import config as config  # import the config file // importar el archivo de configuración
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # library used to communicate with the Telegram bot // librería usada para comunicarse con el bot de Telegram
import modules.decode_utf8 # import the decode_utf8 file // importar el archivo decode_utf8
import modules.convert_to_wav # import the convert_to_wav file // importar el archivo convert_to_wav
import modules.csv_manipulation as csvm # import the store_to_csv file // importar el archivo store_to_csv
import modules.ai_functions as ai # import the ai_functions file // importar el archivo ai_functions 
import modules.subscriptions as subs # import the subscriptions file // importar el archivo subscriptions

# function that handles the audio files // función principal que maneja los archivos de audio
async def handle_audio(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        transcription = await ai.transcribe_audio(update)
        csvm.store_to_csv(username=update.message.from_user.username, message=transcription, sender="other")
        # reply to the message with the text extracted from the audio file // responder al mensaje con el texto extraído del archivo de audio
        await update.message.reply_text("El audio dice:")
        await update.message.reply_text(transcription)
        print(update)
        # call the prompt function // llamar a la función prompt
        response = await ai.complete_prompt(reason="summary", transcription=transcription, username=update.message.from_user.username)
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
        await subs.sendSubscribeMessage(update)

# function that handles the voice notes // función principal que maneja las notas de voz
async def handle_voice(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        transcription = await ai.transcribe_audio(update)
        response = await ai.complete_prompt(reason="instructions", transcription=transcription,username=update.message.from_user.username)
        await update.message.reply_text(response)
        print("Last audio: "+csvm.get_last_audio(update.message.from_user.username))
    else:
        await subs.sendSubscribeMessage(update)


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
    response = await ai.complete_prompt("instructions", clean.options[int(data)], update.callback_query.from_user.username)
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





