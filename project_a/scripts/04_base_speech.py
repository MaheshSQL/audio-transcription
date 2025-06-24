import os
import time
from openai import AzureOpenAI
from dotenv import load_dotenv

from utils import get_speech_to_text_models, get_blob_service_client, upload_binary_data_to_azure_storage, generate_sas_uri, submit_transcription_request, get_transcription, get_transcription_files, download_file_from_web
import json

load_dotenv()

start_time = time.time()  

demo_flag = True
print(f'demo_flag: {demo_flag}')

audio_test_files = ["../audio_files/4379528_trimmed.mp3", "../audio_files/4379528.mp3"] if not demo_flag else ["../audio_files_sample/wikipediaOcelot.wav"]
output_path = "../transcripts" if not demo_flag else "../transcripts_sample"

AZURE_AI_FOUNDRY_KEY = os.getenv("AZURE_AI_FOUNDRY_KEY")  # Azure AI Foundry resource key
STORAGE_BLOB_SAS = os.getenv('STORAGE_BLOB_SAS')
STORAGE_CONTAINER_NAME = os.getenv('STORAGE_CONTAINER_NAME')
STORAGE_NAME= os.getenv('STORAGE_NAME')
STORAGE_KEY = os.getenv('STORAGE_KEY')

audio_test_file_selected = audio_test_files[1] if not demo_flag else audio_test_files[0] # Select the file from the list
audio_test_file_extension = os.path.splitext(audio_test_file_selected)[1].split('.')[1] # mp3, wav, etc.
print(f'audio_test_file_extension: {audio_test_file_extension}')

api_version='2024-11-15' # In this example using v3.2, please check the utils.py for details / modifications

##### Part 1: List available speech-to-text models
# Get list of available speech-to-text models (This is optional, but useful to know available models)
api_url = 'https://australiaeast.api.cognitive.microsoft.com' # 'https://eastus.api.cognitive.microsoft.com'
speech_to_text_models_result = get_speech_to_text_models(api_url=api_url, api_version=api_version, subscription_key=AZURE_AI_FOUNDRY_KEY)
# print(f"Available speech-to-text models: {json.dumps(speech_to_text_models_result, indent=4)}")

# Save available models to a file as all text is not printed to console
region = api_url.split("//")[1].split(".")[0] # Extract region from the URL
speech_to_text_models_file_path = os.path.join(output_path, f'speech_to_text_models_{region}.json')

with open(speech_to_text_models_file_path, "w") as file:
    file.write(json.dumps(speech_to_text_models_result, indent=4))
    print(f"Available speech-to-text models saved to {speech_to_text_models_file_path}")

##### Part 2: Upload the local audio file to Azure Blob Storage

# Get blob service clieant using SAS
blob_service_client_sas = get_blob_service_client(STORAGE_BLOB_SAS)

# Read binary data from the sample file  
with open(audio_test_file_selected, "rb") as audio_file:  
    binary_data = audio_file.read()  

    # Save to Azure Storage (for attribute extraction abnd ingestion to AI Search)
    upload_binary_data_to_azure_storage(blob_service_client=blob_service_client_sas,
                                        storage_container=STORAGE_CONTAINER_NAME, 
                                        storage_path='uploads', 
                                        storage_file_name=os.path.basename(audio_test_file_selected), 
                                        binary_data=binary_data)
    print(f"Uploaded {audio_test_file_selected} to Azure Blob Storage at {STORAGE_CONTAINER_NAME}/uploads/{os.path.basename(audio_test_file_selected)}")

##### Part 3: Transcribe the audtio

# Generate SAS URI for the uploaded file in Azure Storage for use with the transcription API
audio_test_file_SAS = generate_sas_uri(storage_account_name = STORAGE_NAME, 
                                       storage_account_key = STORAGE_KEY, 
                                       container_name = STORAGE_CONTAINER_NAME, 
                                       storage_path='uploads', 
                                       storage_file_name=os.path.basename(audio_test_file_selected), 
                                       expiry_minutes= 5 # Increase this if you need more time for transcription
                                       )

# print(f'audio_test_file_SAS: {audio_test_file_SAS}') # For debugging purpose only
print('SAS URI generated for the uploaded audio file.')

