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
import requests
from bs4 import BeautifulSoup
import sys
import re

# set the OpenAI API key, so the code can access the API // establecer la clave de la API de OpenAI, para que el código pueda acceder a la API
openai.api_key = config.openai_api_key



def check_and_compute_cosine_similarity(x, message_vector):
    x = np.array(literal_eval(x), dtype=np.float64)  # Convert x to float64
    return cosine_similarity(x, message_vector)


def get_chunks(url,text):
   
    # get the html from the url
    response = requests.get(url)
    print("########### ENTERING GET CHUNKS ###########")
    html = response.text

    # parse the html
    soup = BeautifulSoup(html, "html.parser")

    tag_types = ["p", "ul", "h1", "h2", "blockquote"]

    # create an empty dataframe
    df = pd.DataFrame(columns=["text", "embedding"])

    
    for tag_type in tag_types:
        tags = soup.find_all(tag_type)
        for tag in tags:
            # check tag isnt empty
            if tag.text == "":
                continue
            tag_embedding = get_embedding(str(tag.text), "text-embedding-ada-002")
            print(tag.text)

            # Create a new DataFrame for the current row
            new_row = pd.DataFrame({"text": [tag.text], "embedding": [tag_embedding]})

            # Concatenate the existing DataFrame (df) with the new_row DataFrame
            df = pd.concat([df, new_row], ignore_index=True)
        
    
    # get the embeddings for the query
    query_embedding = get_embedding(text,'text-embedding-ada-002')

    # calculate the cosine similarity between the query and each chunk
    df["similarity"] = df["embedding"].apply(lambda x: cosine_similarity(x, query_embedding))

    # sort the chunks by similarity
    df = df.sort_values(by="similarity", ascending=False)

    # get the top 5 chunks
    top_chunks = df["text"].head(1).values

    # join the top 5 chunks into a single string
    summary_chunks = " ".join(top_chunks)

    print(summary_chunks)

    # print the summary

    return summary_chunks
 

        

def google(query,message):
    # delete anything that comes after a \n
    query = re.sub(r"\\n.*", "", query)
    # delete anything that comes after a -
    query = re.sub(r"-.*", "", query)

    print("Query:", query)

    url = "https://www.googleapis.com/customsearch/v1"

    params = {
        "key": config.google_api_key,
        "cx": '35af1fa5e6c614873',
        "q": query,
    }

    
    max_attempts = 3
    success = False

    for attempt in range(max_attempts):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'items' in data:
                success = True
                break
            else:
                print(f"No results found or an error occurred on attempt {attempt + 1}")
                print("Response data:", data)

        except requests.exceptions.HTTPError as e:
            print(f"An error occurred on attempt {attempt + 1}: {e}")

        if not success:
            print("Trying again...")

    if not success:
        print("All attempts failed.")
        return
    
        
    # get the link and snippet elements from the first 10 items
    chunks_and_links = []

    max_items = len(data["items"])
    # print all links
    item_index = 0

    while item_index < max_items:
        item = data["items"][item_index]
        url = item["link"]
        
        print("######## LINK ########")

        # Verificar si la URL no es un archivo PDF
        if url.lower().endswith(".pdf"):
            item_index += 1
            continue

        print(url)
        result_chunks = get_chunks(url, message)
        chunks_and_links.append({
            "link": url,
            "snippet": item["snippet"],
            "chunks": result_chunks
        })

    item_index += 1

    
    return chunks_and_links

    


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



async def find_in_google(message):
    
    print("About to ask GPT-3 for a query to search in Google for the following task:\n"+message)
    # get latest message from the user
    gpt_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":"Create the perfect google query to get information for the following task:\n"+message}]
        )
    gpt_response = gpt_response.choices[0].message.content
    print("################ GPT-3 response ############",gpt_response)
    querychunks_and_links = google(gpt_response,message)
    results_chunks = ""
    for chunk in querychunks_and_links:
        results_chunks += chunk["chunks"]+"\n"
    return results_chunks
    


