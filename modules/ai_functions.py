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
import traceback
import re
import csv
from nanoid import generate
import asyncio
from telegram.error import BadRequest
from telegram.error import RetryAfter
import tiktoken


# set the OpenAI API key, so the code can access the API // establecer la clave de la API de OpenAI, para que el código pueda acceder a la API
openai.api_key = config.openai_api_key

def ensure_csv_extension(database_name):
    file_name, file_extension = os.path.splitext(database_name)
    if file_extension.lower() != '.csv':
        file_name = database_name + '.csv'  # Append '.csv' to the original database_name
    else:
        file_name = database_name  # If the extension is already '.csv', use the original database_name
    return file_name

# read key-value pairs from csv file // leer pares clave-valor de un archivo csv
def read_data_from_csv(key: str, filename: str) -> dict:
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        for row in reader:
            if row[0].strip() == key.strip():
                # return the value of the key // devolver el valor de la clave
                return row[1]
    # return None if the key is not found // devolver None si la clave no se encuentra
    return None



def check_and_compute_cosine_similarity(x, message_vector):
    try:
        x = np.array(literal_eval(x), dtype=np.float64)  # Convert x to float64
    except ValueError:
        print("ValueError: could not convert string to float: '{}'".format(x))
        return 0.0
    except SyntaxError:
        print("SyntaxError: invalid syntax")
        return 0.0
    except TypeError:
        print("TypeError: can't convert {} to float".format(type(x)))
        return 0.0
    except Exception as e:
        print("Exception: {}".format(e))
        return 0.0


   
    return cosine_similarity(x, message_vector)

################## GOOGLE SEARCH ############################

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

################### AUDIO TRANSCRIPTION ############################

# use the OpenAI API to get the text from the audio file // usar la API de OpenAI para obtener el texto del archivo de audio 
async def transcribe_audio(update):
    # Extract the audio file from the message // Extraer el archivo de audio del mensaje
    new_file = await update.message.effective_attachment.get_file()
    # Download the audio file to the computer // Descargar el archivo de audio al computador
    await new_file.download_to_drive()
    # get the name of the audio file // obtener el nombre del archivo de audio
    file_path = Path(new_file.file_path).name
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
            print("⬆️⬆️⬆️⬆️ Starting transcription ⬆️⬆️⬆️⬆️")
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


################### v3 ############################

def get_top_entries(db, query, top_n=15):

    with open(db, 'rb') as f:
        csv_str = f.read()
    entries_df = pd.read_csv(StringIO(csv_str.decode('utf-8')), sep='|', encoding='utf-8', escapechar='\\')
    query_vector = get_embedding(query, 'text-embedding-ada-002')
    entries_df['similarity'] = entries_df['embedding'].apply(lambda x: check_and_compute_cosine_similarity(x, query_vector))
    # sort by similarity
    entries_df = entries_df.sort_values(by=['similarity'], ascending=False)

    # Initialize a string with the df headers
    headers = list(entries_df.columns)
    headers.remove('similarity')

    similar_entries = ''

    # Iterate over the rows of the DataFrame
    for index, row in entries_df.head(top_n).iterrows():
        # Replace the value of the 'embedding'  with ...
        row['embedding'] = '...'
        # delete the similarity column
        del row['similarity']
        del row['embedding']
        del row['row_id']
        # Convert the row to a string and join the values using '|'
        row_str = ' '.join(map(str, row.values))
        # Append the row string to 'similar_entries' followed by a newline character
        similar_entries += row_str + '\n'

    return similar_entries


