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
import ast
from telegram.error import BadRequest
from telegram.error import RetryAfter
import tiktoken
import PyPDF2
# import ast
import shutil


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
        
##################### JSON TOP ENTRIES ############################
def get_json_top_entries(query, database_name, top_n=5):
   
    # read the output.json file
    with open(database_name, 'r', encoding='utf-8') as f:
        data = f.read()

    # convert the json string to a list of dictionaries
    data = json.loads(data)

    # create a dataframe with the data
    df = pd.DataFrame(data)

    # create a new column with the embeddings converted to string
    df['embedding'] = df['embedding'].apply(lambda x: str(x))

    mensajes_sim = df[['filename','metadata', 'text_chunk', 'embedding']].copy()
    print('mensajes_sim: ', mensajes_sim)

    message_vector = get_embedding(query, 'text-embedding-ada-002')

    # Calculate cosine similarity between the message vector and the vectors in the output.json
    mensajes_sim['similarity'] = mensajes_sim['embedding'].apply(lambda x: check_and_compute_cosine_similarity(x, message_vector))
    print('similarity: ', mensajes_sim['similarity'])

    # sort by similarity
    mensajes_sim = mensajes_sim.sort_values(by=['similarity'], ascending=False)
    print('mensajes_sim: ', mensajes_sim)

    now = datetime.now(timezone)
    
    related_data = ''

    for index, row in mensajes_sim[['metadata', 'text_chunk']].head(top_n).iterrows():
        print(str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n')
        try:
            related_data += str(row['filename']) + ' - ' + str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n'
        except:
            related_data += str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n'
    
    return related_data



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


async def chat(update,message,model,document_search):

    now = datetime.now()

    print("################# ENTERING CHAT MODE #################")

    # initialize prompt
    prompt = []

    similar_entries = ''

    # check if chat.csv exists in users/uid folder
    if not os.path.exists('users/'+str(update.message.from_user.id)+'/chat.csv'):
        # create chat.csv
        with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'w', encoding='utf-8') as f: 
            f.write('date|role|content\n')

    prompt.append({"role": "system", "content": config.personalidad+config.vocabulario})

    # add chat history to prompt
    chat_df = pd.read_csv('users/'+str(update.message.from_user.id)+'/chat.csv', sep='|', encoding='utf-8', escapechar='\\')
    chat_df = chat_df.tail(6)
    for index, row in chat_df.iterrows():
        prompt.append({"role": row['role'], "content": row['date']+" "+row['content']})
    try:
        # get a list of the files in vectorized folder
        files = os.listdir('users/'+str(update.message.from_user.id)+'/vectorized')
        print('files: ', files)
        docusearch_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.2,
            messages=[
                {"role": "system", "content": """Prompt: As a powerful language model, your task is to help users by providing relevant JSON documents based on their search query. A user will provide you with a search query and a list of available JSON documents. You must respond with an array of the files that are even remotely relevant to the query.

User: Search query: "Sustainable energy sources" 
Available documents: ["Introduction to Renewable Energy.pdf.json", "Fossil Fuels and Climate Change.pdf.json", "Solar and Wind Power.pdf.json", "Nuclear Energy Pros and Cons.pdf.json", "Sustainable Energy Solutions.pdf.json", "The Future of Oil.pdf.json"]

LLM: ["Introduction to Renewable Energy.pdf.json", "Solar and Wind Power.pdf.json", "Sustainable Energy Solutions.pdf.json"]"""},
                {"role": "user", "content": "Search query: " + message + "\nAvailable documents: " + str(files) + "\n\nLLM: ['"}

            ]
        )
        
        print("################ docusearch_response ############", docusearch_response.choices[0].message.content)
        # add the bracket so it's an array
        docusearch_response = "['" + docusearch_response.choices[0].message.content

        # get the text up until the first '] including the ']'
        docusearch_response = docusearch_response[:docusearch_response.find(']')+1]

        # get the list of files from the response
        docusearch_file = ast.literal_eval(docusearch_response)

        print("################ docusearch_file ############", docusearch_file)

        final_similar_entries = ''
        # for each file in the docusearch_response

        # send a new message saying that i'm writing
        new_message = await update.message.reply_text("Escribiendo...✍️✍️")
        for file in docusearch_file:
            
            # edit message saying that the file is being searched
            await new_message.edit_text("Buscando en " + file + "...")
            # if file doesn't end with .json, add it
            if not file.endswith('.json'):
                file = file + '.json'
            # if file is json
            if file.endswith('.json'):
                top_n = round(15/len(docusearch_file))
                # get similar entries in the file
                similar_entries = get_json_top_entries(message, 'users/'+str(update.message.from_user.id)+'/vectorized/'+file, top_n=top_n)
                # truncate similar_entries to 5000/len(docusearch_file)
                final_similar_entries += similar_entries[:round(5000/len(docusearch_file))]

        prompt.append({"role": "user", "content": final_similar_entries})
        print("################ similar entries ############\n", final_similar_entries)


    except Exception as e:
        print("################ ERROR IN DOCUMENT SEARCH ############", e)
    


    # add user message to prompt
    prompt.append({"role": "user", "content": now.strftime("%d/%m/%Y %H:%M:%S")+" "+ message})

    if model == "3":
        model = "gpt-3.5-turbo"
    else:
        model = "gpt-4"


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

    # store the user message on chat.csv but replace new lines with \n
    with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|user|'+message.replace('\n', ' ').replace('|','-')+'\n')
    

    with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
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

    #get top entries from db/notes.csv
    related_notes = get_top_entries('db/notes.csv', message, 15)
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

    # get the text between '"response": "' and '"}' and store it on chat.csv
    pattern = r'"response":\s?"(.*?)"(?:,|\s?})'


    match = re.search(pattern, response_string)

    if match:
        new_response_string = match.group(1)
        response_string = new_response_string
    else:
        print("No se encontró la respuesta.")

    #check if the user has a chat.csv
    if not os.path.exists('users/'+str(update.message.from_user.id)+'/chat.csv'):
        #create chat.csv
        with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'w', encoding='utf-8') as f:
            f.write('date|role|content\n')

    with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|assistant|' + response_string.replace('\n', ' ').replace('|','-')+ '\n')
    
    print("################ CHAT response ############", response_string)
    return response_string
    
