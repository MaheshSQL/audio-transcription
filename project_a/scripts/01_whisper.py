# Note: The file size limit for the Whisper model is 25 MB. 
# If you need to transcribe a file larger than 25 MB, you can use the Azure AI Speech batch transcription API.

import os
import time
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

start_time = time.time()  

deployment_id = "whisper" # "gpt-4o-transcribe" 
audio_test_files = ["../audio_files/4379528_trimmed.mp3", "../audio_files/4379528.mp3"]
output_path = "../transcripts"
 
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version= '2024-10-21', #'2025-04-01-preview, #'2024-02-01'
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
)

audio_test_file_selected = audio_test_files[1] # Select the file from the list

result = client.audio.transcriptions.create(
    file=open(audio_test_file_selected, "rb"),            
    model=deployment_id,
    temperature=0,
    prompt='''You are generating a text transcript for documentation. 
    You will be given audio file, listen to it carefully ignoring background sounds.
    Do not guess words that you cannot hear clearly.''',
    # response_format="json" # text, srt
)

end_time = time.time()
# print(result.text)

# Calculate time taken in seconds  
time_taken = end_time - start_time  
print(f"Time taken: {time_taken:.2f} seconds")  

# Save the variable to the file
output_file_path = os.path.join(output_path, 'whisper_transcript_' + os.path.basename(audio_test_file_selected) +'.txt')
with open(output_file_path, "w") as file:  
    file.write(result.text)
    print(f"Transcription saved to {output_file_path}")