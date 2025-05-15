from pyannote.audio import Pipeline

# Load the pipeline
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=os.environ["HuggingFace_API_KEY"])

# Run diarization on the audio file
diarization = pipeline("Quiet Your Mind & You Will Receive Life-Changing Impulses[z7kLfGkR7gk].wav")

# Option 1: Print the speaker segments
for turn, _, speaker in diarization.itertracks(yield_label=True):
    print(f"Speaker {speaker} speaks from {turn.start:.1f}s to {turn.end:.1f}s")


# Write to RTTM file manually
with open("diarization.rttm", "w") as rttm_file:
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        start = turn.start
        duration = turn.end - turn.start
        # Use a simple identifier; adjust as needed
        line = f"SPEAKER audio_file 1 {start:.3f} {duration:.3f} <NA> <NA> {speaker} <NA>\n"
        rttm_file.write(line)