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
from openai.embeddings_utils import get_embedding, cosine_similarity
from ast import literal_eval
import numpy as np



import pandas as pd


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

openai.api_key = config.openai_api_key

BOT_ID = client.api_call("auth.test")['user_id']

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
                {"role": "user", "content": "Search query: " + text + "\nAvailable documents: " + str(files) + "\n\nLLM: ["}

            ]
        )
        
        print("################ relevant files for the query ############", docusearch_response.choices[0].message.content)

        # add the bracket so it's an array
        docusearch_response = "[" + docusearch_response.choices[0].message.content

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
                # if file is customer_stories.json
                if file == 'db/customer_stories.json':
                    top_n = 2
                    relevant = get_json_top_entries(text, file, top_n)
                    relevant_text += relevant

                # truncate the final_similar_entries to 5000 characters
                relevant_text = relevant_text[:8000]
                # add the data in text_chunks to the relevant_text
                with open(file,encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    #get text_chunks on each json object in the file   
                    for item in data:
                        relevant_text = relevant_text + item['text_chunk']
                        # truncate the relevant_text to 5000 characters
                        relevant_text = relevant_text[:8000]


        prompt_messages = []

        # append the message
        prompt_messages.append({"role": "user", "content": text + "\nUse the following data as context to generate a response: "})
        prompt_messages.append({"role": "user", "content": relevant_text})
        

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
    
    elif intent.startswith('chat'):

        chat_response = openai.ChatCompletion.create(
            model='gpt-4',
            temperature=0.2,
            messages=[
                {"role": "system", "content": """
You are Cledara Bot. You provide information about Cledara. If someone asks a question that you don't know, say that you don't know and refer the user to support@cledara.com, or the website cledara.com. Your writing style is kind, affectionate and you use emojis.
"""},
                {"role": "user", "content": text}

            ]
        )
        return chat_response.choices[0].message.content



@slack_event_adapter.on('message')
def message(payload):
    print(payload)
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    ts = event.get('ts')

    

    
    if BOT_ID != user_id and BOT_ID in text:
        #react to the message
        client.reactions_add(
            channel=channel_id,
            name="searching",
            timestamp=ts
    )
        # get user intent
        intent = understand_intent(text)

        # extract entities
        entities = extract_entities(text)
        # generate response

        response = generate_response(intent,entities,text)

        client.chat_postMessage(channel=channel_id, text=response,)



        

# TEST
# text = "@Cledara Bot i want to do a quarterly review of my software stack. what process should i follow?"
# intent = understand_intent(text)
# entities = extract_entities(text)
# response = generate_response(intent,entities,text)
# print("response: ", response)



if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5020, debug=True)