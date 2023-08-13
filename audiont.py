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
    filters,
)
# library used to handle conversations // librería usada para manejar conversaciones
from telegram.ext import ConversationHandler
import csv  # library used to handle csv files // librería usada para manejar archivos csv
import config as config  # import the config file // importar el archivo de configuración
# library used to communicate with the Telegram bot // librería usada para comunicarse con el bot de Telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
# import the store_to_csv file // importar el archivo store_to_csv
import modules.csv_manipulation as csvm
# import the ai_functions file // importar el archivo ai_functions
import modules.ai_functions as ai
import telegram.constants
import traceback
from flask import Flask, request, redirect, url_for, flash
import os
from modules.settings_system import check_user_folder, get_settings, write_settings




# CONTANTS // CONSTANTES

# define the states of the conversation // definir los estados de la conversación
AWAIT_INSTRUCTIONS = range(1)

# start the conversation // iniciar la conversación


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    write_settings("uid", str(update.message.from_user.id),update.message.from_user.id)
    # send a message // enviar un mensaje
    await update.message.reply_text(
        config.start_message
    )
    # check if user has folder in users/ folder. if not, create it
    check_user_folder(update.message.from_user.id)
    return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    check_user_folder(update.message.from_user.id)

    await update.message.chat.send_chat_action(action=telegram.constants.ChatAction.TYPING)

    try:

        response = None  # Initialize the 'response' variable here

        # get sender username
        username = update.message.from_user.username
        # get sender full name
        full_name = update.message.from_user.full_name

        # if sender isn't in the approved users list, send a message and return
        if username not in config.approved_users:
            await ai.secretary(update, update.message.text, context)
           
        else:

            await ai.chat(update, update.message.text, get_settings("GPTversion",update.message.from_user.id))
        
        # if the response is an array, send each element of the array as a message // si la respuesta es un array, enviar cada elemento del array como un mensaje

        return
    except Exception as e:
        # print and send the formatted traceback // imprimir y enviar el traceback formateado
        traceback.print_exc()
        await update.message.reply_text(traceback.format_exc())


# function that handles the voice notes // función principal que maneja las notas de voz
async def handle_voice(update, context):

    print("handle_voice")
    print(str(update))

    check_user_folder(update.message.from_user.id)

    message = update.message
    await update.message.chat.send_chat_action(action=telegram.constants.ChatAction.TYPING)

    # get sender username, but first check if it's None
    if update.message.from_user.username == None:
        username = update.message.from_user.full_name
    else:
        username = update.message.from_user.username

    try:

        transcription = await ai.transcribe_audio(update)
        response = None  # Initialize the 'response' variable here

        await update.message.reply_text("El audio dice:")

        # check if transcription length is more than 4000 characters
        if len(transcription) > 4000:
            # separate the transcription in 4000 character chunks
            transcription_chunks = [
                transcription[i : i + 4000]
                for i in range(0, len(transcription), 4000)

            ]
            # send each chunk as a message // enviar cada chunk como un mensaje
            for chunk in transcription_chunks:
                await update.message.reply_text(chunk)

        else:
            # send the transcription as a message // enviar la transcripción como un mensaje
            await update.message.reply_text(transcription)
            
        # check if message has caption (es un audio de WhatsApp)
        if message.caption:

            csvm.store_to_csv(message=transcription)

        # if the message has no caption (it's a voice note)
        else:

            # if sender isn't jin the approved users list, send a message and return
            if username not in config.approved_users:
                response = await ai.secretary(update, transcription, context)

            else:
                response = await ai.chat(update, transcription, get_settings("GPTversion",update.message.from_user.id))

            

    except Exception as e:
        # print and send the formatted traceback // imprimir y enviar el traceback formateado
        traceback.print_exc()
        await update.message.reply_text(traceback.format_exc())

    return ConversationHandler.END





