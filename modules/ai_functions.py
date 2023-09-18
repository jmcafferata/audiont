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
import pdfplumber
# import ast
import shutil
import random
from modules.settings_system import get_settings, write_settings
from modules.vectorize import split_text_into_segments, extract_text_from_pdf

# set the OpenAI API key, so the code can access the API // establecer la clave de la API de OpenAI, para que el código pueda acceder a la API
openai.api_key = config.openai_api_key


################### AI FUNCTIONS ############################

async def get_response_cost(prompt,completion,model,update):
    if model == "gpt-4":
        enc = tiktoken.encoding_for_model("gpt-4")
        num_tokens_prompt = len(enc.encode(str(prompt)))
        num_tokens_completion = len(enc.encode(str(completion.choices[0].message.content)))
        await update.message.reply_text('Enviando $'+str(round((num_tokens_prompt*0.03+num_tokens_completion*0.06)/1000, 2))+' a OpenAI...')
        print('Enviando $'+str(round((num_tokens_prompt*0.03+num_tokens_completion*0.06)/1000, 2))+' a OpenAI...')

async def get_json_top_entries(query, database_name, top_n=5,update=None):
   
    # read the output.json file
    with open(database_name, 'r', encoding='utf-8') as f:
        data = f.read()

    # convert the json string to a list of dictionaries
    data = json.loads(data)

    # create a dataframe with the data
    df = pd.DataFrame(data)

    # create a new column with the embeddings converted to string
    df['embedding'] = df['embedding'].apply(lambda x: str(x))

    # add original index to dataframe before sorting
    df['original_index'] = df.index

    mensajes_sim = df[['filename','metadata', 'text_chunk', 'embedding', 'original_index']].copy()
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

    for index, row in mensajes_sim[['metadata', 'text_chunk', 'original_index']].head(top_n).iterrows():
        related_chunk = ''
        # get adjacent chunks
        original_index = row['original_index']
        if original_index > 0:
            prev_row = df.loc[original_index - 1]
            related_chunk += str(prev_row['metadata']) + ' - ' + str(prev_row['text_chunk']) + ' (Previous chunk)\n\n'
        
        related_chunk += str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n'

        if original_index < len(df) - 1:
            next_row = df.loc[original_index + 1]
            related_chunk += str(next_row['metadata']) + ' - ' + str(next_row['text_chunk']) + ' (Next chunk)\n\n'
        
        print('related_chunk: ', related_chunk)
        # if update:
        #     # trim the chunk to 4000 characters
        #     if len(related_chunk) > 4000:
        #         related_chunk = related_chunk[:4000] + '...'
        #     await update.message.reply_text('👓 Data relacionada...👇\n\n' + related_chunk)
        related_data += related_chunk

    return related_data

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
        if 'row_id' in row:
            del row['row_id']
        # Convert the row to a string and join the values using '|'
        row_str = ' '.join(map(str, row.values))
        # Append the row string to 'similar_entries' followed by a newline character
        similar_entries += row_str + '\n'

    return similar_entries

