import json
##from tkinter import *
import re
import tkinter as tk
import requests
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
import http.server
import socketserver
import threading
import os
import sys

# Determine the script's directory - handle different execution contexts
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
except (NameError, AttributeError):
    # Fallback if __file__ is not available (e.g., some IDEs)
    script_dir = os.getcwd()

src_path = os.path.join(script_dir, "src")
sys.path.insert(0, src_path)
print(f"DEBUG: Adding to path: {src_path}")
print(f"DEBUG: Path exists: {os.path.exists(src_path)}")

try:
    from checkStreamOverlap import filter_videos_with_markers, process_streams, query_videos_by_date_from_json
    from ffmpegFunctions import add_video_filenames_and_durations, append_video_file_to_markers_in_game_folders, collect_and_write_markers_per_game, create_game_marker_files_for_editing, download_video_by_id_from_twitch, get_video_durations, merge_game_marker_json_files, save_durations_to_json, write_individual_marker_files,download_video_by_id_from_twitch_basic,write_video_id_to_file
    from getVideoInfo import get_game_title
    from jsonFunctions import append_video_name_to_video_file, get_app_params, get_video_params, write_or_append_video_info , check_video_in_json  , add_markers_to_video_data , getClipsToCutFromTreeview
except ImportError as e:
    print(f"ERROR importing modules: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to close...")
    sys.exit(1)

import vlc  # Make sure you have python-vlc installed
from tkinter import filedialog, Listbox ,  ttk , messagebox

# Load parameters
datos = get_app_params(script_dir,"programa.json")

CLIENT_ID = datos["client_id"]
CLIENT_SECRET = datos["client_secret"]
REDIRECT_URI = datos["redirect_uri"]

access_token = None
refresh_token = None

# Global variable to store the authorization code
authorization_code = None
 
video_file_name = "video_info.json"
output_file_name = 'video_markers.json'  # The output file
target_date = "2025-01-26"
edit_video_data_file = "video_edit_data.json"
video_durations_file = "video_durations.json"
videos_folder_name = os.path.join(script_dir, "_stream_files")  # Replace with the correct folder path

print("videos folder path " , videos_folder_name)


def get_authorization_url():
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'user:read:email channel:manage:broadcast user:read:subscriptions channel:read:subscriptions channel_subscriptions',
        'state': 'random_string_for_security',
    }
    return f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"

class AuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global authorization_code
        query = parse_qs(urlparse(self.path).query)
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        if 'code' in query:
            authorization_code = query['code'][0]
            self.wfile.write(b"Authorization successful! You can now close this window.")
            status_label.config(text="Authorization successful! Fetching access token...", fg="green")
            threading.Thread(target=get_access_token, daemon=True).start()
        else:
            self.wfile.write(b"Error: No code received.")
            status_label.config(text="Authorization failed!", fg="red")
        self.server.server_close()




def get_access_token():
    global access_token, refresh_token
    if not authorization_code:
        status_label.config(text="No authorization code received!", fg="red")
        return

    token_url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': authorization_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
    }

    response = requests.post(token_url, data=params)
    response_data = response.json()
    
    if response.status_code == 200:
        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')
        status_label.config(text="Access token received! Running main process...", fg="green")
        threading.Thread(target=run_main, daemon=True).start()
    else:
        status_label.config(text="Failed to get access token!", fg="red")


def get_stream_markers(access_token, video_id, user_id, limit=5):
    url = f"https://api.twitch.tv/helix/streams/markers"

    params = {
        'video_id': video_id,  # Specify the video ID
        'first': limit,        # Limit the number of markers returned
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,  # Replace with your actual Client-ID
    }

    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        markers_data = response.json()

        # Print the full response to debug
        # print("Full markers response:", markers_data)

        markers = markers_data.get('data', [])
        if markers:
            print(f"Found {len(markers)} markers for video ID {video_id}:")
            for marker in markers:
                # Extract marker details
                marker_id = marker.get('id', 'N/A')
                created_at = marker.get('created_at', 'N/A')
                description = marker.get('description', 'N/A')
                #print(f"Marker ID: {marker_id}, Created at: {created_at}, Description: {description}")
        else:
            print("No markers found for this video.")
    else:
        print(f"Error fetching stream markers: {response.status_code}, {response.text}")


def get_stream_subs(access_token, subscriber, user_id, limit=5):
    url = f"https://api.twitch.tv/helix/subscriptions"

    params = {
        'broadcaster_id': subscriber,  # Specify the video ID
        'first': limit,        # Limit the number of markers returned
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,  # Replace with your actual Client-ID
    }

    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        markers_data = response.json()

        # Print the full response to debug
        # print("Full markers response:", markers_data)

        markers = markers_data.get('data', [])
        if markers:
            print(f"Found {len(markers)} markers for user ID {marker.get('user_name', 'Unknown User')}:")
            for marker in markers:
                # Extract marker details
                marker_id = marker.get('id', 'N/A')
                created_at = marker.get('created_at', 'N/A')
                description = marker.get('description', 'N/A')
                #print(f"Marker ID: {marker_id}, Created at: {created_at}, Description: {description}")
        else:
            print("No markers found for this video.")
    else:
        print(f"Error fetching stream markers: {response.status_code}, {response.text}")