# Function to handle files
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #get user id from callback query
    uid = update.callback_query.from_user.id

    data = update.callback_query.data

    if data == "vectorizar":
        try:
            await ai.vectorize(update=update, context=context, uid=get_settings("uid",update.callback_query.from_user.id))
            await update.callback_query.message.reply_text("🎉 Vectorización completa!")
            await update.callback_query.message.reply_text("🙏Recordá mencionar el nombre del documento cuando quieras consultarlo")
        except Exception as e:
            # send traceback // enviar traceback
            traceback.print_exc()
            await update.callback_query.message.reply_text(traceback.format_exc())

    if data == "train_si":

        last_pcp_response = get_settings("pending_pcp_response", uid)
        split_data = last_pcp_response.split("Usuario:")[1].split("Roy Cortina:")
        prompt = split_data[0].strip()
        completion = "Roy Cortina:" + split_data[1].strip()

        csvdata = [(prompt, completion)]

        # if users/uid/pcp_pending.csv doesn't exist, create it
        if not os.path.exists("users/"+str(uid)+"/pcp_pending.csv"):
            with open("users/"+str(uid)+"/pcp_pending.csv", "w", newline='', encoding='utf-8') as csvfile:
                # prompt,completion
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(["prompt", "completion"])

        with open("users/"+str(uid)+"/pcp_pending.csv", "a", newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            for row in csvdata:
                csvwriter.writerow(row)

        # get the pending_pcp_message_id from settings.json
        pending_pcp_message_id = get_settings("pending_pcp_message_id", uid)

        # generate a prompt completion pair
        pcp_response = await ai.generate_prompt_completion_pair(uid)

        # write the pcp_response to settings.json
        write_settings(key="pending_pcp_response", value=pcp_response, uid=uid)

        # edit the message using the pending_pcp_message_id with the new pcp_response
        await context.bot.edit_message_text(chat_id=update.callback_query.message.chat_id, message_id=pending_pcp_message_id, text=pcp_response, reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(text='✅ Sí', callback_data="train_si"),
                InlineKeyboardButton(text='❌ No', callback_data="train_no"),
                InlineKeyboardButton(text='↩️ Deshacer', callback_data="train_undo")]]
        ))

    if data == "train_no":
        # generate a prompt completion pair
        pcp_response = await ai.generate_prompt_completion_pair(uid)

        # write the pcp_response to settings.json
        write_settings(key="pending_pcp_response", value=pcp_response, uid=uid)

        # get the pending_pcp_message_id from settings.json
        pending_pcp_message_id = get_settings("pending_pcp_message_id", uid)

        # edit the message using the pending_pcp_message_id with the new pcp_response
        await context.bot.edit_message_text(chat_id=update.callback_query.message.chat_id, message_id=pending_pcp_message_id, text=pcp_response, reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(text='✅ Sí', callback_data="train_si"),
                InlineKeyboardButton(text='❌ No', callback_data="train_no"),
                InlineKeyboardButton(text='↩️ Deshacer', callback_data="train_undo")]]
        ))

    if data == "train_undo":
        # open users/uid/pcp_pending.csv
        with open("users/"+str(uid)+"/pcp_pending.csv", "r",encoding="utf-8") as f:
            # read the last line
            last_line = f.readlines()[-1]
            # delete the last line
            lines = f.readlines()
            lines.pop()
        # write the lines back to users/uid/pcp_pending.csv
        with open("users/"+str(uid)+"/pcp_pending.csv", "w",encoding="utf-8") as f:
            f.writelines(lines)


        # edit the message using the pending_pcp_message_id with the new pcp_response
        await context.bot.edit_message_text(chat_id=update.callback_query.message.chat_id, message_id=pending_pcp_message_id, text="¡Eliminé el anterior! 🫡", reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(text='✅ Bien, sigamos', callback_data="train_no")]]
        ))

    return ConversationHandler.END

    # send a message saying that if they didn't like the response, they can send a voice note with instructions // enviar un mensaje diciendo que si no les gustó la respuesta, pueden enviar una nota de voz con instrucciones


async def chat3(update: Update, context: ContextTypes.DEFAULT_TYPE):

    check_user_folder(update.message.from_user.id)

    # Data: ['explain', 'green', 'hydrogen', 'news', 'in', 'a', 'few', 'steps'] make them a string
    try:
        write_settings(key="GPTversion", value="gpt-3.5-turbo", uid=update.message.from_user.id)
        await update.message.reply_text("Estás usando ChatGPT 3 (es medio tonto pero es rápido y barato 👍👌)")

    except Exception as e:
        exception_traceback = traceback.format_exc()
        print('⬇️⬇️⬇️⬇️ Error en instructions ⬇️⬇️⬇️⬇️\n', exception_traceback)


async def chat4(update: Update, context: ContextTypes.DEFAULT_TYPE):

    check_user_folder(update.message.from_user.id)

    # Data: ['explain', 'green', 'hydrogen', 'news', 'in', 'a', 'few', 'steps'] make them a string
    try:
        write_settings(key="GPTversion", value="gpt-4", uid=update.message.from_user.id)
        await update.message.reply_text("Estás usando ChatGPT 4 (es un poco más caro, no te zarpes🥲)")

    except Exception as e:
        exception_traceback = traceback.format_exc()
        print('⬇️⬇️⬇️⬇️ Error en instructions ⬇️⬇️⬇️⬇️\n', exception_traceback)

# a function that handles the /vectorizar command. It returns a link that takes them to redquequen.com/vectorizar/user_id // una función que maneja el comando /vectorizar. Devuelve un enlace que los lleva a redquequen.com/vectorizar/user_id

