import os
import subprocess
import shutil 
import openai
import random

def convert_to_wav(audio_file):
    audio_file_name = os.path.basename(audio_file)
    audio_file_name_without_extension = os.path.splitext(audio_file_name)[0]
    # generate random number from 1 to 1000

    random_number = str(random.randint(1, 1000))
    new_file_name = audio_file_name_without_extension + random_number + ".mp3"
    
    # compress the audio
    command = ["ffmpeg", "-i", audio_file, "-b:a", "192k", new_file_name]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error:\n{e.stderr.decode('utf-8')}")
        raise e

    return new_file_name



# def partir_video(input_file, counter):

#     output_pattern = 'temp_output_%03d.mp3'

#     # Construct the ffmpeg command
#     command = ['ffmpeg', '-i', input_file, '-vn', '-map', '0:a',
#             '-f', 'segment', '-segment_time', '120', '-reset_timestamps', '1', '-b:a','192k',output_pattern]

#     # Run the command
#     subprocess.run(command)

#     # calculate how many files were created
#     files = os.listdir()
#     audio_files = [file for file in files if file.startswith("temp_output") and file.endswith(".mp3")]
#     print("Number of audio files created: ", len(audio_files))

#     # Rename the output files
#     for i, file in enumerate(sorted(audio_files)):
#         new_name = f'output_{str(counter + i).zfill(3)}.mp3'
#         shutil.move(file, new_name)

#     # increase the counter for the next video according to the number of files created
#     counter = counter + len(audio_files)

#     return counter
    
# def transcribe_audios(prompt, language):
#     files = os.listdir()
#     audio_files = [file for file in files if file.startswith("output") and file.endswith(".mp3")]

#     # sort files
#     audio_files.sort()

#     df = pd.DataFrame(columns=["chunk", "text", "embedding"])

#     csv_file = 'transcriptions.csv'

#     for audio_file in audio_files:
#         print(audio_file)
#         file_number = audio_file.split('.')[0]
#         file_number = file_number[-3:]

#         with open(audio_file, "rb") as file:
#             transcription_object = openai.Audio.transcribe(
#                 "whisper-1", file, language=language, prompt=prompt
#             )
#             print("Transcription:\n" + transcription_object["text"])

#             print("getting embedding")
#             # if transcription empty, skip
#             if transcription_object["text"] == "":
#                 continue
#             vector = get_embedding(transcription_object["text"], "text-embedding-ada-002")

#             new_row = pd.DataFrame({"chunk": [file_number], "text": [transcription_object["text"]], "embedding": [vector]})
#             df = pd.concat([df, new_row], ignore_index=True)

#             # Check if the CSV file exists, if not, create a new file with headers
#             if not os.path.isfile(csv_file):
#                 df.to_csv(csv_file, mode='w', header=True, index=False, encoding='utf-8', sep='|')
#             else:
#                 # Append the new data to the existing CSV
#                 df.to_csv(csv_file, mode='a', header=False, index=False, encoding='utf-8', sep='|')

#             # Clear the DataFrame for the next iteration
#             df = df[0:0]

#     # delete the audio files
#     for file in audio_files:
#         os.remove(file)

# def check_and_compute_cosine_similarity(x, message_vector):
#     x = np.array(literal_eval(x), dtype=np.float64)  # Convert x to float64
#     return cosine_similarity(x, message_vector)

# def get_top_entries(db, query, top_n=15):

#     with open(db, 'rb') as f:
#         csv_str = f.read()
#     entries_df = pd.read_csv(StringIO(csv_str.decode('utf-8')), sep='|', encoding='utf-8', escapechar='\\')
#     query_vector = get_embedding(query, 'text-embedding-ada-002')

#     entries_df['similarity'] = entries_df['embedding'].apply(lambda x: check_and_compute_cosine_similarity(x, query_vector))
   
#     # sort by similarity
#     entries_df = entries_df.sort_values(by=['similarity'], ascending=False)

#     print("Entries df",entries_df)
#     # Initialize a string with the df headers
#     headers = list(entries_df.columns)
#     similar_entries = ' | '.join(headers) + '\n'

#     # Iterate over the rows of the DataFrame
#     for index, row in entries_df.head(top_n).iterrows():
#         # drop the 'embedding' column
#         row = row.drop('embedding')
#         row_str = ' | '.join(map(str, row.values))
#         print("row_str", row_str)
#         # Append the row string to 'similar_entries' followed by a newline character
#         similar_entries += row_str + '\n'

#     return similar_entries

# def make_questions(db,system):
#     search = input("¿Qué querés buscar?")
#     # Get the top entries
#     top_entries = get_top_entries(db, search,25)
#     # delete any text between brackets
#     print(top_entries)
#     query = input("¿Qué querés hacer con esto?")
#     # generate a propmt for answering the query
#     prompt = []
#     prompt.append({"role": "system", "content":system})
#     prompt.append({"role": "user", "content": top_entries})
#     prompt.append({"role": "user", "content": "Based on the data above, do the following: "+query})
#     gpt_response = openai.ChatCompletion.create(
#         model='gpt-4',
#         messages=prompt,
#     )
#     print(gpt_response.choices[0].message.content)


# db = 'transcriptions.csv'

# openai.api_key = "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"
# system = 'Prompt:<data and instructions>\n\nResponse:<answer>'
# description = ""
# language = "es"


# # for each file in input folder partir video
# input_folder = "input"
# files = os.listdir(input_folder)
# input_files = [file for file in files if file.endswith(".MP3")]

# # sort files by name
# input_files.sort()

# counter = 0

# for input_file in input_files:
#     counter = partir_video(os.path.join(input_folder, input_file), counter)

# transcribe_audios(description,language)

# make_questions(db,system)
