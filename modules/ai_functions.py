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
        if update:
            await update.message.reply_text('👓 Data relacionada...👇\n' + str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n')
        try:
            related_data += str(row['filename']) + ' - ' + str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n'

        except:
            related_data += str(row['metadata']) + ' - ' + str(row['text_chunk']) + '\n\n'
    
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
        del row['row_id']
        # Convert the row to a string and join the values using '|'
        row_str = ' '.join(map(str, row.values))
        # Append the row string to 'similar_entries' followed by a newline character
        similar_entries += row_str + '\n'

    return similar_entries

async def understand_intent(update, message):
    # get the message from the user // obtener el mensaje del usuario
    
    prompt = []
    # get global json documents from the users/global folder only if they are JSONs
    global_jsons = [f for f in os.listdir('users/global/vectorized') if f.endswith('.json')]
    # get the json documents from the user's folder
    user_jsons = [f for f in os.listdir('users/' + str(update.message.from_user.id) + '/vectorized') if f.endswith('.json')]
    # combine the two lists // combinar las dos listas
    jsons = global_jsons + user_jsons

    intent_response = openai.ChatCompletion.create(
                model="gpt-4",
                temperature=0.5,
                messages=[
                    {"role": "system", "content": """based on the user input, the available functions and available documents, you will respond with the name of the function to execute. if you don't know, respond "chat"

available_functions=[
{"function":"chat","default":"true","fallback":"true","description":"for chatting with the AI chatbot","example_user_message":"hola! todo bien?"},
{"function":"docusearch","description":"for looking up relevant information in one of the user documents, based on the available_documents","example_user_message":"buscar los efectos de la microdosis en el libro de Hoffman"},
{"function":"scrape","description":"for scraping the internet for additional data","example_user_message":"buscar en cledara.com los features de Cledara"},
{"function":"audiosearch","description":"for looking up relevant information in previous related messages","example_user_message":"buscar en audios anteriores un presupuesto de baño"},
{"function":"personality","description":"for changing the personality of the AI chatbot","example_user_message":"cambiar la personalidad a la de un abogado"},
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
            model="gpt-4",
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
            model="gpt-4",
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
                top_n = round(15/len(docusearch_file))
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


    ######################### AUDIOSEARCH #########################
    elif intent.startswith('audiosearch'):
        await update.message.reply_text('searching audios')
    
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
            model="gpt-4",  
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

    # if users/global folder doesn't exist, create it
    if not os.path.exists('users/global'):
        os.makedirs('users/global')

    now = datetime.now()

    print("################# ENTERING CHAT MODE #################")

    # check what the user wants
    intent = await understand_intent(update, message)

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
        f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|'+full_name+'|'+message+'|'+message_vector+'\n')
    
    return "¡Mensaje guardado!"
    
################### VECTORIZE ############################

def read_files(input_folder):
    content = []
    for root, dirs, files in os.walk(input_folder):
        counter = 0
        counter_end = len(files)
        metadata = ''
        for file in files:
            # if file name doesnt start with metadata_
            if not file.startswith('metadata_'):
                print('Progress: {}/{}'.format(counter, counter_end))
                print(file)
                # get the file name without the extension
                file_name = os.path.splitext(file)[0]
                # get the metadata from the txt file
                if os.path.exists(os.path.join(root, 'metadata_' + file_name+'.txt')):
                    with open(os.path.join(root, 'metadata_' + file_name+'.txt'), 'r', encoding='utf-8') as f:
                        metadata = f.read()

                if file.endswith('.txt'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content.append((f.read(), file, 0,''))  # Add 'None' for the page number
                elif file.endswith('.pdf'):
                    with pdfplumber.open(os.path.join(root, file)) as pdf:
                        for page_num in range(len(pdf.pages)):
                            page = pdf.pages[page_num]
                            text = page.extract_text()
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
        model = "gpt-4"
        chat_messages.append({"role":"user","content":"""
        Me acaban de enviar un mensaje de voz. Dice lo siguiente:
    
        """ + csvm.get_last_audio() + """
        
        Tengo que responder este mensaje con las siguientes instrucciones:
        
        """ + message + """
        
        Escribir el mensaje de parte mía hacia el remitente, usando mis instrucciones como guía (pero no es necesario poner literalmente lo que dice la instrucción), mi personalidad y usando el mismo tono conversacional que mi interlocutor. Ofrecer la mayor cantidad de ayuda posible, y ser bien específico y claro, con lenguaje simple e informal argentino."""})

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