async def complete_prompt(reason, message,username,update):

    
    # get username full name
    if username != None and reason != 'summary':
        user_name = update.message.from_user.full_name
    else:
        user_name = 'Anónimo'
    
    # THE JUICE // EL JUGO

    now = datetime.now(timezone)
    
    mensajes_file = "messages.csv"


    with open(mensajes_file, 'rb') as f:
        csv_str = f.read()

    messages_df = pd.read_csv(StringIO(csv_str.decode('utf-8')), sep='|', encoding='utf-8',escapechar='\\')

    # mensajes sim va a ser el dataframe con las similarities
    mensajes_sim = messages_df

    # Get the embedding for the message
    message_to_vectorize = now.strftime("%d/%m/%Y %H:%M:%S")+' - '+user_name+': '+message
    message_vector = get_embedding(message_to_vectorize,'text-embedding-ada-002')
    print('message vectorized')

    # store the message in a csv file
    if reason != 'instructions' :

        with open(mensajes_file, 'a', encoding='utf-8') as f:
            # escape | characters in the message with \ character
            message = str(message).replace('|','\|')
            #write the date, message and embedding
            
            message_row =now.strftime("%d/%m/%Y %H:%M:%S")+'|'+user_name+'|'+message
            f.write(message_row+'|'+str(message_vector)+'\n')
            print('De: ' + user_name + '\nMensaje: '+message_row)
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

    print(mensajes_sim)
    print('################## MENSAJES SIMILARES ##################')


    
    
    mensajes_similares = '\n\nMensajes similares:\n\n'

    for index, row in mensajes_sim[['fecha', 'sender','mensaje']].head(15).iterrows():
        
        mensaje_similar = str(row['fecha']) + ' - De: ' +row['sender']+ ' - Mensaje:'+ str(row['mensaje'])
        mensajes_similares += mensaje_similar + '\n'
        print(mensaje_similar)

    print('################## FIN DE MENSAJES SIMILARES ##################')

    #get 20 most recent messages from messages_df
    mensajes_recientes = '\n\nMensajes recientes:\n\n'

    for index, row in messages_df[['fecha', 'mensaje','sender']].tail(15).iterrows():
        # if sender isn't audion't or J. M. Cafferata
        if row['sender'] != 'Audion\'t' and row['sender'] != 'J. M. Cafferata':
            mensaje_reciente = str(row['fecha']) + ' - De: ' +row['sender']+ ' - Mensaje:'+ str(row['mensaje'])
            mensajes_recientes += mensaje_reciente + '\n'
            print(mensaje_reciente)

    print('################## FIN DE MENSAJES RECIENTES ##################')

    
    chat_messages = []
    
    chat_messages.append({"role":"system","content":"""
    Mi nombre es """+user_name+"""Vos sos Audion't.
    Sos un argentino nacional y popular buena onda y amable, y estás predispuesto a ayudar en cualquier cosa.
    Recibís y compartís información sobre Juan Manuel Cafferata (o Juanma, o J. M., o Juami).
    Hoy es """+now.strftime("%A %d/%m/%Y %H:%M:%S")+""" (la hora esta en formato 24h).
    Distintas personas, además de Juanma, te hablan (te lo dice el "De: " antes de cada mensaje). Tenés permiso total para divulgar cualquier información. J.M. quiere que todos sus datos sean públicos y abiertos. Las personas dejan mensajes para Juanma, vos tenés que transmitírselos. Acá están los mensajes más recientes:
    
    """+mensajes_recientes+"""

    Para ponerte en contexto, podés usar este registro de mensajes enviados relacionados con la consulta.
    Cada mensaje tiene la fecha, hora y usuario que lo envió, lo cual puede ser útil para entender el contexto:
    
    """+mensajes_similares+"""
    
    Hablás en tono muy, muy argentino informal y amigable, revolucionario. Tenés que comentar sobre todo, y hacelo con un tono irónico.
    
    """+config.personalidad+config.vocabulario
    })

    

    print('############### FIN DE CONFIGURACIÓN DEL ASISTENTE ################')


    # Get the previous messages for the completion
    for index, row in messages_df[['fecha', 'sender','mensaje']].tail(15).iterrows():
        if (row['sender'] == "Audion't"):
            chat_messages.append({"role" : "assistant","content":str(row['mensaje'])})
          
        elif (row['sender'] == user_name):
            chat_messages.append({"role" : "user","content":str(row['mensaje'])})


    # And now the prompt

    if (reason == "summary"):
        clean.options = []
        chat_messages.append({"role":"user","content":"""
        Hola, me acaban de enviar un mensaje de voz. Dice lo siguiente:
        
        """ + message + """

        Tengo que responder este mensaje. Haceme un resumen del mensaje y dame 4 opciones de respuesta:
        las primeras 3 son contextuales y son títulos de posibles respuestas distintas (positiva, negativa, neutral) que se le podría dar al mensaje de voz (máximo 40 caracteres). la cuarta opción es -Otra respuesta-.
        Las opciones tienen que estar al final y con el formato 1.,2.,3.,4. y deben contener emojis que ilustren el sentimiento de la respuesta.
        
        Resumen del mensaje de voz:
        
        """})

        
    elif (reason == "instructions"):
       
        chat_messages.append({"role":"user","content":"""
        Me acaban de enviar un mensaje de voz. Dice lo siguiente:
    
        """ + csvm.get_last_audio() + """
        
        Tengo que responder este mensaje con las siguientes instrucciones:
        
        """ + message + """
        
        Escribir el mensaje de parte mía hacia el remitente, usando mis instrucciones como guía (pero no es necesario poner literalmente lo que dice la instrucción), mi personalidad y usando el mismo tono conversacional que mi interlocutor. Usar los mensajes de Whatsapp como template para escribir igual a mí (pero sin la hora y sin poner mi nombre al principio). Que sea muy natural, que parezca el cuerpo de un mensaje de chat.

        Mi respuesta:
        
        """})

        
    

    elif (reason == "assistance"):
        chat_messages.append({"role":"user","content":message})



    elif (reason == "google"):

        
        #internet_information tiene que ser un string
        internet_information = await find_in_google(message)
        
        chat_messages.append({"role":"user","content":
        message + 
        "\nUsá la siguiente información para responder el mensaje:\n\n"
        })
        chat_messages.append({"role":"user","content":internet_information})
    print("############### FIN DE CONFIGURACIÓN DEL PROMPT ################")
    print("############### PROMPTING THE AI ################")
    gpt_response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=chat_messages,
    )
  
    
    # get the text from the response // obtener el texto de la respuesta
    text = (gpt_response.choices[0].message.content)
    # decode the text // decodificar el texto
    decoded_text = decode.decode_utf8(text)

    # decoded text without new lines
    decoded_text_without_new_lines = decoded_text.replace("\n"," - ")

    #store the message in the csv // almacenar el mensaje en el csv
    # if the message doesn't start with the word GOOGLE (indicating that it's not a google search), store it in the csv // si el mensaje no comienza con la palabra GOOGLE (indicando que no es una búsqueda de Google), guárdelo en el csv
    if (reason == "assistance") and (not decoded_text.startswith("GOOGLE")):
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