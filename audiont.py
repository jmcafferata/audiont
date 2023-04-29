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
import pathlib as Path
import requests
import pytz
import urllib.request
import telegram.constants
import logging
import requests
from bs4 import BeautifulSoup
import openai
import sys
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai.embeddings_utils import get_embedding
from openai.embeddings_utils import cosine_similarity
import traceback
import json
from telegram.constants import ParseMode

# function that reads settings.json (a key given by the user) and returns the value 
def get_settings(key):
    with open('settings.json') as json_file:
        data = json.load(json_file)
        return data[key]
    
# function that writes to settings.json (a key given by the user) and returns the value
def write_settings(key,value):
    with open('settings.json') as json_file:
        data = json.load(json_file)
        data[key] = value
        with open('settings.json', 'w') as outfile:
            json.dump(data, outfile)

# CONTANTS // CONSTANTES

# define the states of the conversation // definir los estados de la conversación
ASK_NAME, ASK_DESCRIPTION,ASK_MESSAGES,AWAIT_INSTRUCTIONS,ASK_MORE_MESSAGES,ASK_PAYEE,CONFIRM_PAYMENT = range(7)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.chat.send_chat_action(action=telegram.constants.ChatAction.TYPING)

    try:

        response = None # Initialize the 'response' variable here
    
        # get sender username
        username = update.message.from_user.username
        #get sender full name
        full_name = update.message.from_user.full_name

        #if sender isn't jmcafferata
        if username != config.my_username:
            response = await ai.secretary(update,update.message.text,context)
           
        else:
            response = await ai.chat(update,update.message.text,get_settings("GPTversion"))

        await update.message.reply_text(response)
        
        
        # if the response is an array, send each element of the array as a message // si la respuesta es un array, enviar cada elemento del array como un mensaje
        
        return
    except Exception as e:
        # print and send the formatted traceback // imprimir y enviar el traceback formateado
        traceback.print_exc()
        await update.message.reply_text(traceback.format_exc())
        

# function that handles the voice notes // función principal que maneja las notas de voz
async def handle_voice(update, context):

    message = update.message
    await update.message.chat.send_chat_action(action=telegram.constants.ChatAction.TYPING)

    # get sender username, but first check if it's None
    if update.message.from_user.username == None:
        username = update.message.from_user.full_name
    else:
        username = update.message.from_user.username

    try:

        transcription = await ai.transcribe_audio(update)
        response = None # Initialize the 'response' variable here

        # check if message has caption (es un audio de WhatsApp)
        if message.caption:

            await update.message.reply_text("El audio dice:")
            await update.message.reply_text(transcription)

            # check if username is  config.my_username
            if username == config.my_username:

                csvm.store_to_csv(message=transcription)
                # call the prompt function // llamar a la función prompt
                response = await ai.complete_prompt(reason="summary", message=transcription, username=update.message.from_user.username,update=update)
                
                # call the clean_options function // llamar a la función clean_options
                response_text, options = await clean.clean_options(response)
                
                # add the options to the current response options
                for option in options:
                    current_response_options.append(option)
            
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

        # if the message has no caption (it's a voice note)
        else:

            #if sender isn't jmcafferata
            if username != config.my_username:
                response = await ai.secretary(update,transcription,context)
                
            else:
                response = await ai.chat(update,transcription,get_settings("GPTversion"))

            await update.message.reply_text(response)
        
    except Exception as e:
        # print and send the formatted traceback // imprimir y enviar el traceback formateado
        traceback.print_exc()
        await update.message.reply_text(traceback.format_exc())
        
        
    return ConversationHandler.END


# function that handles the voice notes // función principal que maneja las notas de voz
async def handle_audio(update, context):

    message = update.message
    await update.message.chat.send_chat_action(action=telegram.constants.ChatAction.TYPING)

    # get sender username, but first check if it's None
    if update.message.from_user.username == None:
        username = update.message.from_user.full_name
    else:
        username = update.message.from_user.username

    try:

        transcription = await ai.transcribe_audio(update)
        response = None # Initialize the 'response' variable here

        # check if message has caption (es un audio de WhatsApp)
        if message.caption:

            await update.message.reply_text("El audio dice:")
            await update.message.reply_text(transcription)

            # check if username is  config.my_username
            if username == config.my_username:

                csvm.store_to_csv(message=transcription)
                # call the prompt function // llamar a la función prompt
                response = await ai.complete_prompt(reason="summary", message=transcription, username=update.message.from_user.username,update=update)
                
                # call the clean_options function // llamar a la función clean_options
                response_text, options = await clean.clean_options(response)
                
                # add the options to the current response options
                for option in options:
                    current_response_options.append(option)
            
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

        # if the message has no caption (it's a voice note)
        else:

            #if sender isn't jmcafferata
            if username != config.my_username:
                response = await ai.secretary(update,transcription,context)
                
            else:
                response = await ai.chat(update,transcription,get_settings("GPTversion"))

            await update.message.reply_text(response)
        
    except Exception as e:
        # print and send the formatted traceback // imprimir y enviar el traceback formateado
        traceback.print_exc()
        await update.message.reply_text(traceback.format_exc())
        
        
    return ConversationHandler.END

