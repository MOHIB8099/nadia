import asyncio
import os
import tempfile
import time

import edge_tts
import numpy as np
import pygame
import sounddevice as sd

from scipy.io.wavfile import write
from faster_whisper import WhisperModel
from personality_v14 import delivery_hint


# ============================================
# SETTINGS
# ============================================

SAMPLE_RATE = 16000
RECORD_SECONDS = 15
MIN_SPEECH_SECONDS = 0.20
# Give a speaker room to pause between words without ending the command.
SILENCE_TO_STOP = 0.90
START_TIMEOUT = 12.0
SPEECH_THRESHOLD = 220.0
ENERGY_INTERVAL = 0.05


def normalize_energy(rms, reference):
    """Convert raw RMS into a smooth 0.0 -> 1.0 GUI value."""
    if reference <= 0:
        return 0.0
    value = float(rms) / float(reference)
    return max(0.0, min(1.0, value))


# ============================================
# SPEECH INPUT
# ============================================

class LocalWhisper:

    def __init__(self, energy_callback=None):

        print("Loading Whisper...")

        self.energy_callback = energy_callback

        self.model = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8"
        )

        print("Whisper ready.")


    def set_energy_callback(self, callback):
        self.energy_callback = callback


    def _send_energy(self, value):
        if self.energy_callback:
            try:
                self.energy_callback(
                    max(0.0, min(1.0, float(value)))
                )
            except Exception:
                pass


    # ========================================
    # GET CURRENT DEFAULT MICROPHONE
    # ========================================

    def get_microphone(self):

        try:

            device_info = sd.query_devices(
                kind="input"
            )

            print(
                "Microphone:",
                device_info["name"]
            )

            # None = Windows current/default mic
            return None

        except Exception as error:

            print(
                "Microphone detection error:",
                error
            )

            return None


    # ========================================
    # LISTEN + REAL MIC ENERGY
    # ========================================

    def listen(self):

        microphone = self.get_microphone()
        print("\nListening... Speak now")

        chunks = []
        speech_chunks = []
        block_seconds = ENERGY_INTERVAL
        blocksize = int(SAMPLE_RATE * block_seconds)

        mic_reference = 3500.0
        speech_started = False
        speech_time = 0.0
        silence_time = 0.0
        started_at = time.monotonic()

        def audio_callback(indata, frames, time_info, status):

            nonlocal speech_started
            nonlocal speech_time
            nonlocal silence_time

            if status:
                print("Audio status:", status)

            chunk = indata.copy()

            samples = chunk.astype(
                np.float32
            ).reshape(-1)

            if samples.size == 0:
                return

            rms = float(
                np.sqrt(
                    np.mean(
                        samples * samples
                    )
                )
            )

            energy = normalize_energy(
                rms,
                mic_reference
            )

            energy = min(
                1.0,
                energy * 1.65
            )

            self._send_energy(
                energy
            )

            # Keep a short pre-roll so the first syllable
            # is not cut off when speech begins.
            chunks.append(chunk)

            max_preroll = max(
                1,
                int(0.50 / block_seconds)
            )

            if not speech_started and len(chunks) > max_preroll:
                chunks.pop(0)

            if rms >= SPEECH_THRESHOLD:

                if not speech_started:
                    speech_started = True
                    speech_chunks.extend(chunks)
                    chunks.clear()

                else:
                    speech_chunks.append(chunk)

                speech_time += block_seconds
                silence_time = 0.0

            elif speech_started:

                speech_chunks.append(chunk)
                silence_time += block_seconds


        try:

            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=microphone,
                blocksize=blocksize,
                callback=audio_callback
            ):

                while True:

                    elapsed = (
                        time.monotonic()
                        - started_at
                    )

                    # No speech yet: keep waiting, but do not
                    # hold the microphone forever.
                    if (
                        not speech_started
                        and elapsed >= START_TIMEOUT
                    ):
                        break

                    # As soon as the user finishes the sentence,
                    # stop recording instead of waiting 6 seconds.
                    if (
                        speech_started
                        and speech_time >= MIN_SPEECH_SECONDS
                        and silence_time >= SILENCE_TO_STOP
                    ):
                        break

                    # Safety limit for a very long question.
                    if elapsed >= RECORD_SECONDS:
                        break

                    time.sleep(
                        0.03
                    )

        except Exception as error:

            self._send_energy(0.0)

            print(
                "Microphone Error:",
                error
            )

            return "", "en"


        self._send_energy(0.0)


        if not speech_started or not speech_chunks:

            print(
                "No voice detected."
            )

            return "", "en"


        audio = np.concatenate(
            speech_chunks,
            axis=0
        )


        audio_level = float(
            np.abs(
                audio.astype(
                    np.float32
                )
            ).mean()
        )

        print(
            "Audio level:",
            round(
                audio_level,
                2
            )
        )


        if audio_level < 70:

            print(
                "No voice detected."
            )

            return "", "en"


        temp_file = os.path.join(
            tempfile.gettempdir(),
            "luna_input_v4.wav"
        )

        write(
            temp_file,
            SAMPLE_RATE,
            audio
        )


        try:

            segments, info = (
                self.model.transcribe(
                    temp_file,
                    beam_size=1,
                    vad_filter=True
                )
            )

            text = " ".join(
                segment.text.strip()
                for segment in segments
            ).strip()

        except Exception as error:

            print(
                "Whisper Error:",
                error
            )

            return "", "en"


        if not text:

            print(
                "No speech recognized."
            )

            return "", "en"


        detected_language = (
            info.language
        )

        if any(
            "\u0980" <= char <= "\u09FF"
            for char in text
        ):
            language = "bn"

        elif any(
            "\u0900" <= char <= "\u097F"
            for char in text
        ):
            language = "hi"

        elif detected_language in [
            "hi",
            "bn",
            "en"
        ]:
            language = detected_language

        else:
            language = "en"


        print(
            "Detected language:",
            language
        )

        print(
            "You:",
            text
        )

        return text, language


