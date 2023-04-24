import csv
from datetime import datetime
import os
import json

# store the audio message in the user's folder to be processed later // almacenar el mensaje de audio en la carpeta del usuario para ser procesado más tarde
def store_to_csv(message):

    if not os.path.exists('audios.csv'):
        with open('audios.csv', 'w', newline='', encoding='utf-8') as file:
            pass

    with open('audios.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), message])

# get the last audio message sent to the user // obtener el último mensaje de audio enviado al usuario
def get_last_audio():
    # open the csv file users/username/messages.csv and find the last message sent by sender "other" // abrir el archivo csv users/username/messages.csv y encontrar el último mensaje enviado por el remitente "other"
    with open('audios.csv', 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reversed(list(reader)):
            return row[1]

