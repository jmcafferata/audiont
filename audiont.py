# -*- coding: utf-8 -*-
# This code is used to process audio files from the telegram bot, get the text from the audio file and generate an automated response.
# Este código se usa para procesar archivos de audio del bot de telegram, obtener el texto del archivo de audio y generar una respuesta automatizada.

# import the necessary libraries // importar las librerías necesarias
# library used to define the types of variables // librería usada para definir los tipos de variables
from typing import DefaultDict, Optional, Set
# library used to handle dictionaries // librería usada para manejar diccionarios
from collections import defaultdict
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
# library used to handle conversations // librería usada para manejar conversaciones
from telegram.ext import ConversationHandler
# import the clean_options file // importar el archivo clean_options
import modules.clean_options as clean
import re  # library used to handle regular expressions // librería usada para manejar expresiones regulares
# library used to handle dates // librería usada para manejar fechas
from datetime import datetime
import csv  # library used to handle csv files // librería usada para manejar archivos csv
import config as config  # import the config file // importar el archivo de configuración
# library used to communicate with the Telegram bot // librería usada para comunicarse con el bot de Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# import the decode_utf8 file // importar el archivo decode_utf8
import modules.decode_utf8
# import the convert_to_wav file // importar el archivo convert_to_wav
import modules.convert_to_wav
# import the store_to_csv file // importar el archivo store_to_csv
import modules.csv_manipulation as csvm
# import the ai_functions file // importar el archivo ai_functions
import modules.ai_functions as ai
# import the subscriptions file // importar el archivo subscriptions
import modules.subscriptions as subs
import pathlib as Path
import requests
import pytz
import urllib.request
import telegram.constants
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CONTANTS // CONSTANTES

# define the states of the conversation // definir los estados de la conversación
ASK_NAME, ASK_DESCRIPTION,ASK_MESSAGES,AWAIT_INSTRUCTIONS,ASK_MORE_MESSAGES,ASK_PAYEE,CONFIRM_PAYMENT = range(7)

# function that handles the audio files // función principal que maneja los archivos de audio

