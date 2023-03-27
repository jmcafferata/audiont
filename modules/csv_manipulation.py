import csv
from datetime import datetime
import os
import json

# store the audio message in the user's folder to be processed later // almacenar el mensaje de audio en la carpeta del usuario para ser procesado más tarde
def store_to_csv(username,sender,message):
    with open('users/'+username+'/audios.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), sender, message])
        print("Audio message stored in users/"+username+"/audios.csv")

# get the last audio message sent to the user // obtener el último mensaje de audio enviado al usuario
def get_last_audio(username):
    # open the csv file users/username/messages.csv and find the last message sent by sender "other" // abrir el archivo csv users/username/messages.csv y encontrar el último mensaje enviado por el remitente "other"
    with open('users/'+username+'/audios.csv', 'r', newline='', encoding='utf-8') as file:
        print("Reading users/"+username+"/audios.csv")
        reader = csv.reader(file)
        for row in reversed(list(reader)):
            if (row[1] == "other"):
                return row[2]

# create a folder for the user with their username, and inside it, a file called messages.csv // crear una carpeta para el usuario con su username, y dentro de ella, un archivo llamado messages.csv
def create_user_folder(username):
    #if folder doesn't exist, create it // si la carpeta no existe, crearla
    if not os.path.exists('users/'+username):
        os.mkdir('users/'+username)
        with open('users/'+username+'/messages.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["date", "sender", "message"])
        # create a json file with the user's username // crear un archivo json con el username del usuario
        with open('users/'+username+'/data.json', 'w', encoding='utf-8') as file:
            file.write('{"username":"'+username+'"}')

def create_user_data(username, field, value):
    # open the json file and update the field with the value // abrir el archivo json y actualizar el campo con el valor
    with open('users/'+username+'/data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    if field in data:
        data[field] = value
    else:
        data.setdefault(field, value)
    with open('users/'+username+'/data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def update_user_data(username, field, value):
    # open the json file and update the field by appending the value // abrir el archivo json y actualizar el campo agregando el valor
    with open('users/'+username+'/data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    if field in data:
        data[field] += value
    else:
        data.setdefault(field, value)
    with open('users/'+username+'/data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def get_user_data(username, field):
    # open the json file and return the value of the field // abrir el archivo json y devolver el valor del campo
    with open('users/'+username+'/data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    if field in data:
        return data[field]
    else:
        return None