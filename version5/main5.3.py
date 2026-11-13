import json
from click import prompt
import speech_recognition as sr
import win32com.client
import os
from dotenv import load_dotenv
import re
import winsound
from openai import OpenAI
import keyboard
import tkinter as tk
from tkinter import simpledialog
import threading
import queue
import winsound

# 👉 THIS IS THE MAGIC CONNECTION:
from my_tools4 import *
# Load the hidden keys at the very top of your script
load_dotenv()
# --- CONFIGURATION ---
USE_VOICE_INPUT = True
USE_VOICE_RESPONSE = True  
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio", timeout=45.0)

# --- NEW: MODEL SELECTOR ---
# --- AI PROVIDER CONFIGURATIONS ---
# Add your API keys here! Make sure the base_url matches the provider.
AI_PROVIDERS = {
    "local": {
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "default_model": None # Will be asked dynamically
    },
    #"chatgpt": {
    #    "base_url": "https://api.openai.com/v1",
    #    "api_key": "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",
    #   "default_model": "gpt-4o"
    #},
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        # Pull the key safely from the .env file!
        "api_key": os.getenv("GEMINI_API_KEY"), 
        "default_model": "gemini-1.5-pro" 
    }
    }

# Global AI Variables
client = None
ACTIVE_MODEL = None
CURRENT_PROVIDER = None

def select_local_model():
    """Fetches local models if LM Studio is selected."""
    try:
        print("\n[Fetching available local models from LM Studio...]")
        models_response = client.models.list()
        models = [m.id for m in models_response.data]
        if not models:
            return "local-model"
            
        print("\n=== AVAILABLE LOCAL MODELS ===")
        for i, model_id in enumerate(models):
            print(f"[{i + 1}] {model_id}")
            
        choice = input("\nEnter model number (or press Enter for default): ")
        if not choice.strip():
            return models[0]
        choice_idx = int(choice) - 1
        return models[choice_idx] if 0 <= choice_idx < len(models) else models[0]
    except Exception:
        return "local-model"

def switch_ai_provider():
    """Selector to change the AI provider dynamically."""
    global client, ACTIVE_MODEL, CURRENT_PROVIDER
    
    print("\n=== SELECT AI PROVIDER ===")
    providers = list(AI_PROVIDERS.keys())
    for i, p in enumerate(providers):
        print(f"[{i + 1}] {p.upper()}")
        
    choice = input("\nEnter the number of the AI you want to use: ")
    try:
        choice_idx = int(choice) - 1
        selected = providers[choice_idx] if 0 <= choice_idx < len(providers) else "local"
    except ValueError:
        selected = "local"
        
    config = AI_PROVIDERS[selected]
    
    # Update the global OpenAI client
    client = OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        timeout=45.0
    )
    CURRENT_PROVIDER = selected
    
    # If it's local, ask for the specific model. Otherwise use the default cloud model.
    if selected == "local":
        ACTIVE_MODEL = select_local_model()
    else:
        ACTIVE_MODEL = config["default_model"]
        
    print(f"\n✅ [Successfully connected to {selected.upper()} using model: {ACTIVE_MODEL}]\n")
switch_ai_provider()
# --- NEW: MODEL SELECTOR ---

# 👉 NEW: The exact word needed to end the conversation
STOP_WORD = "terminate"

# --- VOICE LOGIC ---
def get_voice_input():
    recognizer = sr.Recognizer()
    
    # 1. Keeps the 1.2s breathing room
    recognizer.pause_threshold = 1.2 
    
    # 2. NEW: Automatically adjusts the microphone sensitivity based on room noise!
    recognizer.dynamic_energy_threshold = True 
    
    with sr.Microphone() as source:
        print("\n[Listening...]")
        winsound.Beep(800, 200) 
        
        # 3. Listens to the room for 1 second to calibrate before you speak
        recognizer.adjust_for_ambient_noise(source, duration=1)
        
        try:
            # 4. NEW: phrase_time_limit=15 forces it to process what you said after 15 seconds max, 
            # so it never gets permanently stuck recording a noisy room.
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
            
            text = recognizer.recognize_google(audio)
            print(f"You: {text}")
            return text
            
        except sr.UnknownValueError:
            # Happens if you cough or the mic picks up a random noise
            print("[Didn't catch that...]")
            return None
        except sr.WaitTimeoutError:
            # Happens if you don't say anything
            return None
        except Exception as e:
            return None

def speak(text):
    if USE_VOICE_RESPONSE:
        try:
            # Still scrub the text so emojis don't break the Windows engine
            clean_text = re.sub(r'[^\x00-\x7F]+', '', text) 
            clean_text = clean_text.replace('*', '').replace('#', '').replace('_', '')
            
            if not clean_text.strip(): 
                return
            
            # Connect directly to the core Windows Voice Engine (bypassing pyttsx3 bugs)
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            
            # Optional: You can speed up the voice here (-10 to 10). 0 is normal.
            speaker.Rate = 3            
            speaker.Speak(clean_text)
            
        except Exception as e:
            print(f"\n[Audio Engine Error: {e}]")
