
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

# this is an example CURL request to the MercadoPago API
# curl -X POST \
#       'https://api.mercadopago.com/v1/payments' \
#       -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
#       -H 'Content-Type: application/json' \ 
#       -d '{
#   "additional_info": {
#     "items": [
#       {
#         "id": "MLB2907679857",
#         "title": "Point Mini",
#         "description": "Producto Point para cobros con tarjetas mediante bluetooth",
#         "picture_url": "https://http2.mlstatic.com/resources/frontend/statics/growth-sellers-landings/device-mlb-point-i_medium@2x.png",
#         "category_id": "electronics",
#         "quantity": 1,
#         "unit_price": 58.8
#       }
#     ],
#     "payer": {
#       "first_name": "Test",
#       "last_name": "Test",
#       "phone": {
#         "area_code": 11,
#         "number": "987654321"
#       },
#       "address": {}
#     },
#     "shipments": {
#       "receiver_address": {
#         "zip_code": "12312-123",
#         "state_name": "Rio de Janeiro",
#         "city_name": "Buzios",
#         "street_name": "Av das Nacoes Unidas",
#         "street_number": 3003
#       }
#     },
#     "barcode": {}
#   },
#   "description": "Payment for product",
#   "external_reference": "MP0001",
#   "installments": 1,
#   "metadata": {},
#   "payer": {
#     "entity_type": "individual",
#     "type": "customer",
#     "identification": {}
#   },
#   "payment_method_id": "visa",
#   "token": "ff8080814c11e237014c1ff593b57b4d",
#   "transaction_amount": 58.8
# }'

# CONTANTS // CONSTANTES

# define the states of the conversation // definir los estados de la conversación
ASK_NAME, ASK_DESCRIPTION,ASK_MESSAGES,AWAIT_INSTRUCTIONS,ASK_MORE_MESSAGES,ASK_PAYEE,CONFIRM_PAYMENT = range(7)

# function that handles the audio files // función principal que maneja los archivos de audio

async def handle_audio(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username in config.subscribers:
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
            response = await ai.complete_prompt(reason="summary", transcription=transcription, username=update.message.from_user.username,update=update)
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
    if update.message.from_user.username in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        try:
            transcription = await ai.transcribe_audio(update)
            response = await ai.complete_prompt(reason="assistance", transcription=transcription, username=update.message.from_user.username,update=update)
            # check if the response is a path like users/username/files/... // verificar si la respuesta es un path como users/username/files/...
            if Path.Path(response).is_file():
                # send the document // enviar el archivo
                await update.message.reply_document(document=open(response, 'rb'))
                
            else:
                # send the text // enviar el texto
                await update.message.reply_text(response)
        except:
            pass
    else:
        await subs.sendSubscribeMessage(update)
    return ConversationHandler.END

# function that handles the voice notes when responding to a voice note // función principal que maneja las notas de voz cuando se responde a una nota de voz
async def respond_audio(update, context):
    # check if username in config.subscribers // verificar si el username está en config.subscribers
    if update.message.from_user.username in config.subscribers:
        # call the transcribe_audio function // llamar a la función transcribe_audio
        transcription = await ai.transcribe_audio(update)
        response = await ai.complete_prompt(reason="instructions", transcription=transcription, username=update.message.from_user.username,update=update)
        await update.message.reply_text(response)
        return ConversationHandler.END
    else:
        await subs.sendSubscribeMessage(update)

#++++++++++++++++++++++++++ STEP ONE +++++++++++++++++++++++++++
# handles when the bot receives a start command // maneja cuando el bot recibe un comando de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Starting conversation with user: "+update.message.from_user.username)
    # create a folder for the user with their username, and inside it, a file called messages.csv // crear una carpeta para el usuario con su username, y dentro de ella, un archivo llamado messages.csv
    csvm.create_user_folder(update.message.from_user.username)
    print("Created folder for user: "+update.message.from_user.username)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="😊 Hola! Soy Audion't. Escucho mensajes de audio 🎧 y te ayudo a generar respuestas ✍️. Reenviame un audio o mandame un mensaje de voz!")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Escribí tu nombre 👇")
    return ASK_NAME

#++++++++++++++++++++++++++ STEP TWO +++++++++++++++++++++++++++
# handles when the bot receives a name // maneja cuando el bot recibe un nombre
async def ask_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the name from the message // obtener el nombre del mensaje
    user_name = update.message.text
    print("User name: "+user_name)
    # update the users/username/data.json file with the name // actualizar el archivo users/username/data.json con el nombre
    csvm.create_user_data(update.message.from_user.username, "name", user_name)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Gracias, {}. Ahora decime algo sobre vos (me podés escribir o mandar un audio):".format(user_name))
    return ASK_DESCRIPTION

#++++++++++++++++++++++++++ STEP THREE +++++++++++++++++++++++++++
# handles when the bot receives a description // maneja cuando el bot recibe una descripción
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the description from the message // obtener la descripción del mensaje
    user_description = update.message.text
    print("User description: "+user_description)
    # update the users/username/data.json file with the description // actualizar el archivo users/username/data.json con la descripción
    csvm.create_user_data(update.message.from_user.username, "description", user_description)
    response = await ai.complete_prompt(reason="description", transcription=user_description, username=update.message.from_user.username,update=update)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Ahora andá a Whatsapp, copiate algunos mensajes tuyos y pegalos acá 👇. Así aprendo a escribir como vos.")
    return ASK_MESSAGES