#this just returns one marker
def get_stream_marker_for_video(access_token, video_id):
    url = f"https://api.twitch.tv/helix/streams/markers"

    params = {
        'video_id': video_id,  # Specify the video ID
        'first': 1,        # Limit the number of markers returned
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,  # Replace with your actual Client-ID
    }

    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        markers_data = response.json()

        # Print the full response to debug
        #print("Full markers response:", markers_data)

        markers = markers_data.get('data', [])
        if markers:
            for entry in markers:
                videos = entry.get("videos", [])  # Get videos array safely
                for video in videos:
                    video_id = video.get("video_id", "Unknown Video ID")
                    #print(f"Video ID: {video_id}")

                    video_markers = video.get("markers", [])  # Get markers array safely
                    markerDetails = []
                    for marker in video_markers:
                        
                        stream_marker = {
                            "video_id": video_id,
                            "marker_id": marker.get("id", "Unknown"),
                            "created_at": marker.get("created_at", "Unknown Time"),
                            "position_seconds":  marker.get("position_seconds", "Unknown Position"),
                        }
                        #print("stream marker" , stream_marker)
                        markerDetails.append(stream_marker)
                        #print(markerDetails) 
                        # created_at = marker.get("created_at", "Unknown Time")
                        # position_seconds = marker.get("position_seconds", "Unknown Position")
                        #print(f"  Created At: {created_at}, Position: {position_seconds}s")
                    return markerDetails            
        # else:
        #     print("No markers found for this video.")
    else:
        print(f"Error fetching stream markers: {response.status_code}, {response.text}")


def get_stream_markers_for_video(access_token, video_id, limit=5):
    url = f"https://api.twitch.tv/helix/streams/markers"

    params = {
        'video_id': video_id,  # Specify the video ID
        'first': 100,        # Limit the number of markers returned
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,  # Replace with your actual Client-ID
    }

    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        markers_data = response.json()

        # Print the full response to debug
        #print("Full markers response:", markers_data)

        markers = markers_data.get('data', [])
        if markers:
            for entry in markers:
                videos = entry.get("videos", [])  # Get videos array safely
                for video in videos:
                    video_id = video.get("video_id", "Unknown Video ID")
                    #print(f"Video ID: {video_id}")

                    video_markers = video.get("markers", [])  # Get markers array safely
                    markerDetails = []
                    for marker in video_markers:
                        
                        stream_marker = {
                            "video_id": video_id,
                            "marker_id": marker.get("id", "Unknown"),
                            "created_at": marker.get("created_at", "Unknown Time"),
                            "position_seconds":  marker.get("position_seconds", "Unknown Position"),
                        }
                        #print("stream marker" , stream_marker)
                        markerDetails.append(stream_marker)
                        #print(markerDetails) 
                        # created_at = marker.get("created_at", "Unknown Time")
                        # position_seconds = marker.get("position_seconds", "Unknown Position")
                        #print(f"  Created At: {created_at}, Position: {position_seconds}s")
                    return markerDetails            
        # else:
        #     print("No markers found for this video.")
    else:
        print(f"Error fetching stream markers: {response.status_code}, {response.text}")

def get_stream_markers_for_user_most_recent_video(access_token, user_id, limit=5):
    url = f"https://api.twitch.tv/helix/streams/markers"

    params = {
        'user_id': user_id
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,  # Replace with your actual Client-ID
    }

    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        markers_data = response.json()

        markers = markers_data.get('data', [])
        if markers:
            for entry in markers:
                videos = entry.get("videos", [])  # Get videos array safely
                for video in videos:
                    video_id = video.get("video_id", "Unknown Video ID")
                    #print(f"Video ID: {video_id}")

                    video_markers = video.get("markers", [])  # Get markers array safely
                    for marker in video_markers:
                        created_at = marker.get("created_at", "Unknown Time")
                        position_seconds = marker.get("position_seconds", "Unknown Position")
                        print(f" Video ID: {video_id}  Created At: {created_at}, Position: {position_seconds}s")
        else:
            print("No markers found for this video.")
    else:
        print(f"Error fetching stream markers: {response.status_code}, {response.text}")

# this is used only to get the broadcaster info (only used once)
def get_user_info(access_token, username):
    url = f"https://api.twitch.tv/helix/users?login={username}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        broadcaster_id = user_data['data'][0]['id']
        #print(f"👤 Broadcaster ID for {username}: {broadcaster_id}")
        return broadcaster_id
    else:
        print("⚠️ Failed to fetch user info:", response.text)
        return None

# this function only returns data if the streamer is online 
def get_streams_without_pagination(access_token, broadcaster_id=None, limit=5):
    # Construct URL for fetching active streams (if broadcaster_id is provided, filter by that)
    url = "https://api.twitch.tv/helix/streams"
    
    params = {
        'first': limit,  # How many streams to return (e.g., 5)
    }
    if broadcaster_id:
        params['user_id'] = broadcaster_id  # Optionally filter by broadcaster

    # Set headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,  # Replace with your actual Client-ID
    }

    print("Fetching streams")

    # Make the GET request
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        streams_data = response.json()

        # Print the full response to debug
        # print("Full stream response:", streams_data)

        streams = streams_data.get('data', [])
        if streams:
            #print(f"Found {len(streams)} active stream(s):")
            for stream in streams:
                # Extract stream id and start time
                stream_id = stream.get('id', 'N/A')
                game_id = stream.get('game_id', 'N/A')
                game_name = stream.get('game_name', 'N/A')
                started_at = stream.get('started_at', 'N/A')
                #print(f"Stream ID: {stream_id}, Started at: {started_at}")
        else:
            print("No active streams found.")
    else:
        print(f"Error fetching streams: {response.status_code}, {response.text}")


