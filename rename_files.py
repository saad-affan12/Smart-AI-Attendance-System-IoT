import os

folders = [
    "dataset_final/real",
    "known_faces"
]

for folder in folders:
    for filename in os.listdir(folder):
        if filename.endswith(".jpg"):
            new_name = filename.replace(".mp4", "")
            
            old_path = os.path.join(folder, filename)
            new_path = os.path.join(folder, new_name)
            
            os.rename(old_path, new_path)

print("✅ Renamed ALL files (real + known_faces)")