import time
from RealtimeSTT import AudioToTextRecorder

if __name__ == "__main__":
    recorder = AudioToTextRecorder(
        model=r"C:\whisper_models\small",
        device="cuda",
        compute_type="float16",
        language="en"
    )

    recorder.start()

    print("Speak now... Press Ctrl+C to stop.\n")

    try:
        while True:
            text = recorder.text()
            if text:
                print("Live:", text)
            time.sleep(0.5)

    except KeyboardInterrupt:
        recorder.stop()
        print("\nStopped.")