def get_video_ids(video_info_list):
    # Extract video_id from each video_info dictionary and return as a list
    video_ids = [video_info['video_id'] for video_info in video_info_list]
    return video_ids

def get_videos_without_pagination_return_array_refactored(script_dir,access_token, broadcaster_id=None, limit=5 , debug=True):
    url = "https://api.twitch.tv/helix/videos"
    
    params = {
        'first': limit,  # Number of videos to return
    }
    if broadcaster_id:
        params['user_id'] = broadcaster_id  # Filter by broadcaster ID if provided

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,
    }

    #print("Fetching videos")
    response = requests.get(url, headers=headers, params=params)
    #print("response: " , response.json())

    if response.status_code == 200:
        video_data = response.json()
        videos = video_data.get('data', [])

        # Initialize an empty list to store the video details
        videoDetails = []

        videoCount = 0
        # Loop through each video and extract the relevant data
        for video in videos:
            #print("video: " , video)
            videoCount += 1
            video_id = video.get('id', 'N/A')
            game_name = ""
            noOfVideosToGetData = 1
            
            if (debug == False):
                noOfVideosToGetData = limit  # For debugging, fetch additional data like game name and stream id
            
            if video_id.isdigit():
                video_id_to_check = video_id
                isVideoInFile = check_video_in_json(script_dir,video_file_name, video_id_to_check)
                if (isVideoInFile == False):
                    print("Loading  game details for: " + video_id)
                    game_name = get_game_title(video_id)
            
            video_info = {
                "video_id": video_id,
                "stream_id": video.get('stream_id', 'N/A'),
                "game_name": game_name,
                "started_at": video.get('created_at', 'N/A'),
                "duration": video.get('duration', 'N/A'),
                "title": video.get('title', 'N/A'),
            }

            if(debug == True):
                if (videoCount <= noOfVideosToGetData):
                    #only print first one because its the only one we get game name
                    print("videoCount" , videoCount)
                    #print(video_info)
            videoDetails.append(video_info)  # Add the video info dictionary to the list
        write_or_append_video_info(videoDetails)
        return videoDetails  # Return the list of video details

    else:
        print(f"Error fetching videos: {response.status_code}, {response.text}")
        return []  # Return an empty list in case of failure


def get_videos_without_pagination_return_array_refactored_new(script_dir,access_token, broadcaster_id=None, limit=20 , debug=True , videoIds = [] ):
    url = "https://api.twitch.tv/helix/videos"
    
    params = {
        'first': limit,  # Number of videos to return
    }
    if broadcaster_id:
        params['user_id'] = broadcaster_id  # Filter by broadcaster ID if provided

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,
    }

    #print("Fetching videos")
    response = requests.get(url, headers=headers, params=params)
    #print("response: " , response.json())

    if response.status_code == 200:
        video_data = response.json()
        videos = video_data.get('data', [])

        # Initialize an empty list to store the video details
        videoDetails = []

        videoCount = 0
        # Loop through each video and extract the relevant data
        for video in videos:
            #print("video: " , video)
            videoCount += 1
            video_id = video.get('id', 'N/A')
            game_name = ""
            noOfVideosToGetData = 1
            
            if (debug == False):
                noOfVideosToGetData = limit  # For debugging, fetch additional data like game name and stream id
            
            if video_id.isdigit():
                video_id_to_check = video_id
                isVideoInFile = check_video_in_json(script_dir,video_file_name, video_id_to_check)
                if (isVideoInFile == False):
                    print("Loading  game details for: " + video_id)
                    game_name = get_game_title(video_id)
            
            video_info = {
                "video_id": video_id,
                "stream_id": video.get('stream_id', 'N/A'),
                "game_name": game_name,
                "started_at": video.get('created_at', 'N/A'),
                "duration": video.get('duration', 'N/A'),
                "title": video.get('title', 'N/A'),
            }

            if(debug == True):
                if (videoCount <= noOfVideosToGetData):
                    #only print first one because its the only one we get game name
                    print("videoCount" , videoCount)
                    #print(video_info)
            if(video_id in videoIds):
                videoDetails.append(video_info)  # Add the video info dictionary to the list
        write_or_append_video_info(videoDetails)

    else:
        print(f"Error fetching videos: {response.status_code}, {response.text}")
    return


def get_videos_without_pagination_return_array_new(access_token, broadcaster_id=None, limit=20):
    url = "https://api.twitch.tv/helix/videos"
    
    params = {
        'first': limit,  # Number of videos to return
    }
    if broadcaster_id:
        params['user_id'] = broadcaster_id  # Filter by broadcaster ID if provided

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-ID": CLIENT_ID,
    }

    #print("Fetching videos")
    response = requests.get(url, headers=headers, params=params)
    #print("response: " , response.json())

    if response.status_code == 200:
        video_data = response.json()
        videos = video_data.get('data', [])

        # Initialize an empty list to store the video details
        videoDetails = []

        videoCount = 0
        # Loop through each video and extract the relevant data
        for video in videos:
            #print("video: " , video)
            videoCount += 1
            video_id = video.get('id', 'N/A')
            if video.get('stream_id'):
                videoDetails.append(video_id)
            else:
                videoDetails.append(video_id)
        return videoDetails  # Return the list of video details

    else:
        print(f"Error fetching videos: {response.status_code}, {response.text}")
        return []  # Return an empty list in case of failure



