import os
import openai
import tkinter as tk
import speech_recognition as sr
import threading
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# Load .env keys
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

stop_threads = False  # Stop flag

# Azure TTS
def speak(text):
    if stop_threads:
        return
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    synthesizer.speak_text_async(text).get()
    print(f"🔊 Speaking: {text}")

# Google STT
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        status.set("Listening...")
        mic_icon.config(text="🎤", fg="green")
        audio = recognizer.listen(source, phrase_time_limit=10)
    try:
        text = recognizer.recognize_google(audio)
        print(f"🟢 Recognized: {text}")
        status.set(f"Recognized: {text}")
        mic_icon.config(text="")
        return text
    except sr.UnknownValueError:
        print("🔴 Could not understand audio")
        status.set("Could not understand audio")
        mic_icon.config(text="")
        return None
    except sr.RequestError as e:
        print(f"🔴 Request Error: {e}")
        status.set("Error with Google STT API")
        mic_icon.config(text="")
        return None

# OpenAI GPT-4o

def chat_with_openai(user_message):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": user_message}]
        )
        reply = response.choices[0].message.content
        print("🤖 OpenAI Reply:", reply)
        return reply.strip()
    except Exception as e:
        print(f"🔴 OpenAI API Error: {e}")
        return "Sorry, an error occurred with OpenAI API."

# Handle Voice Interaction
def handle_voice_interaction():
    global stop_threads
    stop_threads = False

    def interaction():
        try:
            input_text.delete("1.0", tk.END)
            chat_output.delete("1.0", tk.END)
            user_input = listen()
            if stop_threads:
                status.set("Stopped")
                return
            if user_input:
                input_text.insert(tk.END, user_input)
                llm_reply = chat_with_openai(user_input)
                if stop_threads:
                    status.set("Stopped")
                    return
                chat_output.insert(tk.END, llm_reply)
                speak(llm_reply)
                status.set("Response complete")
            else:
                chat_output.insert(tk.END, "Sorry, I didn't catch that.")
                speak("Sorry, I didn't catch that.")
                status.set("No speech detected")
        except Exception as e:
            print("🔴 Error:", e)
            speak("An error occurred.")
            status.set(f"Error: {e}")

    threading.Thread(target=interaction, daemon=True).start()

def stop_interaction():
    global stop_threads
    stop_threads = True
    status.set("Stopping...")
    mic_icon.config(text="")
    print("🛑 Stopping interaction")

# Theme Toggle
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

# GUI Setup
window = tk.Tk()
window.title("🧠 Voice Assistant OpenAI")
window.geometry("950x620")
window.config(bg="#f2f2f2")
dark_mode = False

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="Voice Assistant | OpenAI GPT + Google STT + Azure TTS", font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(pady=10)

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
