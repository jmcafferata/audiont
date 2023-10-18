import os
import json
import pdfplumber
from bs4 import BeautifulSoup
import openai
from openai.embeddings_utils import get_embedding

openai.api_key = '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'

def vectorize(input_folder):
    text_data = read_files(input_folder)

    # Check if the output folder exists. If not, create it.
    if not os.path.exists(input_folder + 'vectorized'):
        os.makedirs(input_folder + 'vectorized')

    # get all the filenames to vectorize
    files_to_vectorize = [file for text, file, page_num,metadata in text_data]

    #delete duplicates from files_to_vectorize
    files_to_vectorize = list(dict.fromkeys(files_to_vectorize))
    #truncate files_to_vectorize to 100
    files_to_vectorize = str(files_to_vectorize)[:100]
        

    for text, file, page_num,metadata in text_data:
        vectorized_data = []
        metadata += ' - '+ file + ' - Página ' + str(page_num + 1) if page_num is not None else file 
        text_chunks = split_text(text)
        vectorized_chunks = vectorize_chunks(text_chunks, metadata, file)
        vectorized_data.extend(vectorized_chunks)

        # Save the vectorized data for each file with its original name
        json_filepath = input_folder + 'vectorized/' + file + '.json'

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
                            text = page.extract_text(x_tolerance=2, y_tolerance=2)
                            # split text in chunks of max 500 characters
                            text_chunks = split_text(text, 500)
                            for text_chunk in text_chunks:
                                content.append((text_chunk, file, page_num,metadata))
                elif file.endswith('.html'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')
                        content.append((soup.get_text(), file, None,''))
                counter += 1
    return content

def split_text(text, chunk_size=2048):
    words = text.split()
    chunks = []
    current_chunk = []
    counter = 0
    counter_end = len(words)

    for word in words:

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
        embedding = get_embedding(chunk,"text-embedding-ada-002")
        vectorized_data.append({
            'filename': file,
            'metadata': metadata,
            'text_chunk': chunk,
            'embedding': embedding,
        })
        counter += 1

    return vectorized_data

folder = os.getcwd() + '/modules/vectorize_tests'
print(folder)
vectorize(folder)