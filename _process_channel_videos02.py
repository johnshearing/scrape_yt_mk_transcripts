#!/usr/bin/env python3

# Creates a list of all videos for a YouTube channel and passes each list item (a video) to _merged04.py for processing.

# The following is a sample run command.
# The start index should be zero or where ever you want to start in the list of videos.
# python3 _process_channel_videos02.py "https://www.youtube.com/@abrahamhickstips/videos" --start-index 0

import argparse
import os
import subprocess
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def get_uploads_playlist_id(youtube, handle):
    """
    Retrieve the uploads playlist ID for a YouTube channel using its handle.
    
    Args:
        youtube: The YouTube API client instance.
        handle: The channel handle (e.g., "abrahamhickstips" from "@abrahamhickstips").
    
    Returns:
        str: The uploads playlist ID.
    """
    try:
        # Step 1: Search for the channel using the handle
        search_response = youtube.search().list(
            part="snippet",
            type="channel",
            q="@" + handle  # Prepend "@" to match the handle format
        ).execute()
        
        # Check if any channels were found
        if not search_response.get("items", []):
            print(f"No channel found for handle: @{handle}")
            exit(1)
        
        # Extract the channel ID from the first result
        channel_id = search_response["items"][0]["snippet"]["channelId"]
        print(f"Found channel ID: {channel_id} for handle: @{handle}")
        
        # Step 2: Get channel details using the channel ID
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        # Check if the channel has an uploads playlist
        if "relatedPlaylists" not in channel_response["items"][0]["contentDetails"] or "uploads" not in channel_response["items"][0]["contentDetails"]["relatedPlaylists"]:
            print("Channel does not have an uploads playlist.")
            exit(1)
        
        # Extract the uploads playlist ID
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        print(f"Uploads playlist ID: {uploads_playlist_id}")
        return uploads_playlist_id
    except HttpError as e:
        print(f"Error retrieving channel information: {e}")
        exit(1)
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response: {e}")
        exit(1)

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Process all videos from a YouTube channel's videos page.")
    parser.add_argument("channel_url", help="The URL of the channel's videos page, e.g., https://www.youtube.com/@abrahamhickstips/videos")
    parser.add_argument("--start-index", type=int, default=0, help="The 0-based index to start processing from.")
    parser.add_argument("--api-key", help="Your YouTube Data API key. Alternatively, set the YOUTUBE_API_KEY environment variable.")
    args = parser.parse_args()

    # Validate start_index
    if args.start_index < 0:
        print("Error: start_index must be greater than or equal to 0.")
        exit(1)

    # Get the API key from argument or environment variable
    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("Error: YouTube API key is required. Provide it via --api-key or set YOUTUBE_API_KEY environment variable.")
        exit(1)

    # Extract handle from the channel URL
    try:
        handle = args.channel_url.split('@')[1].split('/')[0]
    except IndexError:
        print("Error: Invalid channel URL format. Expected format: https://www.youtube.com/@handle/videos")
        exit(1)

    # Build the YouTube API client
    youtube = build("youtube", "v3", developerKey=api_key)

    # Get the uploads playlist ID using the handle
    uploads_playlist_id = get_uploads_playlist_id(youtube, handle)

    # Retrieve all video IDs from the uploads playlist
    video_ids = []
    next_page_token = None
    while True:
        try:
            playlistitems_response = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            for item in playlistitems_response["items"]:
                video_ids.append(item["snippet"]["resourceId"]["videoId"])
            next_page_token = playlistitems_response.get("nextPageToken")
            if not next_page_token:
                break
        except HttpError as e:
            print(f"Error retrieving playlist items: {e}")
            exit(1)

    # Construct video URLs
    video_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]

    # Check if start_index is valid
    if args.start_index >= len(video_urls):
        print(f"Start index {args.start_index} is greater than or equal to the number of videos ({len(video_urls)}). Nothing to process.")
        exit(0)

    # Process each video starting from the specified index
    for i, video_url in enumerate(video_urls[args.start_index:], start=args.start_index):
        print(f"Processing video {i+1}/{len(video_urls)}: {video_url}")
        try:
            subprocess.run(["python3", "_merged04.py", video_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error processing video {video_url}: {e}")
            continue

if __name__ == "__main__":
    main()