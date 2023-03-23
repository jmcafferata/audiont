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
import math

# set the OpenAI API key, so the code can access the API // establecer la clave de la API de OpenAI, para que el código pueda acceder a la API
openai.api_key = config.openai_api_key

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
    new_audio_path = convert.convert_to_wav(file_path)
    # open the wav file // abrir el archivo wav
    wav_audio = open(new_audio_path, "rb")
    # call the OpenAI API to get the text from the audio file // llamar a la API de OpenAI para obtener el texto del archivo de audio
    transcription_object = openai.Audio.transcribe(
        "whisper-1", wav_audio, language="es", prompt="esto es una nota de voz. hay momentos de silencio en el audio, cuidado con eso.")
    # print the text extracted from the audio file // imprimir el texto extraído del archivo de audio
    print("Transcription:\n"+transcription_object["text"])
    # store the transcription as a new line in users/username/messages.csv encoded in UTF-8 // almacenar la transcripción como una nueva línea en users/username/messages.csv codificada en UTF-8
    
    return transcription_object["text"]

# use the OpenAI API to generate answers // usar la API de OpenAI para generar respuestas
async def complete_prompt(reason, transcription,username):
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
        prompt = transcription
    elif (reason == "description"):
        prompt = "Te cuento el tipo de persona que yo creo que soy:\n\n"+transcription+"\n\n¿Qué opinás? ¿Cómo te parece que soy como persona? Sé 100 por ciento honesto, te pago para que me digas la verdad\n\n"

    # call the OpenAI API to generate a summary of the voice note // llamar a la API de OpenAI para generar un resumen de la nota de voz
    gpt_response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {"role" : "system","content":assistant_config},
        {"role" : "user","content":prompt}
        ]
    )
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