# --- MEMORY SETUP ---  
MAX_MEMORY_LENGTH = 15 
# Initialize empty list first so the global variable exists
conversation_history = [] 

def reset_conversation():
    global conversation_history, CURRENT_PROVIDER
    
    if CURRENT_PROVIDER == "gemini":
        identity = "You are Gemini, an advanced AI connected via Google API."
    elif CURRENT_PROVIDER == "chatgpt":
        identity = "You are ChatGPT, an advanced AI connected via OpenAI API."
    else:
        identity = "You are Gemma, a highly intelligent local AI running on the user's hardware."
        
    system_prompt = f"{identity} You have access to various tools to control the PC. You possess vast general knowledge and can answer questions about history, science, and the world. ADDITIONALLY, you have tools to open apps, read files, search project files, see the screen, and check the weather. If asked to perform an action, use your tools and ALWAYS reply confirming what you did. IMPORTANT: You must strictly use JSON format for tool calls. Never output raw <|tool_call> syntax in your text."
    
    conversation_history = [{"role": "system", "content": system_prompt}]

# Call this right after you select the AI provider!
reset_conversation()
def auto_route_gemini(prompt):
    """Analyzes the prompt to auto-select the best Gemini model."""
    prompt_lower = prompt.lower()
    
    heavy_tasks = [
        "code", "refactor", "error", "debug", "logic", 
        "keras", "opencv", "minimax", "compare", "verify"
    ]
    
    # Rule 1: Complex keywords
    if any(word in prompt_lower for word in heavy_tasks):
        return "gemini-1.5-pro" # Changed from 3.1
        
    # Rule 2: Long prompt context
    if len(prompt) > 150:
        return "gemini-1.5-pro" # Changed from 3.1
        
    # Default: Use Flash for fast, everyday answers
    return "gemini-2.5-flash" 
