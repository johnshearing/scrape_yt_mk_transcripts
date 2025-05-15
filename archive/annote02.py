from pyannote.audio import Pipeline
from collections import defaultdict

# Load the pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=os.environ["HuggingFace_API_KEY"])

# Process the audio file
diarization = pipeline("Quiet Your Mind & You Will Receive Life-Changing Impulses[z7kLfGkR7gk].wav")

# Calculate total speaking time for each speaker
speaker_times = defaultdict(float)
for turn, _, speaker in diarization.itertracks(yield_label=True):
    duration = turn.end - turn.start
    speaker_times[speaker] += duration

# Identify the speaker with the most speaking time
primary_speaker = max(speaker_times, key=speaker_times.get)

# Print to console with "Hicks" label
for turn, _, speaker in diarization.itertracks(yield_label=True):
    label = "Hicks" if speaker == primary_speaker else speaker
    print(f"Speaker {label}: {turn.start:.1f}s - {turn.end:.1f}s")

# Write to RTTM file with "Hicks" label
with open("diarization.rttm", "w") as rttm_file:
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        label = "Hicks" if speaker == primary_speaker else speaker
        start = turn.start
        duration = turn.end - turn.start
        line = f"SPEAKER audio_file 1 {start:.3f} {duration:.3f} <NA> <NA> {label} <NA>\n"
        rttm_file.write(line)