async def anotar_on(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        write_settings(key="anotar", value="on", uid=update.message.from_user.id)
        await update.message.reply_text("👂 Mandá audios o escribí cosas para que queden anotadas 📃")

    except Exception as e:
        exception_traceback = traceback.format_exc()
        print('⬇️⬇️⬇️⬇️ Error en instructions ⬇️⬇️⬇️⬇️\n', exception_traceback)


async def anotar_off(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        write_settings(key="anotar", value="of", uid=update.message.from_user.id)
        await update.message.reply_text("👂 Ya no voy a anotar más nada 📃")
    except Exception as e:
        exception_traceback = traceback.format_exc()
        print('⬇️⬇️⬇️⬇️ Error en instructions ⬇️⬇️⬇️⬇️\n', exception_traceback)

# a function that handles the /vectorizar command. It returns a link that takes them to redquequen.com/vectorizar/user_id // una función que maneja el comando /vectorizar. Devuelve un enlace que los lleva a redquequen.com/vectorizar/user_id



async def vectorizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the user id // obtener el id del usuario
    user_id = update.message.from_user.id
    # send a message with the link // enviar un mensaje con el enlace
    # get flask_testing from settings.json

    url = "Entrá a este link para subir un archivo:\n\n"
    if get_settings("flask_testing",update.message.from_user.id) == "True":
        url += config.test_server+"/" + \
            config.bot_code+"/vectorizar/"+str(user_id)
    else:
        url += config.website+"/"+config.bot_code+"/vectorizar/"+str(user_id)

    url += "\n\nPor favor 🤲 chequeá que el documento tenga un nombre que lo identifique bien, por ejemplo: 'Resúmenes de la materia Arte Indoamericano'"

    await update.message.reply_text(url, reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                                    text='Listo', callback_data="vectorizar")
            ]
        ]
    ))


async def entrenar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # clean the pending_pcp_list
    write_settings(key="pending_pcp_list", value=[], uid=update.message.from_user.id)
    # get prompt completion pair
    pcp_response = await ai.generate_prompt_completion_pair(update.message.from_user.id)

    # add the pcp_response to the settings.json file with the key "pending_pcp_response"
    write_settings(key="pending_pcp_response", value=pcp_response, uid=update.message.from_user.id)

    print('pending pcp response\n', get_settings("pending_pcp_response", update.message.from_user.id))
    # send a message with the prompt completion pair and a keyboard with two options: sí y no
    pcp_message = await update.message.reply_text(pcp_response, reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text='✅ Sí', callback_data="train_si"),
                InlineKeyboardButton(
                    text='❌ No', callback_data="train_no"),
                InlineKeyboardButton(
                    text='↩️ Deshacer', callback_data="train_undo")
            ]
        ]
    ))

    # add the pcp_message_id to the settings.json file with the key "pending_pcp_message_id"
    write_settings(key="pending_pcp_message_id", value=pcp_message.message_id, uid=update.message.from_user.id)
    print('message id\n', get_settings("pending_pcp_message_id", update.message.from_user.id))


async def flask_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the user id // obtener el id del usuario
    user_id = update.message.from_user.id
    # send a message with the link // enviar un mensaje con el enlace
    # get flask_testing from settings.json
    if get_settings("flask_testing",update.message.from_user.id) == "True":
        write_settings(key="flask_testing", value="False", uid=update.message.from_user.id)
        await update.message.reply_text("flask_testing is now False")
    else:
        write_settings(key="flask_testing", value="True", uid=update.message.from_user.id)
        await update.message.reply_text("flask_testing is now True")
    await ai.vectorize_new(update,context,user_id)




# main function // función principal
if __name__ == '__main__':

    current_response_options = []

    my_username = config.my_username

    # create the bot // crear el bot
    application = Application.builder().token(config.telegram_api_key).build()


    # start handler
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # for when the bot receives a text message // para cuando el bot recibe un archivo de audio
    text_handler = MessageHandler(
        filters.TEXT & (~filters.COMMAND), handle_text)
    application.add_handler(text_handler)

    # for when the bot receives a voice note // para cuando el bot recibe una nota de voz
    # exclude conversation states // excluir estados de conversación
    voice_handler = MessageHandler(
        # filters VOICE or AUDIO
        filters.VOICE | filters.AUDIO & (~filters.COMMAND), handle_voice)
    application.add_handler(voice_handler)
    

    # /chat3 command
    chat3_handler = CommandHandler('chat3', chat3)
    application.add_handler(chat3_handler)

    # /chat4 command
    chat4_handler = CommandHandler('chat4', chat4)
    application.add_handler(chat4_handler)

    # /vectorizar command
    vectorizar_handler = CommandHandler('vectorizar', vectorizar)
    application.add_handler(vectorizar_handler)

    # /test command
    flask_test_handler = CommandHandler('flask_test', flask_test)
    application.add_handler(flask_test_handler)

    # /entrenar command
    entrenar_handler = CommandHandler('entrenar', entrenar)
    application.add_handler(entrenar_handler)

    anotar_on_handler = CommandHandler('anotar_on', anotar_on)
    application.add_handler(anotar_on_handler)

    anotar_off_handler = CommandHandler('anotar_off', anotar_off)
    application.add_handler(anotar_off_handler)

    # a callback query handler // un manejador de consulta de devolución de llamada
    callback_handler = CallbackQueryHandler(callback=callback)
    application.add_handler(callback_handler)

    # start the bot // iniciar el bot
    application.run_polling()
    # logger.info('Bot started')

   