################### VECTORIZE ############################

def read_files(input_folder):
    content = []
    for root, dirs, files in os.walk(input_folder):
        counter = 0
        counter_end = len(files)
        for file in files:
            print('Progress: {}/{}'.format(counter, counter_end))
            print(file)
            if file.endswith('.txt'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content.append((f.read(), file, None))  # Add 'None' for the page number
            elif file.endswith('.pdf'):
                pdf_obj = open(os.path.join(root, file), 'rb')
                pdf_reader = PyPDF2.PdfFileReader(pdf_obj)
                for page_num in range(pdf_reader.numPages):
                    content.append((pdf_reader.getPage(page_num).extractText(), file, page_num))
                pdf_obj.close()
            counter += 1
    print(len(content))
    return content

def split_text(text, chunk_size=2048):
    words = text.split()
    chunks = []
    current_chunk = []
    counter = 0
    counter_end = len(words)

    for word in words:
        print('Progress: {}/{}'.format(counter, counter_end))

        if len(' '.join(current_chunk) + ' ' + word) < chunk_size:
            current_chunk.append(word)
        else:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
        counter += 1


    if current_chunk:
        chunks.append(' '.join(current_chunk))


    return chunks

def vectorize_chunks(text_chunks, metadata,file):
    counter = 0
    counter_end = len(text_chunks)
    vectorized_data = []

    for chunk in text_chunks:
        print('Progress: {}/{}'.format(counter, counter_end))
        embedding = get_embedding(chunk,"text-embedding-ada-002")
        vectorized_data.append({
            'filename': file,
            'metadata': metadata,
            'text_chunk': chunk,
            'embedding': embedding,
        })
        counter += 1

    return vectorized_data

async def vectorize(update, context, uid):
    user_folder = 'users/' + uid + '/'
    # Check if the input folder exists. If not, create it.
    if not os.path.exists(user_folder + 'to_vectorize'):
        os.makedirs(user_folder + 'to_vectorize')
    input_folder = user_folder + 'to_vectorize'
    print("input_folder", input_folder)

    text_data = read_files(input_folder)

    # Check if the output folder exists. If not, create it.
    if not os.path.exists(user_folder + 'vectorized'):
        os.makedirs(user_folder + 'vectorized')

    for text, file, page_num in text_data:
        vectorized_data = []
        metadata = file + ' - Página ' + str(page_num + 1) if page_num is not None else file
        text_chunks = split_text(text)
        vectorized_chunks = vectorize_chunks(text_chunks, metadata, file)
        vectorized_data.extend(vectorized_chunks)

        # Save the vectorized data for each file with its original name
        json_filepath = user_folder + 'vectorized/' + file + '.json'

        # Load the existing data from the JSON file
        existing_data = []
        if os.path.exists(json_filepath):
            with open(json_filepath, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

        # Append the new data to the existing array
        existing_data.extend(vectorized_data)

        # Save the updated array back to the JSON file
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False)

    # Delete the files in the to_vectorize folder
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            os.remove(os.path.join(root, file))

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
