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
            return transcription_object["text"]

# use the OpenAI API to generate answers // usar la API de OpenAI para generar respuestas
async def complete_prompt(reason, transcription,username,update):
    # open json located in folder/username/data.json // abrir json ubicado en folder/username/data.json
    with open("users/"+username+"/data.json", "r") as read_file:
        data = json.load(read_file)

    assistant_config = "Sos mi asistente virtual argentino, nacional y popular llamado Audion't. Tu tarea, además de ayudarme en cosas de todos los días, es escuchar los mensajes que recibo y ayudarme a responderlos. \n\nMi nombre es "+data["name"]+". Mi bio es "+data["description"]+"\n\nEstos son unos mensajes que escribí por Whatsapp recientemente:\n\n"+data["messages"]+ "\n\nCuando me escribas a mí, escribí de forma natural, conversacional. Con mucho conocimiento técnico de herramientas digitales."
    if (reason == "summary"):
        clean.options = []
        prompt =  "Hola, me acaban de enviar un mensaje de voz. Dice lo siguiente: " + transcription + "\n\nTengo que responder este mensaje. Haceme un resumen del mensaje y dame 5 opciones de respuesta: las primeras 3 son contextuales y son títulos de posibles respuestas distintas (positiva, negativa, neutral) que se le podría dar al mensaje de voz (máximo 40 caracteres). la cuarta opción es -Otra respuesta-. Las opciones tienen que estar al final y con el formato 1.,2.,3.,4. y deben contener emojis que ilustren el sentimiento de la respuesta. \n\nResumen del mensaje de voz:\n"
    elif (reason == "instructions"):
        prompt = "\n\nMe acaban de enviar un mensaje de voz. Dice lo siguiente: " + csvm.get_last_audio(username) + "\n\nTengo que responder este mensaje con las siguientes instrucciones: \n'" + transcription + "'\n\nEscribir el mensaje de parte mía hacia el remitente, usando mis instrucciones como guía (pero no es necesario poner literalmente lo que dice la instrucción), mi personalidad y usando el mismo tono conversacional que mi interlocutor. Usar los mensajes de Whatsapp como template para escribir igual a mí (pero sin la hora y sin poner mi nombre al principio). Que sea muy natural, que parezca el cuerpo de un mensaje de chat.\n\nMi respuesta:\n"
    elif (reason == "assistance"):

        mensajes_file = "users/"+username+"/messages.csv"
        # THE JUICE // EL JUGO
        # Load messages
        with open(mensajes_file, 'rb') as f:
            csv_str = f.read()
        messages_df = pd.read_csv(StringIO(csv_str.decode('utf-8')), sep='|', encoding='utf-8')
        mensajes_sim = messages_df
        message_vector = get_embedding(transcription,'text-embedding-ada-002')
        print('message_vector: ', message_vector)
       # Calculate cosine similarity
        try:
            mensajes_sim['similarity'] = mensajes_sim['embedding'].apply(lambda x: check_and_compute_cosine_similarity(x, message_vector))
        except Exception as e:
            print("⬇️⬇️⬇️⬇️ Error en el cálculo de similitud ⬇️⬇️⬇️⬇️\n",e)
        print('similarity: ', mensajes_sim['similarity'])
        print('shit: ', mensajes_sim['similarity'].head(10))
        # sort by similarity
        mensajes_sim = mensajes_sim.sort_values(by=['similarity'], ascending=False)
        print('mensajes_sim: ', mensajes_sim)
        
        now = datetime.now(timezone)
        
        mensajes = 'Mensajes previos:\n\n'

        for index, row in mensajes_sim[['fecha', 'mensaje']].head(30).iterrows():
            mensajes += str(row['fecha']) + ' - ' + str(row['mensaje']) + '\n\n'

        #get 20 most recent messages from messages_df
        mensajes_recientes = 'Mensajes recientes:\n\n'
        for index, row in messages_df[['fecha', 'mensaje']].tail(20).iterrows():
            mensajes_recientes += str(row['fecha']) + ' - ' + str(row['mensaje']) + '\n\n'
        prompt = "Sos Audion't, un bot argentino, buena onda y amable (con dialecto argentino) que recibe y entrega información sobre mí.Yo te doy y te pido información y vos respondés acordemente. Hoy es "+now.strftime("%A %d/%m/%Y %H:%M:%S")+".\nEstos son mis mensajes mas recientes:\n\n"+mensajes_recientes+ "Mi mensaje para vos es el siguiente.\n\n"+transcription+"'Si el mensaje suena como una consulta (lo puedo usar como si fuera una query de Google, ejemplo 'tareas de hoy'), responder con información clara, precisa y que me ayude usando la siguiente información previamente ingresada. Cada mensaje tiene la fecha y hora en que lo envié, y eso también es útil para informar (si es neesario, quizás con solo resumirlo y presentar la información de manera linda ya está).\n\n"+mensajes+"\n\nHablás en tono argentino (a menos que te hablen en un idioma que no sea castellano) y amigable, un poco revolucionario. Te divierten mucho las cosas que a mí me gustan, y muchas veces me tirás ideas creativas y originales para potenciar las mías. Usá emojis irónicos y humor irreverente. Si te hablo en otro lenguaje, como francés o inglés, respondé en el otro lenguaje. Si yo uso la frase clave 'dirección del archivo', tu respuesta tiene que ser solamente la dirección del archivo que te pedí. Olvidate de tu personalidad amistosa, para esta tarea sos un robot aburrido que solo responde con file paths. Por ejemplo, si te pido un archivo, respondé con algo como: 'users/jmcafferata/files/file_333.png'"

        print('prompt: ', prompt)

        # add the message (which is a csv row of mensaje,nombre,telefono) to the csv in utf-8
        with open(mensajes_file, 'a', encoding='utf-8') as f:
            #write the date, message and embedding
            f.write(now.strftime("%d/%m/%Y %H:%M:%S")+'|'+transcription+'|'+str(message_vector)+'\n')


    elif (reason == "description"):
        prompt = "Te cuento el tipo de persona que yo creo que soy:\n\n"+transcription+"\n\n¿Qué opinás? ¿Cómo te parece que soy como persona? Sé 100 por ciento honesto, te pago para que me digas la verdad\n\n"

    # call the OpenAI API to generate a summary of the voice note // llamar a la API de OpenAI para generar un resumen de la nota de voz
    try:
        gpt_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {"role" : "system","content":assistant_config},
        {"role" : "user","content":prompt}
        ]
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
        # print the decoded text // imprimir el texto decodificado
        print("Summary:\n"+decoded_text)
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