# function that handles the voice notes when responding to a voice note // función principal que maneja las notas de voz cuando se responde a una nota de voz
async def respond_audio(update, context):
    # call the transcribe_audio function // llamar a la función transcribe_audio
    transcription = await ai.transcribe_audio(update)
    response = await ai.complete_prompt(reason="answer", message=transcription, username=update.message.from_user.username,update=update)
    await update.message.reply_text(response)
    return ConversationHandler.END
   

# Function to handle files
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = update.callback_query.data
    print("Data: "+data)
    # if the data is a number, then it's an instruction // si los datos son un número, entonces es una instrucción
    if data.isdigit():
        print("current_response_options: "+str(current_response_options))
        response = await ai.complete_prompt("answer", current_response_options[int(data)], update.callback_query.from_user.username, update)
        # send a message saying that if they didn't like the response, they can send a voice note with instructions // enviar un mensaje diciendo que si no les gustó la respuesta, pueden enviar una nota de voz con instrucciones
        await update.callback_query.message.reply_text(response)
    return ConversationHandler.END
    
    # send a message saying that if they didn't like the response, they can send a voice note with instructions // enviar un mensaje diciendo que si no les gustó la respuesta, pueden enviar una nota de voz con instrucciones
    

async def chat3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Data: ['explain', 'green', 'hydrogen', 'news', 'in', 'a', 'few', 'steps'] make them a string
    try:
        write_settings(key="GPTversion",value="3")
        await update.message.reply_text("Estás usando ChatGPT 3 (es medio tonto pero es rápido y barato 👍👌)")
        
    except Exception as e:
        exception_traceback = traceback.format_exc()
        print('⬇️⬇️⬇️⬇️ Error en instructions ⬇️⬇️⬇️⬇️\n',exception_traceback)

async def chat4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Data: ['explain', 'green', 'hydrogen', 'news', 'in', 'a', 'few', 'steps'] make them a string
    try:
        write_settings(key="GPTversion",value="4")
        await update.message.reply_text("Estás usando ChatGPT 4 (es un poco más caro, no te zarpes🥲)")
        
    except Exception as e:
        exception_traceback = traceback.format_exc()
        print('⬇️⬇️⬇️⬇️ Error en instructions ⬇️⬇️⬇️⬇️\n',exception_traceback)

# main function // función principal
if __name__ == '__main__':

    current_response_options = []

    my_username = config.my_username

    # create the bot // crear el bot
    application = Application.builder().token(config.telegram_api_key).build()

    # use ai.generate_embeddings(file,column) to turn the column full_text in users/jmcafferata/justTweets.csv into a list of embeddings
    # print(ai.generate_embeddings("users/jmcafferata/cleandataNoRows.csv","full_text"))

    
    # for when the bot receives a text message // para cuando el bot recibe un archivo de audio
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text)
    application.add_handler(text_handler)


    # for when the bot receives a voice note // para cuando el bot recibe una nota de voz
    # exclude conversation states // excluir estados de conversación
    voice_handler = MessageHandler(filters.VOICE & (~filters.COMMAND), handle_voice)
    application.add_handler(voice_handler)

    # for when the bot receives a voice note // para cuando el bot recibe una nota de voz
    # exclude conversation states // excluir estados de conversación
    audio_handler = MessageHandler(filters.AUDIO & (~filters.COMMAND), handle_audio)
    application.add_handler(audio_handler)


    #/chat3 command
    chat3_handler = CommandHandler('chat3', chat3)
    application.add_handler(chat3_handler)

    #/chat4 command
    chat4_handler = CommandHandler('chat4', chat4)
    application.add_handler(chat4_handler)


    # a callback query handler // un manejador de consulta de devolución de llamada
    callback_handler = CallbackQueryHandler(callback=callback)
    application.add_handler(callback_handler)

    # start the bot // iniciar el bot
    application.run_polling()
    # logger.info('Bot started')