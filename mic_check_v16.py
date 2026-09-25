"""Three-second microphone check. No recording is saved."""

import numpy as np
import sounddevice as sd


def main():
    try:
        device = sd.query_devices(kind="input")
        print("Default input:", device["name"])
        print("Wait half a second, then speak clearly for two seconds.")
        blocks = []

        def callback(indata, frames, time_info, status):
            if status:
                print("Mic status:", status)
            samples = indata.astype(np.float32)
            blocks.append(float(np.sqrt(np.mean(samples * samples))))

        with sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                            blocksize=800, callback=callback):
            sd.sleep(3000)

        if not blocks:
            print("No audio arrived from the microphone.")
            return
        ambient = float(np.median(blocks[:6]))
        threshold = max(70.0, min(550.0, ambient * 2.3 + 35.0))
        print("Ambient level:", round(ambient))
        print("Voice peak:", round(max(blocks)))
        print("Detection threshold:", round(threshold))
        if max(blocks[6:], default=0.0) < threshold:
            print("Voice stayed below the threshold. Check Windows microphone input and level.")
        else:
            print("Microphone captured speech-level sound.")
    except Exception as error:
        print("Microphone check failed:", error)


if __name__ == "__main__":
    main()
