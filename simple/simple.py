import asyncio
import azure.cognitiveservices.speech as speechsdk
import cohere
import os
from dotenv import load_dotenv
import tkinter as tk
import threading

# Load API Keys
load_dotenv()
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_REGION")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

co = cohere.Client(COHERE_API_KEY)

# Azure TTS Function
def speak(text):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
    synthesizer.speak_text_async(text).get()
    print(f"🔊 Speaking: {text}")
    return text  # Return text for GUI display

# Azure STT Function
def listen():
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("🎤 Listening...")
    status.set("Listening...")
    mic_icon.config(text="🎤", fg="green")
    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"🟢 Recognized: {result.text}")
        status.set(f"Recognized: {result.text}")
        mic_icon.config(text="")
        return result.text
    else:
        print(f"🔴 STT Error: {result.reason}")
        status.set("Error: Could not recognize speech")
        mic_icon.config(text="")
        return None

# Cohere LLM Call (command-r)
def chat_with_cohere(user_message):
    response = co.chat(
        model="command-r",
        message=user_message
    )
    reply = response.text
    print("🤖 LLM Reply:", reply)
    return reply.strip()

# Handle Voice Interaction (Bridge GUI and Backend)
def handle_voice_interaction():
    def run_interaction():
        try:
            # Clear previous input/output
            input_text.delete("1.0", tk.END)
            chat_output.delete("1.0", tk.END)

            # Get user input via STT
            user_input = listen()
            if user_input:
                input_text.insert(tk.END, user_input)
                # Process with Cohere LLM
                llm_reply = chat_with_cohere(user_input)
                # Display and speak response
                chat_output.insert(tk.END, llm_reply)
                speak(llm_reply)
                status.set("Response complete")
            else:
                speak("Sorry, I didn't catch that.")
                chat_output.insert(tk.END, "Sorry, I didn't catch that.")
                status.set("No speech detected")
        except Exception as e:
            print(f"Error: {e}")
            status.set(f"Error: {e}")
            speak("An error occurred. Please try again.")

    # Run in asyncio event loop within a thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.ensure_future(asyncio.to_thread(run_interaction)))
    loop.close()

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

# GUI Setup
window = tk.Tk()
window.title("🧠 VoiceGrok - Speak & Hear")
window.geometry("950x620")
window.config(bg="#f2f2f2")
dark_mode = False

header = tk.Frame(window, height=60, bg="#007acc")
header.pack(fill="x")
tk.Label(header, text="Voice-Based Cohere Assistant Dashboard", font=("Arial", 18, "bold"), fg="white", bg="#007acc").pack(pady=10)

main_frame = tk.Frame(window, bg="white", padx=20, pady=10)
main_frame.pack(expand=True, fill="both")

tk.Label(main_frame, text="Your Question (auto from mic):", font=("Arial", 12), bg="white").pack(anchor="w")
input_text = tk.Text(main_frame, height=4, font=("Arial", 11), wrap=tk.WORD)
input_text.pack(fill="x", pady=5)

mic_icon = tk.Label(main_frame, text="", font=("Arial", 14), fg="green", bg="white")
mic_icon.pack()

mic_button = tk.Button(
    main_frame,
    text="🎤 Tap to Speak & Get Answer",
    font=("Arial", 13, "bold"),
    bg="#007acc",
    fg="white",
    activebackground="#005f99",
    activeforeground="white",
    padx=20,
    pady=10,
    command=lambda: threading.Thread(target=handle_voice_interaction, daemon=True).start()
)
mic_button.pack(pady=20)
mic_button.bind("<Enter>", lambda e: mic_button.config(bg="#005f99"))
mic_button.bind("<Leave>", lambda e: mic_button.config(bg="#007acc"))

output_label = tk.Label(main_frame, text=" R:", font=("Arial", 12, "bold"), bg="white")
output_label.pack(anchor="w", pady=(10, 0))
chat_output = tk.Text(main_frame, height=10, font=("Arial", 11), wrap=tk.WORD)
chat_output.pack(fill="both", expand=True, pady=5)

status = tk.StringVar(value="Ready")
tk.Label(window, textvariable=status, bd=1, relief="sunken", anchor="w", font=("Arial", 10), bg="#f2f2f2").pack(fill="x", side="bottom")

# Theme Toggle Button
theme_button = tk.Button(
    header,
    text="Toggle Theme",
    font=("Arial", 10),
    bg="#7289da" if dark_mode else "#007acc",
    fg="white",
    command=toggle_theme
)
theme_button.pack(anchor="e", padx=10, pady=5)

window.mainloop()