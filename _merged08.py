import subprocess
import json
from datetime import datetime
import os
from pyannote.audio import Pipeline
from collections import defaultdict
import argparse

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="Process a video: download audio, transcribe, and save as JSON, segmented .txt, and metadata JSON.")
parser.add_argument("video_url", help="The URL of the video to process.")
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
# Use the first name or channel name as the speaker label
primary_speaker_name = metadata['channelName'].split()[0]  # e.g., "Max" from "Max Gulhane MD"
print(f"Primary speaker identified: {primary_speaker} (labeled as {primary_speaker_name})")

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
        return primary_speaker_name if assigned_speaker == primary_speaker else assigned_speaker
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

# Step 10: Save the updated JSON transcript
with open(whisper_output, 'w') as f:
    json.dump(final_data, f, indent=4)
print(f"Updated JSON transcript saved: {whisper_output}")

# Step 11: Generate segmented .txt file for transcript segments
txt_output = f"{video_id}.txt"
try:
    # Build segments with rounded timestamps
    segments_lines = []
    for segment in whisper_data['segments']:
        start = round(segment['start'], 2)
        end = round(segment['end'], 2)
        text = segment['text'].strip()
        speaker = segment['speaker']
        segment_line = f"[{start} > {end}] ({speaker}) {text}"
        segments_lines.append(segment_line)

    # Write to .txt file
    with open(txt_output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(segments_lines))
    print(f"Segmented .txt file saved: {txt_output}")
except Exception as e:
    print(f"Error generating .txt file: {e}")

