import os
import json
import subprocess

def divide_items_into_groups(video_markers):
    """
    Divides markers into 5 groups as evenly as possible.

    :param video_markers: List of marker dictionaries.
    :return: List of groups, where each group is a list of markers.
    """
    total_items = len(video_markers)
    base_size = total_items // 5
    remainder = total_items % 5

    groups = []
    start_idx = 0

    for i in range(5):
        group_size = base_size + (1 if i < remainder else 0)
        group = video_markers[start_idx:start_idx + group_size]
        if group:  # Only add non-empty groups
            groups.append(group)
        start_idx += group_size

    return groups


def create_video_clip(video_file_name, output_file_name, start_seconds, end_seconds):
    """
    Creates a video clip from the given video file using FFmpeg.

    :param video_file_path: Path to the original video file.
    :param output_file_name: Desired name for the output clip file.
    :param start_seconds: The start time of the clip in seconds.
    :param end_seconds: The end time of the clip in seconds.
    :return: Path to the created clip if successful, otherwise None.
    """

    video_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    video_file_path = os.path.join(video_folder_dir, video_file_name)

    print('video file path ' + video_file_path)
    print('output file name' + output_file_name)

    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None

    # FFmpeg command to extract the clip
    ffmpeg_cmd = [
        'ffmpeg',
        '-n',                             # Do not overwrite existing files
        '-ss', str(start_seconds),
        '-i', video_file_path,
        '-t', str(duration),
        '-c', 'copy',
        output_file_name
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        #print(f"Clip created: {output_file_name}")
        return output_file_name
    except subprocess.CalledProcessError as e:
        #print(f"Error creating clip: {e}")
        return None



def create_vertical_video_clip(video_file_name, output_file_name, start_seconds, end_seconds):
    """
    Creates a vertical (9:16) video clip from the given video file using FFmpeg for TikTok.

    :param video_file_name: Name of the original video file.
    :param output_file_name: Desired name for the output vertical clip.
    :param start_seconds: Start time of the clip in seconds.
    :param end_seconds: End time of the clip in seconds.
    :return: Path to the created vertical clip if successful, otherwise None.
    """
    
    video_folder_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_stream_files")
    video_file_path = os.path.join(video_folder_dir, video_file_name)

    duration = end_seconds - start_seconds
    if duration <= 0:
        print("End time must be greater than start time.")
        return None

    # FFmpeg command to crop and make the video vertical (9:16 aspect ratio)
    ffmpeg_cmd = [
        'ffmpeg',
        '-n',                             # Do not overwrite existing files
        '-ss', str(start_seconds),
        '-i', video_file_path,
        '-t', str(duration),
        '-vf', "crop=(ih*9/16):ih",       # Crop the video to a vertical 9:16 aspect ratio
        '-c:a', 'copy',                   # Copy audio without re-encoding
        output_file_name
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Vertical clip created: {output_file_name}")
        return output_file_name
    except subprocess.CalledProcessError as e:
        print(f"Error creating vertical clip: {e}")
        return None


def concatenate_clips(clips, output_file_path):
    """
    Concatenates a list of video clips into a single video using FFmpeg.

    :param clips: List of clip file paths to concatenate.
    :param output_file_path: Path for the final concatenated video.
    """
    # Create a temporary text file listing all clips
    list_file_path = "concat_list.txt"
    with open(list_file_path, 'w') as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    # FFmpeg command to concatenate clips
    ffmpeg_cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file_path,
        '-c', 'copy',
        output_file_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"Concatenated video created: {output_file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating clips: {e}")
    finally:
        os.remove(list_file_path)  # Clean up temp file


def write_best_moments_marker_files():
    """
    Reads marker files from the 'output' folder in the root directory,
    groups them into batches of 5, and concatenates the clips into combined videos.

    :return: None
    """
    root_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_game_marker_files")
    clips_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips")

    # Iterate through all marker files in the root folder
    for file in os.listdir(root_folder):
        file_path = os.path.join(root_folder, file)

        if os.path.isfile(file_path) and file.endswith('.json'):
            try:
                # Read markers from file
                with open(file_path, 'r') as json_file:
                    markers = json.load(json_file)

                # Group markers into batches of 5
                groups = divide_items_into_groups(markers)

                # Prepare output folder for game
                game_folder_name = file.replace('_markers.json', '')
                game_folder_path = os.path.join(clips_folder, game_folder_name , "bestmoments")
                os.makedirs(game_folder_path, exist_ok=True)

                # Process each group
                for idx, group in enumerate(groups, start=1):
                    temp_clips = []

                    # Create individual clips for each marker in the group
                    for marker in group:
                        video_file = marker.get('video_file')
                        start_seconds = marker.get('position_pre')
                        end_seconds = marker.get('position_post')
                        marker_id = marker.get('marker_id')

                        temp_clip_path = os.path.join(game_folder_path, f'temp_clip_{marker_id}.mp4')
                        temp_clip_path_tiktok = os.path.join(game_folder_path, f'temp_clip_tiktok_{marker_id}.mp4')
                        clip_path = create_video_clip(video_file, temp_clip_path, start_seconds, end_seconds)
                        clip_path_tiktok = create_vertical_video_clip(video_file, temp_clip_path_tiktok, start_seconds, end_seconds)
                        if clip_path:
                            temp_clips.append(clip_path)

                    # Concatenate clips in the group
                    if temp_clips:
                        output_file = os.path.join(game_folder_path, f'best_moments_group_{idx}.mp4')
                        concatenate_clips(temp_clips, output_file)

                        # Cleanup temporary clips
                        for clip in temp_clips:
                            os.remove(clip)

                print(f"Best moments for '{game_folder_name}' written to '{game_folder_path}'")

            except (FileNotFoundError, json.JSONDecodeError) as e:
                print('test')
                #print(f"Error reading '{file_path}': {e}")
            except Exception as e:
                print('test')
                #print(f"Unexpected error with '{file_path}': {e}")


write_best_moments_marker_files()