def getDownloadedVideos(folder_name):

    # # --- DEBUG PROBES ---
    # print(f"--- DEBUGGING getDownloadedVideos ---")
    # print(f"Current Working Directory (CWD): {os.getcwd()}")
    # print(f"Input folder_name: {folder_name}")

    # Resolve relative paths against script_dir so we don't end up in C:\Windows\System32
    if not os.path.isabs(folder_name):
        folder_name = os.path.join(script_dir, folder_name)

    # print(f"Resolved folder path: {folder_name}")
    # print(f"Absolute path being checked: {os.path.abspath(folder_name)}")
    # print(f"Does it exist?: {os.path.exists(folder_name)}")
    # # --------------------

    if not os.path.exists(folder_name):
        print(f"Folder not found: {folder_name}")
        return []

    # Get list of files in the given folder
    files = [entry.name for entry in os.scandir(folder_name) if entry.is_file() and entry.name.endswith('.mp4')]

    # Filter the downloaded videos based on the provided video IDs
    video_file_array = []
    for file in files:
        videoFilearray = file.split('_')

        # Check if the split array has at least two elements
        if len(videoFilearray) > 1:
            try:
                video_file_id = int(videoFilearray[1])
                video_file_array.append(str(video_file_id))
            except ValueError:
                print(f"Skipping file with non-numeric id: {file}")
        else:
            print(f"Skipping file {file} due to unexpected format")

    return video_file_array

