import subprocess
import json
from datetime import datetime
import os

# Define the YouTube video URL
url = "https://www.youtube.com/watch?v=z7kLfGkR7gk"

# Step 1: Get metadata using yt-dlp
try:
    result = subprocess.run(['yt-dlp', '--dump-json', url], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    metadata = {
        "channelName": info['uploader'],
        "videoTitle": info['title'],
        "url": info['webpage_url'],
        "videoPostDate": datetime.utcfromtimestamp(info['timestamp']).strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    print("Metadata captured:", metadata)
except subprocess.CalledProcessError as e:
    print(f"Error getting metadata: {e}")
    exit(1)

# Step 2: Download audio using yt-dlp and capture the output filename
# Use the video ID to create a unique filename
video_id = info['id']
audio_filename = f"{video_id}.wav"

try:
    subprocess.run(['yt-dlp', '-x', '--audio-format', 'wav', '--output', audio_filename, url], check=True)
    print(f"Audio downloaded successfully: {audio_filename}")
except subprocess.CalledProcessError as e:
    print(f"Error downloading audio: {e}")
    exit(1)

# Step 3: Run Whisper to transcribe the audio and output to JSON
whisper_output = f"{video_id}.json"
try:
    subprocess.run(['whisper', audio_filename, '--model', 'medium', '--output_format', 'json'], check=True)
    print(f"Transcription completed: {whisper_output}")
except subprocess.CalledProcessError as e:
    print(f"Error running Whisper: {e}")
    exit(1)

# Step 4: Append metadata to the Whisper JSON output
try:
    # Load the Whisper JSON output
    with open(whisper_output, 'r') as f:
        whisper_data = json.load(f)
    
    # Append the metadata
    whisper_data['metadata'] = metadata
    
    # Write the updated data back to the JSON file
    with open(whisper_output, 'w') as f:
        json.dump(whisper_data, f, indent=4)
    print(f"Metadata appended to {whisper_output}")
except FileNotFoundError:
    print(f"Error: {whisper_output} not found. Whisper may have failed to generate the file.")
except json.JSONDecodeError:
    print(f"Error: Failed to decode JSON from {whisper_output}.")