# ============================================
# LUNA VOICE OUTPUT
# ============================================

class LunaVoiceOutput:

    def __init__(self, energy_callback=None):

        self.energy_callback = energy_callback

        self.voice_profiles = {
            "Hindi female": "hi-IN-SwaraNeural",
            "Hindi male": "hi-IN-MadhurNeural",
            "English female": "en-IN-NeerjaNeural",
            "English male": "en-IN-PrabhatNeural",
            "Bengali female": "bn-IN-TanishaaNeural",
            "Bengali male": "bn-IN-BashkarNeural",
        }

        # V13 defaults requested by user.
        self.voice_name = "Hindi female"
        self.speech_speed = "Fast"

        # Kept for compatibility with older language-selection code.
        self.hindi_voice = self.voice_profiles["Hindi female"]
        self.bengali_voice = self.voice_profiles["Bengali female"]
        self.english_voice = self.voice_profiles["English female"]


        try:

            if not pygame.mixer.get_init():

                pygame.mixer.init()

            print(
                "Luna audio engine ready."
            )

        except Exception as error:

            print(
                "Audio engine error:",
                error
            )


    def set_energy_callback(self, callback):
        self.energy_callback = callback


    def _send_energy(self, value):
        if self.energy_callback:
            try:
                self.energy_callback(
                    max(0.0, min(1.0, float(value)))
                )
            except Exception:
                pass


    # ========================================
    # DETECT RESPONSE LANGUAGE
    # ========================================

    def detect_language(
        self,
        text
    ):

        if any(
            "\u0980" <= char <= "\u09FF"
            for char in text
        ):

            return "bn"

        if any(
            "\u0900" <= char <= "\u097F"
            for char in text
        ):

            return "hi"

        return "en"


    # ========================================
    # V13 VOICE SETTINGS
    # ========================================

    def set_voice(self, voice_name):
        if voice_name in self.voice_profiles:
            self.voice_name = voice_name

    def set_speed(self, speed):
        if speed in {"Normal", "Fast", "Very fast"}:
            self.speech_speed = speed

    def get_rate(self):
        return {
            "Normal": "+0%",
            "Fast": "+25%",
            "Very fast": "+45%",
        }.get(self.speech_speed, "+25%")


    # ========================================
    # SELECT LUNA VOICE
    # ========================================

    def select_voice(self, text):
        return self.voice_profiles.get(
            self.voice_name,
            "hi-IN-SwaraNeural"
        )


    # ========================================
    # GENERATE SPEECH
    # ========================================

    async def _generate(
        self,
        text,
        selected_voice,
        output_file,
        rate_offset="+0%",
        pitch="+0Hz"
    ):

        base_rate = int(self.get_rate().rstrip("%"))
        offset = int(rate_offset.rstrip("%"))
        effective_rate = max(-30, min(35, base_rate + offset))
        communicate = (
            edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=f"{effective_rate:+d}%",
                pitch=pitch
            )
        )

        await communicate.save(
            output_file
        )


    # ========================================
    # BUILD REAL TTS ENERGY ENVELOPE
    # ========================================

    def _build_energy_envelope(
        self,
        sound
    ):

        try:

            raw = sound.get_raw()

            mixer_info = (
                pygame.mixer.get_init()
            )

            if not mixer_info:
                return []

            frequency, sample_format, channels = (
                mixer_info
            )

            # pygame mixer commonly uses signed 16-bit.
            # Handle 8-bit too as a fallback.
            bits = abs(
                int(sample_format)
            )

            if bits == 16:

                samples = np.frombuffer(
                    raw,
                    dtype=np.int16
                ).astype(np.float32)

                full_scale = 32768.0

            elif bits == 8:

                samples = np.frombuffer(
                    raw,
                    dtype=np.int8
                ).astype(np.float32)

                full_scale = 128.0

            else:

                return []


            if channels > 1:

                usable = (
                    samples.size
                    - samples.size % channels
                )

                samples = (
                    samples[:usable]
                    .reshape(-1, channels)
                    .mean(axis=1)
                )


            window = max(
                1,
                int(
                    frequency
                    * ENERGY_INTERVAL
                )
            )

            energies = []

            for start in range(
                0,
                samples.size,
                window
            ):

                chunk = samples[
                    start:start + window
                ]

                if chunk.size == 0:
                    continue

                rms = float(
                    np.sqrt(
                        np.mean(
                            chunk * chunk
                        )
                    )
                )

                normalized = (
                    rms
                    / full_scale
                )

                # TTS speech RMS is usually well below full scale.
                # Boost for a useful visual 0..1 range.
                energy = min(
                    1.0,
                    normalized * 7.0
                )

                energies.append(
                    energy
                )


            return energies

        except Exception as error:

            print(
                "TTS energy analysis error:",
                error
            )

            return []


    # ========================================
    # PLAY AUDIO + REAL OUTPUT ENERGY
    # ========================================

    def play_audio(
        self,
        audio_file
    ):

        try:

            # Sound lets us access decoded PCM bytes.
            sound = pygame.mixer.Sound(
                audio_file
            )

            envelope = (
                self._build_energy_envelope(
                    sound
                )
            )

            channel = sound.play()

            if channel is None:

                raise RuntimeError(
                    "Could not start Luna audio playback."
                )


            index = 0

            while channel.get_busy():

                if envelope:

                    if index < len(
                        envelope
                    ):

                        energy = (
                            envelope[index]
                        )

                    else:

                        energy = 0.0

                else:

                    # Fallback only if this pygame build
                    # cannot expose MP3 PCM data.
                    energy = 0.45

                self._send_energy(
                    energy
                )

                index += 1

                time.sleep(
                    ENERGY_INTERVAL
                )


            self._send_energy(
                0.0
            )


        except Exception as error:

            self._send_energy(0.0)

            print(
                "Audio playback error:",
                error
            )

            # Compatibility fallback: preserve speech
            # even if Sound() cannot decode MP3.
            try:

                pygame.mixer.music.load(
                    audio_file
                )

                pygame.mixer.music.play()

                while (
                    pygame.mixer.music.get_busy()
                ):

                    self._send_energy(
                        0.45
                    )

                    time.sleep(
                        ENERGY_INTERVAL
                    )

                pygame.mixer.music.unload()

            except Exception as fallback_error:

                print(
                    "Fallback playback error:",
                    fallback_error
                )

            finally:

                self._send_energy(
                    0.0
                )


    # ========================================
    # SPEAK
    # ========================================

    def speak(
        self,
        text
    ):

        selected_voice = (
            self.select_voice(
                text
            )
        )

        print(
            "Selected voice:",
            selected_voice
        )

        audio_file = os.path.join(
            tempfile.gettempdir(),
            "luna_voice_v14_%s_%s.mp3" % (os.getpid(), __import__("threading").get_ident())
        )


        rate_offset, pitch = delivery_hint(text)
        asyncio.run(
            self._generate(
                text,
                selected_voice,
                audio_file,
                rate_offset,
                pitch
            )
        )


        self.play_audio(
            audio_file
        )


        try:

            if os.path.exists(
                audio_file
            ):

                os.remove(
                    audio_file
                )

        except Exception:

            pass