# Step 12: Generate metadata .json file in custom KG format
metadata_json_output = f"{video_id}_metadata.json"
try:
    # Extract platform from URL
    platform = metadata['url'].split('/')[2].split('?')[0]
    # Prepare metadata values
    metadata_values = {
        "VIDEO_URL": metadata['url'],
        "VIDEO_PLATFORM": platform,
        "VIDEO_CHANNEL": metadata['channelName'],
        "VIDEO_TITLE": metadata['videoTitle'],
        "VIDEO_POST_DATETIME": metadata['videoPostDate'],
        "VIDEO_LANGUAGE": whisper_data['language']
    }
    # Construct custom KG JSON
    custom_kg = {
        "chunks": [
            {
                "content": (
                    f"The video URL is {metadata_values['VIDEO_URL']}\n"
                    f"The video platform is {metadata_values['VIDEO_PLATFORM']}\n"
                    f"The video channel is {metadata_values['VIDEO_CHANNEL']}\n"
                    f"The video title is {metadata_values['VIDEO_TITLE']}\n"
                    f"The video was posted on {metadata_values['VIDEO_POST_DATETIME']}\n"
                    f"The video language is {metadata_values['VIDEO_LANGUAGE']}"
                ),
                "source_id": f"{video_id}_metadata.json"
            }
        ],
        "entities": [
            {
                "entity_name": "source-document-global-hub",
                "entity_type": "source-document-global-hub",
                "description": "The source-document-global-hub joins all source documents via edge relationships. source-document-global-hub can be referenced to list all source documents",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": "metadata-global-hub",
                "entity_type": "metadata-global-hub",
                "description": "The metadata-global-hub joins all metadata-hub entities using edge relationships. metadata-global-hub can be referenced to list all metadata-hubs",
                "source_id": f"{video_id}_metadata.json"
            },            
            {
                "entity_name": f"metadata-hub-{video_id}.txt",
                "entity_type": "metadata-hub",
                "description": f"The metadata-hub-{video_id}.txt is a meta-data-hub. All metadata for the source document {video_id}.txt can be located by referencing metadata-hub-{video_id}.txt",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": f"{video_id}.txt",
                "entity_type": "source-document",
                "description": f"{video_id}.txt is the file name of a source document used to populate this index with information. {video_id}.txt contains a video transcript",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": metadata_values['VIDEO_URL'],
                "entity_type": f"metadata-for-{video_id}.txt",
                "description": "URL for source video",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": metadata_values['VIDEO_PLATFORM'],
                "entity_type": f"metadata-for-{video_id}.txt",
                "description": "video platform which hosted the source video.",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": metadata_values['VIDEO_CHANNEL'],
                "entity_type": f"metadata-for-{video_id}.txt",
                "description": "Video channel which published the source video.",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": metadata_values['VIDEO_TITLE'],
                "entity_type": f"metadata-for-{video_id}.txt",
                "description": "Video title for source video",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": metadata_values['VIDEO_POST_DATETIME'],
                "entity_type": f"metadata-for-{video_id}.txt",
                "description": "Date source video was posted.",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": metadata_values['VIDEO_LANGUAGE'],
                "entity_type": f"metadata-for-{video_id}.txt",
                "description": "Language spoken in the source video",
                "source_id": f"{video_id}_metadata.json"
            }
        ],
        "relationships": [
            {
                "src_id": metadata_values['VIDEO_URL'],
                "tgt_id": metadata_values['VIDEO_PLATFORM'],
                "description": f"The source video found at the URL {metadata_values['VIDEO_URL']} was hosted by {metadata_values['VIDEO_PLATFORM']} platform",
                "keywords": "source video URL host platform",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_URL'],
                "tgt_id": metadata_values['VIDEO_CHANNEL'],
                "description": f"The source video found at URL {metadata_values['VIDEO_URL']} was produced by the {metadata_values['VIDEO_CHANNEL']} video channel",
                "keywords": "source video URL channel produced",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_URL'],
                "tgt_id": metadata_values['VIDEO_TITLE'],
                "description": f"The source video at URL {metadata_values['VIDEO_URL']} is titled {metadata_values['VIDEO_TITLE']}",
                "keywords": "source video URL title",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_URL'],
                "tgt_id": metadata_values['VIDEO_POST_DATETIME'],
                "description": f"The source video at URL {metadata_values['VIDEO_URL']} was posted at the date and time of {metadata_values['VIDEO_POST_DATETIME']}",
                "keywords": "source video URL posted date time",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_PLATFORM'],
                "tgt_id": metadata_values['VIDEO_CHANNEL'],
                "description": f"{metadata_values['VIDEO_PLATFORM']} was the platform hosting the {metadata_values['VIDEO_CHANNEL']} channel",
                "keywords": "platform hosting channel",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_CHANNEL'],
                "tgt_id": metadata_values['VIDEO_TITLE'],
                "description": f"The {metadata_values['VIDEO_CHANNEL']} channel produced the video titled {metadata_values['VIDEO_TITLE']}",
                "keywords": "channel content creator produced video",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_TITLE'],
                "tgt_id": metadata_values['VIDEO_POST_DATETIME'],
                "description": f"The video titled {metadata_values['VIDEO_TITLE']} was posted on {metadata_values['VIDEO_POST_DATETIME']}",
                "keywords": "titled video posted date time",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": metadata_values['VIDEO_TITLE'],
                "tgt_id": metadata_values['VIDEO_LANGUAGE'],
                "description": f"The video titled {metadata_values['VIDEO_TITLE']} was presented in the {metadata_values['VIDEO_LANGUAGE']} language",
                "keywords": "titled video spoken language",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": "metadata-global-hub",
                "tgt_id": f"metadata-hub-{video_id}.txt",                
                "description": f"The metadata-hub-{video_id}.txt belongs to the set of metadata-global-hub",
                "keywords": "element of metadata-global-hub",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": "source-document-global-hub",
                "tgt_id": f"{video_id}.txt",                
                "description": f"{video_id}.txt belongs to the set of source-document-global-hub",
                "keywords": "element of source-document-global-hub",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },            
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": f"{video_id}.txt",
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for the source document {video_id}.txt",
                "keywords": f"metadata for {video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },            
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": metadata_values['VIDEO_URL'],
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for the URL {metadata_values['VIDEO_URL']}",                
                "keywords": f"URL metadata-hub-{video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": metadata_values['VIDEO_PLATFORM'],
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for the video platform {metadata_values['VIDEO_PLATFORM']}",                
                "keywords": f"video platform metadata-hub-{video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": metadata_values['VIDEO_CHANNEL'],
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for the video channel {metadata_values['VIDEO_CHANNEL']}",                 
                "keywords": f"video channel metadata-hub-{video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": metadata_values['VIDEO_TITLE'],
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for the video titled {metadata_values['VIDEO_TITLE']}",                
                "keywords": f"video title metadata-hub-{video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": metadata_values['VIDEO_POST_DATETIME'],
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for the video posting time and date of {metadata_values['VIDEO_POST_DATETIME']}",                
                "keywords": f"posting date time metadata-hub-{video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"metadata-hub-{video_id}.txt",
                "tgt_id": metadata_values['VIDEO_LANGUAGE'],
                "description": f"metadata-hub-{video_id}.txt is the metadata hub for {metadata_values['VIDEO_LANGUAGE']}, the spoken language in the video",                 
                "keywords": f"{metadata_values['VIDEO_LANGUAGE']} spoken language metadata-hub-{video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            }
        ]
    }

    # Write to .json file
    with open(metadata_json_output, 'w', encoding='utf-8') as f:
        json.dump(custom_kg, f, indent=4)
    print(f"Metadata JSON file saved: {metadata_json_output}")
except Exception as e:
    print(f"Error generating metadata .json file: {e}")