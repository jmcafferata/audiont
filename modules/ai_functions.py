import modules.clean_options as clean
import openai
import modules.convert_to_wav as convert
import modules.csv_manipulation as csvm
import modules.decode_utf8 as decode
import json
from pathlib import Path # library used to handle file paths // librería usada para manejar rutas de archivos
import config as config # import the config file // importar el archivo de configuración
import pandas as pd # library used to handle dataframes // librería usada para manejar dataframes
from openai.embeddings_utils import get_embedding
from openai.embeddings_utils import cosine_similarity
import numpy as np
from ast import literal_eval
from datetime import datetime
import pytz
timezone = pytz.timezone('America/Argentina/Buenos_Aires')
from io import StringIO
import os

# set the OpenAI API key, so the code can access the API // establecer la clave de la API de OpenAI, para que el código pueda acceder a la API
openai.api_key = config.openai_api_key



def check_and_compute_cosine_similarity(x, message_vector):
    x = np.array(literal_eval(x), dtype=np.float64)  # Convert x to float64
    return cosine_similarity(x, message_vector)


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
    try:
        new_audio_path = convert.convert_to_wav(file_path)
    except Exception as e:
        print("⬇️⬇️⬇️⬇️ Error en la conversión de audio ⬇️⬇️⬇️⬇️\n",e)
        # send a message to the user, telling them there was an error // enviar un mensaje al usuario, diciéndoles que hubo un error
        await update.message.reply_text('Hubo un error en la conversión de audio. Probá de nuevo.')
        # send e
        await update.message.reply_text(str(e))
        # send an images/cat.jpg to the user // enviar una imagen a la usuaria
        await update.message.reply_photo(open('images/cat.jpg', 'rb'))
    else:
        # open the wav file // abrir el archivo wav
        wav_audio = open(new_audio_path, "rb")
        # call the OpenAI API to get the text from the audio file // llamar a la API de OpenAI para obtener el texto del archivo de audio
        try:
            transcription_object = openai.Audio.transcribe(
            "whisper-1", wav_audio, language="es", prompt="esto es una nota de voz. hay momentos de silencio en el audio, cuidado con eso.")
            print("Transcription:\n"+transcription_object["text"])
        except Exception as e:
            print("⬇️⬇️⬇️⬇️ Error en la transcripción de audio ⬇️⬇️⬇️⬇️\n",e)
            # send a message to the user, telling them there was an error // enviar un mensaje al usuario, diciéndoles que hubo un error
            await update.message.reply_text('Hubo un error en la transcripción de audio. Probá de nuevo.')
            # send e
            await update.message.reply_text(str(e))
            # send an images/cat.jpg to the user // enviar una imagen a la usuaria
            await update.message.reply_photo(open('images/sad.jpg', 'rb'))
            raise e
        else:
            print("Transcription:\n"+transcription_object["text"])
            # delete audio files from the server
            wav_audio.close()
            os.remove(file_path)
            os.remove(new_audio_path)


            return transcription_object["text"]

