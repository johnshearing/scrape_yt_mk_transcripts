# Run this script with the following command:
# python3 generate_metadata_json.py <video_id>.json

# This script relies on the file <video_id>.json which must be created by _merge??.py.
# <video_id>.json is an argument for the name of the input file.
# Use the actual name of the file which was created by _merge??.py.

# Sometimes I need to tweek the output of <video_id>_metadata.json after _merge??.py has been run.
# I could modify the dictionary (custom_kg) in _merge??.py and run it again, but the run time would just as long as the first time it was run.
# This by tweeking the dictionary (custom_kg) in this script we greatly reduce the time required to get the same result.



import json
import argparse
import os

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="Generate metadata JSON from an existing video transcript JSON.")
parser.add_argument("json_file", help="Path to the video transcript JSON file (e.g., <video_id>.json).")
args = parser.parse_args()

# Get the input JSON file
json_file = args.json_file
video_id = os.path.splitext(os.path.basename(json_file))[0]  # Extract video_id from filename

# Step 1: Load the transcript JSON
try:
    with open(json_file, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    print(f"Loaded transcript JSON: {json_file}")
except FileNotFoundError:
    print(f"Error: {json_file} not found.")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: Failed to decode JSON from {json_file}.")
    exit(1)

# Step 2: Extract metadata and language
try:
    metadata = transcript_data['metadata']
    language = transcript_data['language']
except KeyError as e:
    print(f"Error: Missing key {e} in {json_file}. Ensure it contains 'metadata' and 'language'.")
    exit(1)

# Step 3: Generate metadata .json file in custom KG format
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
        "VIDEO_LANGUAGE": language
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
                "description": "The metadata-global-hub joins all metadata-hub entities via edge relationships. metadata-global-hub can be referenced to list all metadata-hubs",
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "entity_name": f"{video_id}_metadata.json",
                "entity_type": "metadata-hub",
                "description": f"{video_id}_metadata.json is a meta-data-hub. All metadata for the source document {video_id}.txt can be located by referencing {video_id}_metadata.json",
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
                "tgt_id": f"{video_id}_metadata.json",
                "description": f"{video_id}_metadata.json is an element of the set metadata-global-hub",
                "keywords": "element of metadata-global-hub",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": "source-document-global-hub",
                "tgt_id": f"{video_id}.txt",
                "description": f"{video_id}.txt is an element of the set source-document-global-hub",
                "keywords": "element of source-document-global-hub",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": f"{video_id}.txt",
                "description": f"{video_id}_metadata.json is the metadata hub for the source document {video_id}.txt",
                "keywords": f"metadata for {video_id}.txt",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": metadata_values['VIDEO_URL'],
                "description": f"{video_id}_metadata.json is the metadata hub for the URL {metadata_values['VIDEO_URL']}",
                "keywords": f"URL {video_id}_metadata.json",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": metadata_values['VIDEO_PLATFORM'],
                "description": f"{video_id}_metadata.json is the metadata hub for the video platform {metadata_values['VIDEO_PLATFORM']}",
                "keywords": f"video platform {video_id}_metadata.json",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": metadata_values['VIDEO_CHANNEL'],
                "description": f"{video_id}_metadata.json is the metadata hub for the video channel {metadata_values['VIDEO_CHANNEL']}",
                "keywords": f"video channel {video_id}_metadata.json",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": metadata_values['VIDEO_TITLE'],
                "description": f"{video_id}_metadata.json is the metadata hub for the video titled {metadata_values['VIDEO_TITLE']}",
                "keywords": f"video title {video_id}_metadata.json",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": metadata_values['VIDEO_POST_DATETIME'],
                "description": f"{video_id}_metadata.json is the metadata hub for the video posting time and date of {metadata_values['VIDEO_POST_DATETIME']}",
                "keywords": f"posting date time {video_id}_metadata.json",
                "weight": 7.0,
                "source_id": f"{video_id}_metadata.json"
            },
            {
                "src_id": f"{video_id}_metadata.json",
                "tgt_id": metadata_values['VIDEO_LANGUAGE'],
                "description": f"{video_id}_metadata.json is the metadata hub for {metadata_values['VIDEO_LANGUAGE']}, the spoken language in the video",
                "keywords": f"{metadata_values['VIDEO_LANGUAGE']} spoken language {video_id}_metadata.json",
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