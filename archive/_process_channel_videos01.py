#!/usr/bin/env python3

import argparse
import os
import subprocess
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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

    # Extract username from the channel URL
    try:
        username = args.channel_url.split('@')[1].split('/')[0]
    except IndexError:
        print("Error: Invalid channel URL format. Expected format: https://www.youtube.com/@username/videos")
        exit(1)

    # Build the YouTube API client
    youtube = build("youtube", "v3", developerKey=api_key)

    # Get the uploads playlist ID from the channel
    try:
        channel_response = youtube.channels().list(
            part="contentDetails",
            forUsername=username
        ).execute()
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except (HttpError, IndexError) as e:
        print(f"Error retrieving channel information: {e}")
        exit(1)

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