def getClippedVideos(folder_name):

    # Resolve relative paths against script_dir so we don't end up in C:\Windows\System32
    if not os.path.isabs(folder_name):
        folder_name = os.path.join(script_dir, folder_name)


    if not os.path.exists(folder_name):
        print(f"Folder not found: {folder_name}")
        return []
    
    output_file_path = os.path.join(folder_name, "video_id_clipped.json")

        # Load existing list (or create a new one)
    if os.path.exists(output_file_path):
        with open(output_file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # If the file contained a dict (old format), convert to list of keys
                if isinstance(data, dict):
                    video_ids = list(data.keys())
                elif isinstance(data, list):
                    video_ids = data
                else:
                    video_ids = []
            except json.JSONDecodeError:
                video_ids = []
    else:
        video_ids = []

    return video_ids

def validate_number_input(P):
    if P == "" or P == "-" or P == "-0" or P == "0" or P.replace("-", "", 1).replace(".", "", 1).isdigit():
        return True
    return False

def save_ultimos_directos():
    # Get the new value from the entry field
    new_value = n1_entry.get()
    print(new_value)

    update_ultimos_directos("datos.json", new_value)

def update_ultimos_directos(filename, new_value):
    # Ensure that new_value is an integer
    try:
        new_value = int(new_value)  # Convert to an integer
    except ValueError:
        print("Error: Invalid value for ultimos_directos. It must be a number.")
        return

    # Retrieve current video parameters
    video_params = get_video_params2(script_dir , filename)
    
    if video_params is None:
        print(f"Error: Could not retrieve video parameters from {filename}.")
        return
    
    # Print current data for debugging
    print("Current video parameters:", video_params)

    # Update the ultimos_directos value
    video_params["ultimos_directos"] = new_value
    
    # Construct the file path again for saving
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    video_info_path = os.path.join(json_dir, filename)

    # Print the file path for debugging
    print(f"Saving to file path: {video_info_path}")

    # Check if the path is correct
    if not os.path.exists(video_info_path):
        print(f"Error: {filename} file does not exist.")
        return
    
    # Save the updated parameters back to the file
    try:
        with open(video_info_path, "w", encoding="utf-8") as file:
            print("Saving data...")
            json.dump(video_params, file, ensure_ascii=False, indent=4)
            print(f"Successfully updated ultimos_directos to {new_value} in {filename}.")
    except Exception as e:
        print(f"Error saving the updated file: {e}")

def get_video_params2(script_dir, filename):
    # Define json_data directory in the project root
    json_dir = script_dir
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    video_info_path = os.path.join(json_dir, filename)
    print(video_info_path)
    # Check if video info file exists
    if not os.path.exists(video_info_path):
        print(f"Error: {filename} does not exist.")
        return None

    # Load video_info JSON data from file
    with open(video_info_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {filename}: {e}")
            return None

def delete_files_from_cache(script_dir, folder_name):
    """Delete all files from the cache folder"""
    import shutil
    
    # Resolve relative paths against script_dir
    if not os.path.isabs(folder_name):
        cache_path = os.path.join(script_dir, folder_name)
    else:
        cache_path = folder_name
    
    # Check if the folder exists
    if not os.path.exists(cache_path):
        print(f"Cache folder not found: {cache_path}")
        return
    
    # Delete all files in the cache folder
    try:
        for filename in os.listdir(cache_path):
            file_path = os.path.join(cache_path, filename)
            # Check if it's a file (not a directory)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            # Optionally remove subdirectories
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                print(f"Deleted directory: {file_path}")
        print(f"Cache folder cleaned: {cache_path}")
    except Exception as e:
        print(f"Error deleting cache files: {e}")

def start_auth_server():
    handler = AuthHandler
    with socketserver.TCPServer(("localhost", 8081), handler) as httpd:
        httpd.handle_request()

def authenticate():
    auth_url = get_authorization_url()
    webbrowser.open(auth_url)
    threading.Thread(target=start_auth_server, daemon=True).start()

def getNextVideos(broadcaster_id, ultimos_directos):

    ## gets the list of videos from twitch
    videoIds = get_videos_without_pagination_return_array_new(access_token,broadcaster_id)

    # Keep only video IDs that have markers.
    videoIds = [videoId for videoId in videoIds if hasVideoGotMarkers(videoId)]

    

    subs = get_stream_subs(access_token, broadcaster_id, broadcaster_id, 20)

    broadcaster_id = 908908905

    # # get all the videos we have already clipped got markers for
    # downloadedVideos = getClippedVideos("json_data" ) # we can pass the videoIds to check only those that we are interested in

    # these are the actual downloaded streams in the folder
    downloadedStreams = getDownloadedVideos("_stream_files") # we can pass the videoIds to check only those that we are interested in
    
    # # Remove videos that have already been clipped or downloaded
    videoIds = [video for video in videoIds if video not in downloadedStreams]
    
    ## this is to save the videoIdDeets in the video_info json file
    get_videos_without_pagination_return_array_refactored_new(script_dir,access_token,broadcaster_id,videoIds=videoIds)
       
    # Limit to only the specified number of recent streams
    videoIds = videoIds[:ultimos_directos]
    
    print(f"Videos to download: {videoIds}")

    return videoIds

def hasVideoGotMarkers(videoId):

    markers_data = get_stream_markers_for_video(access_token,videoId ,20 )
    if(markers_data):
        return True
    else:
        return False

def run_main():
    global access_token
    if not access_token:
        status_label.config(text="No access token! Authenticate first.", fg="red")
        return
    
    #get from env variables
    broadcaster_id = 908908905; #get_user_info(access_token, broadcaster_username)
    #print(f"Got broadcaster ID: {broadcaster_id}")

    if broadcaster_id:
        #fetch streams information only accessible while live
        #get_streams_without_pagination(access_token, broadcaster_id,10)
        
        # gets the video data from twitch 
        # and gets the game name from the video url using seleneium
        datos = get_video_params(script_dir , "datos.json")
        ultimos_directos = datos["ultimos_directos"]

        videoIds = getNextVideos(broadcaster_id, ultimos_directos)

        # download videos from twitch
        if(videoIds):
            #Ensure cache directory exists and use absolute path to avoid permission issues
            cache_dir = os.path.join(script_dir, "temp_cache")
            os.makedirs(cache_dir, exist_ok=True)
            output_dir = os.path.join(script_dir, "_stream_files")
            os.makedirs(output_dir, exist_ok=True)
            output_template = os.path.join(output_dir, "{date}_{id}_{game_slug}.{format}")
            # Download videos one-by-one because not all videos support the same quality
            for vid in videoIds:
                try:
                    download_video_by_id_from_twitch_basic([
                                                    "-q",
                                                    "1080p60",
                                                    "--output",
                                                    output_template,
                                                    "--skip-existing",
                                                    "-f", "mp4",
                                                    "--cache-dir",
                                                    cache_dir,
                                                    vid ])
                except Exception as e:
                    print(f"error encontrando 1080p60 para {vid} : {e}; probando 1080p")
                    try:
                        download_video_by_id_from_twitch_basic([
                                                    "-q",
                                                    "1080p",
                                                    "--output",
                                                    output_template,
                                                    "--skip-existing",
                                                    "-f", "mp4",
                                                    "--cache-dir",
                                                    cache_dir,
                                                    vid ])
                    except Exception as e2:
                        print(f"1080p tampoco funciono para {vid} error {e2}")
                        write_video_id_to_file(script_dir,vid)
                        delete_files_from_cache(script_dir,"temp_cache")

            print("Video descargado correctamente.")
        else:
            print("No hay videos para descargar o tienes directos para borrar")

        #save_stuff to video_info

        print("Videos bajados ", videoIds)
        markers_full_set = []
        for videoId in videoIds:
            #print("getting marker for video" + videoId)
            markers_data = get_stream_markers_for_video(access_token,videoId ,20 )
            if(markers_data):
                for marker in markers_data:
                    #print(marker)
                    markers_full_set.append(marker)

        
        if markers_full_set:
            # get all videos in video folder and get durations
            durations = get_video_durations(videos_folder_name)
            durations_filename = save_durations_to_json(durations ,video_durations_file)
            print("video durations file saved" + str(durations_filename))
            
            # add child stream id and parent stream id to videos
            process_streams(script_dir , "video_info.json")

            append_video_name_to_video_file(script_dir , durations,video_file_name)

            # this is the last thing to add
            add_markers_to_video_data(script_dir , video_file_name, markers_full_set, output_file_name)

            # create vide_edit_data_file
            filter_videos_with_markers(script_dir , output_file_name, edit_video_data_file)

            # creates marker data ready for clip creation
            create_game_marker_files_for_editing(script_dir , edit_video_data_file)

            # creates merged files
            merge_game_marker_json_files(script_dir)

            append_video_file_to_markers_in_game_folders(script_dir,45,45)
            collect_and_write_markers_per_game(script_dir)
            print("Procesando Clips ...")
            write_individual_marker_files(script_dir)
            print("Fin del processo")
        else:
            print("No se encontraron marcadores para los videos procesados.")
            print("Fin del processo")
    
    status_label.config(text="Running main processing...", fg="blue")
    threading.Thread(target=process_data, daemon=True).start()

def process_data():
    import time  # Simulating long-running tasks
    time.sleep(3)  # Replace with actual video processing logic
    status_label.config(text="Processing complete!", fg="green")




# Create UI
# Set path to VLC
os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")



def donothing():
    pass

class Consoleredirect:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        if not re.search(r"\d+K", message) and "%" not in message and "GB" not in message and "MB" not in message and "ETA" not in message and "VODs" not in message:
            stripped_message = message.strip()  
            if stripped_message:
                self.text_widget.insert(tk.END, stripped_message + "\n")
                self.text_widget.see(tk.END)  

    def flush(self):
        pass  

## UI Stuff

root = tk.Tk()
root.title("Clips Admin - Twitch Clip Manager")
root.geometry("1200x1000")  


style = ttk.Style()
style.configure("Treeview", font=("Arial", 10 , "bold"))  # or Consolas for monospace
style.configure("Treeview.Heading", font=("Arial", 12, "bold"))

# Load video parameters
datos_sacar_clips = get_video_params(script_dir,"datos.json")

n1_default = datos_sacar_clips.get("ultimos_directos", "0")

# Function to switch views
def show_frame(frame):
    frame.tkraise()


def themed_label(parent, text="", **kwargs):
    return tk.Label(
        parent,
        text=text,
        font=("Arial", 12, "bold"),        # or use a theme color
        fg="black",         # text color
        padx=5,
        pady=3,
        anchor="w",         # left-align text
        **kwargs
    )


def themed_label_title(parent, text="", **kwargs):
    return tk.Label(
        parent,
        text=text,
        font=("Arial", 14, "bold"),        # or use a theme color
        fg="black",         # text color
        padx=5,
        pady=3,
        anchor="w",         # left-align text
        **kwargs
    )

def themed_button_back(parent, **kwargs):
    return tk.Button(
        parent,
        font=("Arial", 12, "bold"),
        bg="#e74c3c",
        fg="black",
        activebackground="#c0392b",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )


def themed_button_play(parent, **kwargs):
    return tk.Button(
        parent,
        text="▶ Play",
        font=("Arial", 12, "bold"),
        bg="#2ecc71",
        fg="black",
        activebackground="#27ae60",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )

def themed_button_pause(parent, **kwargs):
    return tk.Button(
        parent,
        text="⏸ Pause",
        font=("Arial", 12, "bold"),
        bg="#f1c40f",
        fg="black",
        activebackground="#f39c12",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )


def themed_button_stop(parent, **kwargs):
    return tk.Button(
        parent,
        text="⏹ Stop",
        font=("Arial", 12, "bold"),
        bg="#e74c3c",
        fg="black",
        activebackground="#c0392b",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )

def themed_button_regular(parent, **kwargs):
    return tk.Button(
        parent,
        font=("Arial", 12 , "bold"),
        bg="gray",              # Green
        fg="black",
        activebackground="gray",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )

def themed_button_regular_light(parent, **kwargs):
    return tk.Button(
        parent,
        font=("Arial", 12 , "bold"),
        bg="lightgray",              # Green
        fg="black",
        activebackground="lightgray",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )

def themed_button_save(parent, **kwargs):
    return tk.Button(
        parent,
        text="Save Setting 💾",  # Emoji at the end
        font=("Arial", 12 , "bold"),  # Legible font
        bg="#1abc9c",
        fg="black",
        activebackground="#16a085",
        activeforeground="black",
        relief=tk.RAISED,
        bd=2,
        cursor="hand2",
        **kwargs
    )


### VLC setup

vlc_instance = vlc.Instance()
media_player = vlc_instance.media_player_new()

vlc_instance2 = vlc.Instance()
media_player_clips_cortados = vlc_instance2.media_player_new()

clip_directory = ""

# --- Graceful Exit ---
def on_close():
    if media_player:
        media_player.stop()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# --- Frame Management ---
# def show_frame(frame):
#     frame.tkraise()


# Add a selected clip to the tree
def open_clip_file():
    clips_root = os.path.join(os.getcwd(), "clips")
    file_path = filedialog.askopenfilename(
        initialdir=clips_root,
        title="Select a Clip",
        filetypes=[("Video Files", "*.mp4;*.avi;*.mov;*.mkv")]
    )

    if file_path:
        # Ensure path is inside a subfolder of clips/
        abs_clips_root = os.path.abspath(clips_root)
        abs_file_path = os.path.abspath(file_path)
        common_path = os.path.commonpath([abs_clips_root, abs_file_path])
        rel_path = os.path.relpath(abs_file_path, abs_clips_root)
        parts = rel_path.split(os.sep)

        # Must be in a subfolder of clips (not directly inside clips/)
        if common_path != abs_clips_root or len(parts) < 2:
            messagebox.showerror("Invalid Selection", "Please select a clip from a subfolder inside the 'clips' directory.")
            return

        # Prevent duplicate clip paths in the Treeview
        for child in tree.get_children():
            existing_path = tree.item(child)["values"][0]
            if abs_file_path == existing_path:
                messagebox.showinfo("Clip Duplicado", "Clip Duplicado")
                return

        # If valid and not a duplicate, add to Treeview
        tree.insert("", tk.END, values=(abs_file_path, 0, 0, 0, 0))


# --- Playback Controls ---
def pause_video():
    if media_player.is_playing():
        media_player.pause()

def stop_video():
    media_player.stop()

def set_volume(val):
    volume = int(val)
    media_player.audio_set_volume(volume)


###


# --- Playback Controls media player cortados ---
def pause_video_cortado():
    if media_player_clips_cortados.is_playing():
        media_player_clips_cortados.pause()

def stop_video_cortado():
    media_player_clips_cortados.stop()

def set_volume_cortado(val):
    volume = int(val)
    media_player_clips_cortados.audio_set_volume(volume)


###


# Container frame to hold different sections
container = tk.Frame(root)
container.pack(fill="both", expand=True)

# Create main and clip sections
main_frame = tk.Frame(container)
clip_frame = tk.Frame(container)

for frame in (main_frame, clip_frame):
    frame.grid(row=0, column=0, sticky="nsew")

# --- MAIN FRAME ---
# themed_label_title(main_frame, text="Sito Clips").pack(pady=10)
# themed_button_regular_light(main_frame, text="📥  Sacar Clips", command=authenticate).pack(pady=5)

# themed_label(main_frame, text="Ultimos Directos:").pack(pady=5)
# vcmd = root.register(validate_number_input)
# n1_entry = tk.Entry(main_frame, font=("Arial", 12), validate="key", validatecommand=(vcmd, "%P"))
# n1_entry.pack(pady=2)
# n1_entry.insert(0, n1_default)

# save_button = themed_button_save(main_frame, command=save_ultimos_directos)
# save_button.pack(pady=10)



# Packing other widgets
themed_label_title(main_frame, text="Clips Management").pack(pady=10)
themed_button_regular_light(main_frame, text="📥 Download Clips", command=authenticate).pack(pady=15)


# Top row frame for the "Ultimos Directos" label, entry, and save button
top_row_frame = tk.Frame(main_frame)
top_row_frame.pack(padx=350, fill="x", anchor="center", pady=15)  # Center the entire frame in the parent




# Label (centered)
themed_label(top_row_frame, text="Number of previous Streams:").pack(side="left", padx=1)

# Entry (side-by-side)
vcmd = root.register(validate_number_input)
n1_entry = tk.Entry(top_row_frame, font=("Arial", 12 , "bold"), validate="key", validatecommand=(vcmd, "%P"))
n1_entry.pack(side="left", padx=5)
n1_entry.insert(0, n1_default)

# Save button (side-by-side)
save_button = themed_button_save(top_row_frame, command=save_ultimos_directos)
save_button.pack(side="left", padx=5)



# Switch to "Cortar Clips"
themed_button_regular_light(main_frame, text="✂️ Cut/Edit Clips", command=lambda: show_frame(clip_frame)).pack(pady=1)

status_label = tk.Label(main_frame, text="", font=("Arial", 12))
status_label.pack(pady=10)

# Scrollable Console
frame = tk.Frame(main_frame)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

console = tk.Text(frame, font=("Helvetica", 12), wrap="word", yscrollcommand=scrollbar.set, height=8)
console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=console.yview)

sys.stdout = Consoleredirect(console)
print("App Ready...")

# --- CORTAR CLIPS FRAME ---
tk.Label(clip_frame, text="Cut/Edit Clips", font=("Arial", 14, "bold")).pack(pady=10)
themed_button_back(clip_frame, text="⏴ Volver atras", command=lambda: show_frame(main_frame)).pack(pady=10)

#tk.Button(clip_frame, text="Open Folder and Select Clip", command=open_clip_directory, font=("Arial", 12)).pack(pady=10)




bottom_button_frame = tk.Frame(clip_frame)
bottom_button_frame.pack(fill="x", pady=5)  # Packs below the other buttons

# Left button
themed_button_regular(
    bottom_button_frame,
    text="📁 Select Clip",
    command=open_clip_file
).pack(side="left", padx=10)

# Right button
themed_button_regular(
    bottom_button_frame,
    text="✂️ Cut All Clips",
    command=lambda: getClipsToCutFromTreeview(tree, tree2, tk)
).pack(side="right", padx=10)

# In your clip_frame UI setup:
tk.Label(clip_frame, text="Clips originales", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

columns = ("path", "add_start", "remove_start", "add_end", "remove_end")
tree = ttk.Treeview(clip_frame, columns=columns, show="headings", height=6)



tree.heading("path", text="Clip")
tree.heading("add_start", text="Add to Beginning")
tree.heading("remove_start", text="Cut Beginning")
tree.heading("add_end", text="Extend End")
tree.heading("remove_end", text="Cut End")

# Set column widths (adjust if needed)
tree.column("path", width=500)
tree.column("add_start", width=120)
tree.column("remove_start", width=120)
tree.column("add_end", width=100)
tree.column("remove_end", width=100)

tree.pack(padx=10,pady=10, fill=tk.X)



def play_selected_tree_clip(event):
    selected = tree.selection()
    if selected:
        file_path = tree.item(selected[0])["values"][0]

        if media_player.is_playing():
            media_player.pause()

        # Load the new media
        media = vlc_instance.media_new(file_path)
        media_player.set_media(media)

        # Re-bind video panel to player
        media_player.set_hwnd(video_panel.winfo_id())

        # Optional: Set volume again if needed
        media_player.audio_set_volume(volume_slider.get())

        print(f"Clip ready to play: {file_path}")

tree.bind("<<TreeviewSelect>>", play_selected_tree_clip)


def delete_selected_tree_item(event):
    selected_item = tree.selection()  # Get the selected item
    if selected_item:
        tree.delete(selected_item)  # Delete the selected item
    else:
        messagebox.showinfo("No Selection", "No Selection")


def show_delete_menu(event):
    delete_menu = tk.Menu(root, tearoff=0)
    delete_menu.add_command(label="Delete", command=lambda: delete_selected_tree_item(event))
    delete_menu.post(event.x_root, event.y_root)  # Show the menu at the mouse position

tree.bind("<Button-3>", show_delete_menu)  # Bind right-click to show delete menu


def on_double_click(event):
    global media_player  # Ensure media_player is accessible here

    # Stop the clip if it is currently playing
    if media_player.is_playing():
        media_player.pause()

    item = tree.identify_row(event.y)
    column = tree.identify_column(event.x)

    if not item or column == "#1":  # Skip editing the path field
        return

    x, y, width, height = tree.bbox(item, column)
    value = tree.set(item, column)

    # Create an entry widget to edit the field
    entry = tk.Entry(clip_frame)
    entry.place(x=x, y=y + tree.winfo_y(), width=width, height=height)
    entry.insert(0, value)
    entry.focus()

    def save_edit(event):
        tree.set(item, column, entry.get())
        entry.destroy()

    # Save the edited value on Enter press or when focus is lost
    entry.bind("<Return>", save_edit)
    entry.bind("<FocusOut>", lambda e: entry.destroy())

# Bind the double-click event to the Treeview
tree.bind("<Double-1>", on_double_click)



# Container to hold both video panels side by side
video_container = tk.Frame(clip_frame)
video_container.pack(anchor="w", padx=10, pady=10, fill="x")

# --- LEFT VIDEO PANEL + CONTROLS ---
left_panel = tk.Frame(video_container)
left_panel.pack(side="left", padx=100 )

tk.Label(left_panel, text="Original Clip", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

video_panel = tk.Frame(left_panel, bg="black", width=420, height=240)
video_panel.pack()

controls_frame = tk.Frame(left_panel)
controls_frame.pack(pady=5)

themed_button_play(controls_frame, command=lambda: media_player.play()).grid(row=0, column=0, padx=5)
themed_button_pause(controls_frame, command=pause_video).grid(row=0, column=1, padx=5)
themed_button_stop(controls_frame, command=stop_video).grid(row=0, column=2, padx=5)

tk.Label(controls_frame, text="Volume", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5)
volume_slider = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=set_volume)
volume_slider.set(80)
volume_slider.grid(row=0, column=4)

# --- RIGHT VIDEO PANEL + CONTROLS ---
right_panel = tk.Frame(video_container)
right_panel.pack(side="left", padx=10)

tk.Label(right_panel, text="Edited Clip", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=5)

video_panel_clips_cortados = tk.Frame(right_panel, bg="black", width=420, height=240)
video_panel_clips_cortados.pack()

controls_frame_clips_cortados = tk.Frame(right_panel)
controls_frame_clips_cortados.pack(pady=5)

themed_button_play(controls_frame_clips_cortados, command=lambda: media_player_clips_cortados.play()).grid(row=0, column=0, padx=5)
themed_button_pause(controls_frame_clips_cortados, command=pause_video_cortado).grid(row=0, column=1, padx=5)
themed_button_stop(controls_frame_clips_cortados, command=stop_video_cortado).grid(row=0, column=2, padx=5)

tk.Label(controls_frame_clips_cortados, text="Volume", font=("Arial", 10 , "bold")).grid(row=0, column=3, padx=5)
volume_slider2 = tk.Scale(controls_frame_clips_cortados, from_=0, to=100, orient=tk.HORIZONTAL, command=set_volume_cortado)
volume_slider2.set(80)
volume_slider2.grid(row=0, column=4)


## clips cortado tree
tk.Label(clip_frame, text="Edited Clips", font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=10)
columns2 = ("path")
tree2 = ttk.Treeview(clip_frame, columns=columns2, show="headings", height=6)
#clips cortados tree
tree2.heading("path", text="Clip")

# Set column widths (adjust if needed)
tree2.column("path", width=200)
tree2.pack(padx=10, pady=10, fill=tk.X)


def play_selected_tree2_clip(event):
    selected = tree2.selection()
    if selected:
        file_path = tree2.item(selected[0])["values"][0]

        print('filepath for cortado' , file_path)

        if media_player_clips_cortados.is_playing():
            media_player_clips_cortados.pause()

        # Load the new media
        media = vlc_instance2.media_new(file_path)
        media_player_clips_cortados.set_media(media)

        # Re-bind video panel to player
        media_player_clips_cortados.set_hwnd(video_panel_clips_cortados.winfo_id())

        # Optional: Set volume again if needed
        media_player_clips_cortados.audio_set_volume(volume_slider.get())

        print(f"Edited Clip ready to play: {file_path}")

tree2.bind("<<TreeviewSelect>>", play_selected_tree2_clip)



# --- MENUBAR ---
menubar = tk.Menu(root)
filemenu = tk.Menu(menubar, tearoff=0)
filemenu.add_command(label="New", command=donothing)
filemenu.add_command(label="Cut/Edit Clips", command=lambda: show_frame(clip_frame))
filemenu.add_command(label="Save", command=save_ultimos_directos)
filemenu.add_separator()
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

root.config(menu=menubar)

# Show main frame first
show_frame(main_frame)

try:
    root.mainloop()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to close...")