async def understand_intent(update, message):
    # get the message from the user // obtener el mensaje del usuario
    
    prompt = []
    # get model from settings
    model = get_settings('GPTversion', update.message.from_user.id)

    # get global json documents from the users/global folder only if they are JSONs
    global_jsons = [f for f in os.listdir('users/global/vectorized') if f.endswith('.json')]
    # get the json documents from the user's folder
    user_jsons = [f for f in os.listdir('users/' + str(update.message.from_user.id) + '/vectorized') if f.endswith('.json')]
    # combine the two lists // combinar las dos listas
    jsons = global_jsons + user_jsons

    intent_response = openai.ChatCompletion.create(
                model=model,
                temperature=0.5,
                messages=[
                    {"role": "system", "content": """based on the user input, the available functions and available documents, you will respond with the name of the function to execute. if you don't know, respond "chat"

available_functions=[
{"function":"calendar","description":"for accessing the user's calendar","example_user_messages":["mostrame mi calendario","qué eventos tengo mañana?"},                     
{"function":"chat","default":"true","fallback":"true","description":"for chatting with the AI chatbot","example_user_message":"hola! todo bien?"},
{"function":"docusearch","description":"for looking up relevant information in one of the user documents, based on the available_documents","example_user_message":"buscar los efectos de la microdosis en el libro de Hoffman"},
{"function":"scrape","description":"for scraping the internet for additional data","example_user_message":"buscar en cledara.com los features de Cledara"},
{"function":"messagesearch","description":"for looking up relevant information in previous related messages","example_user_message":"buscar en mensajes anteriores un presupuesto de baño"},
{"function":"messagestore","description":"for logging messages","example_user_message":"anotar que un pancho cuesta cinco dólares"},
{"function":"personality","description":"for changing the personality of the AI chatbot","example_user_message":"cambiá tu personalidad a la de un abogado"},
{"function":"vocabulary","description":"for changing the vocabulary of the AI chatbot","example_user_message":"agregar las siguientes palabras al vocabulario: 'schadenfreude', 'watafak', 'papafrita'"},    

]

available_documents=""" + str(jsons) + """

###

User: <user message>
Assistant: <function>"""},
                    {"role": "user", "content": message }

                ]
            )
    intent = intent_response.choices[0].message.content
    print("intent: \n", intent)
    return intent

async def extract_entities(message):
    entities = None
    return entities

