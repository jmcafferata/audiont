import modules.clean_options as clean
import openai
import modules.convert_to_wav as convert
import modules.csv_manipulation as csvm
import modules.decode_utf8 as decode
import json
from pathlib import Path # library used to handle file paths // librería usada para manejar rutas de archivos
import config as config # import the config file // importar el archivo de configuración

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
    if (reason == "summary"):
        clean.options = []
        prompt = "Yo soy un asistente virtual llamado Audion't. Mi tarea es escuchar los mensajes que mis amos reciben y ayudar a responderlos. \n\nMi amo se llama "+config.my_name+". "+config.about_me_spanish+"\n\nA mi amo le acaban de enviar un mensaje de voz. Dice lo siguiente: " + transcription + "\n\nTengo que ayudar a mi amo a responder este mensaje. Primero le voy a hacer un resumen del mensaje y luego le voy a dar 5 opciones de respuesta: las primeras 3 son contextuales y son títulos de posibles respuestas distintas (positiva, negativa, neutral) que se le podría dar al mensaje de voz (máximo 40 caracteres). la cuarta opción es -Otra respuesta-. Las opciones tienen que estar al final y con el formato 1.,2.,3.,4. y deben contener emojis que ilustren el sentimiento de la respuesta. \n\nResumen del mensaje de voz:\n"
    elif (reason == "instructions"):
        prompt = "Yo soy un asistente virtual llamado Audion't. Mi tarea es escuchar los mensajes que mis amos reciben y ayudar a responderlos. \n\nMi amo se llama "+config.my_name+". "+config.about_me_spanish+"\n\nA mi amo le acaban de enviar un mensaje de voz. Dice lo siguiente: " + csvm.get_last_audio(username) + "\n\nTengo que ayudar a mi amo a responder este mensaje. Me dio las siguientes instrucciones: \n'" + transcription + "'\n\nEscribir el mensaje de parte de mi amo hacia el remitente, usando sus instrucciones como guía.\n\nMensaje de mi amo:\n"
    # call the OpenAI API to generate a summary of the voice note // llamar a la API de OpenAI para generar un resumen de la nota de voz
    gpt_response = openai.Completion.create(
        model="text-davinci-003",
        # The prompt is the text that the model will use to generate a response. I add some things about me so that the model can generate a more personalized response // El prompt es el texto que el modelo usará para generar una respuesta. Agrego algunas cosas sobre mí para que el modelo pueda generar una respuesta más personalizada
        prompt=prompt,
        # The temperature is a number between 0 and 1 that determines how random the model's response will be // La temperatura es un número entre 0 y 1 que determina qué tan aleatoria será la respuesta del modelo
        temperature=0.7,
        # Tokens is kinda like the number of words the model will use to generate a response // Tokens es como el número de palabras que el modelo usará para generar una respuesta
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    # get the text from the response // obtener el texto de la respuesta
    text = (gpt_response.choices[0].text)
    # decode the text // decodificar el texto
    decoded_text = decode.decode_utf8(text)
    # print the decoded text // imprimir el texto decodificado
    print("Summary:\n"+decoded_text)
    return decoded_text
