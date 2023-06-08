import json
import os
from pathlib import Path

# function to check if user has folder in users/ folder. if not, create it
def check_user_folder(user_id):
    user_folder = Path("users/"+str(user_id))
    global_folder = Path("users/global")
    user_data_folders = ['vectorized','to_vectorize']
    if not user_folder.exists():
        user_folder.mkdir(parents=True, exist_ok=True)
        for folder in user_data_folders:
            Path("users/"+str(user_id)+"/"+folder).mkdir(parents=True, exist_ok=True)
    
    
    if not global_folder.exists():
        global_folder.mkdir(parents=True, exist_ok=True)
        for folder in user_data_folders:
            Path("users/global/"+folder).mkdir(parents=True, exist_ok=True)

     
    
    

def check_settings(uid):

    check_user_folder(uid)

    file_name = 'users/'+str(uid)+'/settings.json'

    default_settings = {
        "access_level": "user",
        "GPTversion": "gpt-4",
        "flask_testing": "False",
        "docusearch": "False",
        "uid": str(uid),
        "language": "es",
        "pending_pcp_response": "",
        "pending_pcp_message_id": 0,
        "pending_pcp_list": [],
        "scrapear": "False",
        "personality": "Soy un chatbot argentino, buena onda, copado y loco!",
        "vocabulary": "Vocabulario de palabras para usar: watafaaak, zarpado, ke loko, me muero, yasss, no me la contés bro!"
    }

    # If the file exists, check if any settings are missing.
    if os.path.isfile(file_name):
        with open(file_name, 'r') as json_file:
            user_settings = json.load(json_file)

        # Check if all default settings exist in user settings
        settings_updated = False
        for key in default_settings.keys():
            if key not in user_settings:
                user_settings[key] = default_settings[key]
                settings_updated = True
                print("Added missing setting: " + key)

        # If any settings were missing, update the file
        if settings_updated:
            with open(file_name, 'w') as json_file:
                json.dump(user_settings, json_file)

    # If the file does not exist, create it with the default settings.
    else:
        with open(file_name, 'w') as json_file:
            json.dump(default_settings, json_file)

# function that reads settings.json (a key given by the user) and returns the value
def get_settings(key,uid):

    # Check if the file exists, if not create it with default settings
    check_settings(uid)
    
    with open('users/'+str(uid)+'/settings.json') as json_file:
        data = json.load(json_file)
        return data[key]

# function that writes to settings.json (a key given by the user) and returns the value
def write_settings(key, value,uid):

    # Check if the file exists, if not create it with default settings
    check_settings(uid)

    # Write the value to the key
    with open('users/'+str(uid)+'/settings.json') as json_file:
        data = json.load(json_file)
        data[key] = value
        with open('users/'+str(uid)+'/settings.json', 'w') as outfile:
            json.dump(data, outfile)


