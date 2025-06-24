import os  
import base64  
from io import BytesIO  
from pydub import AudioSegment
from mutagen.mp3 import MP3  

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas  

from datetime import datetime, timedelta, timezone
import requests  

def split_audio(file_path, chunk_length=30):  
    """  
    Splits an audio file into smaller chunks of specified length.  
    :param file_path: Path to the input audio file (MP3 or WAV).  
    :param chunk_length: Length of each chunk in seconds (default is 30 seconds).  
    :return: List of AudioSegment objects representing the chunks.  
    """  
    print('Current working directory:', os.getcwd())  
      
    # Load the audio file  
    audio = AudioSegment.from_file(file_path)
    print(f'len(audio): {len(audio)}')  # Length of the audio in milliseconds

    # bitrate = f"{audio.frame_rate // 1000}k"  # Approximate bit rate (in kbps)  
    # sample_rate = audio.frame_rate            # Sample rate (in Hz)
    # channels = audio.channels                 # Number of channels (e.g., mono or stereo)
    # print(f'*bitrate: {bitrate}, *sample_rate: {sample_rate}, *channels: {channels}')

    # audio = MP3(file_path)  
    # print("Bitrate mutagen:", audio.info.bitrate)  
    # print("Sample Rate mutagen:", audio.info.sample_rate)  
    # print("Channels mutagen:", audio.info.channels)  
      
    # Calculate chunk length in milliseconds  
    chunk_length_ms = chunk_length * 1000     
      
    # Split the audio into chunks  
    chunks = []  
    if len(audio) <= chunk_length_ms:
        chunks.append(audio)  # If audio is shorter than chunk length, return it as a single chunk
    else:
        for i in range(0, len(audio), chunk_length_ms):  
            chunk = audio[i:i + chunk_length_ms]  
            bitrate = f"{chunk.frame_rate // 1000}k"  # Approximate bit rate (in kbps)  
            sample_rate = chunk.frame_rate            # Sample rate (in Hz)  
            
            if i == 0:
                print(f'**bitrate: {bitrate}, **sample_rate: {sample_rate}, **channels: {chunk.channels}')

            chunks.append(chunk)  
    
    # print(f'Number of audio chunks: {len(chunks)}')
    return chunks  
  
def export_chunk_to_base64(chunk, file_format="mp3", temp_file_path=None):  
    """  
    Exports an audio chunk to Base64 format.  
    :param chunk: AudioSegment object representing the chunk.  
    :param file_format: Format to export the chunk (default is "mp3").  
    :param temp_file_path: Path to save the temporary file (optional). 
    :return: Base64-encoded string of the chunk.  
    """  

    if temp_file_path:  
        
        # Extract properties from the chunk  
        bitrate = f"{chunk.frame_rate // 1000}k"  # Approximate bit rate (in kbps)  
        sample_rate = chunk.frame_rate            # Sample rate (in Hz)  
        channels = chunk.channels                 # Number of channels (e.g., mono or stereo) 
        print(f"Bitrate: {bitrate}, Sample Rate: {sample_rate}, Channels: {channels}")
  
        # Export the chunk with extracted properties  
        chunk.export(  
            temp_file_path,  
            format=file_format,  
            bitrate=bitrate,  
            parameters=["-ar", str(sample_rate), "-ac", str(channels)]  
        )  
    
    # Save the chunk to a BytesIO object  
    chunk_buffer = BytesIO()  
    chunk.export(chunk_buffer, format=file_format)  # Export the chunk  
      
    # Get the binary data  
    chunk_data = chunk_buffer.getvalue()  
    # print(f"Chunk size (bytes): {len(chunk_data)}")  
      
    # Encode the chunk data to Base64  
    chunk_base64 = base64.b64encode(chunk_data).decode('utf-8')  
    # print(f"Base64 string length: {len(chunk_base64)}")  
      
    return chunk_base64  

