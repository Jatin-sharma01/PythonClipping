import json
from datetime import datetime, timedelta
import re
import os

def parse_duration(duration):
    match = re.match(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", duration)
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def process_streams(script_dir, input_file):
    # Define json_data directory in the project root
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full input file path
    input_file_path = os.path.join(json_dir, input_file)

    # Check if input file exists
    if not os.path.exists(input_file_path):
        #print(f"Warning: The file {input_file} does not exist in json_data.")
        return

    # Read the input JSON file
    with open(input_file_path, "r", encoding="utf-8") as f:
        try:
            videos = json.load(f)
        except json.JSONDecodeError:
            #print(f"Error: {input_file} contains invalid JSON.")
            return
    
    # Convert start times and compute end times
    for video in videos:
        video["started_at"] = datetime.strptime(video["started_at"], "%Y-%m-%dT%H:%M:%SZ")
        video["end_at"] = video["started_at"] + parse_duration(video["duration"])
        video["child_video_id"] = None  # Default value
        video["parent_video_id"] = None  # Default value for later assignment
    
    # Check for overlapping streams (only one possible child)
    for video in videos:
        end_time = video["end_at"]
        closest_child = None
        min_diff = timedelta(hours=1, minutes=1)  # Slightly more than 1 hour
        
        for other_video in videos:
            if other_video["video_id"] != video["video_id"]:
                start_time = other_video["started_at"]
                diff = start_time - end_time
                
                if timedelta(0) <= diff <= timedelta(hours=1) and diff < min_diff:
                    closest_child = other_video["video_id"]
                    min_diff = diff
                    other_video["parent_video_id"] = video["video_id"]
        
        video["child_video_id"] = closest_child
    
    # Remove temporary fields
    for video in videos:
        video["started_at"] = video["started_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        del video["end_at"]
    
    # Write updated data back to the same file
    with open(input_file_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, indent=4)

    print(f"Updated stream data saved to {input_file_path}.")

# this function gets all videos by date
def query_videos_by_date_from_json(input_file, target_date, output_file):
    # Define json_data directory in the project root
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file paths
    input_file_path = os.path.join(json_dir, input_file)
    output_file_path = os.path.join(json_dir, output_file)

    # Check if input file exists
    if not os.path.exists(input_file_path):
        #print(f"Warning: The file {input_file} does not exist in json_data.")
        return

    # Read the input JSON file
    with open(input_file_path, "r", encoding="utf-8") as f:
        try:
            videos = json.load(f)
        except json.JSONDecodeError:
            #print(f"Error: {input_file} contains invalid JSON.")
            return

    # Convert target_date to a datetime object
    target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    # Find all videos that started on the target date 
    # and all its parent and child data
    filtered_videos = [
        video for video in videos
        if datetime.strptime(video["started_at"], "%Y-%m-%dT%H:%M:%SZ").date() == target_date
    ]

    # Set to track already added stream_ids
    seen_stream_ids = set()
    related_videos = []

    # Function to recursively add related videos (parent and child)
    def add_related_videos(video):
        if video["video_id"] not in seen_stream_ids:
            related_videos.append(video)  # Add to result list
            seen_stream_ids.add(video["video_id"])  # Mark this stream_id as added

            # Check for child stream and add it recursively if not already added
            if video["child_video_id"]:
                child_video = next((v for v in videos if v["video_id"] == video["child_video_id"]), None)
                if child_video:
                    add_related_videos(child_video)

            # Check for parent stream and add it recursively if not already added
            if video["parent_video_id"]:
                parent_video = next((v for v in videos if v["video_id"] == video["parent_video_id"]), None)
                if parent_video:
                    add_related_videos(parent_video)

    # Process all filtered videos and add them and their related ones
    for video in filtered_videos:
        add_related_videos(video)

    # Sort related videos by the 'started_at' field in ascending order
    related_videos.sort(key=lambda v: datetime.strptime(v["started_at"], "%Y-%m-%dT%H:%M:%SZ"))

    # Write the result to a JSON file
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(related_videos, f, indent=4)

    print(f"Results written to {output_file_path}")


def filter_videos_with_markers(script_dir , input_file, output_file):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file paths
    input_file_path = os.path.join(json_dir, input_file)
    output_file_path = os.path.join(json_dir, output_file)

    # Check if input file exists
    if not os.path.exists(input_file_path):
        #print(f"Warning: The file {input_file} does not exist in json_data.")
        return

    # Read the input JSON file
    with open(input_file_path, "r", encoding="utf-8") as f:
        try:
            videos = json.load(f)
        except json.JSONDecodeError:
            #print(f"Error: {input_file} contains invalid JSON.")
            return

    # Filter videos that have markers
    filtered_videos = [video for video in videos if video.get("markers")]

    # Write filtered videos to the output JSON file
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(filtered_videos, f, ensure_ascii=False, indent=4)

    print(f"Filtered videos saved to {output_file}")
    
    