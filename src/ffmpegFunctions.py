from collections import defaultdict
import datetime  # for checking the module path
import json
import os
import re
import subprocess
import sys

import twitchdl
import twitchdl.cli
import twitchdl.commands
import twitchdl.commands.download



sys.path.append(os.path.abspath("src/downloads/"))

print(datetime.__file__)


def duration_to_seconds(duration_str):
    """
    Converts a duration string like '2h37m26s' into total seconds.

    :param duration_str: Duration string in the format 'XhYmZs' (hours, minutes, seconds).
    :return: Total duration in seconds.
    """
    # Regular expression to capture hours, minutes, and seconds
    pattern = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
    match = pattern.fullmatch(duration_str)
    
    if not match:
        raise ValueError(f"Invalid duration format: '{duration_str}'")

    # Extract hours, minutes, and seconds, defaulting to 0 if not present
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0

    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds

def get_camera_params(filename):
    # Define json_data directory in the project root
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    video_info_path = os.path.join(json_dir, filename)

    # Check if video info file exists
    if not os.path.exists(video_info_path):
        #print(f"Warning: The file {video_info_filename} does not exist in json_data.")
        return

    # Load video_info JSON data from file
    with open(video_info_path, "r", encoding="utf-8") as file:
        try:
            return  json.load(file)
        except json.JSONDecodeError:
            #print(f"Error: {video_info_filename} contains invalid JSON.")
            return


def get_video_durations(folder_name):
    # Get list of files in the given folder
    files = [entry.name for entry in os.scandir(folder_name) if entry.is_file()]

    def get_duration(file_path):
        # Convert to absolute path and format for Windows
        file_path = os.path.abspath(file_path).replace("\\", "/")

        # Run ffprobe command and capture the output
        cmd = [
            "ffprobe",
            "-i", file_path,
            "-show_entries", "format=duration",
            "-v", "error",
            "-of", "default=noprint_wrappers=1:nokey=1"
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Debugging output
        # print(f"Running command: {' '.join(cmd)}")
        # print(f"STDOUT: {result.stdout.strip()}")
        # print(f"STDERR: {result.stderr.strip()}")

        # Parse the duration output and return it
        duration = result.stdout.strip()
        return float(duration) if duration else None

    def format_duration(seconds):
        # Convert total seconds into hours, minutes, and seconds
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours}h{minutes}m{seconds}s"

    # Store durations in a dictionary
    durations = {}
    for file in files:
        if file.lower().endswith(('.png', '.gif')):
                continue  # Skip PNG and GIF files

        file_path = os.path.join(folder_name, file)

        if not os.path.exists(file_path):
            #print(f"File not found: {file_path}")
            durations[file] = "File not found"
            continue

        duration = get_duration(file_path)
        durations[file] = format_duration(duration) if duration is not None else "N/A"

    return durations

def save_durations_to_json(durations, output_filename):
    # Ensure the json_data directory exists
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    os.makedirs(json_dir, exist_ok=True)

    # Define full file path
    file_path = os.path.join(json_dir, output_filename)

    # Write JSON file
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(durations, json_file, indent=4)

    #print(f"Durations saved to {file_path}")
    return file_path  # Optional: return the full path for reference

