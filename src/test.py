def divide_items_into_groups(video_markers):
    total_items = len(video_markers)
    base_size = total_items // 5
    remainder = total_items % 5

    groups = []
    start_idx = 0

    for i in range(5):
        group_size = base_size + (1 if i < remainder else 0)
        group = video_markers[start_idx:start_idx + group_size]
        groups.append(group)
        start_idx += group_size

    return groups

# Example usage
video_markers = list(range(28))  # Replace with your actual items
groups = divide_items_into_groups(video_markers)

for idx, group in enumerate(groups, 1):
    print(f"Group {idx}: {group}")

