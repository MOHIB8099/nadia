import tkinter as tk
from tkinter import scrolledtext
import threading
import math
import random
import time

import ollama

from voice_v13 import LocalWhisper, LunaVoiceOutput
from memory import LunaMemory
from actions_v13 import execute_action, get_due_reminders


# ============================================
# SETTINGS
# ============================================

MODEL = "llama3"


# ============================================
# LUNA DESKTOP APPLICATION
# ============================================

class LunaApp:

    def __init__(self, root):

        self.root = root

        self.root.title("LUNA AI")

        self.root.geometry("1380x820")
        self.root.minsize(1100, 680)

        self.root.configure(bg="#02070D")

        # ------------------------------------
        # LUNA SYSTEMS
        # ------------------------------------

        self.memory = LunaMemory()

        self.listener = None

        # Real audio energy from microphone / Luna TTS.
        # Range: 0.0 -> 1.0
        self.real_audio_energy = 0.0

        self.voice = LunaVoiceOutput(
            energy_callback=self.update_audio_energy
        )

        # V13 default voice settings
        self.voice_choice = tk.StringVar(value="Hindi female")
        self.speed_choice = tk.StringVar(value="Fast")

        # ------------------------------------
        # STATE
        # ------------------------------------

        self.state = "READY"

        self.angle = 0
        self.angle2 = 0
        self.angle3 = 0

        self.pulse = 0
        self.wave_phase = 0.0
        self.energy_level = 0.12
        self.target_energy = 0.12
        self.scanner_phase = 0.0

        self.busy = False
        self.continuous_voice = False

        # Random particles
        self.particles = []

        for _ in range(45):

            self.particles.append(
                {
                    "angle": random.uniform(
                        0,
                        math.pi * 2
                    ),

                    "radius": random.uniform(
                        80,
                        175
                    ),

                    "speed": random.uniform(
                        0.002,
                        0.012
                    ),

                    "size": random.uniform(
                        1,
                        3
                    )
                }
            )

        self.build_interface()

        self.animate_core()

        self.add_message(
            "LUNA",
            "System online. Luna is ready."
        )


    # ========================================
    # INTERFACE
    # ========================================

    def build_interface(self):

        # ====================================
        # TOP HUD
        # ====================================

        top = tk.Frame(self.root, bg="#02070D", height=74)
        top.pack(fill="x", padx=18, pady=(12, 6))
        top.pack_propagate(False)

        brand = tk.Frame(top, bg="#02070D")
        brand.pack(side="left", fill="y")

        tk.Label(
            brand,
            text="L U N A",
            font=("Segoe UI", 25, "bold"),
            bg="#02070D",
            fg="#00E5FF"
        ).pack(anchor="w")

        tk.Label(
            brand,
            text="LOCAL INTELLIGENT ASSISTANT // NEURAL INTERFACE V2",
            font=("Consolas", 8),
            bg="#02070D",
            fg="#4C7784"
        ).pack(anchor="w", pady=(1, 0))

        self.top_status = tk.Label(
            top,
            text="SYSTEM ONLINE  ●",
            font=("Consolas", 10, "bold"),
            bg="#02070D",
            fg="#00E5FF"
        )
        self.top_status.pack(side="right", padx=10)

        # ====================================
        # MAIN SHELL
        # ====================================

        shell = tk.Frame(self.root, bg="#02070D")
        shell.pack(fill="both", expand=True, padx=18, pady=(0, 16))

        # ---------- LEFT NAV ----------
        nav = tk.Frame(
            shell,
            width=170,
            bg="#04101A",
            highlightbackground="#0B3948",
            highlightthickness=1
        )
        nav.pack(side="left", fill="y", padx=(0, 10))
        nav.pack_propagate(False)

        tk.Label(
            nav,
            text="LUNA // CORE",
            font=("Consolas", 11, "bold"),
            bg="#04101A",
            fg="#00E5FF"
        ).pack(anchor="w", padx=16, pady=(18, 18))

        for label in [
            "◈  HOME",
            "◉  CHAT",
            "◌  VOICE",
            "⌁  ACTIONS",
            "◇  MEMORY",
            "⚙  TOOLS",
            "≡  SETTINGS"
        ]:
            active = label.endswith("HOME")
            button = tk.Label(
                nav,
                text=label,
                font=("Consolas", 10, "bold" if active else "normal"),
                bg="#082330" if active else "#04101A",
                fg="#00E5FF" if active else "#638A96",
                anchor="w",
                padx=14,
                pady=10
            )
            button.pack(fill="x", padx=8, pady=2)

        tk.Frame(nav, bg="#0B3948", height=1).pack(fill="x", padx=14, pady=14)

        self.nav_state = tk.Label(
            nav,
            text="● CORE LINKED\n● VOICE READY\n● MEMORY READY\n● OLLAMA READY",
            justify="left",
            font=("Consolas", 8),
            bg="#04101A",
            fg="#3F8C99"
        )
        self.nav_state.pack(anchor="w", padx=16)

        # V13 // VOICE SETTINGS
        voice_settings = tk.Frame(nav, bg="#04101A")
        voice_settings.pack(fill="x", padx=12, pady=(14, 0))

        tk.Label(
            voice_settings,
            text="VOICE // PROFILE",
            font=("Consolas", 7, "bold"),
            bg="#04101A",
            fg="#4C7784"
        ).pack(anchor="w")

        voice_menu = tk.OptionMenu(
            voice_settings,
            self.voice_choice,
            "Hindi female",
            "Hindi male",
            "English female",
            "English male",
            "Bengali female",
            "Bengali male",
            command=self.change_voice
        )
        voice_menu.config(
            bg="#082330", fg="#00E5FF",
            activebackground="#0C4051",
            activeforeground="white",
            relief="flat",
            font=("Consolas", 8),
            highlightthickness=0
        )
        voice_menu["menu"].config(
            bg="#082330", fg="white",
            font=("Consolas", 8)
        )
        voice_menu.pack(fill="x", pady=(3, 8))

        tk.Label(
            voice_settings,
            text="SPEECH // SPEED",
            font=("Consolas", 7, "bold"),
            bg="#04101A",
            fg="#4C7784"
        ).pack(anchor="w")

        speed_menu = tk.OptionMenu(
            voice_settings,
            self.speed_choice,
            "Normal",
            "Fast",
            "Very fast",
            command=self.change_speed
        )
        speed_menu.config(
            bg="#082330", fg="#00E5FF",
            activebackground="#0C4051",
            activeforeground="white",
            relief="flat",
            font=("Consolas", 8),
            highlightthickness=0
        )
        speed_menu["menu"].config(
            bg="#082330", fg="white",
            font=("Consolas", 8)
        )
        speed_menu.pack(fill="x", pady=(3, 0))

        tk.Label(
            nav,
            text="LUNA OS\nNEURAL BUILD 2.0",
            justify="left",
            font=("Consolas", 7),
            bg="#04101A",
            fg="#31535D"
        ).pack(side="bottom", anchor="w", padx=16, pady=18)

        # ---------- CENTER CORE ----------
        center = tk.Frame(
            shell,
            bg="#06111C",
            highlightbackground="#0C4051",
            highlightthickness=1
        )
        center.pack(side="left", fill="both", expand=True, padx=(0, 10))

        center_head = tk.Frame(center, bg="#06111C")
        center_head.pack(fill="x", padx=14, pady=(12, 0))

        tk.Label(
            center_head,
            text="NEURAL CORE",
            font=("Consolas", 10, "bold"),
            bg="#06111C",
            fg="#00E5FF"
        ).pack(side="left")

        self.status_label = tk.Label(
            center_head,
            text="● READY",
            font=("Consolas", 10, "bold"),
            bg="#06111C",
            fg="#00E5FF"
        )
        self.status_label.pack(side="right")

        self.canvas = tk.Canvas(
            center,
            bg="#06111C",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # ---------- RIGHT CHAT ----------
        right = tk.Frame(
            shell,
            width=410,
            bg="#06111C",
            highlightbackground="#0C4051",
            highlightthickness=1
        )
        right.pack(side="right", fill="both")
        right.pack_propagate(False)

        chat_header = tk.Frame(right, bg="#06111C")
        chat_header.pack(fill="x", padx=14, pady=(14, 8))

        tk.Label(
            chat_header,
            text="CONVERSATION STREAM",
            font=("Consolas", 10, "bold"),
            bg="#06111C",
            fg="#00E5FF"
        ).pack(side="left")

        tk.Label(
            chat_header,
            text="ENCRYPTED // LOCAL",
            font=("Consolas", 7),
            bg="#06111C",
            fg="#3F6975"
        ).pack(side="right")

        self.chat_box = scrolledtext.ScrolledText(
            right,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg="#02070D",
            fg="#D5F7FF",
            insertbackground="#00E5FF",
            selectbackground="#0C4051",
            relief="flat",
            padx=14,
            pady=14
        )
        self.chat_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        self.chat_box.config(state="disabled")

        input_frame = tk.Frame(right, bg="#06111C")
        input_frame.pack(fill="x", padx=14, pady=(0, 14))

        self.input_box = tk.Entry(
            input_frame,
            font=("Segoe UI", 10),
            bg="#0A1824",
            fg="white",
            insertbackground="#00E5FF",
            relief="flat"
        )
        self.input_box.pack(fill="x", ipady=10, pady=(0, 8))
        self.input_box.bind("<Return>", self.send_text)

        buttons = tk.Frame(input_frame, bg="#06111C")
        buttons.pack(fill="x")

        self.send_button = tk.Button(
            buttons,
            text="SEND",
            command=self.send_text,
            font=("Segoe UI", 9, "bold"),
            bg="#0C4051",
            fg="white",
            activebackground="#11647C",
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        self.send_button.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 4))

        self.voice_button = tk.Button(
            buttons,
            text="🎤 START VOICE",
            command=self.toggle_voice_mode,
            font=("Segoe UI", 9, "bold"),
            bg="#0C4051",
            fg="white",
            activebackground="#11647C",
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        self.voice_button.pack(side="left", fill="x", expand=True, ipady=7, padx=(4, 0))

        self.input_box.focus_set()


    # ========================================
    # V13 VOICE SETTINGS
    # ========================================

    def change_voice(self, value=None):
        selected = value or self.voice_choice.get()
        self.voice.set_voice(selected)
        self.add_message("SYSTEM", "Voice changed to " + selected + ".")

    def change_speed(self, value=None):
        selected = value or self.speed_choice.get()
        self.voice.set_speed(selected)
        self.add_message("SYSTEM", "Speaking speed changed to " + selected + ".")


    # ========================================
    # STATUS
    # ========================================

    def update_audio_energy(self, value):
        """Called by voice_v3 from audio worker threads."""
        try:
            self.real_audio_energy = max(
                0.0,
                min(1.0, float(value))
            )
        except Exception:
            self.real_audio_energy = 0.0


    def set_state(self, state):

        self.state = state

        if state == "READY":
            self.real_audio_energy = 0.0

        text = "● " + state

        self.status_label.config(
            text=text
        )

        if hasattr(self, "top_status"):
            self.top_status.config(
                text="SYSTEM // " + state + "  ●"
            )


    # ========================================
    # ANIMATION
    # ========================================

    def animate_core(self):

        try:
            self.canvas.delete("all")

            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()

            if width < 100:
                width = 560
            if height < 100:
                height = 600

            cx = width / 2
            cy = height * 0.43

            # =================================
            # STATE -> VISUAL ENERGY
            # =================================

            if self.state == "LISTENING":
                speed = 4.0 + self.real_audio_energy * 5.0
                pulse_speed = 0.10 + self.real_audio_energy * 0.34
                self.target_energy = max(
                    0.05,
                    self.real_audio_energy
                )

            elif self.state == "THINKING":
                # Thinking has no live audio, so keep a subtle
                # processor animation while Ollama works.
                speed = 8.0
                pulse_speed = 0.13
                self.target_energy = 0.34

            elif self.state == "SPEAKING":
                speed = 4.5 + self.real_audio_energy * 6.0
                pulse_speed = 0.12 + self.real_audio_energy * 0.38
                self.target_energy = max(
                    0.06,
                    self.real_audio_energy
                )

            else:
                speed = 2.0
                pulse_speed = 0.06
                self.target_energy = 0.08

            self.energy_level += (
                self.target_energy - self.energy_level
            ) * 0.16

            self.angle += speed
            self.angle2 -= speed * 0.67
            self.angle3 += speed * 0.38
            self.pulse += pulse_speed
            self.wave_phase += 0.20 + self.energy_level * 0.35
            self.scanner_phase += 0.035

            pulse = math.sin(self.pulse) * (
                7 + self.energy_level * 18
            )

            # =================================
            # DEEP HUD BACKGROUND
            # =================================

            grid = 42
            for x in range(0, int(width), grid):
                self.canvas.create_line(
                    x, 0, x, height,
                    fill="#081B25"
                )

            for y in range(0, int(height), grid):
                self.canvas.create_line(
                    0, y, width, y,
                    fill="#081B25"
                )

            # Perspective lines
            for offset in range(-5, 6):
                self.canvas.create_line(
                    cx,
                    cy,
                    cx + offset * 72,
                    height,
                    fill="#071822"
                )

            scanner_y = (
                cy
                + math.sin(self.scanner_phase) * min(205, height * 0.32)
            )
            self.canvas.create_line(
                max(15, cx - 230),
                scanner_y,
                min(width - 15, cx + 230),
                scanner_y,
                fill="#0B4050",
                width=1
            )

            # =================================
            # PARTICLE ORBIT
            # =================================

            orbit_scale = min(width, height) / 500
            for particle in self.particles:
                particle["angle"] += particle["speed"] * speed
                radius = particle["radius"] * orbit_scale

                px = cx + math.cos(particle["angle"]) * radius
                py = cy + math.sin(particle["angle"]) * radius * 0.56

                sparkle = (
                    particle["size"]
                    + self.energy_level
                    * abs(math.sin(particle["angle"] * 3))
                    * 2
                )

                self.canvas.create_oval(
                    px - sparkle,
                    py - sparkle,
                    px + sparkle,
                    py + sparkle,
                    fill="#178AA0",
                    outline=""
                )

            # =================================
            # PSEUDO-3D ENERGY SPHERE
            # =================================

            base = min(width, height) * 0.24
            base = max(105, min(base, 155))

            # Elliptical orbital planes
            for index, squash in enumerate([0.30, 0.46, 0.64]):
                r = base + 25 + index * 13 + pulse * 0.15
                self.canvas.create_oval(
                    cx - r,
                    cy - r * squash,
                    cx + r,
                    cy + r * squash,
                    outline="#0B4B5B",
                    width=1
                )

            # Outer halo rings
            for add, line_width in [(52, 1), (39, 1), (25, 2)]:
                r = base + add + pulse * 0.18
                self.canvas.create_oval(
                    cx-r, cy-r, cx+r, cy+r,
                    outline="#0A3544",
                    width=line_width
                )

            # Rotating node ring
            node_radius = base + 39
            for i in range(16):
                a = math.radians(self.angle + i * 22.5)
                x = cx + math.cos(a) * node_radius
                y = cy + math.sin(a) * node_radius
                node = 1.8 + self.energy_level * 3.8

                self.canvas.create_oval(
                    x-node, y-node, x+node, y+node,
                    fill="#00E5FF",
                    outline=""
                )

            # Broken outer arcs
            ring1 = base + 17
            for i in range(6):
                self.canvas.create_arc(
                    cx-ring1, cy-ring1,
                    cx+ring1, cy+ring1,
                    start=self.angle + i * 60,
                    extent=31,
                    style="arc",
                    outline="#00C6DF",
                    width=3
                )

            ring2 = base - 10
            for i in range(5):
                self.canvas.create_arc(
                    cx-ring2, cy-ring2,
                    cx+ring2, cy+ring2,
                    start=self.angle2 + i * 72,
                    extent=39,
                    style="arc",
                    outline="#17758A",
                    width=2
                )

            ring3 = base - 37
            for i in range(18):
                self.canvas.create_arc(
                    cx-ring3, cy-ring3,
                    cx+ring3, cy+ring3,
                    start=self.angle3 + i * 20,
                    extent=7,
                    style="arc",
                    outline="#00E5FF",
                    width=2
                )

            # Crosshair / targeting marks
            target_r = base + 70
            for a_deg in [0, 90, 180, 270]:
                a = math.radians(a_deg)
                x1 = cx + math.cos(a) * (target_r - 12)
                y1 = cy + math.sin(a) * (target_r - 12)
                x2 = cx + math.cos(a) * target_r
                y2 = cy + math.sin(a) * target_r
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill="#1590A5",
                    width=2
                )

            # =================================
            # GLOWING INNER CORE
            # =================================

            core_energy = self.energy_level
            glow_layers = [
                (68 + pulse * 0.7, "#082B38"),
                (58 + pulse * 0.6, "#0A4554"),
                (48 + pulse * 0.5, "#086C7D"),
                (37 + pulse * 0.35, "#00AFC4")
            ]

            for size, color in glow_layers:
                size += core_energy * 11
                self.canvas.create_oval(
                    cx-size, cy-size,
                    cx+size, cy+size,
                    fill=color,
                    outline=""
                )

            core = 25 + core_energy * 18 + pulse * 0.20
            self.canvas.create_oval(
                cx-core, cy-core,
                cx+core, cy+core,
                fill="#00D7ED",
                outline="#B8FCFF",
                width=2
            )

            # Hot center
            hot = 9 + core_energy * 8
            self.canvas.create_oval(
                cx-hot, cy-hot,
                cx+hot, cy+hot,
                fill="#ECFFFF",
                outline=""
            )

            # Highlight gives sphere depth
            self.canvas.create_oval(
                cx-core*0.55,
                cy-core*0.62,
                cx-core*0.10,
                cy-core*0.18,
                fill="#BDFBFF",
                outline=""
            )

            # =================================
            # STATE HUD
            # =================================

            self.canvas.create_text(
                cx,
                cy + base + 92,
                text="LUNA // " + self.state,
                fill="#00E5FF",
                font=("Consolas", 11, "bold")
            )

            self.canvas.create_text(
                cx,
                cy + base + 111,
                text="NEURAL ENERGY  {:03d}%".format(
                    int(
                        (
                            self.real_audio_energy
                            if self.state in [
                                "LISTENING",
                                "SPEAKING"
                            ]
                            else self.energy_level
                        )
                        * 100
                    )
                ),
                fill="#527D88",
                font=("Consolas", 8)
            )

            # =================================
            # AUDIO ENERGY WAVEFORM
            # =================================

            wave_y = height - 62
            left = 28
            right = width - 28
            points = []

            count = 70
            available = max(1, right - left)

            for i in range(count):
                x = left + (available * i / (count - 1))

                envelope = math.sin(
                    math.pi * i / (count - 1)
                ) ** 0.55

                signal = (
                    math.sin(self.wave_phase + i * 0.58)
                    + 0.45 * math.sin(
                        self.wave_phase * 1.7 + i * 1.14
                    )
                    + 0.22 * math.sin(
                        self.wave_phase * 0.43 + i * 2.05
                    )
                )

                amplitude = (
                    3
                    + self.energy_level * 25
                ) * envelope

                y = wave_y + signal * amplitude
                points.extend([x, y])

            if len(points) >= 4:
                self.canvas.create_line(
                    *points,
                    fill="#00D9F2",
                    width=2,
                    smooth=True
                )

            self.canvas.create_line(
                left,
                wave_y,
                right,
                wave_y,
                fill="#0A3340",
                width=1
            )

            self.canvas.create_text(
                left,
                height - 24,
                text="REAL AUDIO ENERGY",
                anchor="w",
                fill="#3E707C",
                font=("Consolas", 7, "bold")
            )

            self.canvas.create_text(
                right,
                height - 24,
                text=self.state + " // LINK STABLE",
                anchor="e",
                fill="#3E707C",
                font=("Consolas", 7)
            )

            self.root.after(
                33,
                self.animate_core
            )

        except tk.TclError:
            return


    # ========================================
    # CHAT MESSAGE
    # ========================================

    def add_message(
        self,
        sender,
        message
    ):

        self.chat_box.config(
            state="normal"
        )

        current_time = (
            time.strftime(
                "%H:%M:%S"
            )
        )

        self.chat_box.insert(
            tk.END,
            f"[{current_time}] "
            f"{sender}\n"
        )

        self.chat_box.insert(
            tk.END,
            message + "\n\n"
        )

        self.chat_box.config(
            state="disabled"
        )

        self.chat_box.see(
            tk.END
        )


    # ========================================
    # LANGUAGE INSTRUCTION
    # ========================================

    def language_instruction(
        self,
        language
    ):

        if language == "hi":

            return """
The current user is speaking Hindi.
Answer naturally in Hindi using Devanagari script.
Do not switch to English unless requested.
"""

        elif language == "bn":

            return """
The current user is speaking Bengali.
Answer naturally in Bengali using Bengali script.
Do not switch to English unless requested.
"""

        else:

            return """
The current user is speaking English.
Answer naturally in English.
"""


    # ========================================
    # DETECT TYPED LANGUAGE
    # ========================================

    def detect_text_language(
        self,
        text
    ):

        if any(
            "\u0980" <= c <= "\u09FF"
            for c in text
        ):

            return "bn"

        if any(
            "\u0900" <= c <= "\u097F"
            for c in text
        ):

            return "hi"

        return "en"


    # ========================================
    # SEND TYPED MESSAGE
    # ========================================

    def send_text(
        self,
        event=None
    ):

        if self.busy:
            return

        text = (
            self.input_box
            .get()
            .strip()
        )

        if not text:
            return

        self.input_box.delete(
            0,
            tk.END
        )

        self.add_message(
            "YOU",
            text
        )

        language = (
            self.detect_text_language(
                text
            )
        )

        threading.Thread(
            target=self.process_command,
            args=(
                text,
                language
            ),
            daemon=True
        ).start()


    # ========================================
    # CONTINUOUS HANDS-FREE VOICE MODE
    # ========================================

    def toggle_voice_mode(self):

        if self.continuous_voice:

            self.continuous_voice = False

            self.voice_button.config(
                text="🎤 START VOICE"
            )

            self.add_message(
                "SYSTEM",
                "Hands-free voice mode stopped."
            )

            return


        if self.busy:
            return

        self.continuous_voice = True

        self.voice_button.config(
            text="■ STOP VOICE"
        )

        self.add_message(
            "SYSTEM",
            "Hands-free voice mode active."
        )

        threading.Thread(
            target=self.continuous_voice_worker,
            daemon=True
        ).start()


    def continuous_voice_worker(self):

        self.busy = True

        try:

            if self.listener is None:

                self.root.after(
                    0,
                    lambda:
                    self.add_message(
                        "SYSTEM",
                        "Loading voice recognition..."
                    )
                )

                self.listener = LocalWhisper(
                    energy_callback=self.update_audio_energy
                )


            while self.continuous_voice:

                self.root.after(
                    0,
                    lambda:
                    self.set_state(
                        "LISTENING"
                    )
                )

                text, language = (
                    self.listener.listen()
                )


                if not self.continuous_voice:
                    break


                if not text:

                    # No speech during the listening window.
                    # Stay in hands-free mode and listen again.
                    continue


                self.root.after(
                    0,
                    lambda t=text:
                    self.add_message(
                        "YOU",
                        t
                    )
                )


                # process_command blocks until Luna has
                # finished answering AND speaking.
                # Only then do we reopen the microphone,
                # preventing Luna from hearing herself.
                self.process_command(
                    text,
                    language,
                    keep_voice_mode=True
                )


            self.root.after(
                0,
                lambda:
                self.set_state(
                    "READY"
                )
            )

        except Exception as error:

            error_text = str(error)

            self.root.after(
                0,
                lambda e=error_text:
                self.add_message(
                    "SYSTEM ERROR",
                    e
                )
            )

        finally:

            self.busy = False
            self.continuous_voice = False

            self.root.after(
                0,
                lambda:
                self.voice_button.config(
                    text="🎤 START VOICE"
                )
            )

            self.root.after(
                0,
                lambda:
                self.set_state(
                    "READY"
                )
            )


    # ========================================
    # PROCESS COMMAND
    # ========================================

    def process_command(
        self,
        user_text,
        language,
        keep_voice_mode=False
    ):

        self.busy = True

        self.root.after(
            0,
            lambda:
            self.set_state(
                "THINKING"
            )
        )


        try:

            # =================================
            # TRY ACTION
            # =================================

            action_result = (
                execute_action(
                    user_text
                )
            )


            if action_result:

                answer = action_result

                self.memory.save(
                    "user",
                    user_text
                )

                self.memory.save(
                    "assistant",
                    answer
                )

            else:

                # =============================
                # NORMAL AI CONVERSATION
                # =============================

                self.memory.save(
                    "user",
                    user_text
                )


                instruction = (
                    self.language_instruction(
                        language
                    )
                )


                system_prompt = f"""
You are Luna, my personal local Windows AI assistant.

You understand Hindi, Bengali, Hinglish, Banglish, and English.

{instruction}

You have a real local action system. It can perform supported computer tasks such as:
- open, close, find, and search apps or websites
- find and open files and folders
- read real CPU, RAM, battery, disk, and system information
- control windows, desktop, scrolling, mouse clicks, and keyboard shortcuts
- read, copy, and clear clipboard text and type Unicode text

Tool-aware rules:

1. Follow the current user's language and speaking style.
2. Be natural and conversational.
3. Keep normal answers concise; give detail when requested.
4. Your name is Luna.
5. Never say you are just a language model or that you cannot control the computer in general.
6. A computer action is real ONLY when the action system actually performed it and its result appears in recent conversation history.
7. Never invent, assume, or falsely claim that an action happened.
8. If the user asks what you did, whether you opened/closed something, or corrects a previous action, use recent conversation history as the source of truth.
9. Clearly distinguish an action that actually happened from something that was only discussed.
10. If a specific requested action is not supported yet, say that specific feature is not available yet instead of denying all computer-control ability.
"""


                messages = [
                    {
                        "role": "system",
                        "content":
                        system_prompt
                    }
                ]


                messages.extend(
                    self.memory.get_history(
                        limit=6
                    )
                )


                response = ollama.chat(
                    model=MODEL,
                    messages=messages,
                    options={
                        "temperature": 0.4,
                        "num_predict": 180
                    },
                    keep_alive="30m"
                )


                answer = (
                    response[
                        "message"
                    ][
                        "content"
                    ]
                    .strip()
                )


                self.memory.save(
                    "assistant",
                    answer
                )


            # =================================
            # SHOW ANSWER
            # =================================

            self.root.after(
                0,
                lambda a=answer:
                self.add_message(
                    "LUNA",
                    a
                )
            )


            # =================================
            # SPEAK
            # =================================

            self.root.after(
                0,
                lambda:
                self.set_state(
                    "SPEAKING"
                )
            )


            try:

                self.voice.speak(
                    answer
                )

            except Exception as error:

                print(
                    "Voice Error:",
                    error
                )


        except Exception as error:

            error_text = str(error)

            self.root.after(
                0,
                lambda e=error_text:
                self.add_message(
                    "SYSTEM ERROR",
                    e
                )
            )


        finally:

            if not keep_voice_mode:
                self.busy = False

                self.root.after(
                    0,
                    lambda:
                    self.set_state(
                        "READY"
                    )
                )
            elif self.continuous_voice:
                self.root.after(
                    0,
                    lambda:
                    self.set_state(
                        "LISTENING"
                    )
                )


# ============================================
# START LUNA
# ============================================

if __name__ == "__main__":

    root = tk.Tk()

    app = LunaApp(
        root
    )

    # V12 reminder watcher
    def check_luna_reminders():
        try:
            for item in get_due_reminders():
                if item.get("kind") == "timer":
                    alert = "Timer complete ho gaya."
                else:
                    alert = "Reminder: " + item.get("message", "Reminder")

                add_message("Luna", alert)
                threading.Thread(
                    target=voice.speak,
                    args=(alert,),
                    daemon=True
                ).start()
        except Exception as error:
            print("Reminder watcher error:", error)

        root.after(1000, check_luna_reminders)

    root.after(1000, check_luna_reminders)

    root.mainloop()