async def chat(update,message,model):

    now = datetime.now()

    print("################# ENTERING CHAT MODE #################")

    # check if chat.csv exists. if not, create it
    if not os.path.isfile('chat.csv'):
        with open('chat.csv', 'w') as f:
            f.write('date|role|content\n')

    #get similar entries in notes.csv
    similar_entries = get_top_entries('db/notes.csv', message, top_n=8)
    
    # initialize prompt
    prompt = []

    # System configuration
    # open the text from prompts/audiont.txt
    with open('prompts/chat.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        prompt.append({"role": "system", "content": config.personalidad+config.vocabulario+similar_entries +"\n" +text})

    print("################ similar entries ############", similar_entries)

    # add chat history to prompt
    chat_df = pd.read_csv('chat.csv', sep='|', encoding='utf-8', escapechar='\\')
    chat_df = chat_df.tail(6)
    for index, row in chat_df.iterrows():
        prompt.append({"role": row['role'], "content": row['date']+" "+row['content']})

    # add user message to prompt
    prompt.append({"role": "user", "content": now.strftime("%d/%m/%Y %H:%M:%S")+" "+ message})

    # add the response beginning to the prompt
    prompt.append({"role": "assistant", "content": '{"store_message":"'})


    if model == "3":
        model = "gpt-3.5-turbo"
    else:
        model = "gpt-4"

    print(str(prompt))

    gpt_response = openai.ChatCompletion.create(
        model=model,
        messages=prompt,
    )

    # send a message saying how much the prompt will cost bsed on $0.03 / 1K tokens for prompt and $0.06 / 1K tokens for completion
    if model == "gpt-4":
        enc = tiktoken.encoding_for_model("gpt-4")
        num_tokens_prompt = len(enc.encode(str(prompt)))
        num_tokens_completion = len(enc.encode(str(gpt_response.choices[0].message.content)))
        await update.message.reply_text('Enviando $'+str(round((num_tokens_prompt*0.03+num_tokens_completion*0.06)/1000, 2))+' a OpenAI...')

    response_string = gpt_response.choices[0].message.content

    # if message starts with 'True', store the user message on db/notes.csv
    if response_string.startswith('True'):
        with open('db/notes.csv', 'a', encoding='utf-8') as f:
            date = now.strftime("%d/%m/%Y")
            time = now.strftime("%H:%M:%S")
            note_vector = get_embedding(message, 'text-embedding-ada-002')
            row_id = str(generate('0123456789', 5))
            f.write(date+'|'+time+'|'+message.replace('\n', ' ').replace('|','-')+'|'+row_id+'|'+str(note_vector)+'\n')

    # store the user message on chat.csv but replace new lines with \n
    with open('chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|user|'+message.replace('\n', ' ').replace('|','-')+'\n')
    
    # get the text from the assistant between '"response": "' and '"}' and store it on chat.csv
    
    pattern = r'"response":\s?"(.*?)"(?:,|\s?})'


    match = re.search(pattern, response_string)

    if match:
        new_response_string = match.group(1)
        response_string = new_response_string
    else:
        print("No se encontró la respuesta.")

    with open('chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|assistant|' + response_string.replace('\n', ' ').replace('|','-')+ '\n')
    
    print("################ CHAT response ############", response_string)
    return response_string

async def secretary(update,message,context):
    now = datetime.now()

    #check if there is a username and a full name
    if update.message.from_user.username is None:
        #get user id
        username = "User ID: "+str(update.message.from_user.id)
    else:
        #get user username
        username = update.message.from_user.username
    #check if full name is none
    if update.message.from_user.full_name is None:
        #get user id
        full_name = "User ID: "+str(update.message.from_user.id)
    else:
        full_name = update.message.from_user.full_name
    
    #embed and store the message in db/messages.csv
    message_vector = get_embedding(message, 'text-embedding-ada-002')

    with open('db/messages.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|'+full_name+'|'+message.replace('\n', ' ')+'|'+str(message_vector)+'|'+str(generate('0123456789', 5))+'\n')
    
    #get top entries from db/notes.csv
    related_notes = get_top_entries('db/notes.csv', message, 10)
    #truncate the string to 2000 characters
    related_notes = related_notes[:2000]
    print("related_notes", related_notes)
    prompt = []

    prompt.append({"role": "system", "content": "Today is " + now.strftime("%d/%m/%Y %H:%M:%S")+ "\n"+"\nMantené tus respuestas a menos de 100 caracteres.\nAcá van algunas notas de "+config.my_name+" que pueden ayudar:\n"+related_notes+" \nMi nombre es "+full_name+" ("+username+")"})
    #print all those values to check their type
    prompt.append({"role": "user", "content": message})
    gpt_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=prompt
    )
    response_string = gpt_response.choices[0].message.content
    print("response_string", response_string)
    # if response_string starts with "True":
    if response_string.startswith('True'):
        #store user message on db/notes.csv that has date|time|content|row_id|embedding format
        with open('db/messages.csv', 'a', encoding='utf-8') as f:
            date = now.strftime("%d/%m/%Y")
            time = now.strftime("%H:%M:%S")
            note_vector = get_embedding(message, 'text-embedding-ada-002')
            row_id = str(generate('0123456789', 5))
            f.write(date+'|'+time+'|'+message.replace('\n', ' ').replace('|','-')+'|'+row_id+'|'+str(note_vector)+'\n')

    # get the text between '"response": "' and '"}' and store it on chat.csv
    pattern = r'"response":\s?"(.*?)"(?:,|\s?})'


    match = re.search(pattern, response_string)

    if match:
        new_response_string = match.group(1)
        response_string = new_response_string
    else:
        print("No se encontró la respuesta.")

    with open('chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|assistant|' + response_string.replace('\n', ' ').replace('|','-')+ '\n')
    
    print("################ CHAT response ############", response_string)
    return response_string
    
   