async def perform_action(intent, entities, message,update):

    now = datetime.now(timezone)
 
    prompt_messages = []

    model = get_settings('GPTversion', update.message.from_user.id)

    ######################### CHAT #########################
    if intent.startswith('chat'):
        typing_message = await update.message.reply_text('Pensando antes de hablar...')
        # check if chat.csv exists in users/uid folder
        if not os.path.exists('users/'+str(update.message.from_user.id)+'/chat.csv'):
        # create chat.csv
            with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'w', encoding='utf-8') as f: 
                f.write('date|role|content\n')
        
        # CONFIG THE MODEL FOR CHAT
        personalidad = get_settings('personality', update.message.from_user.id)
        vocabulario = get_settings('vocabulary', update.message.from_user.id)
        prompt_messages.append({"role": "system", "content": "Bot personality:\n"+ personalidad+'\n\n' + "Bot vocabulary:\n"+vocabulario})

        # add chat history to prompt
        chat_df = pd.read_csv('users/'+str(update.message.from_user.id)+'/chat.csv', sep='|', encoding='utf-8', escapechar='\\')
        chat_df = chat_df.tail(15)
        for index, row in chat_df.iterrows():
            prompt_messages.append({"role": row['role'], "content": row['content']})
        
        # add user message to prompt
        prompt_messages.append({"role": "user", "content": message})

        response = openai.ChatCompletion.create(
            model=model,
            temperature=0.5,
            messages=prompt_messages
        )

        response_string = response.choices[0].message.content

        # store the user message on chat.csv but replace new lines with \n
        with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
            f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|user|'+message.replace('\n', ' ').replace('|','-')+'\n')
        

        with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
            f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|assistant|' + response_string.replace('\n', ' ').replace('|','-')+ '\n')

        print('############ CHAT RESPONSE ############')
        print(response_string)
        await typing_message.edit_text(response_string)

    ######################### DOCUSEARCH #########################
    elif intent.startswith('docusearch'):
        await update.message.reply_text('🔭Buscando en documentos...')
        files = []
        # get the json documents from the user's folder
        user_jsons = [f for f in os.listdir('users/' + str(update.message.from_user.id) + '/vectorized') if f.endswith('.json')]
        # get the file paths // obtener las rutas de los archivos
        for file in user_jsons:
            files.append('users/' + str(update.message.from_user.id) + '/vectorized/' + file)
        # get the json documents from the global folder
        global_jsons = [f for f in os.listdir('users/global/vectorized') if f.endswith('.json')]
        # get the file paths // obtener las rutas de los archivos
        for file in global_jsons:
            files.append('users/global/vectorized/' + file)

        print('files: ', files)
        docusearch_response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": """Prompt: As a powerful language model, your task is to help users by providing relevant JSON documents based on their search query. A user will provide you with a search query and a list of available JSON documents. You must respond with an array of the files that are even remotely relevant to the query.

                User: Search query: "Sustainable energy sources" 
                Available documents: ["Introduction to Renewable Energy.pdf.json", "Fossil Fuels and Climate Change.pdf.json", "Solar and Wind Power.pdf.json", "Nuclear Energy Pros and Cons.pdf.json", "Sustainable Energy Solutions.pdf.json", "The Future of Oil.pdf.json"]

                LLM: ["users/global/vectorized/Introduction to Renewable Energy.pdf.json", "users/26472364/vectorized/Solar and Wind Power.pdf.json", "users/global/vectorized/Sustainable Energy Solutions.pdf.json"]"""},
                {"role": "user", "content": "Search query: " + message + "\nAvailable documents: " + str(files) + "\n\nLLM: ['"}

            ]
        )
        
        print("################ docusearch_response ############", docusearch_response.choices[0].message.content)
        # add the bracket so it's an array
        docusearch_response = "['" + docusearch_response.choices[0].message.content

        # get the text up until the first '] including the ']'
        docusearch_response = docusearch_response[:docusearch_response.find(']')+1]

        #TODO: remove brackets from the files

        # get the list of files from the response
        print("################ docusearch_response PARSED ############", docusearch_response)
        docusearch_file = ast.literal_eval(docusearch_response)

        print("################ docusearch_file ############", docusearch_file)

        final_similar_entries = ''
        # for each file in the docusearch_response

        # send a new message saying that i'm writing
        new_message = await update.message.reply_text("Escribiendo...✍️✍️")

        #extract the search query from the message
        query_response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role":"system","content":"Example input: 'buscar en henry george el concepto de impuesto único'.\nExample output: 'impuesto único'"},
                {"role": "user", "content": "Extract the search query from the following message: " + message},
                {"role":"assistant","content":"The search query is: "}
            ]
        )
        query = query_response.choices[0].message.content

        for file in docusearch_file:
            
            # edit message saying that the file is being searched
            await new_message.edit_text("🔬 Buscando "+query+" en " + file + "...")
            # if file doesn't end with .json, add it
            if not file.endswith('.json'):
                file = file + '.json'
            # if file is json
            if file.endswith('.json'):
                top_n = round(7/len(docusearch_file))
                similar_entries = await get_json_top_entries(query, file, top_n,update)
                final_similar_entries += similar_entries

        # truncate the final_similar_entries to 5000 characters
        final_similar_entries = final_similar_entries[:8000]

        prompt_messages.append({"role": "user", "content": final_similar_entries})
        
        # append the message
        prompt_messages.append({"role": "user", "content": message})

        await update.message.reply_text("Escribiendo una respuesta...✍️✍️")

        #for each prompt message, print
        for prompt_message in prompt_messages:
            print(prompt_message)

        response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=prompt_messages
        )

        response_string = response.choices[0].message.content
        print("################ response_string ############", response_string)

        await update.message.reply_text(response_string)
    
    ######################### SCRAPE #########################
    elif intent.startswith('scrape'):
        typing_message = await update.message.reply_text('🌐 Metiéndome en la deep web...')

        #use chatgpt to extract the links from the message
        links_response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "user", "content": "Return an array containing all the links in the following string, and add http or https if need be:\n"+message},
                {"role":"assistant", "content": "Sure! Here's an array containing all the links in your message:\n"}
            ])

        links_response_string = links_response.choices[0].message.content

        # parse the links from the responsestring as an array
        links = ast.literal_eval(links_response_string)
        print("################ links ############\n", links)

        #if no links, return
        if len(links) == 0:
            await typing_message.edit_text("😛No encontré ningún link en tu mensaje. Intenta de nuevo.")
            return
        # Initialize an empty string to hold all the text
        text_collection = ''    
        # for each link
        for link in links:
                # Get the HTML of the page
            response = requests.get(link)

            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all paragraph tags
            paragraphs = soup.find_all('p')

            # use tiktoken to count the number of tokens
            enc = tiktoken.encoding_for_model("gpt-4")
            token_count = 0
            page_text = ''

            # For each paragraph, print the text and add it to text_collection
            for p in paragraphs:
                text = p.get_text()
                page_text += text + '\n'  # Add a newline between paragraphs
                print(text)
                token_count += len(enc.encode(text))
                print("################ token_count ############", token_count)
                if token_count > 3500/len(links):
                    print("################ token_count > 3500/len(links) ############", token_count > 3500/len(links))
                    break

            text_collection += page_text

        # add the text to the prompt
        prompt_messages.append({"role": "user", "content": text_collection})

        # append the message
        prompt_messages.append({"role": "user", "content": message})

        response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=prompt_messages
        )

        response_string = response.choices[0].message.content
        print("################ response_string ############\n", response_string)

        await typing_message.edit_text(response_string)

    ######################### MESSAGESTORE #########################
    elif intent.startswith('messagestore'):

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
        
        #embed and store the message in users/userid/messages.csv

        message_vector = get_embedding(message, 'text-embedding-ada-002')
        
        #check if csv exists. if not, create it
        if not os.path.exists('users/'+str(update.message.from_user.id)+'/messages.csv'):
            with open('users/'+str(update.message.from_user.id)+'/messages.csv', 'w', encoding='utf-8') as f:
                f.write('date|message|embedding\n')
        with open('users/'+str(update.message.from_user.id)+'/messages.csv', 'a', encoding='utf-8') as f:
            f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|'+message+'|'+str(message_vector)+'\n')
        await update.message.reply_text('✍️ ¡Anotado!')

    ######################### MESSAGESEARCH #########################
    elif intent.startswith('messagesearch'):
        await update.message.reply_text('🔍 Buscando en anotaciones...')
        # get the user folder called users/id/messages.csv
        messages_file = 'users/'+str(update.message.from_user.id)+'/messages.csv'
        top_n = 5
        similar_messages = get_top_entries(messages_file,message,top_n)
        print("################ similar_messages ############\n", similar_messages)
        top_messages_response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "user", "content": message},
                {"role":"user","content": "Los siguientes mensajes pueden ayudar a contestar mi pregunta:\n"},
                {"role":"user","content": similar_messages},
                {"role":"assistant","content":"En base a los mejores anteriores, a respuesta a tu pregunta es: "}
            ])
        top_messages_response_string = top_messages_response.choices[0].message.content
        print("################ top_messages_response_string ############\n", top_messages_response_string)
        await update.message.reply_text(top_messages_response_string)
    
    ######################### PERSONALITY #########################
    elif intent.startswith('personality'):
        await update.message.reply_text('🧠🤯 Cambiando personalidad del bot...')
        # get the current personality from the user settings
        current_personality = get_settings("personality", update.message.from_user.id)
        personality_response = openai.ChatCompletion.create(
            model="gpt-4",
            temperature=0.2,
            messages=[
                {"role": "user", "content": message + "\nCurrent personality: " + current_personality + "\n\nReescribir la personalidad en base al pedido.\n\n"},
                {"role": "assistant", "content": "Nueva personalidad: "}
            ])
        
        new_personality_text = personality_response.choices[0].message.content

        # update the user settings with the new personality
        write_settings("personality", new_personality_text, update.message.from_user.id)
        await update.message.reply_text("👀😵‍💫 Esta va a ser mi nueva personalidad:")
        await update.message.reply_text(new_personality_text)
        prompt_messages.append({"role": "user", "content": new_personality_text})

    ############################## VOCABULARY ##############################
    elif intent.startswith('vocabulary'):
        await update.message.reply_text('📚📖 Cambiando vocabulario del bot...')
        # get the current vocabulary from the user settings
        current_vocabulary = get_settings("vocabulary", update.message.from_user.id)
        vocabulary_response = openai.ChatCompletion.create(
            model=model,  
            temperature=0.2,
            messages=[
                {"role": "user", "content": message + "\nCurrent vocabulary: " + current_vocabulary + "\n\nReescribir el vocabulario en base al pedido.\n\n"},
                {"role": "assistant", "content": "Nuevo vocabulario: "}
            ])
    
        new_vocabulary_text = vocabulary_response.choices[0].message.content

        # update the user settings with the new vocabulary
        write_settings("vocabulary", new_vocabulary_text, update.message.from_user.id)

        await update.message.reply_text("👀😵‍💫 Este va a ser mi nuevo vocabulario:")
        await update.message.reply_text(new_vocabulary_text)

        prompt_messages.append({"role": "user", "content": new_vocabulary_text})

    ######################### CALENDAR #########################
    elif intent.startswith('calendar'):

        events = '' 
        await update.message.reply_text('📅Buscando en el calendario...')
        from modules.google_calendar import get_events
        from modules.google_calendar import check_auth
        from modules.google_calendar import get_auth_url

        # check if the user has authorized the app
        if not check_auth(update.message.from_user.id):
            # if not, send the auth url
            await update.message.reply_text('🔐 Necesito que me autorices para acceder a tu calendario. Por favor, hacé click en el siguiente link y seguí las instrucciones:\n\n' + get_auth_url(update.message.from_user.id))
            return
        else:
            # if yes, get the events
            events = get_events(update.message.from_user.id)

        response = openai.ChatCompletion.create(
            model=model,
            temperature=0.2,
            messages=[
                
                {"role":"user","content":"Estos son mis eventos:\n"},
                {"role":"user","content": events},
                {"role":"user","content":"En base a los mejores anteriores, responder la siguiente pregunta: \n" + message},

            ])
        response_string = response.choices[0].message.content
        print("################ response_string ############\n", response_string)
        await update.message.reply_text(response_string)

    for prompt_message in prompt_messages:
        # print the message
        print(prompt_message)
    return prompt_messages
    
def ensure_csv_extension(database_name):
    file_name, file_extension = os.path.splitext(database_name)
    if file_extension.lower() != '.csv':
        file_name = database_name + '.csv'  # Append '.csv' to the original database_name
    else:
        file_name = database_name  # If the extension is already '.csv', use the original database_name
    return file_name

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

async def transcribe_audio(update):
    # Extract the audio file from the message // Extraer el archivo de audio del mensaje
    new_file = await update.message.effective_attachment.get_file()
    # Download the audio file to the computer // Descargar el archivo de audio al computador
    await new_file.download_to_drive()
    # get the name of the audio file // obtener el nombre del archivo de audio
    file_path = Path(new_file.file_path).name
    # convert the audio file to a wav file // convertir el archivo de audio a un archivo wav
    transcription_text = ""
    try:
        # new_audio_path = convert.convert_to_wav(file_path)
        new_audio_paths = convert.split_in_chunks(file_path)
    except Exception as e:
        print("⬇️⬇️⬇️⬇️ Error en la conversión de audio ⬇️⬇️⬇️⬇️\n",e)
        # send a message to the user, telling them there was an error // enviar un mensaje al usuario, diciéndoles que hubo un error
        await update.message.reply_text('Hubo un error en la conversión de audio. Probá de nuevo.')
        # send e
        await update.message.reply_text(str(e))
        # send an images/cat.jpg to the user // enviar una imagen a la usuaria
        await update.message.reply_photo(open('images/cat.jpg', 'rb'))
    else:
        # transcribe chunks
        print(new_audio_paths)
        for new_audio_path in new_audio_paths:
            # open the wav file // abrir el archivo wav
            wav_audio = open(new_audio_path, "rb")
            # call the OpenAI API to get the text from the audio file // llamar a la API de OpenAI para obtener el texto del archivo de audio
            try:
                print("⬆️⬆️⬆️⬆️ Starting transcription ⬆️⬆️⬆️⬆️")
                transcription_object = openai.Audio.transcribe(
                "whisper-1", wav_audio, language="es", prompt="esto es una nota de voz. hay momentos de silencio en el audio, cuidado con eso.")
                transcription_text += transcription_object["text"]
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
                # delete audio files from the server
                wav_audio.close()
                os.remove(new_audio_path)
        print("Transcription:\n"+transcription_object["text"])
        os.remove(file_path)
        return transcription_text
    
################### TRAINING ############################

async def generate_prompt_completion_pair(user_id):
    print(user_id)
    # get the files from the user flder. if folder doesn't exist, create it
    if not os.path.exists('users/'+str(user_id)+'/training_data/'):
        os.makedirs('users/'+str(user_id)+'/training_data/')
    files = os.listdir('users/'+str(user_id)+'/training_data/')
    print('files: ', files)
    # pick a random file 
    random_file = random.choice(files)

    info_for_pcp = ''

    # check if it's a json
    if random_file.endswith('.json'):
        # initialize the pcp data
        # get a random object in the json
        with open('users/'+str(user_id)+'/vectorized/'+random_file, 'r', encoding='utf-8') as f:
            data = f.read()
        # convert the json string to a list of dictionaries
        data = json.loads(data)
        # get a random object in the json
        obj = random.choice(data)

        # get the text_chunk, the metadata and the filename
        text_chunk = obj['text_chunk']
        metadata = obj['metadata']
        filename = obj['filename']
        # add the text_chunk, the metadata and the filename to the pcp data
        info_for_pcp += text_chunk + ' - ' + metadata + ' - ' + filename + '\n\n'


    elif random_file.endswith('.txt'):
        #get random 400 character chunk
        with open('users/'+str(user_id)+'/training_data/'+random_file, 'r', encoding='utf-8') as f:
            data = f.read()
        # put the cursor at a random position
        random_position = random.randint(0, len(data)-400)
        f.seek(random_position)
        # read 400 characters
        text_chunk = f.read(400)
        # add the text_chunk to the pcp data
        info_for_pcp += text_chunk + '\n\n'

    elif random_file.endswith('.csv'):
        # check if there's a | delimiter in the header
        with open('users/'+str(user_id)+'/training_data/'+random_file, 'r', encoding='utf-8') as f:
            # read first line
            first_line = f.readline()
            # check if there's a | delimiter
            if '|' in first_line:
                # read the csv with the | delimiter
                df = pd.read_csv('users/'+str(user_id)+'/training_data/'+random_file, sep='|')
            else:
                # read the csv with the , delimiter
                df = pd.read_csv('users/'+str(user_id)+'/training_data/'+random_file)
        # get a random row in the csv
        obj = df.sample()
        # remove embedding column if there is one
        if 'embedding' in obj.columns:
            obj = obj.drop(columns=['embedding'])
        # add the row to the pcp data
        info_for_pcp += obj.to_string(index=False) + '\n\n'

    print('info_for_pcp: ', info_for_pcp)
        
    pcp_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"system","content":"""{"prompt":"Summary: """+ config.summary+"""\n\nSpecific information: """+info_for_pcp+"""\n\n###\n\nUsuario: <pregunta1 acerca de la información específica>\n"""+config.my_name+""": <respuesta1, usando su lenguaje>\nUsuario: <pregunta2>\n"""+config.my_name+""":"},
        {"completion": <respuesta2, en su lenguaje>}
        """}],
    )

    # send the response to the user
    return pcp_response.choices[0].message.content
  