# List Base Models request to get available base models for all locales
def get_speech_to_text_models(api_url, api_version, subscription_key):  
    """  
    Fetches speech-to-text models from the specified API endpoint.  
  
    Args:  
        api_url (str): The base URL of the API (e.g., "https://eastus.api.cognitive.microsoft.com").  
        api_version (str): The API version (e.g., "2024-11-15").  
        subscription_key (str): Azure AI Foundry resource key / Azure Speech resource subscription key.  
  
    Returns:  
        dict: The JSON response from the API if successful.  
        None: If the request fails.  
    """  
    # Construct the full URL  
    # Ref: https://learn.microsoft.com/en-us/rest/api/speechtotext/models/list-base-models?view=rest-speechtotext-v3.2&tabs=HTTP
    # url = f"{api_url}/speechtotext/models/base?api-version={api_version}"  
    # url = f"{api_url}/speechtotext/v3.2/models/base?api-version={api_version}"
    # url = f"{api_url}/speechtotext/v3.2-preview.2/models/base?api-version={api_version}&filter=displayName eq '20240228 Whisper Large V2'"  # Filter on displayName
    # url = f"{api_url}/speechtotext/v3.2/models/base?api-version={api_version}&filter=displayName eq '20240228 Whisper Large V2'"  # Filter on displayName
    url = f"{api_url}/speechtotext/v3.2/models/base?api-version={api_version}&filter=createdDateTime gt 2024-01-01T00:00:00Z"  # Filter on createdDateTime
    print(f'Filtered URL: {url}, please modify the filter as per your requirements')
      
    # Set the headers  
    headers = {  
        "Ocp-Apim-Subscription-Key": subscription_key  
    }  
      
    try:  
        # Make the GET request  
        response = requests.get(url, headers=headers)  
          
        # Check if the request was successful  
        if response.status_code == 200:  
            return response.json()  # Return the JSON response  
        else:  
            print(f"Error: {response.status_code} - {response.text}")  
            return None  
    except requests.exceptions.RequestException as e:  
        print(f"Request failed: {e}")  
        return None  

  
def submit_transcription_request(api_url, api_version, subscription_key, content_urls, locale, transcription_display_name, model_url, word_level_timestamps_enabled=True, is_whisper=False):  
    """  
    Submits a transcription request to the Azure Speech-to-Text API.  
  
    Args:  
        api_url (str): The base URL of the API (e.g. "https://eastus.api.cognitive.microsoft.com").  
        api_version (str): The API version (e.g. "2024-11-15").  
        subscription_key (str): Azure AI Foundry resource key / Azure Speech resource subscription key.  
        content_urls (list): List of URLs pointing to audio files to be transcribed.  
        locale (str): Locale of the audio files (e.g. "en-US").  
        display_name (str): A name for the transcription job.  
        model_url (str): URL of the specific speech-to-text model to use.  (e.g. "https://eastus.api.cognitive.microsoft.com/speechtotext/models/base/69adf293-9664-4040-932b-02ed16332e00?api-version=2024-11-15")
        word_level_timestamps_enabled (bool): Whether to enable word-level timestamps in the transcription.  
  
    Returns:  
        dict: The JSON response from the API if successful.  
        None: If the request fails.  
    """  
    # Construct the full URL for the transcription submission endpoint  
    # url = f"{api_url}/speechtotext/transcriptions:submit?api-version={api_version}"
    url = f"{api_url}/speechtotext/v3.2/transcriptions"
    print(f'Transcription submission URL: {url}')
  
    # Prepare the request payload  
    payload = {  
        "contentUrls": content_urls,  
        "locale": locale,  
        "displayName": transcription_display_name,  
        "model": {  
            "self": model_url  
        },  
        "properties": {  
            "ProfanityFilterMode": "None",  # Options: "Masked", "Removed", "None"
            "diarizationEnabled": True,  # Enable speaker diarization
            "diarization": {
                "speakers": {
                    "minCount": 1,
                    "maxCount": 5
                },            
            },            
            # "wordLevelTimestampsEnabled": word_level_timestamps_enabled, # Setting this in if condition below
            "timeToLiveHours": 48 # The shortest supported duration is 6 hours, the longest supported duration is 31 days. The recommended value is 48 hours (two days) when data is consumed directly.
        }  
    } 

    # Word level timestamp property name depends on the model type
    if is_whisper:
        payload["properties"]["displayFormWordLevelTimestampsEnabled"] = word_level_timestamps_enabled
    else:
        payload["properties"]["wordLevelTimestampsEnabled"] = word_level_timestamps_enabled
  
    # Set the headers  
    headers = {  
        "Ocp-Apim-Subscription-Key": subscription_key,  
        "Content-Type": "application/json"  
    }  
  
    try:  
        # Make the POST request  
        response = requests.post(url, headers=headers, json=payload)  
  
        # Check if the request was successful  
        if response.status_code == 201:  
            return response.json()  # Return the JSON response  
        else:  
            print(f"Error: {response.status_code} - {response.text}")  
            return None  
    except requests.exceptions.RequestException as e:  
        print(f"Request failed: {e}")  
        return None
    