# use the OpenAI API to generate answers // usar la API de OpenAI para generar respuestas
async def complete_prompt(reason, message,username,update):

    

    
    # THE JUICE // EL JUGO

    now = datetime.now(timezone)
    
    mensajes_file = "messages.csv"

    with open(mensajes_file, 'rb') as f:
        csv_str = f.read()

    messages_df = pd.read_csv(StringIO(csv_str.decode('utf-8')), sep='|', encoding='utf-8')

    # mensajes sim va a ser el dataframe con las similarities
    mensajes_sim = messages_df

    # Get the embedding for the message
    message_to_vectorize = now.strftime("%d/%m/%Y %H:%M:%S")+' - '+username+': '+message
    message_vector = get_embedding(message_to_vectorize,'text-embedding-ada-002')

    # store the message in a csv file
    with open(mensajes_file, 'a', encoding='utf-8') as f:
        #write the date, message and embedding
        message_row =now.strftime("%d/%m/%Y %H:%M:%S")+'|'+username+'|'+message
        f.write(message_row+'|'+str(message_vector)+'\n')
        print('De: ' + username + '\nMensaje: '+message_row)
        print('message added to csv')
        #close
        f.close()

    # Calculate cosine similarity
    try:
        mensajes_sim['similarity'] = mensajes_sim['embedding'].apply(lambda x: check_and_compute_cosine_similarity(x, message_vector))
    except Exception as e:
        print("⬇️⬇️⬇️⬇️ Error en el cálculo de similitud ⬇️⬇️⬇️⬇️\n",e)

    # sort by similarity
    mensajes_sim = mensajes_sim.sort_values(by=['similarity'], ascending=False)
    
    
    mensajes_similares = '\n\nMensajes previos:\n\n'
    print(mensajes_similares)

    for index, row in mensajes_sim[['fecha', 'sender','mensaje']].head(50).iterrows():
        if row['sender'] != "Audion't":
            mensaje_similar = str(row['fecha']) + ' - De: ' +row['sender']+ ' - Mensaje:'+ str(row['mensaje'])
            mensajes_similares += mensaje_similar + '\n'
            print(mensaje_similar)

    print('################## FIN DE MENSAJES SIMILARES ##################')

    #get 20 most recent messages from messages_df
    mensajes_recientes = '\n\nMensajes recientes:\n\n'
    print(mensajes_recientes)

    for index, row in messages_df[['fecha', 'mensaje','sender']].tail(20).iterrows():
        # if sender isn't audion't
        if row['sender'] != "Audion't":
            mensaje_reciente = str(row['fecha']) + ' - De: ' +row['sender']+ ' - Mensaje:'+ str(row['mensaje'])
            mensajes_recientes += mensaje_reciente + '\n'
            print(mensaje_reciente)

    print('################## FIN DE MENSAJES RECIENTES ##################')


    assistant_config =  """Sos Audion't, un amigo de J. M. Cafferata (jmcafferata).
    Sos un argentino nacional y popular buena onda y amable, y estás predispuesto a ayudar en cualquier cosa.
    Recibís y compartís información sobre Juan Manuel Cafferata (o Juanma, o J. M.).
    Distintas personas, además de Juanma, te hablan.
    Hoy es """+now.strftime("%A %d/%m/%Y %H:%M:%S")+""" (la hora esta en formato 24h).\n
    Si un mensaje suena como una consulta (como si fuera una query de Google, ejemplo 'tareas de hoy'),
    responder con información clara, concisa, al grano, precisa.
    Para ponerte en contexto, podés usar este registro de mensajes enviados relacionados con la consulta.
    Cada mensaje tiene la fecha, hora y usuario que lo envió, lo cual puede ser útil para entender el contexto:
    \n\n"""+mensajes_similares+"""
    \n\nHablás en tono muy, muy argentino informal y amigable, revolucionario.\n\n"""+config.personalidad+config.vocabulario
    print(assistant_config)
    if (reason == "summary"):
        clean.options = []
        prompt =  "Hola, me acaban de enviar un mensaje de voz. Dice lo siguiente: " + message + """
        "\n\nTengo que responder este mensaje. Haceme un resumen del mensaje y dame 4 opciones de respuesta:
        las primeras 3 son contextuales y son títulos de posibles respuestas distintas (positiva, negativa, neutral)
        que se le podría dar al mensaje de voz (máximo 40 caracteres). la cuarta opción es -Otra respuesta-.
        Las opciones tienen que estar al final y con el formato 1.,2.,3.,4. y deben contener emojis que ilustren el sentimiento de la respuesta.
        \n\nResumen del mensaje de voz:\n"""
    elif (reason == "instructions"):
        prompt = """\n\nMe acaban de enviar un mensaje de voz. Dice lo siguiente: """ + csvm.get_last_audio(username) + """
        \n\nTengo que responder este mensaje con las siguientes instrucciones: \n""" + message + """
        \n\nEscribir el mensaje de parte mía hacia el remitente, usando mis instrucciones como guía (pero no es necesario poner literalmente lo que dice la instrucción),
        mi personalidad y usando el mismo tono conversacional que mi interlocutor. Usar los mensajes de Whatsapp como template para escribir igual a mí
        (pero sin la hora y sin poner mi nombre al principio). Que sea muy natural, que parezca el cuerpo de un mensaje de chat.\n\nMi respuesta:\n"""
    elif (reason == "assistance"):
        print("Asistencia")
        prompt = {"role":"user","content":message}

        

    chat_messages = []
    chat_messages.append({"role" : "system","content":assistant_config})
    # for each item of the most recent messages, check if the message contains "De: Audion't".
    # if it does, add it to the chat_messages list with property "role" : "assistant"
    # if it doesn't, add it to the chat_messages list with property "role" : "user"

    
    for index, row in messages_df[['fecha', 'sender','mensaje']].tail(50).iterrows():
        if (row['sender'] == "Audion't"):
            chat_messages.append({"role" : "assistant","content":str(row['mensaje'])})
            # print the message
            print('Mensaje de Audion\'t: '+str(row['mensaje']))
        elif (row['sender'] == username):
            chat_messages.append({"role" : "user","content":str(row['mensaje'])})
            # print the message
            print('Mensaje de '+username+': '+str(row['mensaje']))

    chat_messages.append(prompt)
    print("Prompt: "+str(prompt))

    
    # call the OpenAI API to generate a summary of the voice note // llamar a la API de OpenAI para generar un resumen de la nota de voz
    try:
        gpt_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=chat_messages,
        temperature=1.8,
        )
    except Exception as e:
        print('⬇️⬇️⬇️⬇️ Error en la generación de texto ⬇️⬇️⬇️⬇️\n',e)
        # send a message to the user, telling them there was an error // enviar un mensaje al usuario, diciéndoles que hubo un error
        await update.message.reply_text('Hubo un error en la generación de texto. Probá de nuevo.')
        # send e
        await update.message.reply_text(str(e))
        # send an images/hidethepainharold.jpg to the user // enviar una imagen a la usuaria
        await update.message.reply_photo(open('images/hidethepainharold.jpg', 'rb'))
        return
    else:
        # get the text from the response // obtener el texto de la respuesta
        text = (gpt_response.choices[0].message.content)
        # decode the text // decodificar el texto
        decoded_text = decode.decode_utf8(text)

        # decoded text without new lines
        decoded_text_without_new_lines = decoded_text.replace("\n"," - ")

        #store the message in the csv // almacenar el mensaje en el csv
        with open(mensajes_file, 'a', encoding='utf-8') as f:
            f.write(now.strftime("%d/%m/%Y %H:%M:%S")+"|Audion't|"+decoded_text_without_new_lines+'|'+str(message_vector)+'\n')
            f.close()
        # print the decoded text // imprimir el texto decodificado
        print("Response:\n"+decoded_text)



        return decoded_text


# use the Embeddings API to turn text into vectors // usar la API de Embeddings para convertir texto en vectores
def generate_embeddings(file,column_to_embed):
    # read the csv file // leer el archivo csv
    df = pd.read_csv(file)
    # create a new column to store the embeddings // crear una nueva columna para almacenar los incrustaciones
    df["embeddings"] = ""
    # loop through the rows of the dataframe // bucle a través de las filas del dataframe
    for index, row in df.iterrows():
        # get the text from the row // obtener el texto de la fila
        text = row[column_to_embed]
        # get the embedding from the text // obtener el incrustación del texto
        embedding = get_embedding(text)
        # store the embedding in the dataframe // almacenar el incrustación en el dataframe
        df.at[index, "embeddings"] = embedding
    # save the dataframe to a csv file // guardar el dataframe en un archivo csv
    df.to_csv(file, index=False)