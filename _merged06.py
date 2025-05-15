import subprocess
import json
from datetime import datetime
import os
from pyannote.audio import Pipeline
from collections import defaultdict
import argparse

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="Process a YouTube video: download audio, transcribe, and save as JSON and segmented .txt with natural language metadata.")
parser.add_argument("video_url", help="The URL of the YouTube video to process.")
args = parser.parse_args()

# Use the provided video URL
url = args.video_url

# Print a message to indicate which video is being processed
print(f"Starting processing for video: {url}")

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

# Step 6: Remove unnecessary fields from each segment
for segment in whisper_data['segments']:
    segment.pop('temperature', None)
    segment.pop('seek', None)
    segment.pop('tokens', None)

# Step 7: Assign speakers to each transcription segment
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
        return "Charles" if assigned_speaker == primary_speaker else assigned_speaker
    return "Unknown"

# Add speaker labels to each segment
for segment in whisper_data['segments']:
    speaker = assign_speaker(segment['start'], segment['end'], diarization_turns)
    segment['speaker'] = speaker

# Step 8: Add metadata to the JSON
whisper_data['metadata'] = metadata

# Step 9: Reorder the keys to have 'language' and 'metadata' at the top
final_data = {
    "language": whisper_data["language"],
    "metadata": whisper_data["metadata"],
    "text": whisper_data["text"],
    "segments": whisper_data["segments"]
}

# Step 10: Save the updated JSON
with open(whisper_output, 'w') as f:
    json.dump(final_data, f, indent=4)
print(f"Updated JSON with transcription, speakers, and metadata saved: {whisper_output}")

# Step 11: Generate segmented .txt file with natural language metadata
txt_output = f"{video_id}.txt"
try:
    # Build metadata lines as natural language sentences
    metadata_lines = [
        f"The language spoken in this video is {whisper_data['language']}.",
        f"The video platform where this video was sourced is {metadata['url'].split('/')[2].split('?')[0]}.",
        f"The channel name from which this video was sourced is {metadata['channelName']}.",
        f"The title of the video is {metadata['videoTitle']}.",
        f"The URL where this video can be viewed is {metadata['url']}.",
        f"The video was posted on {metadata['videoPostDate']}."
    ]

    # Build segments with rounded timestamps
    segments_lines = []
    for segment in whisper_data['segments']:
        start = round(segment['start'], 2)
        end = round(segment['end'], 2)
        text = segment['text'].strip()
        speaker = segment['speaker']
        segment_line = f"[{start} > {end}] ({speaker}) {text}"
        segments_lines.append(segment_line)

    # Combine metadata and segments
    txt_content = metadata_lines + segments_lines

    # Write to .txt file
    with open(txt_output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_content))
    print(f"Segmented .txt file saved: {txt_output}")
except Exception as e:
    print(f"Error generating .txt file: {e}")