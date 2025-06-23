import os  
import base64  
from io import BytesIO  
from pydub import AudioSegment
from mutagen.mp3 import MP3  

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