# Get submitted transcription identified by given ID
def get_transcription(api_url, api_version, submission_id, subscription_key):  
    """  
    Submits a transcription request to the Azure Speech-to-Text API.  
  
    Args:  
        api_url (str): The base URL of the API (e.g. "https://eastus.api.cognitive.microsoft.com").  
        api_version (str): The API version (e.g. "2024-11-15").  
        subscription_key (str): Azure AI Foundry resource key / Azure Speech resource subscription key.          
  
    Returns:  
        dict: The JSON response from the API if successful.  
        None: If the request fails.  
    """  
    # Construct the full URL for the transcription submission endpoint  
    # url = f"{api_url}/speechtotext/transcriptions/{submission_id}?api-version={api_version}"
    url = f"{api_url}/speechtotext/v3.2/transcriptions/{submission_id}"
    print(f'Transcription get URL: {url}') 
   
  
    # Set the headers  
    headers = {  
        "Ocp-Apim-Subscription-Key": subscription_key,  
        "Content-Type": "application/json"  
    }  
  
    try:  
        # Make the GET request  
        response = requests.get(url, headers=headers)  
  
        # Check if the request was successful  
        if response.status_code == 200:
            return response.json()  # Return the JSON response  
        else:  
            print(f"Error: {response.status_code} - {response.text}")  
            return None  
    except requests.exceptions.RequestException as e:  
        print(f"Request failed: {e}")  
        return None

# Get transcription files
def get_transcription_files(api_url, api_version, submission_id, subscription_key):  
    """  
    Submits a transcription request to the Azure Speech-to-Text API.  
  
    Args:  
        api_url (str): The base URL of the API (e.g. "https://eastus.api.cognitive.microsoft.com").  
        api_version (str): The API version (e.g. "2024-11-15").  
        submission_id (str): The ID of the transcription submission.        
        subscription_key (str): Azure AI Foundry resource key / Azure Speech resource subscription key.          
  
    Returns:  
        dict: The JSON response from the API if successful.  
        None: If the request fails.  
    """  
    # Construct the full URL for the transcription submission endpoint  
    # url = f"{api_url}/speechtotext/transcriptions/{submission_id}/files?api-version={api_version}"
    url = f"{api_url}/speechtotext/v3.2/transcriptions/{submission_id}/files"
    print(f'Transcription get files URL: {url}') 
   
  
    # Set the headers  
    headers = {  
        "Ocp-Apim-Subscription-Key": subscription_key,  
        "Content-Type": "application/json"  
    }  
  
    try:  
        # Make the GET request  
        response = requests.get(url, headers=headers)  
  
        # Check if the request was successful  
        if response.status_code == 200:
            return response.json()  # Return the JSON response  
        else:  
            print(f"Error: {response.status_code} - {response.text}")  
            return None  
    except requests.exceptions.RequestException as e:  
        print(f"Request failed: {e}")  
        return None 

# To download the transcription file from the content URL SAS URI
def download_file_from_web(url, save_path):  
    try:  
        response = requests.get(url, stream=True)  
        response.raise_for_status()  # Raise an error for bad status codes  
        with open(save_path, 'wb') as file:  
            for chunk in response.iter_content(chunk_size=8192):  
                file.write(chunk)  
        print(f"File downloaded successfully: {save_path}")  
    except requests.exceptions.RequestException as e:  
        print(f"Error downloading file: {e}")     

# Azure storage
def get_blob_service_client(storage_account_sas_url):
    # Create a BlobServiceClient object
    blob_service_client_sas = BlobServiceClient(account_url=storage_account_sas_url)

    return blob_service_client_sas

# Azure storage
def upload_binary_data_to_azure_storage(blob_service_client, storage_container, storage_path, storage_file_name, binary_data):
    blob_client = blob_service_client.get_blob_client(container=storage_container, blob=storage_path+'/'+storage_file_name)

    # Upload the blob data - default blob type is BlockBlob
    blob_client.upload_blob(binary_data, blob_type="BlockBlob", overwrite=True)
 
# Generate a SAS URI for a file in Azure Storage.  
# Returns SAS URI for the specified blob.  
def generate_sas_uri(storage_account_name, storage_account_key, container_name, storage_path, storage_file_name, expiry_minutes=1):  

    # Construct the full blob name (path + filename)  
    blob_name_with_path = f"{storage_path}/{storage_file_name}"  
  
    # Define the expiry time for the SAS token using timezone-aware datetime  
    expiry_time = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)  
  
    # Generate the SAS token  
    sas_token = generate_blob_sas(  
        account_name=storage_account_name,  
        account_key=storage_account_key,  
        container_name=container_name,  
        blob_name=blob_name_with_path,  
        permission=BlobSasPermissions(read=True),  # Grant read permissions  
        expiry=expiry_time  
    )  
  
    # Construct the SAS URI  
    sas_uri = f"https://{storage_account_name}.blob.core.windows.net/{container_name}/{blob_name_with_path}?{sas_token}"  
  
    return sas_uri  