################### CHAT ############################

async def chat(update,message,model):

    uid = update.message.from_user.id

    # if users/global folder doesn't exist, create it
    if not os.path.exists('users/global'):
        os.makedirs('users/global')


    now = datetime.now()

  

    # check what the user wants
    intent = await understand_intent(update, message)

    print("intent: \n", intent)

    # TODO: get the entities from the message
    entities = await extract_entities(update)

    # perform the action
    await perform_action(intent,entities,message,update)


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
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|'+full_name+'|'+message+'|'+str(message_vector)+'\n')
    
    typing_message = await update.message.reply_text('✍️✍️✍️')
    # check if chat.csv exists in users/uid folder
    if not os.path.exists('users/'+str(update.message.from_user.id)+'/chat.csv'):
    # create chat.csv
        with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'w', encoding='utf-8') as f: 
            f.write('date|role|content\n')
    
    # CONFIG THE MODEL FOR CHAT
    prompt_messages = []
    #get global personality from users/global/personality.txt
    with open('users/global/personality.txt', 'r', encoding='utf-8') as f:
        personalidad = f.read()
    prompt_messages.append({"role": "system", "content":personalidad})

    # add chat history to prompt
    chat_df = pd.read_csv('users/'+str(update.message.from_user.id)+'/chat.csv', sep='|', encoding='utf-8', escapechar='\\')
    chat_df = chat_df.tail(6)
    for index, row in chat_df.iterrows():
        prompt_messages.append({"role": row['role'], "content": row['content']})
    
    # add user message to prompt
    prompt_messages.append({"role": "user", "content": message})

    response = openai.ChatCompletion.create(
        model='gpt-4',
        temperature=0.5,
        messages=prompt_messages
    )

    response_string = response.choices[0].message.content

    # store the user message on chat.csv but replace new lines with \n
    with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|user|'+message.replace('\n', ' ').replace('|','-')+'\n')
    

    with open('users/'+str(update.message.from_user.id)+'/chat.csv', 'a', encoding='utf-8') as f:
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|assistant|' + response_string.replace('\n', ' ').replace('|','-')+ '\n')

    print('############ CHAT RESPONSE ############')
    print(response_string)
    await typing_message.edit_text(response_string)
    
    
