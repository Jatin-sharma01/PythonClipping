import json
import os
import datetime

from ffmpegFunctions import create_video_clip_cut_cortar_clips_page, create_video_clip_cut_tiktok_cortar_clips_page , create_video_clip_cut_tiktok, create_video_clip_cut

def write_or_append_video_info(video_infos, file_name="video_info.json"):
    # Ensure the json_data directory exists
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    os.makedirs(json_dir, exist_ok=True)

    file_path = os.path.join(json_dir, file_name)

    # Check if the file exists
    if os.path.exists(file_path):
        # Read the existing data from the file
        with open(file_path, 'r') as json_file:
            try:
                existing_data = json.load(json_file)
            except json.JSONDecodeError:
                existing_data = []

        # Extract existing video_ids to avoid duplicates
        existing_video_ids = {video['video_id'] for video in existing_data}

        # Append only unique video entries
        for video_info in video_infos:
            if video_info['video_id'] not in existing_video_ids:
                existing_data.append(video_info)

        # Write the updated data back to the file
        with open(file_path, 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)

    else:
        # If the file doesn't exist, create it and write the video_infos
        with open(file_path, 'w') as json_file:
            json.dump(video_infos, json_file, indent=4)


def check_video_in_json(script_dir,file_name, video_id):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    file_path = os.path.join(json_dir, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        #print(f"Warning: The file {file_name} does not exist in json_data.")
        return False

    # Read the existing data from the file
    with open(file_path, 'r', encoding="utf-8") as json_file:
        try:
            existing_data = json.load(json_file)
        except json.JSONDecodeError:
            #print(f"Error: {file_name} contains invalid JSON.")
            return False

    # Check if any video in the data has the given video_id
    for video in existing_data:
        if video.get('video_id') == video_id:
            return True  # Video found

    return False  # Video not found


def get_videos_by_ids(file_name, video_ids):
    # Define json_data directory in the project root
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    file_path = os.path.join(json_dir, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        #print(f"Warning: The file {file_name} does not exist in json_data.")
        return []

    # Read the existing data from the file
    with open(file_path, 'r', encoding="utf-8") as json_file:
        try:
            data = json.load(json_file)
        except json.JSONDecodeError:
            #print(f"Error: {file_name} contains invalid JSON.")
            return []

    # Ensure 'data' is a list of video objects
    if not isinstance(data, list):
        #print(f"Error: Expected a list of videos, but got {type(data)}.")
        return []

    # Filter videos by the provided video_ids
    filtered_videos = [video for video in data if 'video_id' in video and video['video_id'] in video_ids]

    return filtered_videos

def add_markers_to_video_data(script_dir , video_file_name, markers_data, output_file_name):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full paths for input and output files
    video_file_path = os.path.join(json_dir, video_file_name)
    output_file_path = os.path.join(json_dir, output_file_name)

    # Step 1: Read the video data from the existing video file
    if os.path.exists(video_file_path):
        with open(video_file_path, 'r', encoding="utf-8") as json_file:
            try:
                video_data = json.load(json_file)
            except json.JSONDecodeError:
                #print(f"Error: {video_file_name} contains invalid JSON.")
                return
    else:
        #print(f"Warning: The file {video_file_name} does not exist in json_data.")
        return
    
    # Step 2: Group markers by video_id
    markers_by_video_id = {}
    for marker in markers_data:
        video_id = marker['video_id']
        if video_id not in markers_by_video_id:
            markers_by_video_id[video_id] = []
        markers_by_video_id[video_id].append(marker)
    
    # Step 3: Add markers to the video data, ensuring no duplicates
    for video in video_data:
        video_id = video['video_id']
        if video_id in markers_by_video_id:
            existing_markers = {m['marker_id'] for m in video.get('markers', [])}
            new_markers = markers_by_video_id[video_id]
            # Add only markers that don't already exist for this video
            for marker in new_markers:
                if marker['marker_id'] not in existing_markers:
                    if 'markers' not in video:
                        video['markers'] = []
                    video['markers'].append(marker)
        else:
            video['markers'] = []  # No markers for this video
    
    # Step 4: Write the updated video data with markers to a new JSON file
    with open(output_file_path, 'w', encoding="utf-8") as output_file:
        json.dump(video_data, output_file, indent=4)

    print(f"Data has been written to {output_file_path}.")
    return output_file_path  # Optional: return the full path for reference

#not need at the moment
def get_videos_by_date(file_name, target_date):
    try:
        # Load JSON data
        with open(file_name, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        # Debug: Print the data type
        print("Raw JSON type:", type(data))

        # Ensure the data is a list
        if not isinstance(data, list):
            #print("Error: JSON data is not a list")
            return []

        # Convert target_date to a datetime object
        target_date_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()

        # Filter videos that match the given date
        filtered_videos = [
            video for video in data
            if 'started_at' in video and
               datetime.datetime.fromisoformat(video['started_at'].split("T")[0]).date() == target_date_obj
        ]

        return filtered_videos

    except FileNotFoundError:
        #print(f"Error: File '{file_name}' not found.")
        return []
    except json.JSONDecodeError:
        #print("Error: Failed to decode JSON. Check if the file is formatted correctly.")
        return []
    except Exception as e:
        #print(f"Unexpected error: {e}")
        return []
    
def write_json_file(file_name, data):
    """Writes data to a JSON file, overwriting if it exists."""
    try:
        with open(file_name, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        print(f"Data successfully written to {file_name}")
    except Exception as e:
        print(f"Error writing to file {file_name}: {e}")

def append_video_name_to_video_file(script_dir, video_durations, video_info_filename):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    json_dir = os.path.join(script_dir, "json_data")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    video_info_path = os.path.join(json_dir, video_info_filename)

    # Check if video info file exists
    if not os.path.exists(video_info_path):
        #print(f"Warning: The file {video_info_filename} does not exist in json_data.")
        return

    # Load video_info JSON data from file
    with open(video_info_path, "r", encoding="utf-8") as file:
        try:
            video_info = json.load(file)
        except json.JSONDecodeError:
            #print(f"Error: {video_info_filename} contains invalid JSON.")
            return

    # Create a lookup dictionary with duration as the key and filename as the value
    duration_lookup = {v: k for k, v in video_durations.items()}

    # Append the matching video file name to video_info
    for video in video_info:
        if video["duration"] in duration_lookup:
            video["video_file"] = duration_lookup[video["duration"]]

    # Save updated data back to the file
    with open(video_info_path, "w", encoding="utf-8") as file:
        json.dump(video_info, file, indent=4)

    #print(f"Updated {video_info_path} with video file names.")

def get_app_params(script_dir, filename):
    # Define json_data directory in the project root
    print("script dir in get app params " , os.path.join(script_dir, "json_data"))
    json_dir = os.path.join(script_dir, "json_data")
    ##json_dir = os.path.join(script_dir, "json_data")
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


def get_app_params3(script_dir, filename):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "json_data")
    json_dir = os.path.join(script_dir, "json_data")
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


def get_video_params(script_dir,filename):
    # Define json_data directory in the project root
    ##json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    json_dir = script_dir
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    video_info_path = os.path.join(json_dir, filename)
    print(video_info_path)

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


def getDownloadedVideos(folder_name):
    # Get list of files in the given folder
    files = [entry.name for entry in os.scandir(folder_name) if entry.is_file() and entry.name.endswith('.mp4')]

    # Filter the downloaded videos based on the provided video IDs
    video_file_array = []
    for file in files:
        videoFilearray = file.split('_')

        # Check if the split array has at least two elements
        if len(videoFilearray) > 1:
            video_file_id = int(videoFilearray[1])
            video_file_array.append(str(video_file_id))
            # You can add your logic for matching the video ID here
            # if video_file_id in videoIds:
            #     Do something
        else:
            print(f"Skipping file {file} due to unexpected format")

    return video_file_array

def getClipsToCut(folder_name):
    # Get list of files in the given folder
    files = [entry.name for entry in os.scandir(folder_name) if entry.is_file() and entry.name.endswith('.mp4')]

    #print(files)
    # Filter the downloaded videos based on the provided video IDs
    id_marcador = 0
    id_directo = 0
    juego = ""
    cortar_principio = 0
    cortar_final = 0

    for file in files:
        if file.endswith('tiktok.mp4'):
            clip = file.split('_')
            id_directo = clip[3]
            id_marcador = clip[2]
            indexNum = clip[0]
            #print(indexNum)
            datos_cortar_clip = get_video_params("datos.json")
            cortar_principio = datos_cortar_clip["cortar_principio"]
            cortar_final = datos_cortar_clip["cortar_fin"]
            juego = clip[1].replace("-","_")
            game_marker_file = juego + "_markers.json"
            print(game_marker_file)
            marker_data = get_marker_in_json(game_marker_file , id_marcador)    
            print(marker_data)
            juego = juego.replace("_", "-")

            video_file_name = marker_data["video_file"]
            marker_file_name = f'{indexNum}_{juego}_{id_marcador}_{id_directo}.mp4'
            marker_file_name_tiktok = f'{indexNum}_{juego}_{id_marcador}_{id_directo}_tiktok.mp4'

            marker_data_principio = marker_data["position_pre"]
            marker_data_final = marker_data["position_post"]
            # print(marker_data_principio)
            # print(marker_data_final)
            
            pre_seconds_start = int(marker_data_principio) - cortar_principio
            post_seconds_end = int(marker_data_final) + cortar_final
            print(pre_seconds_start)
            print(post_seconds_end)


            create_video_clip_cut(video_file_name, marker_file_name, pre_seconds_start, post_seconds_end, 'horizontal', indexNum, indexNum)
            create_video_clip_cut_tiktok(video_file_name, marker_file_name_tiktok, pre_seconds_start, post_seconds_end, 'vertical', indexNum, indexNum)

        else:
            clip = file.split('_')
            id_directo = clip[3].split('.')[0]
            id_marcador = clip[2]
            indexNum = clip[0]
            #print("id marcador " + id_marcador)
            #print(indexNum)
            datos_cortar_clip = get_video_params("datos.json")
            cortar_principio = datos_cortar_clip["cortar_principio"]
            cortar_final = datos_cortar_clip["cortar_fin"]
            juego = clip[1].replace("-","_")
            #print("juego " + juego)
            game_marker_file = juego + "_markers.json"
            #print(game_marker_file)
            marker_data = get_marker_in_json(game_marker_file , id_marcador)    
            #print(marker_data)
            juego = juego.replace("_", "-")

            video_file_name = marker_data["video_file"]
            marker_file_name = f'{indexNum}_{juego}_{id_marcador}_{id_directo}.mp4'
            marker_file_name_tiktok = f'{indexNum}_{juego}_{id_marcador}_{id_directo}_tiktok.mp4'

            marker_data_principio = marker_data["position_pre"]
            marker_data_final = marker_data["position_post"]
            # print(marker_data_principio)
            # print(marker_data_final)
            
            pre_seconds_start = int(marker_data_principio) - cortar_principio
            post_seconds_end = int(marker_data_final) + cortar_final
            print(pre_seconds_start)
            print(post_seconds_end)

            create_video_clip_cut(video_file_name, marker_file_name, pre_seconds_start, post_seconds_end, 'horizontal', indexNum, indexNum)
            create_video_clip_cut_tiktok(video_file_name, marker_file_name_tiktok, pre_seconds_start, post_seconds_end, 'vertical', indexNum, indexNum)

    return files

def get_marker_in_json(file_name, marker_id):
    # Define json_data directory in the project root
    json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_game_marker_files")
    os.makedirs(json_dir, exist_ok=True)  # Ensure the directory exists

    # Construct full file path
    file_path = os.path.join(json_dir, file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        #print(f"Warning: The file {file_name} does not exist in json_data.")
        return False

    # Read the existing data from the file
    with open(file_path, 'r', encoding="utf-8") as json_file:
        try:
            existing_data = json.load(json_file)
        except json.JSONDecodeError:
            #print(f"Error: {file_name} contains invalid JSON.")
            return False

    # Check if any video in the data has the given video_id
    for marker in existing_data:
        if marker.get('marker_id') == marker_id:
            return marker  # Video found

    return False  # V


def getClipsToCutFromTreeview(treeview , treeview2 , tk):
    
    #print(files)
    # Filter the downloaded videos based on the provided video IDs
    id_marcador = 0
    id_directo = 0
    juego = ""
    cortar_principio = 0
    cortar_final = 0

    individual_clipfile = ""
    tiktok_file = ""

    #clear treeview2 
    treeview2.delete(*treeview2.get_children())

    for item in treeview.get_children():
        item_data = treeview.item(item)
        clip_path = item_data["values"][0]



        add_start = item_data["values"][1]
        remove_start = item_data["values"][2]
        add_end = item_data["values"][3]
        remove_end = item_data["values"][4]

        if(add_start > 0):
            cortar_principio = add_start
        
        if(remove_start > 0):
            cortar_principio = -remove_start

        if(add_end > 0):
            cortar_final = add_end

        if(remove_end > 0):
            cortar_final = -remove_end

        if clip_path.endswith('tiktok.mp4'):
            clip_parse = clip_path.split('\\')
            last_index = len(clip_parse)
            clip_path = clip_parse[last_index - 1]
            clip = clip_path.split('_')
            #print("a " , clip)
            id_directo = clip[3]
            #print("b " ,  id_directo)
            id_marcador = clip[2]
            #print("c" , id_marcador)
            indexNum = clip[0]
            #print("d" , indexNum)
            
            
            #print(indexNum)
            # datos_cortar_clip = get_video_params("datos.json")
            # cortar_principio = datos_cortar_clip["cortar_principio"]
            # cortar_final = datos_cortar_clip["cortar_fin"]
            
            
            juego = clip[1].replace("-","_")
            game_marker_file = juego + "_markers.json"
            #print(game_marker_file)
            marker_data = get_marker_in_json(game_marker_file , id_marcador)    
            #print(marker_data)
            juego = juego.replace("_", "-")

            video_file_name = marker_data["video_file"]
            #print(video_file_name)
            marker_file_name = f'{indexNum}_{juego}_{id_marcador}_{id_directo}.mp4'

            marker_file_name_tiktok = f'{indexNum}_{juego}_{id_marcador}_{id_directo}_tiktok.mp4'

            #print(marker_file_name)
            #print(marker_file_name_tiktok)

            marker_data_principio = marker_data["position_pre"]
            marker_data_final = marker_data["position_post"]
            # print(marker_data_principio)
            # print(marker_data_final)
            
            pre_seconds_start = int(marker_data_principio) - cortar_principio
            post_seconds_end = int(marker_data_final) + cortar_final
            #print(pre_seconds_start)
            #print(post_seconds_end)

            individual_clipfile = create_video_clip_cut_cortar_clips_page(video_file_name, marker_file_name, pre_seconds_start, post_seconds_end, 'horizontal', indexNum, indexNum)
            tiktok_clipfile = create_video_clip_cut_tiktok_cortar_clips_page(video_file_name, marker_file_name_tiktok, pre_seconds_start, post_seconds_end, 'vertical', indexNum, indexNum)
            print('tiktoken' , tiktok_clipfile)
            # individual_clipfile = individual_clipfile.replace("\\/", "\\")
            # tiktok_clipfile = tiktok_clipfile.replace("\\/", "\\")
            safe_path = os.path.normpath(tiktok_clipfile).replace("\\", "/")
            print("Safe path for Treeview:", safe_path)
            treeview2.insert("", tk.END, values=(safe_path,))

        else:
            clip_parse = clip_path.split('\\')
            last_index = len(clip_parse)
            clip_path = clip_parse[last_index - 1]
            clip = clip_path.split('_')
            id_directo = clip[3].split('.')[0]
            id_marcador = clip[2]
            indexNum = clip[0]
            #print("id marcador " + id_marcador)
            #print(indexNum)

            if(add_start > 0):
                cortar_principio = add_start
            
            if(remove_start > 0):
                cortar_principio = -remove_start

            if(add_end > 0):
                cortar_final = add_end

            if(remove_end > 0):
                cortar_final = -remove_end

            juego = clip[1].replace("-","_")
            #print("juego " + juego)
            game_marker_file = juego + "_markers.json"
            #print(game_marker_file)
            marker_data = get_marker_in_json(game_marker_file , id_marcador)    
            print('marker data ' , marker_data)
            juego = juego.replace("_", "-")

            video_file_name = marker_data["video_file"]
            marker_file_name = f'{indexNum}_{juego}_{id_marcador}_{id_directo}.mp4'
            marker_file_name_tiktok = f'{indexNum}_{juego}_{id_marcador}_{id_directo}_tiktok.mp4'

            marker_data_principio = marker_data["position_pre"]
            marker_data_final = marker_data["position_post"]
            # print(marker_data_principio)
            # print(marker_data_final)
            
            pre_seconds_start = int(marker_data_principio) - cortar_principio
            post_seconds_end = int(marker_data_final) + cortar_final
            print(pre_seconds_start)
            print(post_seconds_end)

            individual_clipfile = create_video_clip_cut_cortar_clips_page(video_file_name, marker_file_name, pre_seconds_start, post_seconds_end, 'horizontal', indexNum, indexNum)
            tiktok_clipfile = create_video_clip_cut_tiktok_cortar_clips_page(video_file_name, marker_file_name_tiktok, pre_seconds_start, post_seconds_end, 'vertical', indexNum, indexNum)
            print('individuales' , individual_clipfile)
            safe_path = os.path.normpath(individual_clipfile).replace("\\", "/")
            print("Safe path for Treeview:", safe_path)
            treeview2.insert("", tk.END, values=(safe_path,))

    return
