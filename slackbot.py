import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
import openai
import json
import ast
import config

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

openai.api_key = config.openai_api_key

BOT_ID = client.api_call("auth.test")['user_id']

def understand_intent(text):
    global_jsons = [f for f in os.listdir('db') if f.endswith('.json')]
    intent_response = openai.ChatCompletion.create(
                model='gpt-4',
                temperature=0.5,
                messages=[
                    {"role": "system", "content": """
                     based on the user input, the available functions and available documents, you will respond with the name of the function to execute. if you don't know, respond "chat"

                    available_functions=[
                    {"function":"chat","default":"true","fallback":"true","description":"for chatting with the AI chatbot","example_user_message":"hola! todo bien?"},
                    {"function":"docusearch","description":"for looking up relevant information in one of the documents, based on the available_documents","example_user_messages":["how to add an application in cledara","get me a customer story about finance","what can cledara do"]},

                    ]

                    available_documents=""" + str(global_jsons) + """

                    ###

                    User: <user message>
                    Assistant: <function>"""},
                    {"role": "user", "content": text }

                ]
            )
    intent = intent_response.choices[0].message.content
    print("intent: \n", intent)
    return intent

def extract_entities(text):
    #extract the search query from the message
    query_response = openai.ChatCompletion.create(
        model='gpt-4',
        temperature=0.2,
        messages=[
            {"role":"system","content":"Example input: 'buscar en henry george el concepto de impuesto único'.\nExample output: 'impuesto único'"},
            {"role": "user", "content": "Extract the search query from the following message: " + text},
            {"role":"assistant","content":"The search query is: "}
        ]
    )
    return query_response.choices[0].message.content

def generate_response(intent,entities,text):
    ###### DOCUSEARCH ######
    if intent.startswith('docusearch'):
        
        # get the available documents
        files = []
        global_jsons = [f for f in os.listdir('db') if f.endswith('.json')]

        # get the file paths // obtener las rutas de los archivos
        for file in global_jsons:
            files.append('db/' + file)

        print('files: ', files)

        # get a list of the relevant files for the query
        docusearch_response = openai.ChatCompletion.create(
            model='gpt-4',
            temperature=0.2,
            messages=[
                {"role": "system", "content": """Prompt: As a powerful language model, your task is to help users by providing relevant JSON documents based on their search query. A user will provide you with a search query and a list of available JSON documents. You must respond with an array of the 3 files that are most relevant to the query.

                User: Search query: "Sustainable energy sources" 
                Available documents: ["Introduction to Renewable Energy.pdf.json", "Fossil Fuels and Climate Change.pdf.json", "Solar and Wind Power.pdf.json", "Nuclear Energy Pros and Cons.pdf.json", "Sustainable Energy Solutions.pdf.json", "The Future of Oil.pdf.json"]

                LLM: ['db/Introduction to Renewable Energy.pdf.json', 'db/Solar and Wind Power.pdf.json', 'db/Sustainable Energy Solutions.pdf.json']"""},
                {"role": "user", "content": "Search query: " + text + "\nAvailable documents: " + str(files) + "\n\nLLM: ['"}

            ]
        )
        
        print("################ relevant files for the query ############", docusearch_response.choices[0].message.content)

        # add the bracket so it's an array
        docusearch_response = "['" + docusearch_response.choices[0].message.content

        # get the text up until the first '] including the ']'
        docusearch_response = docusearch_response[:docusearch_response.find(']')+1]

        docusearch_files = ast.literal_eval(docusearch_response)

        print("################ documents PARSED ############", docusearch_files)

        relevant_text = ''

        # for each file in the docusearch_response
        for file in docusearch_files:
            
            # if file doesn't end with .json, add it
            if not file.endswith('.json'):
                file = file + '.json'
            # if file is json
            if file.endswith('.json'):
                # add the data in text_chunks to the relevant_text
                with open(file,encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    #get text_chunks on each json object in the file   
                    for item in data:
                        relevant_text = relevant_text + item['text_chunk']

        prompt_messages = []

        prompt_messages.append({"role": "user", "content": relevant_text})
        
        # append the message
        prompt_messages.append({"role": "user", "content": text})

        #for each prompt message, print
        for prompt_message in prompt_messages:
            print(prompt_message)

        response = openai.ChatCompletion.create(
            model='gpt-4',
            temperature=0.2,
            messages=prompt_messages
        )

        response_string = response.choices[0].message.content
        print("################ response_string ############", response_string)

        return response_string


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    
    if BOT_ID != user_id and BOT_ID in text:
        # get user intent
        intent = understand_intent(text)

        # extract entities
        entities = extract_entities(text)
        # generate response

        response = generate_response(intent,entities,text)

        client.chat_postMessage(channel=channel_id, text=response)
        

# TEST
# text = "how to add a new app"
# intent = understand_intent(text)
# entities = extract_entities(text)
# response = generate_response(intent,entities,text)
# print("response: ", response)



if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5020, debug=True)