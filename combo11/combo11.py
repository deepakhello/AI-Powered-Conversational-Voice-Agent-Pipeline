import os
import tkinter as tk
import threading
import time
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import google.generativeai as genai

# === Load Environment Variables ===
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION     = os.getenv("AZURE_REGION")
GOOGLE_API_KEY   = os.getenv("GOOGLE_API_KEY")

# === Gemini Setup (Free-tier) ===
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# === Globals ===
stop_threads = False
synthesizer  = None
dark_mode    = False

# === Azure TTS Function ===
def speak(text):
    global synthesizer
    if stop_threads or not text.strip():
        return
    start = time.time()
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        result = synthesizer.speak_text_async(text).get()
        print(f"🔊 TTS Time: {round(time.time() - start, 2)}s")
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("🔴 TTS failed:", result.reason)
    except Exception as e:
        print("🔴 TTS Exception:", e)

# === Azure STT Function ===
def listen():
    global stop_threads
    start = time.time()
    try:
        speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
        audio_config  = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer    = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        status.set("🎤 Listening...")
        mic_icon.config(text="🎤", fg="green")
        result = recognizer.recognize_once_async().get()
        mic_icon.config(text="")
        print(f"🎧 STT Time: {round(time.time() - start, 2)}s")
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print(f"🟢 Recognized: {result.text}")
            status.set(f"Recognized: {result.text}")
            return result.text.strip()
        else:
            print("🔴 STT Failed:", result.reason)
            status.set("Speech not recognized")
            return None
    except Exception as e:
        print("🔴 STT Exception:", e)
        status.set("STT Error")
        return None

# === Gemini Flash Function ===
def chat_with_gemini(user_message):
    if stop_threads or not user_message.strip():
        return ""
    start = time.time()
    try:
        response = model.generate_content(user_message)
        reply = response.text.strip()
        print(f"🤖 Gemini Time: {round(time.time() - start, 2)}s")
        return reply
    except Exception as e:
        print("🔴 Gemini Exception:", e)
        return "Sorry, Gemini encountered an error."

# === Main Interaction Thread ===
def handle_voice_interaction():
    global stop_threads
    stop_threads = False

    def interaction():
        input_text.delete("1.0", tk.END)
        chat_output.delete("1.0", tk.END)
        user_input = listen()
        if stop_threads or not user_input:
            status.set("Stopped or no input")
            return
        input_text.insert(tk.END, user_input)
        status.set("🤖 Thinking...")
        llm_reply = chat_with_gemini(user_input)
        if stop_threads or not llm_reply:
            status.set("Stopped or no reply")
            return
        chat_output.insert(tk.END, llm_reply)
        status.set("🔊 Speaking...")
        speak(llm_reply)
        status.set("✅ Done")

    threading.Thread(target=interaction, daemon=True).start()

# === Stop Interaction ===
def stop_interaction():
    global stop_threads, synthesizer
    stop_threads = True
    if synthesizer:
        try:
            synthesizer.stop_speaking_async()
            print("🛑 Speech stopped")
        except Exception as e:
            print("Error stopping speech:", e)
    mic_icon.config(text="")
    status.set("🛑 Stopped")

# === Theme Toggle ===
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg         = "#2c2f33" if dark_mode else "#f2f2f2"
    content_bg = "#23272a" if dark_mode else "white"
    text_fg    = "white"    if dark_mode else "black"
    accent     = "#7289da"  if dark_mode else "#007acc"

    window.config(bg=bg)
    header.config(bg=accent)
    main_frame.config(bg=content_bg)
    theme_button.config(bg=accent, fg="white")
    mic_button.config(bg=accent, fg="white")
    stop_button.config(bg=accent, fg="white")

    for widget in main_frame.winfo_children():
        widget.config(bg=content_bg, fg=text_fg)
    input_text.config(bg=content_bg, fg=text_fg, insertbackground=text_fg)
    chat_output.config(bg=content_bg, fg=text_fg, insertbackground=text_fg)

# === GUI Setup ===
window = tk.Tk()
window.title("🧠 Voice Assistant | Gemini Flash + Azure STT/TTS")
window.geometry("950x620")
window.config(bg="#f2f2f2")

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="Voice Assistant | Azure STT + Gemini Flash + Azure TTS", font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(pady=10)
theme_button = tk.Button(header, text="Toggle Theme", font=("Arial", 10), bg="#7289da", fg="white", command=toggle_theme)
theme_button.pack(anchor="e", padx=10, pady=5)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")
tk.Label(main_frame, text="Your Question:", font=("Arial", 12), bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial", 11), wrap=tk.WORD)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()
mic_button = tk.Button(main_frame, text="🎤 Speak", font=("Arial", 13, "bold"), bg="#007acc", fg="white", command=handle_voice_interaction, padx=20, pady=10)
mic_button.pack(pady=10)
stop_button = tk.Button(main_frame, text="🛑 Stop", font=("Arial", 13, "bold"), bg="#007acc", fg="white", command=stop_interaction, padx=20, pady=10)
stop_button.pack(pady=10)

tk.Label(main_frame, text="Response:", font=("Arial", 12, "bold"), bg="white").pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10, font=("Arial", 11), wrap=tk.WORD)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w", font=("Arial", 10), bg="#f2f2f2").pack(fill="x", side="bottom")

window.mainloop()