def add_video_filenames_and_durations(durations ,video_file, output_file):
    """
    Reads a JSON file, adds the video filename and duration based on video_id,
    and writes the updated data back to a new JSON file.
    """
    # Load JSON data
    with open(video_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Get video durations
    #durations = get_video_durations(folder_name)

    # Process each item and add the video filename and duration
    for item in data:
        video_id = item.get("video_id", "unknown")
        video_filename = f"{video_id}.mp4"
        duration = durations.get(video_filename, "N/A")
        
        item["video_filename"] = video_filename
        item["duration"] = duration

    # Save updated JSON
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    print(f"Updated JSON saved to {output_file}")

# def download_video_by_id_from_twitch(command):
#     print(f"Bajando Video: {id}")
#     twitchdl.cli.download(command)
#     return


def fake_exit(*args):
    print("sys.exit() was called but ignored!")

sys.exit = fake_exit  # Prevent script from exiting unexpectedly


def download_video_by_id_from_twitch_basic(command):
    print(f"Downloading Video: {command}")
    try:
        import io
        import sys
        from contextlib import redirect_stderr, redirect_stdout
        
        # Capture stdout and stderr from twitchdl
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            twitchdl.cli.download(command)
        
        output = stdout_capture.getvalue()
        error_output = stderr_capture.getvalue()
        
        # Print only "Found video" and "Target" lines
        for line in output.split('\n'):
            if 'Found video' in line or 'Target:' in line:
                print(line)
        
        # Check for error indicators in both stdout and stderr
        error_indicators = [
            'Error: Joining files failed',
            'Invalid data found when processing input',
            'Error opening input',
            'error'
        ]
        
        combined_output = (output + error_output).lower()
        for indicator in error_indicators:
            if indicator.lower() in combined_output:
                print(f"ERROR DETECTED: {error_output if error_output else output}")
                raise RuntimeError(f"TwitchDL error detected: {indicator}")
        
    except Exception as e:
        error_msg = f"Error running TwitchDL: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
        raise RuntimeError(error_msg)

def download_video_by_id_from_twitch(command):
    print(f"Downloading Video: {command}")
    try:
        # Always skip TwitchDL's internal join and perform manual join to ensure
        # ffmpeg can handle segment files regardless of extension format.
        cmd_skip_join = list(command)
        if '--no-join' not in cmd_skip_join:
            cmd_skip_join.append('--no-join')

        print(f"Downloading segments (no-join)")
        try:
            twitchdl.cli.download(cmd_skip_join)
        except Exception as e:
            print(f"Failed with --no-join: {e}; attempting without flag")
            twitchdl.cli.download(command)

        # Extract command parameters
        cache_dir = None
        output_template = None
        video_id = None
        if '--cache-dir' in command:
            try:
                idx = command.index('--cache-dir')
                cache_dir = command[idx + 1]
            except Exception:
                cache_dir = None
        if '--output' in command:
            try:
                idx = command.index('--output')
                output_template = command[idx + 1]
            except Exception:
                output_template = None
        try:
            video_id = str(command[-1])
        except Exception:
            video_id = None

        if not cache_dir:
            cache_dir = os.path.join(os.getcwd(), 'temp_cache')

        # Find playlist
        playlist_path = os.path.join(cache_dir, 'playlist_downloaded.m3u8')
        if not os.path.exists(playlist_path):
            try:
                for f in os.listdir(cache_dir):
                    if f.endswith('.m3u8'):
                        playlist_path = os.path.join(cache_dir, f)
                        break
            except Exception:
                playlist_path = None

        if playlist_path and os.path.exists(playlist_path):
            print(f"Found playlist: {playlist_path}")
            fixed_playlist = os.path.join(cache_dir, 'playlist_fixed.m3u8')

            # Normalize: rename segments without extension
            try:
                with open(playlist_path, 'r', encoding='utf-8') as pf:
                    lines = pf.readlines()

                new_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#'):
                        new_lines.append(line)
                        continue
                    seg = stripped
                    seg_path = os.path.join(cache_dir, seg)
                    if not os.path.splitext(seg)[1]:
                        seg_ts = seg + '.ts'
                        seg_ts_path = os.path.join(cache_dir, seg_ts)
                        if os.path.exists(seg_path) and not os.path.exists(seg_ts_path):
                            try:
                                os.rename(seg_path, seg_ts_path)
                                print(f"Renamed {seg} to {seg_ts}")
                            except Exception:
                                try:
                                    import shutil
                                    shutil.copy(seg_path, seg_ts_path)
                                except Exception as copy_e:
                                    print(f"Failed to rename/copy {seg}: {copy_e}")
                        new_lines.append(seg_ts + '\n')
                    else:
                        new_lines.append(line)

                with open(fixed_playlist, 'w', encoding='utf-8') as ff:
                    ff.writelines(new_lines)
                print(f"Wrote fixed playlist: {fixed_playlist}")

                # Run ffmpeg to join segments
                out_dir = os.path.dirname(output_template) if output_template else os.path.join(os.getcwd(), '_stream_files')
                os.makedirs(out_dir, exist_ok=True)
                out_file = os.path.join(out_dir, f"{video_id}.mp4") if video_id else os.path.join(out_dir, 'output.mp4')

                ffmpeg_cmd = [
                    'ffmpeg',
                    '-allowed_extensions', 'ALL',
                    '-protocol_whitelist', 'file,http,https,tcp,tls',
                    '-i', fixed_playlist,
                    '-c', 'copy',
                    '-y',
                    out_file
                ]
                print(f"Running ffmpeg to join into {out_file}")
                res = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode != 0:
                    print(f"ffmpeg join failed: {res.stderr}")
                else:
                    print(f"Successfully joined to {out_file}")
            except Exception as e:
                print(f"Manual join step failed: {e}")
    except Exception as e:
        print("Error running TwitchDL:", e)


#this creates a folder per game and then 
# creates a date folder inside and 
# creates a json filer for the streams on that day 
# for that game
def create_game_marker_files_for_editing(script_dir , input_file):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full input file path
    input_file_path = os.path.join(json_dir, input_file)

    # Check if input file exists
    if not os.path.exists(input_file_path):
        #print(f"Error: The file {input_file} does not exist in json_data.")
        return

    # Load the JSON data
    try:
        with open(input_file_path, 'r', encoding="utf-8") as json_file:
            data = json.load(json_file)
    except json.JSONDecodeError:
        #print(f"Error: {input_file_path} contains invalid JSON.")
        return

    # Group videos by game_name
    grouped_videos = defaultdict(list)
    for video in data:
        grouped_videos[video['game_name']].append(video)

    # Process each game
    for game, videos in grouped_videos.items():
        try:
            # Sort videos by started_at
            videos.sort(key=lambda x: datetime.datetime.fromisoformat(x['started_at'].replace("Z", "+00:00")))
        except Exception as e:
            #print(f"Error parsing date for game '{game}': {e}")
            continue

        # Create a folder for each game
        game_folder = os.path.join(script_dir, "_stream_files", game.replace(" ", "_"))
        os.makedirs(game_folder, exist_ok=True)

        # Further group videos by date (without time)
        date_grouped_videos = defaultdict(list)
        for video in videos:
            try:
                video_date = datetime.datetime.fromisoformat(video['started_at'].replace("Z", "+00:00")).strftime("%Y-%m-%d")
                date_grouped_videos[video_date].append(video)
            except Exception as e:
                print(f"Error processing date for video {video['video_id']}: {e}")

        # Process each date
        for date, date_videos in date_grouped_videos.items():
            # Create folder for the date
            date_folder = os.path.join(game_folder, date)
            os.makedirs(date_folder, exist_ok=True)

            # Consolidate marker data for all videos on this date
            consolidated_markers = [
                {
                    "video_id": video['video_id'],
                    "started_at": video['started_at'],
                    "markers": video['markers'],
                    "duration": video['duration'],
                    "game_name": video['game_name'],
                    "video_file": video.get("video_file", None)
                }
                for video in date_videos
            ]

            # Save all marker data in one file for the date
            marker_file = os.path.join(date_folder, game.replace(" ", "_") + "_" + date + "_markers.json")
            with open(marker_file, "w", encoding="utf-8") as f:
                json.dump(consolidated_markers, f, indent=4, ensure_ascii=False)

            #print(f"Saved consolidated markers for {game} on {date} in {marker_file}")

#creates a full json file for that game 
# with all the marker data
def merge_game_marker_json_files(script_dir):
    # Define the root folder where the 'output' directory is located
    root_folder = os.path.join(script_dir, "_stream_files")#os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    

    # Check if the root folder exists
    if not os.path.exists(root_folder):
        #print(f"Error: The folder '_stream_files' does not exist.")
        return

    date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')

    # Traverse the 'output' root folder
    for game_folder in os.listdir(root_folder):
        game_path = os.path.join(root_folder, game_folder)
        merged_data = []

        if os.path.isdir(game_path):
            # Traverse date folders inside each game folder
            for date_folder in os.listdir(game_path):
                if date_pattern.fullmatch(date_folder):
                    date_path = os.path.join(game_path, date_folder)

                    # Identify the single JSON file in the date folder
                    json_files = [f for f in os.listdir(date_path) if f.endswith('.json')]
                    if len(json_files) != 1:
                        print(f"Warning: Expected one JSON file in {date_path}, found {len(json_files)}.")
                        continue

                    json_file_path = os.path.join(date_path, json_files[0])

                    # Load the JSON data
                    try:
                        with open(json_file_path, 'r', encoding="utf-8") as file:
                            data = json.load(file)
                            if isinstance(data, list):
                                for item in data:
                                    item['game'] = game_folder
                                    item['date'] = date_folder
                                    merged_data.append(item)
                            else:
                                print(f"Unexpected data format in {json_file_path}")
                    except json.JSONDecodeError:
                        #print(f"Error: {json_file_path} contains invalid JSON.")
                        continue

            # Write merged data to a file in the root of each game folder only if data exists
            if merged_data:
                output_file = os.path.join(game_path, f'{game_folder}_full_data.json')
                with open(output_file, 'w') as outfile:
                    json.dump(merged_data, outfile, indent=4)


def append_video_file_to_markers_in_game_folders(script_dir,pre_amount,post_amount):
    """
    Processes JSON files located only at the root of each game folder inside the root_folder.
    Appends the video_file property to each marker in those files.

    :param root_folder: The root directory containing game folders.
    """

    root_folder = os.path.join(script_dir, "_stream_files")


      # Iterate through the game folders inside the root folder
    for game_folder in os.listdir(root_folder):
        game_folder_path = os.path.join(root_folder, game_folder)
        
        # Check if it's a directory (game folder)
        if os.path.isdir(game_folder_path):
            # Process only JSON files in the root of the game folder
            for file in os.listdir(game_folder_path):
                file_path = os.path.join(game_folder_path, file)
                
                if os.path.isfile(file_path) and file.endswith('.json'):
                    try:
                        # Read the JSON file
                        with open(file_path, 'r') as json_file:
                            data = json.load(json_file)

                        # Update markers with video_file and game_folder
                        for video in data:
                            video_file = video.get("video_file")
                            duration_time = video.get("duration")
                            duration_seconds = duration_to_seconds(duration_time)
                            for marker in video.get("markers", []):
                                pre_seconds = marker.get("position_seconds") - pre_amount
                                post_seconds = marker.get("position_seconds") + post_amount
                                
                                if pre_seconds <= 0:
                                    pre_seconds = 0

                                if post_seconds > duration_seconds:
                                    post_seconds = duration_seconds

                                marker["video_file"] = video_file
                                marker["game_folder"] = game_folder  # Add game folder name
                                marker["duration"] = duration_time
                                marker["duration_seconds"] = duration_seconds  # Add duration time if available
                                marker["position_pre"] = pre_seconds
                                marker["position_post"] = post_seconds
                        # Write the updated data back to the same file
                        with open(file_path, 'w') as json_file:
                            json.dump(data, json_file, indent=4)

                        #print(f"Updated '{file_path}' successfully!")

                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        print(f"Error processing '{file_path}': {e}")
                    except Exception as e:
                        print(f"Unexpected error with '{file_path}': {e}")

def write_video_id_to_file(script_dir, video_id):
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists
    output_file_path = os.path.join(json_dir, "video_id_clipped.json")

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

    # Normalize and append the new video ID if not already present
    vid_str = str(video_id)
    if vid_str not in video_ids:
        video_ids.append(vid_str)

    # Write the updated list back to the JSON file
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(video_ids, f, indent=4)



def collect_and_write_markers_per_game(script_dir):
    """
    Collects all markers from JSON files located at the root of each game folder
    and writes them into separate files in an 'output' folder inside the root directory.

    Each output file will contain all markers in a single array for that game.

    :param root_folder: The root directory containing game folders.
    """
    ##root_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    root_folder = os.path.join(script_dir, "_stream_files")
    ##game_marker_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_game_marker_files")
    game_marker_folder = os.path.join(script_dir, "_game_marker_files")

    # Iterate through the game folders inside the root folder
    for game_folder in os.listdir(root_folder):
        game_folder_path = os.path.join(root_folder, game_folder)
        
        # Check if it's a directory (game folder)
        if os.path.isdir(game_folder_path):
            all_markers = []  # Collect all markers for this game

            # Process only JSON files in the root of the game folder
            for file in os.listdir(game_folder_path):
                file_path = os.path.join(game_folder_path, file)
                
                if os.path.isfile(file_path) and file.endswith('.json'):
                    try:
                        # Read the JSON file
                        with open(file_path, 'r') as json_file:
                            data = json.load(json_file)

                        # Collect markers, adding video_file and game_folder properties
                        for video in data:
                            video_file = video.get("video_file")
                            for marker in video.get("markers", []):
                                marker["video_file"] = video_file
                                marker["game_folder"] = game_folder
                                all_markers.append(marker)

                    except (FileNotFoundError, json.JSONDecodeError) as e:
                        print(f"Error processing '{file_path}': {e}")
                    except Exception as e:
                        print(f"Unexpected error with '{file_path}': {e}")

            # Write all collected markers to an output file per game
            if all_markers:
                output_file_path = os.path.join(game_marker_folder, f'{game_folder}_markers.json')
                with open(output_file_path, 'w') as output_file:
                    json.dump(all_markers, output_file, indent=4)

                #print(f"Markers for '{game_folder}' written to '{output_file_path}'")


def getDownloadedVideo(script_dir , folder_name , filename):

    # Resolve relative paths against script_dir so we don't end up in C:\Windows\System32
    if not os.path.isabs(folder_name):
        folder_name = os.path.join(script_dir, folder_name)


    if not os.path.exists(folder_name):
        print(f"stream files folder not found: {folder_name}")
        return False

    # Get list of files in the given folder (no extension filtering)
    files = [entry.name for entry in os.scandir(folder_name) if entry.is_file()]

    # Normalize filename
    fname = str(filename)

    # Quick exact/endswith/substr checks
    for file in files:
        if file == fname or file.endswith(fname) or fname in file:
            return True

        # If the provided filename is a numeric id, check typical patterns
        if fname.isdigit():
            parts = file.split('_')
            if len(parts) > 1 and parts[1] == fname:
                return True
            # also try to find numeric portion in the base name
            base = os.path.splitext(file)[0]
            m = re.search(r"(\d+)", base)
            if m and m.group(1) == fname:
                return True

    return False

def write_individual_marker_files(script_dir):
    """
    Reads marker files from the 'output' folder in the root directory,
    and writes each marker into a separate file in a folder named after the game.

    Each marker will be saved as an individual JSON file inside the game folder.

    :param root_folder: The root directory containing the 'output' folder.
    """
    ##root_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_game_marker_files")
    root_folder = os.path.join(script_dir, "_game_marker_files")

    ##clips_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips")
    clips_folder = os.path.join(script_dir, "clips")

    # Iterate through all marker files in the 'root' folder
    for file in os.listdir(root_folder):
        file_path = os.path.join(root_folder, file)
        
        if os.path.isfile(file_path) and file.endswith('.json'):
            try:
                # Read the markers from the file
                with open(file_path, 'r') as json_file:
                    markers = json.load(json_file)

                # Determine game folder name from the file name
                game_folder_name = file.replace('_markers.json', '')
                game_folder_path = os.path.join(clips_folder, game_folder_name)

                # Create a folder for the game if it doesn't exist
                os.makedirs(game_folder_path, exist_ok=True)

                for idx, marker in enumerate(markers, start=1):

                    num_markers = len(markers)

                    marker_id = marker.get('marker_id', f'marker_{idx}')
                    video_id = marker.get('video_id')
                    video_file_name = marker.get('video_file')
                    
                    # Skip if video_file_name is missing or None
                    if not video_file_name:
                        continue

                    #check if the downloaded fiel exists in the stream files folder, if not skip the marker
                    if (not getDownloadedVideo(script_dir, os.path.join(script_dir, "_stream_files"), video_file_name)):
                        continue

                    game_folder = marker.get('game_folder')
                    game_name = game_folder.replace(':', '').replace("_","-")

                    idx_padded = f"{idx:03d}"  # Format index as two digits (01, 02, ..., 10, 11, ...)

                    marker_file_name = f'{idx_padded}_{game_name}_{marker_id}_{video_id}.mp4'
                    marker_file_name_tiktok = f'{idx_padded}_{game_name}_{marker_id}_{video_id}_tiktok.mp4'

                    pre_seconds_start = marker.get('position_pre')
                    post_seconds_end = marker.get('position_post')

                    # Create clips only if the video file exists
                    horizontal = "horizontal"
                    vertical = "vertical"
                    
                    create_individual_video_clip(video_file_name, marker_file_name, game_folder, pre_seconds_start, post_seconds_end, horizontal, idx_padded, num_markers)
                    create_individual_video_clip_for_tiktok(video_file_name, marker_file_name_tiktok, game_folder, pre_seconds_start, post_seconds_end, vertical, idx_padded, num_markers)
                    write_video_id_to_file(script_dir, video_id)
                #print(f"Markers for '{game_folder_name}' written to '{game_folder_path}'")

            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error reading '{file_path}': {e}")
            except Exception as e:
                print(f"Unexpected error with '{file_path}': {e}")


def create_individual_video_clip(input_file_name,output_file_name, game_folder, start_seconds, end_seconds , orientation , index , num_markers):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """

    video_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    input_file_path = os.path.join(video_folder_dir, input_file_name)

    clips_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips")

    individual_folder = os.path.join(clips_folder_dir, game_folder, "individuales")
    # Create a folder for the game if it doesn't exist
    os.makedirs(individual_folder, exist_ok=True)

    # Define full file path
    file_path = os.path.join(individual_folder, output_file_name)

    # Calculate clip duration
    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None

    if not os.path.exists(input_file_path):
        #print(f"Warning: Input file does not exist: {input_file_path}")
        return None

    # FFmpeg command to extract the clip
    ffmpeg_cmd = [
        'ffmpeg',
        '-loglevel', 'error',  # Show only errors
        '-n',  # Do not overwrite existing files
        '-ss', str(start_seconds),
        '-i', input_file_path,
        '-t', str(duration),
        '-c:v', 'libx264',  # Re-encode video
        '-preset', 'fast',  # Set encoding speed/quality
        '-crf', '23',       # Constant rate factor (quality)
        '-c:a', 'aac',      # Re-encode audio
        '-b:a', '192k',     # Audio bitrate
        file_path
    ]

    try:

        # Run the FFmpeg command
        output_file = ffmpeg_cmd[-1]
        if not os.path.exists(output_file):
            print(f'Generando clip {orientation} {index} de {num_markers}')
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Clip creado {orientation} {index} de {num_markers} en {file_path}")
            return file_path
        else:
            #print(f"Clip already exists: {file_path}")
            return file_path
    except subprocess.CalledProcessError as e:
        print(f"Error creating clip: {e}")
        return None



def create_individual_video_clip_for_tiktok(input_file_name,output_file_name, game_folder, start_seconds, end_seconds , orientation , index , num_markers):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """

    video_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    input_file_path = os.path.join(video_folder_dir, input_file_name)

    logo1_file_path = os.path.join(video_folder_dir,"twitchlogo.png")
    logo2_file_path = os.path.join(video_folder_dir,"sito.jpeg")

    clips_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips")

    tiktok_folder = os.path.join(clips_folder_dir, game_folder, "tiktok")
    # Create a folder for the game if it doesn't exist
    os.makedirs(tiktok_folder, exist_ok=True)

    # Define full file path
    file_path = os.path.join(tiktok_folder, output_file_name)

    # Calculate clip duration
    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None
    
    if not os.path.exists(input_file_path):
        #print(f"Warning: Input file does not exist: {input_file_path}")
        return None
    
    # Define crop and scale parameters for camera and game feed
    # camera_crop = "crop=400:300:50:50,scale=1080:960"
    # game_crop = "crop=1280:720:0:400,scale=1080:960"


    # camera_crop = "crop=400:300:50:50,scale=270:202"
    # game_crop_black_bars_top_bottom = "crop=1280:720:0:0,scale=1080:1920"
    # game_crop = "crop=720:1280:280:0,scale=1080:1920"
    # game_crop = "scale=1080:1920:force_original_aspect_ratio=decrease,crop=1080:1920"
    # overlay_position = "main_w-overlay_w-10:main_h-overlay_h-10"

    camera_width = 250
    camera_height = 50
    #camera_crop = "crop=400:250:50:440,scale=450:337,format=rgba," \
    #          "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gte(sqrt((X-225)*(X-225)+(Y-168)*(Y-168)),150),255,0)'"
    # original camera_crop = "crop=400:300:50:50,scale=270:202"
    # Adjust the game feed to cover the full vertical area and position the camera as picture-in-picture in the top right
    game_crop = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    camera_top_default = 440
    camera_left_default = 50

    camara_params = get_camera_params("camara.json")
    camara_top = camara_params["camara_arriba"]
    camara_left = camara_params["camara_izquierda"]

    print(camara_params)

    camara_top_final = camera_top_default + camara_top
    camara_left_final = camera_left_default + camara_left

    # camara_top_final_str = camara_top_final.to_string()
    # camara_left_final_str = camara_left_final.to_string()   

    #camera_crop = "crop=400:250:50:440,scale=270:202"
    # camera_crop = "crop=400:250:50:440,scale=450:337"
    camera_crop = f"crop=400:250:{camara_left_final}:{camara_top_final},scale=450:337"
    print(camera_crop)
    
    overlay_position = "main_w-overlay_w-10:10"


    ffmpeg_cmd = [
    'ffmpeg',
    '-loglevel', 'error',  # Show only errors
    '-n',  # Do not overwrite existing files
    '-ss', str(start_seconds),
    '-i', input_file_path,  # Main video input
    # '-i', logo1_file_path,  # First logo input
    # '-i', logo2_file_path,  # Second logo input
    '-t', str(duration),
    # '-filter_complex',
    # (
    #     # f"[0:v]{game_crop}[game];"
    #     # f"[0:v]{camera_crop},format=rgba[cam];"  # Ensure the camera is in rgba format for transparency
        
    #     # # Create a larger circular alpha mask (Increased circle size)
    #     # f"[cam]split[cam][mask];"
    #     # f"[mask]geq='if(lt(sqrt((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2)),W/2),255,0)'[masked];"  # Increased the radius to W/2
        
    #     # # Apply the mask to the camera feed
    #     # f"[cam][masked]alphamerge[masked_camera];"
        
    #     # # Combine the game and masked camera
    #     # f"[game][masked_camera]overlay={overlay_position}[base];"
        
    #     # # Scale logos
    #     # f"[1:v]scale=30:30[logo1_scaled];"
    #     # f"[2:v]scale=29:29[logo2_scaled];"
        
    #     # # Position logos
    #     # f"[base][logo1_scaled]overlay=615:H-h-1540[logo1];"
    #     # f"[logo1][logo2_scaled]overlay=1020:H-h-1540[v];"
        
    #     # # Add text overlay
    #     # f"[v]drawtext=fontfile='C\\:/Windows/Fonts/calibrib.ttf':text='WWW.TWITCH.TV/MDESITO':fontcolor=purple:fontsize=32:"
    #     # f"box=1:boxcolor=white@0.5:x=W-tw-60:y=350:shadowcolor=white:shadowx=2:shadowy=2[v]"
    # ),
    # '-map', '[v]',
    # '-map', '0:a',
    '-c:v', 'libx264',  # H.264 encoding for video
    '-preset', 'fast',
    '-crf', '23',
    '-c:a', 'aac',  # AAC encoding for audio
    '-b:a', '192k',
    '-pix_fmt', 'yuv420p',  # Ensures compatibility for TikTok
    '-movflags', '+faststart',  # Ensure quick playback start
    file_path
]

    try:
        # Run the FFmpeg command
        output_file = ffmpeg_cmd[-1]
        if not os.path.exists(output_file):

            print(f'Generando clip {orientation} {index} de {num_markers}')
            subprocess.run(ffmpeg_cmd, check=True)
            print(f"Clip creado {orientation} {index} de {num_markers} en {file_path}")
            return file_path

        else:
            #print(f"Clip already exists: {file_path}")
            return file_path
    except subprocess.CalledProcessError as e:
        print(f"Error creating clip: {e}")
        return None


def create_video_clip_cut(input_file_name,output_file_name, start_seconds, end_seconds , orientation , index , num_markers):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """

    video_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    input_file_path = os.path.join(video_folder_dir, input_file_name)

    clips_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips_cortados")

    individual_folder = os.path.join(clips_folder_dir, "horizontal")
    # Create a folder for the game if it doesn't exist
    os.makedirs(individual_folder, exist_ok=True)

    # Define full file path
    file_path = os.path.join(individual_folder, output_file_name)
    print('cortando.... ' , file_path)

    # Calculate clip duration
    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None

    if not os.path.exists(input_file_path):
        #print(f"Warning: Input file does not exist: {input_file_path}")
        return None

    # FFmpeg command to extract the clip
    ffmpeg_cmd = [
        'ffmpeg',
        '-loglevel', 'error',  # Show only errors
        '-y', 
        '-ss', str(start_seconds),
        '-i', input_file_path,
        '-t', str(duration),
        '-c:v', 'libx264',  # Re-encode video
        '-preset', 'fast',  # Set encoding speed/quality
        '-crf', '23',       # Constant rate factor (quality)
        '-c:a', 'aac',      # Re-encode audio
        '-b:a', '192k',     # Audio bitrate
        file_path
    ]

    try:
        print(f'Generando clip {orientation} {index} de {num_markers}')
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Clip creado {orientation} {index} de {num_markers} en {file_path}")
        return file_path

    except subprocess.CalledProcessError as e:
        print(f"Error creating clip: {e}")
        return None
    

def create_video_clip_cut_cortar_clips_page(input_file_name,output_file_name, start_seconds, end_seconds , orientation , index , num_markers):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """
    #print('input filename ' , input_file_name)
    video_folder_dir = os.path.join(os.getcwd(), "_stream_files")
    #print('video_dir' , video_folder_dir)
    input_file_path = os.path.join(video_folder_dir, input_file_name)
    #print('input file path ' , input_file_path)

    clips_folder_dir = os.path.join(os.getcwd(), "clips_cortados")

    individual_folder = os.path.join(clips_folder_dir, "horizontal")
    # Create a folder for the game if it doesn't exist
    os.makedirs(individual_folder, exist_ok=True)

    # Define full file path
    file_path = os.path.join(individual_folder, output_file_name)
    print('cortando.... ' , file_path)

    # Calculate clip duration
    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None

    if not os.path.exists(input_file_path):
        print(f"Warning: Input file does not exist: {input_file_path}")
        return None

    # FFmpeg command to extract the clip
    ffmpeg_cmd = [
        'ffmpeg',
        '-loglevel', 'error',  # Show only errors
        '-y', 
        '-ss', str(start_seconds),
        '-i', input_file_path,
        '-t', str(duration),
        '-c:v', 'libx264',  # Re-encode video
        '-preset', 'fast',  # Set encoding speed/quality
        '-crf', '23',       # Constant rate factor (quality)
        '-c:a', 'aac',      # Re-encode audio
        '-b:a', '192k',     # Audio bitrate
        file_path
    ]
    print(ffmpeg_cmd)

    try:
        print(f'Generando clip {orientation} {index} de {num_markers}')
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Clip creado {orientation} {index} de {num_markers} en {file_path}")
        return file_path

    except subprocess.CalledProcessError as e:
        print(f"Error creating clip: {e}")
        return None


def create_video_clip_cut_tiktok(input_file_name,output_file_name, start_seconds, end_seconds , orientation , index , num_markers):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """

    video_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    input_file_path = os.path.join(video_folder_dir, input_file_name)

    logo1_file_path = os.path.join(video_folder_dir,"twitchlogo.png")
    logo2_file_path = os.path.join(video_folder_dir,"sito.jpeg")

    clips_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips_cortados")

    tiktok_folder = os.path.join(clips_folder_dir, "vertical")
    # Create a folder for the game if it doesn't exist
    os.makedirs(tiktok_folder, exist_ok=True)

    # Define full file path
    file_path = os.path.join(tiktok_folder, output_file_name)

    # Calculate clip duration
    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None
    
    if not os.path.exists(input_file_path):
        #print(f"Warning: Input file does not exist: {input_file_path}")
        return None
    

    camera_width = 250
    camera_height = 50
    # Adjust the game feed to cover the full vertical area and position the camera as picture-in-picture in the top right
    game_crop = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    #camera_crop = "crop=400:250:50:440,scale=270:202"
    camera_crop = "crop=400:250:50:440,scale=450:337"

    
    overlay_position = "main_w-overlay_w-10:10"

    ffmpeg_cmd = [
        'ffmpeg',
        '-loglevel', 'error',  # Show only errors
        '-y',  # Do not overwrite existing files
        '-ss', str(start_seconds),
        '-i', input_file_path,  # Main video input
        # '-i', logo1_file_path,  # First logo input
        # '-i', logo2_file_path,  # Second logo input
        '-t', str(duration),
        # '-filter_complex',
        # (
        #     f"[0:v]{game_crop}[game];"
        #     f"[0:v]{camera_crop},format=rgba[cam];"  # Ensure the camera is in rgba format for transparency
            
        #     # Create a larger circular alpha mask (Increased circle size)
        #     f"[cam]split[cam][mask];"
        #     f"[mask]geq='if(lt(sqrt((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2)),W/2),255,0)'[masked];"  # Increased the radius to W/2
            
        #     # Apply the mask to the camera feed
        #     f"[cam][masked]alphamerge[masked_camera];"
            
        #     # Combine the game and masked camera
        #     f"[game][masked_camera]overlay={overlay_position}[base];"
            
        #     # Scale logos
        #     f"[1:v]scale=30:30[logo1_scaled];"
        #     f"[2:v]scale=29:29[logo2_scaled];"
            
        #     # Position logos
        #     f"[base][logo1_scaled]overlay=615:H-h-1540[logo1];"
        #     f"[logo1][logo2_scaled]overlay=1020:H-h-1540[v];"
            
        #     # Add text overlay
        #     f"[v]drawtext=fontfile='C\\:/Windows/Fonts/calibrib.ttf':text='WWW.TWITCH.TV/MDESITO':fontcolor=purple:fontsize=32:"
        #     f"box=1:boxcolor=white@0.5:x=W-tw-60:y=350:shadowcolor=white:shadowx=2:shadowy=2[v]"
        # ),
        # '-map', '[v]',
        # '-map', '0:a',
        '-c:v', 'libx264',  # Re-encode to maintain sync
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        file_path
    ]

    try:
        print(f'Generando clip {orientation} {index} de {num_markers}')
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Clip creado {orientation} {index} de {num_markers} en {file_path}")
        return file_path

    except subprocess.CalledProcessError as e:
        print(f"Error creating clip: {e}")
        return None



def create_video_clip_cut_tiktok_cortar_clips_page(input_file_name,output_file_name, start_seconds, end_seconds , orientation , index , num_markers):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """

    video_folder_dir = os.path.join(os.getcwd(), "_stream_files")
    input_file_path = os.path.join(video_folder_dir, input_file_name)

    logo1_file_path = os.path.join(video_folder_dir,"twitchlogo.png")
    logo2_file_path = os.path.join(video_folder_dir,"sito.jpeg")

    clips_folder_dir = os.path.join(os.getcwd(), "clips_cortados")

    tiktok_folder = os.path.join(clips_folder_dir, "vertical")
    # Create a folder for the game if it doesn't exist
    os.makedirs(tiktok_folder, exist_ok=True)

    # Define full file path
    file_path = os.path.join(tiktok_folder, output_file_name)

    # Calculate clip duration
    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None
    
    if not os.path.exists(input_file_path):
        #print(f"Warning: Input file does not exist: {input_file_path}")
        return None
    

    camera_width = 250
    camera_height = 50
    # Adjust the game feed to cover the full vertical area and position the camera as picture-in-picture in the top right
    game_crop = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    #camera_crop = "crop=400:250:50:440,scale=270:202"
    camera_crop = "crop=400:250:50:440,scale=450:337"

    
    overlay_position = "main_w-overlay_w-10:10"

    ffmpeg_cmd = [
        'ffmpeg',
        '-loglevel', 'error',  # Show only errors
        '-y',  # Do not overwrite existing files
        '-ss', str(start_seconds),
        '-i', input_file_path,  # Main video input
        # '-i', logo1_file_path,  # First logo input
        # '-i', logo2_file_path,  # Second logo input
        '-t', str(duration),
        # '-filter_complex',
        # (
        #     f"[0:v]{game_crop}[game];"
        #     f"[0:v]{camera_crop},format=rgba[cam];"  # Ensure the camera is in rgba format for transparency
            
        #     # Create a larger circular alpha mask (Increased circle size)
        #     f"[cam]split[cam][mask];"
        #     f"[mask]geq='if(lt(sqrt((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2)),W/2),255,0)'[masked];"  # Increased the radius to W/2
            
        #     # Apply the mask to the camera feed
        #     f"[cam][masked]alphamerge[masked_camera];"
            
        #     # Combine the game and masked camera
        #     f"[game][masked_camera]overlay={overlay_position}[base];"
            
        #     # Scale logos
        #     f"[1:v]scale=30:30[logo1_scaled];"
        #     f"[2:v]scale=29:29[logo2_scaled];"
            
        #     # Position logos
        #     f"[base][logo1_scaled]overlay=615:H-h-1540[logo1];"
        #     f"[logo1][logo2_scaled]overlay=1020:H-h-1540[v];"
            
        #     # Add text overlay
        #     f"[v]drawtext=fontfile='C\\:/Windows/Fonts/calibrib.ttf':text='WWW.TWITCH.TV/MDESITO':fontcolor=purple:fontsize=32:"
        #     f"box=1:boxcolor=white@0.5:x=W-tw-60:y=350:shadowcolor=white:shadowx=2:shadowy=2[v]"
        # ),
        # '-map', '[v]',
        # '-map', '0:a',
        '-c:v', 'libx264',  # Re-encode to maintain sync
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        file_path
    ]

    try:
        print(f'Generando clip {orientation} {index} de {num_markers}')
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Clip creado {orientation} {index} de {num_markers} en {file_path}")
        return file_path

    except subprocess.CalledProcessError as e:
        print(f"Error creating clip: {e}")
        return None