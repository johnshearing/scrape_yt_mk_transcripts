import os
import subprocess

# Path to the folder containing your .wav files
AUDIO_FOLDER = "./temp"
# Path to your static image (used as a video background)
IMAGE_PATH = "_Abraham.jpg"
# Output folder for .mp4 files (it will be created if it doesn't exist)
OUTPUT_FOLDER = "mp4_files"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def convert_wav_to_mp4(wav_path, image_path, output_path):
    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-framerate", "2",
        "-i", image_path,
        "-i", wav_path,
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # 👈 this line is the fix
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"❌ ffmpeg failed for {wav_path}:\n{result.stderr.decode()}")


# Loop through all .wav files in the folder
for filename in os.listdir(AUDIO_FOLDER):
    if filename.endswith(".wav"):
        wav_path = os.path.join(AUDIO_FOLDER, filename)
        output_filename = os.path.splitext(filename)[0] + ".mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        print(f"Converting: {filename} -> {output_filename}")
        convert_wav_to_mp4(wav_path, IMAGE_PATH, output_path)

print("✅ Batch conversion complete.")