################### v1 ############################

async def complete_prompt(reason, message,username,update):

    user_name = 'Anónimo'
    # THE JUICE // EL JUGO

    now = datetime.now(timezone)

    chat_messages = []
    chat_messages.append({"role":"system","content":config.personalidad + "\n Today is " + now.strftime("%d/%m/%Y %H:%M:%S")})
    

    if (reason == "summary"):
        model = "gpt-3.5-turbo"
        clean.options = []
        chat_messages.append({"role":"user","content":"""
        Hola, me acaban de enviar un mensaje de voz. Dice lo siguiente:
        
        """ + message + """

        Tengo que responder este mensaje. Haceme un resumen del mensaje y dame 4 opciones de respuesta:
        las primeras 3 son contextuales y son títulos de posibles respuestas distintas (positiva, negativa, neutral) que se le podría dar al mensaje de voz (máximo 40 caracteres). la cuarta opción es -Otra respuesta-.
        Las opciones tienen que estar al final y con el formato 1.,2.,3.,4. y deben contener emojis que ilustren el sentimiento de la respuesta."""})

        
    elif (reason == "answer"):
        # get related notes from db/notes.csv using pandas cosine similiaryty and get_top_entries
        notes_file = 'db/notes.csv'
        # get the top 3 entries
        similar_entries = get_top_entries(notes_file,csvm.get_last_audio(), 7)


        model = "gpt-4"
        chat_messages.append({"role":"user","content":"""
        Me acaban de enviar un mensaje de voz. Dice lo siguiente:
    
        """ + csvm.get_last_audio() + """
        
        Tengo que responder este mensaje con las siguientes instrucciones:
        
        """ + message + """
        
        Escribir el mensaje de parte mía hacia el remitente, usando mis instrucciones como guía (pero no es necesario poner literalmente lo que dice la instrucción), mi personalidad y usando el mismo tono conversacional que mi interlocutor. Usar las siguientes notas mías para escribir igual a mí.
         
          """ + similar_entries + """
        Que sea muy natural, que parezca el cuerpo de un mensaje de chat."""})

        
 

    print("############### FIN DE CONFIGURACIÓN DEL PROMPT ################")
    print("############### PROMPTING THE AI ################")
    print('chat_messages: ', chat_messages)

    gpt_response = openai.ChatCompletion.create(
    model=model,
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
    print("Response:\n"+decoded_text)
    return decoded_text

        

    

################## EMBEDDINGS ##################

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
