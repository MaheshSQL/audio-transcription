# Note: The file size limit for the Whisper model is 25 MB. 
# If you need to transcribe a file larger than 25 MB, you can use the Azure AI Speech batch transcription API.

import os
import time
from openai import AzureOpenAI
from dotenv import load_dotenv
import base64
from io import BytesIO  

from utils import split_audio, export_chunk_to_base64

load_dotenv()

start_time = time.time()  

deployment_id = "gpt-4o-audio-preview"
audio_test_files = ["../audio_files/4379528_trimmed.mp3", "../audio_files/4379528.mp3"]
output_path = "../transcripts"
 
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version= '2025-01-01-preview',
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
)

audio_test_file_selected = audio_test_files[1] # Select the file from the list
audio_test_file_extension = os.path.splitext(audio_test_file_selected)[1].split('.')[1] # mp3, wav, etc.
print(f'audio_test_file_extension: {audio_test_file_extension}')

system_message = '''You are generating a text transcript for documentation. 
    You will be given audio file, listen to it carefully ignoring background sounds.
    Do not guess words that you cannot hear clearly. Say [inaudible] for words that you cannot hear clearly.
    Do not say transcription or anything else at start or end of the transcription.
    Do not say I can't assist with transcribing audio.
    '''

prompt = '''Transcribe this audio file into text.'''

# Split the audio file into chunks of chunk_length (e.g. NN seconds) for supplying into chat completion messages
audio_chunks = split_audio(audio_test_file_selected, chunk_length=30)
print(f'Number of audio chunks: {len(audio_chunks)}')

completion_result_list = []

for _c, chunk in enumerate(audio_chunks):

    print(f'Processing chunk {_c + 1} of {len(audio_chunks)}')
    
    temp_file_path = None # You may want to save the chunk to a temporary file if needed for analysis or further processing
    # OR
    # temp_file_path = os.path.splitext(audio_test_file_selected)[0] + '_chunk.' + audio_test_file_extension
    
    # Export chunk to Base64
    chunk_base64 = export_chunk_to_base64(chunk, file_format=audio_test_file_extension, temp_file_path=temp_file_path) 

    # To read and encode from local audio audio uncomment the following lines
    # with open(audio_test_file_selected, 'rb') as audio_reader:     
    #     encoded_string = base64.b64encode(audio_reader.read()).decode('utf-8') 

    # To save the chunk to a temporary file and read it back as Base64 uncomment the following lines
    # with open(temp_file_path, 'rb') as audio_reader: 
    #     chunk_base64 = None
    #     chunk_base64 = base64.b64encode(audio_reader.read()).decode('utf-8') 

    # Make the audio chat completions request
    completion_result_chunk = client.chat.completions.create( 
        model=deployment_id, 
        modalities=["text"],  # ["text", "audio"]
        # audio={"voice": "alloy", "format": "wav"}, 
        temperature=0,
        max_tokens =4096,
        messages=[ 
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_message
                    }
                ]
            },
            { 
                "role": "user", 
                "content": [ 
                    {  
                        "type": "text", 
                        "text": prompt
                    }, 
                    { 
                        "type": "input_audio", 
                        "input_audio": { 
                            "data": chunk_base64, 
                            "format": audio_test_file_extension # mp3, wav
                        } 
                    } 
                ] 
            }, 
        ] 
    ) 

    completion_result_list.append(completion_result_chunk)

    # break  # Remove this line to process all chunks

end_time = time.time()

# print(f'completion_result_list: {completion_result_list}')

# Calculate time taken in seconds  
time_taken = end_time - start_time  
print(f"Time taken: {time_taken:.2f} seconds")  

# Save the variable to the file
output_file_path = os.path.join(output_path, '4o_audio_transcript_' + os.path.basename(audio_test_file_selected) +'.txt')
with open(output_file_path, "w") as file:  
    for _r, completion_result in enumerate(completion_result_list):
        if completion_result.choices and completion_result.choices[0].finish_reason == "stop":
            content = completion_result.choices[0].message.content
            file.write( str(f'Audio chunk {_r+1}') + ': '+ content + "\n")
        elif completion_result.choices and completion_result.choices[0].finish_reason != "stop":
            file.write( str(f'Audio chunk {_r+1}') + ': ' + f'Skipped,{completion_result.choices[0].finish_reason}' + "\n")
        else:
            file.write( str(f'Audio chunk {_r+1}') + ': '+ f'Skipped, {completion_result}' + "\n")
    print(f"Transcription saved to {output_file_path}")