################### VECTORIZE ############################
# get user language
def get_user_language(user_id):
    # get the language from the user's config file
    with open('users/'+str(user_id)+'/settings.json', 'r', encoding='utf-8') as f:
        settings = json.load(f)
    return settings['language']

# vectorize a text

def read_files(input_folder):
    # content is a list of dictionaries
    # schema: text, filename, pagenum, metadata
    content = []
    for root, dirs, files in os.walk(input_folder):
        counter = 0
        counter_end = len(files)
        metadata = ''
        # for each file in the folder
        for file in files:
            # if file name doesnt start with metadata_, it's a file with text
            if not file.startswith('metadata_'):
                # TODO: progress bar
                print(file)
                # get the file name without the extension
                file_name = os.path.splitext(file)[0]
                # get the metadata from the txt file
                if os.path.exists(os.path.join(root, 'metadata_' + file_name+'.txt')):
                    with open(os.path.join(root, 'metadata_' + file_name+'.txt'), 'r', encoding='utf-8') as f:
                        metadata = f.read()
                # if it's a txt file that's not metadata
                if file.endswith('.txt') and not file.startswith('metadata_'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content.append((f.read(), file, 0,metadata))  # Add 'None' for the page number
                # if it's a pdf file
                elif file.endswith('.pdf'):
                    with pdfplumber.open(os.path.join(root, file)) as pdf:
                        for page_num in range(len(pdf.pages)):
                            page = pdf.pages[page_num]
                            text = page.extract_text()
                            from vectorize import split_text_into_segments
                            segments = split_text_into_segments(text,language='es')
                            content.append((text, file, page_num,metadata))
                            print(content)
                elif file.endswith('.html'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')
                        content.append((soup.get_text(), file, None,''))
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

    # get all the filenames to vectorize
    files_to_vectorize = [file for text, file, page_num,metadata in text_data]

    #delete duplicates from files_to_vectorize
    files_to_vectorize = list(dict.fromkeys(files_to_vectorize))
    #truncate files_to_vectorize to 100
    files_to_vectorize = str(files_to_vectorize)[:100]
        
    await update.callback_query.message.reply_text("💿 Vectorizando "+files_to_vectorize+"...")

    for text, file, page_num,metadata in text_data:
        vectorized_data = []
        metadata += ' - '+ file + ' - Página ' + str(page_num + 1) if page_num is not None else file 
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

async def vectorize_new(update, context,uid):
    # get file
    file = "Manual Scholas Ciudadania 2023.txt"
    if file.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif file.endswith('.txt'):
        with open(file, 'r', encoding='utf-8') as f:
            text = f.read()
    print(text)
    segments = split_text_into_segments(text,language='es')
    print(len(segments))
    vectorized_chunks = vectorize_chunks(segments,'','')
    # Save the vectorized data for each file with its original name
    json_filepath = 'vect.json'
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(vectorized_chunks, f, ensure_ascii=False)