# --- AGENT BRAIN ---
def run_agent(user_prompt):
    global ACTIVE_MODEL, CURRENT_PROVIDER
    
    # --- NEW: INTERCEPT AND AUTO-ROUTE GEMINI ---
    if CURRENT_PROVIDER == "gemini":
        previous_model = ACTIVE_MODEL
        ACTIVE_MODEL = auto_route_gemini(user_prompt)
        
        # Just to let you know in the terminal if it switched gears
        if previous_model != ACTIVE_MODEL:
            print(f"🔄 [Auto-Router]: Switched engine to {ACTIVE_MODEL}")
    # --------------------------------------------

    # ... (Keep the rest of your run_agent code exactly as it is below this)
    # messages.append({"role": "user", "content": prompt})
    # response = client.chat.completions.create(...)
    global conversation_history
    conversation_history.append({"role": "user", "content": user_prompt})
    
    try:
        response = client.chat.completions.create(model=ACTIVE_MODEL, messages=conversation_history, tools=tools)
        msg = response.choices[0].message
        conversation_history.append(msg)

        if msg.tool_calls:
            for tool in msg.tool_calls:
                name = tool.function.name
                args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                print(f"--- [Action]: {name} ---")
                
                tool_res = ""
                
                # These tools are pulled perfectly from my_tools.py!
                
                if name == "lock_screen": tool_res = lock_screen()
                elif name == "get_system_stats": tool_res = get_system_stats()
                elif name == "open_application": tool_res = open_application(args.get("app_name"))
                elif name == "list_project_files": tool_res = list_project_files()
                elif name == "read_text_file": tool_res = read_text_file(args.get("filename"))
                elif name == "get_current_time": tool_res = get_current_time()
                elif name == "capture_screen": tool_res = capture_screen()
                elif name == "search_project_files": tool_res = search_project_files(args.get("keyword"))
                elif name == "get_weather": tool_res = get_weather(args.get("location"))
                elif name == "delete_file": tool_res = delete_file(args.get("filename"))
                elif name == "get_gpu_stats": tool_res = get_gpu_stats()
                elif name == "capture_image":
                    filename, b64_img = capture_image()
                    if b64_img is None:
                        tool_res = filename  
                    else:
                        v_msg = [{"role": "user", "content": [{"type": "text", "text": "Describe this photo."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                        v_res = client.chat.completions.create(model=ACTIVE_MODEL, messages=v_msg)
                        description = v_res.choices[0].message.content
                        tool_res = f"Image saved as {filename}. Description of what you see: {description}"
                elif name == "analyze_saved_image":
                    b64_img = analyze_saved_image(args.get("filename"))
                    if "Error" in b64_img: tool_res = b64_img
                    else:
                        # Dynamically check if it's a PNG or JPG
                        filename = args.get('filename', '')
                        mime_type = "image/png" if filename.endswith(".png") else "image/jpeg"
                        
                        v_msg = [{"role": "user", "content": [{"type": "text", "text": f"Analyze {filename}"}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}]}]
                        v_res = client.chat.completions.create(model="local-model", messages=v_msg)
                        tool_res = v_res.choices[0].message.content
                        
                conversation_history.append({"role": "tool", "tool_call_id": tool.id, "name": name, "content": str(tool_res)})

            final = client.chat.completions.create(model=ACTIVE_MODEL, messages=conversation_history)
            answer = final.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": answer})
        else:
            answer = msg.content

        print(f"Gemma: {answer}")
        speak(answer)

        if len(conversation_history) > MAX_MEMORY_LENGTH:
            conversation_history = [conversation_history[0]] + conversation_history[-(MAX_MEMORY_LENGTH-1):]

    except Exception as e:
        print(f"\n[System Error]: LM Studio took too long or dropped connection. ({e})")
        speak("I lost connection to the local server.")
        if conversation_history[-1]["role"] == "user":
            conversation_history.pop()

# --- MAIN LOOP UI FIX ---
gui_root = tk.Tk()
gui_root.withdraw()
task_queue = queue.Queue()

def get_text_input():
    gui_root.attributes('-topmost', True)  
    prompt = simpledialog.askstring("Command Center", "Type your command:", parent=gui_root)
    return prompt

def intercept_command(prompt):
    """
    Checks if a command is simple enough to handle instantly without the AI.
    Returns True if handled, False if it needs to be sent to Gemma.
    """
    # Make everything lowercase so it's easy to check
    text = prompt.lower().strip()

    # --- 1. INSTANT TIME CHECK ---
    if text in ["what time is it", "what's the time", "tell me the time"]:
        print("--- [Instant Action]: get_current_time ---")
        time_str = get_current_time()
        speak(time_str)
        return True

    # --- 2. INSTANT SCREEN LOCK ---
    elif text == "lock my screen" or text == "lock the computer":
        print("--- [Instant Action]: lock_screen ---")
        speak("Locking the computer now.")
        lock_screen()
        return True
    
    # --- 3. INSTANT AI SWITCHER ---
    elif text in ["switch ai", "change ai", "change provider", "switch model"]:
        print("--- [Instant Action]: switch_ai_provider ---")
        speak("Switching A.I. Check your terminal to select the provider.")
        switch_ai_provider() # Triggers the terminal menu again
        
        # When done, clear the history so the new AI doesn't get confused by the old AI's context 
        global conversation_history
        reset_conversation() 
        
        speak("Ready.")
        return True

    # If nothing matched our instant list, return False to wake up the AI
    return False

def wake_agent_voice():
    """Triggered by the voice hotkey. Loops until the stop word is spoken."""
    print("\n[Voice Mode Activated]")
    speak("I am listening.")  # Tells your mom it's ready!
    
    while True:
        prompt = get_voice_input()
        
        if prompt:
            # If it's the stop word, go to sleep
            if prompt.strip().lower() == STOP_WORD:
                print(f"\n[Stop Word '{STOP_WORD}' Detected. Going to sleep.]")
                speak("Goodbye.")
                break  
            
            # 👉 NEW: Try to intercept the command instantly!
            handled_locally = intercept_command(prompt)
            
            # If the interceptor didn't know what to do with it, wake up the big AI
            if not handled_locally:
                run_agent(prompt)
            
            print("\n[Continuing conversation... waiting for next command or stop word.]")

def wake_agent_text():
    print("\n[Text Active] Awaiting manual input...")
    prompt = get_text_input()
    if prompt: 
        # Check the fast-lane first
        handled_locally = intercept_command(prompt)
        if not handled_locally:
            run_agent(prompt)

def trigger_voice(): task_queue.put("voice")
def trigger_text(): task_queue.put("text")

if __name__ == "__main__":  
    print("\n" + "="*40)
    print("🚀 LOCAL COMMAND CENTER: ACTIVE")
    print("🎤 Voice Hotkey: 'F9'")
    print("⌨️  Text Hotkey: 'F10'")
    print(f"🛑 Say exactly '{STOP_WORD}' to end a voice conversation.")
    print("Hold 'esc' to safely shut down.")
    print("="*40)

    # The new, finger-friendly hotkeys
    keyboard.add_hotkey('f9', trigger_voice)
    keyboard.add_hotkey('f10', trigger_text)

    while True:
        if keyboard.is_pressed('esc'):
            print("\nShutting down Command Center.")
            break
        
        try:
            task = task_queue.get(timeout=0.1)
            if task == "text": wake_agent_text()
            elif task == "voice": wake_agent_voice()
        except queue.Empty: pass