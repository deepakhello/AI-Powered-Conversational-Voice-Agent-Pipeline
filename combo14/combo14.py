import os
import tkinter as tk
import threading
import time
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import requests

# Load .env keys
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

stop_threads = False  # Stop flag
synthesizer = None  # Global synthesizer to stop speech
interaction_active = False  # Flag to prevent multiple interaction threads

# Azure TTS
def speak(text):
    global synthesizer
    if stop_threads:
        return
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    speak_task = synthesizer.speak_text_async(text)
    while not speak_task.get().reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        if stop_threads:
            print("🛑 Stopping speech midway")
            synthesizer.stop_speaking_async()
            break
    print(f"🔊 Speaking Done")

# Modified Azure STT for continuous listening with 3-second silence wait
def listen():
    global stop_threads
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    # Set timeout for silence detection (3 seconds)
    speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "3000")
    speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000")

    while not stop_threads:
        try:
            print("🎤 Listening...")
            status.set("Listening...")
            mic_icon.config(text="🎤", fg="green")
            result = speech_recognizer.recognize_once_async().get()
            if stop_threads:
                print("🛑 Listening stopped")
                return None
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = result.text
                print(f"🟢 Recognized: {text}")
                status.set(f"Recognized: {text}")
                mic_icon.config(text="")
                return text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("🔴 No speech detected for 3 seconds, listening again...")
                status.set("No speech detected, listening again...")
                mic_icon.config(text="🎤", fg="green")
                continue
            elif result.reason == speechsdk.ResultReason.Canceled:
                print("🔴 Speech recognition canceled")
                status.set("Speech recognition canceled")
                mic_icon.config(text="")
                return None
        except Exception as e:
            print(f"🔴 Listening Error: {e}")
            status.set("Listening error occurred")
            mic_icon.config(text="")
            return None
    print("🛑 Listening stopped due to stop_threads")
    return None

# Groq LLM (corrected)
def chat_with_groq(user_message):
    if stop_threads:
        print("🛑 LLM call skipped")
        return ""
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [{"role": "user", "content": user_message}],
            "max_tokens": 4096
        }
        response = requests.post("https://aimlapi.com/app/keys", headers=headers, json=data)
        response.raise_for_status()
        reply = response.json()['choices'][0]['message']['content'].strip()
        print("🤖 Groq Reply:", reply)
        return reply
    except requests.exceptions.RequestException as e:
        print(f"🔴 Groq API Request Error: {e}")
        return "Sorry, an error occurred with Groq API."
    except (KeyError, ValueError) as e:
        print(f"🔴 Groq API Response Parsing Error: {e}")
        return "Sorry, an error occurred while parsing the Groq API response."

# Modified Handle Voice Interaction for continuous listening
def handle_voice_interaction():
    global stop_threads, interaction_active
    if interaction_active:
        status.set("Interaction already in progress")
        print("🔴 Interaction already in progress")
        return
    stop_threads = False
    interaction_active = True

    def interaction():
        try:
            while not stop_threads:
                input_text.delete("1.0", tk.END)
                chat_output.delete("1.0", tk.END)
                user_input = listen()
                if stop_threads or user_input is None:
                    break
                input_text.insert(tk.END, user_input)
                llm_reply = chat_with_groq(user_input)
                if stop_threads or not llm_reply:
                    break
                chat_output.insert(tk.END, llm_reply)
                speak(llm_reply)
                status.set("Response complete, listening again...")
            status.set("Stopped")
            interaction_active = False
        except Exception as e:
            print("🔴 Error:", e)
            speak("An error occurred.")
            status.set(f"Error: {e}")
            interaction_active = False

    threading.Thread(target=interaction, daemon=True).start()

def stop_interaction():
    global stop_threads, synthesizer, interaction_active
    stop_threads = True
    if synthesizer:
        try:
            synthesizer.stop_speaking_async()
            print("🛑 Speech stopped")
        except Exception as e:
            print(f"Error stopping synthesizer: {e}")
    status.set("Stopping...")
    mic_icon.config(text="")
    interaction_active = False
    print("🛑 Stopping interaction")

# Theme Toggle (unchanged)
def toggle_theme():
    global dark_mode
    dark_mode = not dark_mode
    bg = "#2c2f33" if dark_mode else "#f2f2f2"
    content_bg = "#23272a" if dark_mode else "white"
    fg = "white" if dark_mode else "black"
    entry_bg = "#2c2f33" if dark_mode else "white"
    entry_fg = "white" if dark_mode else "black"
    window.config(bg=bg)
    header.config(bg="#7289da" if dark_mode else "#007acc")
    main_frame.config(bg=content_bg)
    for widget in main_frame.winfo_children():
        widget.config(bg=content_bg, fg=fg)
    input_text.config(bg=entry_bg, fg=entry_fg, insertbackground=fg)
    chat_output.config(bg=entry_bg, fg=entry_fg, insertbackground=fg)
    mic_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")
    stop_button.config(bg="#7289da" if dark_mode else "#007acc", fg="white")

# GUI Setup (unchanged)
window = tk.Tk()
window.title("🧠 Voice Assistant | Azure STT + Groq LLM + Azure TTS")
window.geometry("950x620")
window.config(bg="#f2f2f2")
dark_mode = False

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="Voice Assistant | Azure STT + Groq LLM + Azure TTS", font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(pady=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question (via Mic):", font=("Arial", 12), bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial", 11), wrap=tk.WORD)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(main_frame, text="🎤 Tap to Speak & Get Answer", font=("Arial", 13, "bold"), bg="#007acc", fg="white", command=handle_voice_interaction, padx=20, pady=10)
mic_button.pack(pady=10)

stop_button = tk.Button(main_frame, text="🛑 Stop", font=("Arial", 13, "bold"), bg="#007acc", fg="white", command=stop_interaction, padx=20, pady=10)
stop_button.pack(pady=10)

output_label = tk.Label(main_frame, text="Response:", font=("Arial", 12, "bold"), bg="white")
output_label.pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10, font=("Arial", 11), wrap=tk.WORD)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w", font=("Arial", 10), bg="#f2f2f2").pack(fill="x", side="bottom")

theme_button = tk.Button(header, text="Toggle Theme", font=("Arial", 10), bg="#7289da", fg="white", command=toggle_theme)
theme_button.pack(anchor="e", padx=10, pady=5)

window.mainloop()