# Submit transcription request to Azure AI Speech service
# Note: model_url is obtained from the list of available models JSON created in Part 1 above.
transcription_request_response = submit_transcription_request(api_url=api_url, 
                                                              api_version=api_version, 
                                                              subscription_key=AZURE_AI_FOUNDRY_KEY, 
                                                              content_urls = [audio_test_file_SAS], 
                                                              locale = 'en-AU', 
                                                              transcription_display_name = 'Transcription of ' + os.path.basename(audio_test_file_selected), 
                                                              model_url = 'https://australiaeast.api.cognitive.microsoft.com/speechtotext/v3.2/models/base/7b06ba5e-9d1b-4a16-abde-a02efc587644?api-version=3.2', # "20240614 Batch Transcription" "en-AU base model
                                                              word_level_timestamps_enabled=True,
                                                              is_whisper = True,  # Set to True for Whisper model
                                                              )
# print(f'transcription_request_response: {json.dumps(transcription_request_response, indent=4)}')
if transcription_request_response:
    print(f'Transcription request submitted successfully.')

submission_id = None
if transcription_request_response and transcription_request_response.get('self'):
    submission_id = transcription_request_response['self'].split('/')[-1]  # Extract submission ID from the self link

##### Part 4: Retrieve the transcription result    

if submission_id:
    print(f'Started polling for transcription result with submission ID: {submission_id}')

    completed_flag = False # Set the flag

    while not completed_flag:
    
        get_transcription_response = get_transcription(api_url=api_url, api_version=api_version, submission_id=submission_id, subscription_key=AZURE_AI_FOUNDRY_KEY)

        if get_transcription_response and get_transcription_response.get("status") == "Succeeded":
            print(f'Transcription succeeded, getting files')
            # print(f'get_transcription_response: {json.dumps(get_transcription_response, indent=4)}')

            # Get transcription files
            get_transcription_files_response = get_transcription_files(api_url=api_url, api_version=api_version, submission_id=submission_id, subscription_key=AZURE_AI_FOUNDRY_KEY)
            # print(f'get_transcription_files_response: {json.dumps(get_transcription_files_response, indent=4)}')

            # Get file URL from the response
            if get_transcription_files_response and get_transcription_files_response.get("values"):

                # Go through the each file in the response
                for _f, file_info in enumerate(get_transcription_files_response.get("values", [])):
                    file_name = file_info.get("name")
                    file_kind = file_info.get("kind")
                    content_url = file_info.get("links", {}).get("contentUrl")

                    output_file_path_json = os.path.join(output_path, f'base_speech_transcript_{_f}_' + os.path.basename(audio_test_file_selected) +'.json')

                    # There could be multiple files, so we will save each file with a unique name
                    if file_kind == 'Transcription':
                        # Download the transcription file from the content URL SAS URI
                        download_file_from_web(url=content_url, save_path=output_file_path_json)

                        # Get the text component from JSON file saved in the output path
                        with open(output_file_path_json, 'r') as file:
                            transcription_data = json.load(file)
                            transcription_text = transcription_data.get('combinedRecognizedPhrases', [{}])[0].get('display', '')
                            
                            # Save to a text file
                            output_file_path_txt = os.path.join(output_path, f'base_speech_transcript_{_f}_' + os.path.basename(audio_test_file_selected) +'.txt')
                            with open(output_file_path_txt, 'w') as text_file:
                                text_file.write(transcription_text)
                            print(f'Transcription text saved to {output_file_path_txt}')

                    if file_kind == 'TranscriptionReport':
                        # Handle the transcription report file donwload if needed
                        pass                                           

            completed_flag = True

        elif get_transcription_response and get_transcription_response.get("status") == "NotStarted" or get_transcription_response and get_transcription_response.get("status") == "Running":
            print(f'Not completed yet, waiting for 5 seconds to retry...')
            # print(f'get_transcription_response: {json.dumps(get_transcription_response, indent=4)}')
            time.sleep(5)
        elif get_transcription_response and get_transcription_response.get("status") == "Failed":
            print(f'Transcription failed with error: {get_transcription_response}')
            completed_flag = True    


end_time = time.time()

# Calculate time taken in seconds  
time_taken = end_time - start_time  
print(f"Time taken: {time_taken:.2f} seconds") 