# handles when the description is a voice note // maneja cuando la descripción es una nota de voz
async def get_description_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # call the transcribe_audio function // llamar a la función transcribe_audio
    transcription = await ai.transcribe_audio(update)
    print("User description: "+transcription)
    # update the users/username/data.json file with the description // actualizar el archivo users/username/data.json con la descripción
    csvm.create_user_data(update.message.from_user.username, "description", transcription)
    response = await ai.complete_prompt(reason="description", transcription=transcription, username=update.message.from_user.username,update=update)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bien. Ahora andá a Whatsapp, copiate algunos mensajes tuyos y pegalos acá 👇. Así aprendo a escribir como vos.")
    return ASK_MESSAGES

#++++++++++++++++++++++++++ STEP FOUR +++++++++++++++++++++++++++
# handles when the bot receives a name // maneja cuando el bot recibe un nombre
async def save_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("asking messages")
    user_messages = update.message.text
    # update the users/username/data.json file with the name // actualizar el archivo users/username/data.json con el nombre
    csvm.create_user_data(update.message.from_user.username, "messages", user_messages)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bravo! Ahora considerame un doble tuyo. Reenviame un audio que te hayan mandado y yo te ayudo a contestarlo. ¡Más tiempo libre!")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Cuando quieras que aprenda más cosas, escribime /aprender")
    return ConversationHandler.END

# handles when the bot receives a name // maneja cuando el bot recibe un nombre
async def save_new_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_messages = update.message.text
    # update the users/username/data.json file with the name // actualizar el archivo users/username/data.json con el nombre
    csvm.update_user_data(update.message.from_user.username, "messages", user_messages)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Messi rve una bocha!")
    return ConversationHandler.END

async def pagar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ask for the amount // preguntar por la cantidad
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¿Cuánto querés pagar?")
    return ASK_PAYEE

async def ask_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the amount from the message // obtener la cantidad del mensaje
    amount = update.message.text
    print("Amount: "+amount)
    # update the users/username/data.json file with the amount // actualizar el archivo users/username/data.json con la cantidad
    csvm.create_user_data(update.message.from_user.username, "amount", amount)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¿A quién querés pagar?")
    return CONFIRM_PAYMENT

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the payee from the message // obtener el beneficiario del mensaje
    payee = update.message.text
    print("Payee: "+payee)
    # update the users/username/data.json file with the payee // actualizar el archivo users/username/data.json con el beneficiario
    csvm.create_user_data(update.message.from_user.username, "payee", payee)
    # create the keyboard // crear el teclado
    keyboard = [[InlineKeyboardButton("Sí", callback_data='yes'), InlineKeyboardButton("No", callback_data='no')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # send the message with the keyboard // enviar el mensaje con el teclado
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¿Estás seguro que querés pagar {} a {}?".format(csvm.get_user_data(update.message.from_user.username, "amount"), csvm.get_user_data(update.message.from_user.username, "payee")), reply_markup=reply_markup)
    return CONFIRM_PAYMENT

async def confirm_payment_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # get the payee from the message // obtener el beneficiario del mensaje
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Listo! Pagaste {} a {}".format(csvm.get_user_data(update.message.from_user.username, "amount"), csvm.get_user_data(update.message.from_user.username, "payee")))
    return ConversationHandler.END

# handles when the bot receives something that is not a command // maneja cuando el bot recibe algo que no es un comando
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text="No entiendo ese comando.")

# handles when the bot receives a callback query // maneja cuando el bot recibe una consulta de devolución de llamada
async def aprender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Si querés darme datos, andá a WhatsApp, copiá mensajes de texto y pegalos acá 👇.")
    return ASK_MORE_MESSAGES

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        response = await ai.complete_prompt("assistance", text, update.message.from_user.username,update)
        await context.bot.send_message(chat_id=update.effective_chat.id,text=response)
    except:
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

    # for when the bot receives a start command // para cuando el bot recibe un comando de inicio
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),CommandHandler('aprender', aprender),CommandHandler('pagar', pagar)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & (~filters.COMMAND), ask_description)],
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & (~filters.COMMAND), get_description),MessageHandler(filters.VOICE, get_description_voice)],
            ASK_MESSAGES: [MessageHandler(filters.TEXT & (~filters.COMMAND), save_messages)],
            AWAIT_INSTRUCTIONS: [MessageHandler(filters.TEXT & (~filters.COMMAND), respond_audio)],
            ASK_MORE_MESSAGES: [MessageHandler(filters.TEXT & (~filters.COMMAND), save_new_messages)],
            ASK_PAYEE: [MessageHandler(filters.TEXT & (~filters.COMMAND), ask_amount)],
            CONFIRM_PAYMENT: [MessageHandler(filters.TEXT & (~filters.COMMAND), confirm_payment)],
        },fallbacks=[MessageHandler(filters.COMMAND, unknown)])
    application.add_handler(conv_handler)

    # for when the bot receives a learn command // para cuando el bot recibe un comando de inicio
    start_handler = CommandHandler('aprender', aprender)
    application.add_handler(start_handler)

    # for when the bot receives a payment command // para cuando el bot recibe un comando de inicio
    payment_handler = CommandHandler('pagar', pagar)
    application.add_handler(payment_handler)


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