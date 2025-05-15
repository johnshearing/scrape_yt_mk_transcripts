import subprocess
import json
from datetime import datetime

# Define the YouTube video URL
url = "https://www.youtube.com/watch?v=z7kLfGkR7gk"

# Step 1: Get metadata
result = subprocess.run(['yt-dlp', '--dump-json', url], capture_output=True, text=True)
info = json.loads(result.stdout)
metadata = {
    "channelName": info['uploader'],
    "videoTitle": info['title'],
    "url": info['webpage_url'],
    "videoPostDate": datetime.utcfromtimestamp(info['timestamp']).strftime('%Y-%m-%dT%H:%M:%SZ')
}
print("Metadata:", metadata)

# Step 2: Download audio
subprocess.run(['yt-dlp', '-x', '--audio-format', 'wav', url])
print("Audio downloaded successfully.")