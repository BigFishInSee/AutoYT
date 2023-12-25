import os
import sys
import subprocess
from pytube import YouTube
from pytube.exceptions import RegexMatchError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

FFMPEG_PATH = ''#path to ffmpeg.exe here

def download_video_clip(video_url, start_timestamp, end_timestamp, output_folder, mode):
    global video_stream 

    def resize_video(input_path, output_path):
    # Resize video to 1:2 aspect ratio
        subprocess.run([FFMPEG_PATH, '-i', input_path, '-vf', 'scale=iw:2*ih', output_path], capture_output=True)
    # Convert to seconds
    def timestamp_to_seconds(timestamp):
        timestamp_parts = timestamp.split(':')
        if len(timestamp_parts) == 3:
            hours, minutes, seconds = map(int, timestamp_parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(timestamp_parts) == 2:
            minutes, seconds = map(int, timestamp_parts)
            return minutes * 60 + seconds
        else:
            raise ValueError("Invalid timestamp format")    
    if mode.upper() == "DOWNLOAD":
        try:
            # Create output folder if not exist
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            # Get video
            try:
                yt = YouTube(video_url)
            except RegexMatchError:
                print("Invalid YouTube URL")
                return      

            start_seconds = timestamp_to_seconds(start_timestamp)
            end_seconds = timestamp_to_seconds(end_timestamp)

            # Download clip
            video_stream = yt.streams.filter(file_extension='mp4').first()
            video_stream.download(output_folder, filename='clip_temp.mp4')

            # Trim 
            output_file = os.path.join(output_folder, 'clip.mp4')
            subprocess.run([FFMPEG_PATH, '-ss', str(start_seconds), '-i', os.path.join(output_folder, 'clip_temp.mp4'), '-to', str(end_seconds), '-c', 'copy', output_file])

            # Remove temp file
            os.remove(os.path.join(output_folder, 'clip_temp.mp4'))

            print(f"Video clip saved to {output_file}")

        except Exception as e:
            print(f"Error: {e}")
    
    if mode.upper() == "UPLOAD":

        input_video_path = os.path.join(output_folder, 'clip.mp4')
        output_resized_path = os.path.join(output_folder, 'resized_clip.mp4')
        resize_video(input_video_path, output_resized_path)

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        CLIENT_SECRETS_FILE = ''#Client_secret,json here

        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)

        # Create a YouTube API service
        youtube = build("youtube", "v3", credentials=credentials)

        duration_seconds = timestamp_to_seconds(end_timestamp) - timestamp_to_seconds(start_timestamp)
        # Video metadata for YouTube short
        request_body = {
            "snippet": {
                "title": "test",
                "description": "test",
                "tags": ["tag1", "tag2"],
                "categoryId": "15",  # Choose the appropriate category ID for your video
                "channelId": "",  # Your channel ID
                "position": {"type": "position", "value": "end", "cornerPosition": "topRight"},
            },
            "status": {
                "privacyStatus": "",  # Set privacy status: private, public, or unlisted
            },
            "contentDetails": {
                "durationMs": str(duration_seconds),  
                "isShort": True,
            },
        }


        # Video file path
        video_file_path = output_resized_path

        # Upload video
        media_file_upload = MediaFileUpload(video_file_path, chunksize=-1, resumable=True)
        videos_insert_response = (
            youtube.videos()
            .insert(
                part="snippet,status,contentDetails",
                body=request_body,
                media_body=media_file_upload,
            )
            .execute()
        )

        # Get the uploaded video URL
        uploaded_video_url = f"https://www.youtube.com/watch?v={videos_insert_response['id']}"

        print(f"Video uploaded successfully. View it here: {uploaded_video_url}")

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python autovid.py <YouTube Video URL> <Start Timestamp (HH:MM:SS or MM:SS)> <End Timestamp (HH:MM:SS or MM:SS)> <Output Folder> <mode(upload/download)> OR JUST UPLOAD MANUALLY")
    else:
        video_url = sys.argv[1]
        start_timestamp = sys.argv[2]
        end_timestamp = sys.argv[3]
        output_folder = sys.argv[4]
        mode = sys.argv[5]
        download_video_clip(video_url, start_timestamp, end_timestamp, output_folder, mode)

