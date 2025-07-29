import os
import tkinter as tk
import threading
import requests
import pyaudio
import wave
import openai
from dotenv import load_dotenv

# === Load API Keys ===
load_dotenv()
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY   = os.getenv("DEEPGRAM_API_KEY")

openai.api_key = OPENAI_API_KEY

# === Audio Config ===
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024
RECORD_SECONDS = 10
TEMP_WAV = "temp_audio.wav"

# === Deepgram TTS ===
def speak(text):
    try:
        url = "https://api.deepgram.com/v1/speak"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model": "aura-asteria-en",  # You can change voice model
            "encoding": "linear16",
            "sample_rate": SAMPLE_RATE
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            audio_data = response.content
            stream = pyaudio.PyAudio().open(format=FORMAT,
                                            channels=CHANNELS,
                                            rate=SAMPLE_RATE,
                                            output=True)
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            print(f"🔊 Speaking (Deepgram): {text}")
        else:
            print(f"🔴 Deepgram Error: {response.text}")
    except Exception as e:
        print("🔴 Deepgram TTS Error:", e)

# === Whisper STT ===
def transcribe_with_whisper():
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE,
                            input=True, frames_per_buffer=CHUNK)
        frames = []

        print("🎙 Recording...")
        for _ in range(int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(TEMP_WAV, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b''.join(frames))

        with open(TEMP_WAV, "rb") as f:
            response = openai.Audio.transcribe("whisper-1", f)
            transcript = response["text"]
            print("📝 Whisper Transcript:", transcript)
            return transcript
    except Exception as e:
        print("🔴 Whisper Error:", e)
        return None

# === GPT-4.1 Nano ===
def chat_with_openai(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()
        print("🤖 GPT-4.1 Nano:", reply)
        return reply
    except Exception as e:
        print("🔴 OpenAI Error:", e)
        return "Sorry, OpenAI API error."

# === GUI Voice Interaction ===
def handle_voice_interaction():
    def task():
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)

        status.set("🎙 Recording...")
        mic_icon.config(text="🎤", fg="green")
        transcript = transcribe_with_whisper()
        mic_icon.config(text="")

        if not transcript:
            chat_output.insert(tk.END, "Sorry, I didn't catch that.")
            speak("Sorry, I didn't catch that.")
            status.set("No speech detected")
            return

        input_text.insert(tk.END, transcript)
        status.set("🤖 Thinking...")
        reply = chat_with_openai(transcript)
        chat_output.insert(tk.END, reply)
        status.set("🔊 Speaking...")
        speak(reply)
        status.set("✅ Done")

    threading.Thread(target=task, daemon=True).start()

# === Theme Toggle ===
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg = "#2c2f33" if dark_mode else "#f2f2f2"
    panel = "#23272a" if dark_mode else "white"
    fg = "white" if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=panel)
    for w in main_frame.winfo_children():
        w.config(bg=panel, fg=fg)
    input_text.config(bg=panel, fg=fg, insertbackground=fg)
    chat_output.config(bg=panel, fg=fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")

# === GUI Setup ===
dark_mode = False
window = tk.Tk()
window.title("Voice Assistant | Whisper STT + GPT-4.1 Nano + Deepgram TTS")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="🎤 Assistant | Whisper STT + GPT-4.1 Nano + Deepgram TTS",
         font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(pady=10)
tk.Button(header, text="Toggle Theme", command=toggle_theme,
          bg="#7289da", fg="white").pack(anchor="e", padx=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question:", bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame, text="🎤 Speak & Get Answer",
                       command=handle_voice_interaction,
                       bg="#007acc", fg="white", padx=20, pady=10)
mic_button.pack(pady=10)

tk.Label(main_frame, text="Response:", bg="white").pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w",
         bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()