async def handle_audio(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username not in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        
        try:
            transcription = await ai.transcribe_audio(update)
            # if there's an error send a message // si hay un error enviar un mensaje
        except:
            pass
        else:
            csvm.store_to_csv(username=update.message.from_user.username,
                            message=transcription, sender="other")
            # reply to the message with the text extracted from the audio file // responder al mensaje con el texto extraído del archivo de audio
            await update.message.reply_text("El audio dice:")
            await update.message.reply_text(transcription)
            
            # call the prompt function // llamar a la función prompt
            response = await ai.complete_prompt(reason="summary", message=transcription, username=update.message.from_user.username,update=update)
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
            return AWAIT_INSTRUCTIONS            
    else:
        await subs.sendSubscribeMessage(update)

# function that handles the voice notes // función principal que maneja las notas de voz
async def handle_voice(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username not in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        try:
            transcription = await ai.transcribe_audio(update)
            response = await ai.complete_prompt(reason="assistance", message=transcription, username=update.message.from_user.username,update=update)
            # check if the response is a path like users/username/files/... // verificar si la respuesta es un path como users/username/files/...
            if Path.Path(response).is_file():
                # send the document // enviar el archivo
                await update.message.reply_document(document=open(response, 'rb'))
                
            else:
                # send the text // enviar el texto
                await update.message.reply_text(response)
        except Exception as e:
            print('Algo falló. \n'+str(e))
            pass
    else:
        await subs.sendSubscribeMessage(update)
    return ConversationHandler.END

# function that handles the voice notes when responding to a voice note // función principal que maneja las notas de voz cuando se responde a una nota de voz
async def respond_audio(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username not in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        transcription = await ai.transcribe_audio(update)
        response = await ai.complete_prompt(reason="instructions", message=transcription, username=update.message.from_user.username,update=update)
        await update.message.reply_text(response)
        return ConversationHandler.END
    else:
        await subs.sendSubscribeMessage(update)

# handles when the bot receives something that is not a command // maneja cuando el bot recibe algo que no es un comando
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="No entiendo ese comando.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # remove any newlines from the text // eliminar cualquier salto de línea del texto
    text = update.message.text.replace('\n', ' ')
    text = update.message.text
    await update.message.chat.send_chat_action(action=telegram.constants.ChatAction.TYPING)

    try:
        response = await ai.complete_prompt("assistance", text, update.message.from_user.username,update)


        await context.bot.send_message(chat_id=update.effective_chat.id,text=response)
    except Exception as e:
        print(e)
        return

# Function to handle files
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Extract the file and its description from the message
    file = await update.message.document.get_file()
    description = update.message.caption
    #print the file components
    

    # Get the user's username
    username = update.message.from_user.username

  # Save the file to the users/{username}/files folder
    file_path = "users/"+username+"/files/"
    print('file id: '+file.file_id)
    print('file path: '+file.file_path)
    print('file uid: '+file.file_unique_id)
    print('file size: '+str(file.file_size))

    # Remove the duplicate file path assignment
    new_file_path = file_path + file.file_path.split('/')[-1]
    print('new file path: '+new_file_path)

    # Make sure that the directories in the file path exist
    import os
    os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

    urllib.request.urlretrieve(file.file_path, new_file_path)


    timezone = pytz.timezone("America/Argentina/Buenos_Aires")
    # Store the file path, the time of the message (in Buenos Aires time), and the description
    now = datetime.now(timezone)
    file_entry = f"{now.strftime('%d/%m/%Y %H:%M:%S')}|{description}: {new_file_path}|{ai.get_embedding(description,'text-embedding-ada-002')}\n"
  
    # Save the entry to the users/{username}/messages.csv file
    with open(f"users/{username}/messages.csv", "a", encoding="utf-8") as f:
        f.write(file_entry)

    # Send a confirmation message to the user
    await update.message.reply_text("Archivo y descripción guardados correctamente.")


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the data from the callback query // obtener los datos de la consulta de devolución de llamada
    data = update.callback_query.data
    print("Data: "+data)
    # if the data is a number, then it's an instruction // si los datos son un número, entonces es una instrucción
    if data.isdigit():
        response = await ai.complete_prompt("instructions", clean.options[int(data)], update.callback_query.from_user.username,update)
        # send a message saying that if they didn't like the response, they can send a voice note with instructions // enviar un mensaje diciendo que si no les gustó la respuesta, pueden enviar una nota de voz con instrucciones
        await update.callback_query.message.reply_text(response)
        await update.callback_query.message.reply_text("🥲 Si no te gustó la respuesta, podés mandarme una nota de voz con instrucciones 🗣️ o apretar otro botón.")
    



# main function // función principal
if __name__ == '__main__':

    # create the bot // crear el bot
    application = Application.builder().token(config.telegram_api_key).build()

    # use ai.generate_embeddings(file,column) to turn the column full_text in users/jmcafferata/justTweets.csv into a list of embeddings
    # print(ai.generate_embeddings("users/jmcafferata/cleandataNoRows.csv","full_text"))

 

    # for when the bot receives an audio file // para cuando el bot recibe un archivo de audio
    audio_handler = MessageHandler(filters.AUDIO, handle_audio)
    application.add_handler(audio_handler)

    
    # for when the bot receives a text message // para cuando el bot recibe un archivo de audio
    text_handler = MessageHandler(filters.TEXT, handle_text)
    application.add_handler(text_handler)


    # for when the bot receives a voice note // para cuando el bot recibe una nota de voz
    # exclude conversation states // excluir estados de conversación
    voice_handler = MessageHandler(filters.VOICE & (~filters.COMMAND), handle_voice)
    application.add_handler(voice_handler)

    file_handler = MessageHandler(filters.Document.ALL, handle_file)
    application.add_handler(file_handler)

    # a callback query handler // un manejador de consulta de devolución de llamada
    callback_handler = CallbackQueryHandler(callback=callback)
    application.add_handler(callback_handler)

    # start the bot // iniciar el bot
    application.run_polling()
    logger.info('Bot started')