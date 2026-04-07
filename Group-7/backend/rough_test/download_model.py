from huggingface_hub import snapshot_download

print("Downloading model safely...")

snapshot_download(
    repo_id="Systran/faster-whisper-small",
    local_dir=r"C:\whisper_models\small",
    local_dir_use_symlinks=False
)

print("Download complete.")
