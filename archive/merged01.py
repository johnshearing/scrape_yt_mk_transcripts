import subprocess
import json
from datetime import datetime
import os
from pyannote.audio import Pipeline
from collections import defaultdict

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

# Step 2: Download audio using yt-dlp
video_id = info['id']
audio_filename = f"{video_id}.wav"
try:
    subprocess.run(['yt-dlp', '-x', '--audio-format', 'wav', '--output', audio_filename, url], check=True)
    print(f"Audio downloaded successfully: {audio_filename}")
except subprocess.CalledProcessError as e:
    print(f"Error downloading audio: {e}")
    exit(1)

# Step 3: Run Whisper to transcribe the audio
whisper_output = f"{video_id}.json"
try:
    subprocess.run(['whisper', audio_filename, '--model', 'medium', '--output_format', 'json'], check=True)
    print(f"Transcription completed: {whisper_output}")
except subprocess.CalledProcessError as e:
    print(f"Error running Whisper: {e}")
    exit(1)

# Step 4: Perform diarization using pyannote
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization",
    use_auth_token=os.environ["HuggingFace_API_KEY"]
)
diarization = pipeline(audio_filename)

# Calculate total speaking time for each speaker
speaker_times = defaultdict(float)
for turn, _, speaker in diarization.itertracks(yield_label=True):
    duration = turn.end - turn.start
    speaker_times[speaker] += duration

# Identify the primary speaker
primary_speaker = max(speaker_times, key=speaker_times.get)
print(f"Primary speaker identified: {primary_speaker}")

# Step 5: Load the Whisper JSON output
try:
    with open(whisper_output, 'r') as f:
        whisper_data = json.load(f)
except FileNotFoundError:
    print(f"Error: {whisper_output} not found.")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: Failed to decode JSON from {whisper_output}.")
    exit(1)

# Step 6: Assign speakers to each transcription segment
diarization_turns = list(diarization.itertracks(yield_label=True))

def assign_speaker(segment_start, segment_end, turns):
    """Assign a speaker to a segment based on maximum overlap with diarization turns."""
    overlap_durations = defaultdict(float)
    for turn, _, speaker in turns:
        turn_start = turn.start
        turn_end = turn.end
        overlap_start = max(segment_start, turn_start)
        overlap_end = min(segment_end, turn_end)
        if overlap_start < overlap_end:
            overlap_duration = overlap_end - overlap_start
            overlap_durations[speaker] += overlap_duration
    if overlap_durations:
        assigned_speaker = max(overlap_durations, key=overlap_durations.get)
        return "Hicks" if assigned_speaker == primary_speaker else assigned_speaker
    return "Unknown"

# Add speaker labels to each segment
for segment in whisper_data['segments']:
    speaker = assign_speaker(segment['start'], segment['end'], diarization_turns)
    segment['speaker'] = speaker

# Step 7: Add metadata to the JSON
whisper_data['metadata'] = metadata

# Step 8: Save the updated JSON
with open(whisper_output, 'w') as f:
    json.dump(whisper_data, f, indent=4)
print(f"Updated JSON with transcription, speakers, and metadata saved: {whisper_output}")