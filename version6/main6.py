import json
import speech_recognition as sr
import win32com.client
import os
import re   
import winsound
from openai import OpenAI
import keyboard
import tkinter as tk
from tkinter import simpledialog
import threading
import queue
from dotenv import load_dotenv
import sys
load_dotenv()
from my_tools4 import *

# --- CONFIGURATION ---
USE_VOICE_INPUT = True
USE_VOICE_RESPONSE = True  

AI_PROVIDERS = {
    "local": {
        "base_url": "http://localhost:1234/v1",
        "api_key": "lm-studio",
        "default_model": None 
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY"), 
        "default_model": "gemini-2.5-flash" 
    }
}   

# =======================================================
# 🚀 THE AGENT CLASS
# =======================================================
class CommandCenterAgent:
    def __init__(self):
        """Initializes the agent's state, memory, and UI elements."""
        self.client = None
        self.ACTIVE_MODEL = None
        self.CURRENT_PROVIDER = None
        
        self.conversation_history = []
        self.MAX_MEMORY_LENGTH = 15  
        self.STOP_WORD = "terminate"
        
        if USE_VOICE_RESPONSE:
            try:
                self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
                self.speaker.Rate = 3
            except Exception as e:
                print(f"[Warning: Failed to initialize audio engine: {e}]")
                self.speaker = None
        
        self.gui_root = tk.Tk()
        self.gui_root.withdraw()

        self.switch_ai_provider()
        
        # 🎂 Run startup check after AI and TTS setup
        self.check_birthday_on_launch()
    def check_birthday_on_launch(self):
        """Checks memory.txt on startup and wishes Happy Birthday if dates match."""
        import datetime
    
        # Formats current date as "July 17"
        today_str = datetime.datetime.now().strftime("%B %d")
    
        if os.path.exists("memory.txt"):
            try:
                with open("memory.txt", "r", encoding="utf-8") as f:
                    memory_content = f.read()
                
                # Checks if today's date appears alongside birthday notes in memory.txt
                if "birthday" in memory_content.lower() and today_str in memory_content:
                    wish = f"🎉 Happy Birthday, Shubham! Wishing you an awesome day!"
                    print(f"\n[BIRTHDAY NOTIFICATION]: {wish}\n")
                    self.speak(wish)
            except Exception as e:
                print(f"[Warning: Failed to check birthday on launch: {e}]")

    def reset_conversation(self, clear_history=True):
        """Updates the dynamic system prompt, loading long-term memory facts if available."""
        if self.CURRENT_PROVIDER == "gemini":
            identity = "You are Gemini, an advanced AI connected via Google API."
        else:
            identity = "You are Gemma, a highly intelligent local AI running on the user's hardware."

        # --- READ LONG-TERM MEMORY FILE ---
        memory_content = "No long-term memories stored yet."
        if os.path.exists("memory.txt"):
            try:
                with open("memory.txt", "r", encoding="utf-8") as f:
                    memory_content = f.read().strip()
            except Exception:
                pass

        system_prompt = f"""{identity} You have access to PC control tools.
You possess vast general knowledge and can answer questions about history, science, and the world. ADDITIONALLY, you have tools to open apps, read files, search project files, see the screen, and check the weather. If asked to perform an action, use your tools and ALWAYS reply confirming what you did. IMPORTANT: You must strictly use JSON format for tool calls. Never output raw <|tool_call> syntax in your text.

CRITICAL TOOL INSTRUCTIONS:
You must strictly use the provided JSON schema to call tools. 
DO NOT output raw tool tags in your text response.
NEVER output strings like "<|tool_call>call:function_name{{...}}<tool_call|>".
If you need to analyze an image, you must trigger the JSON tool call silently.

[LONG-TERM MEMORY NOTES]
The following are important facts you must remember across resets:
{memory_content}

CRITICAL INSTRUCTIONS:
1. If the user tells you something vital (their preferences, tasks, important facts), call 'append_to_memory' to save it permanently.
2. Use strict JSON formatting for tools. Never output raw <|tool_call> tags."""

        if clear_history or not self.conversation_history:
            # Full wipe of short-term chat messages, but system prompt still carries persistent memory.
            self.conversation_history = [{"role": "system", "content": system_prompt}]
        else:
            # Swapping AI provider: retain recent chat messages while updating system prompt
            self.conversation_history[0] = {"role": "system", "content": system_prompt}

    def select_local_model(self):
        """Fetches local models if LM Studio is selected."""
        try:
            print("\n[Fetching available local models from LM Studio...]")
            models_response = self.client.models.list()
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

    def switch_ai_provider(self):
        """Selector to change the AI provider dynamically."""
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
        
        self.client = OpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
            timeout=45.0
        )
        self.CURRENT_PROVIDER = selected
        
        if selected == "local":
            self.ACTIVE_MODEL = self.select_local_model()
        else:
            self.ACTIVE_MODEL = config["default_model"]
            
        # Retain history when manually switching providers
        self.reset_conversation(clear_history=False)
        print(f"\n✅ [Successfully connected to {selected.upper()} using model: {self.ACTIVE_MODEL}]\n")

    def auto_route_gemini(self, prompt):
        """Analyzes the prompt to auto-select the best Gemini model."""
        prompt_lower = prompt.lower()
        heavy_tasks = [
            "code", "refactor", "error", "debug", "logic", 
            "keras", "opencv", "minimax", "compare", "verify"
        ]
        if any(word in prompt_lower for word in heavy_tasks) or len(prompt) > 150:
            # Update to a newer Pro model
            return "gemini-3.1-pro" 
    
        # Update to a newer Flash model
        return "gemini-3.6-flash"

    # --- VOICE & TEXT IO ---
    def get_voice_input(self):
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.2 
        recognizer.dynamic_energy_threshold = True 
        
        with sr.Microphone() as source:
            print("\n[Listening...]")
            winsound.Beep(800, 200) 
            recognizer.adjust_for_ambient_noise(source, duration=1)
            
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                text = recognizer.recognize_google(audio)
                print(f"You: {text}")
                return text
            except sr.UnknownValueError:
                print("[Didn't catch that...]")
                return None
            except sr.WaitTimeoutError:
                return None
            except Exception:
                return None

    def get_text_input(self):
        self.gui_root.attributes('-topmost', True)  
        prompt = simpledialog.askstring("Command Center", "Type your command:", parent=self.gui_root)
        return prompt

    def speak(self, text):
        if USE_VOICE_RESPONSE and hasattr(self, 'speaker') and self.speaker:
            try:
                clean_text = re.sub(r'[^\x00-\x7F]+', '', text) 
                clean_text = clean_text.replace('*', '').replace('#', '').replace('_', '')
                if not clean_text.strip(): return
                self.speaker.Speak(clean_text)
            except Exception as e:
                print(f"\n[Audio Engine Error: {e}]")

    # --- AGENT LOGIC ---
    def intercept_command(self, prompt):
        text = prompt.lower().strip()

        if text == self.STOP_WORD:
            print(f"\n[Stop Word '{self.STOP_WORD}' Detected.]")
            self.speak("Goodbye.")
            return True

        if text in ["what time is it", "what's the time", "tell me the time"]:
            print("--- [Instant Action]: get_current_time ---")
            self.speak(get_current_time())
            return True

        elif text in ["lock my screen", "lock the computer"]:
            print("--- [Instant Action]: lock_screen ---")
            self.speak("Locking the computer now.")
            lock_screen()
            return True
        
        elif text in ["switch ai", "change ai", "change provider", "switch model"]:
            print("--- [Instant Action]: switch_ai_provider ---")
            self.speak("Switching A.I. Check your terminal to select the provider.")
            self.switch_ai_provider() 
            self.speak("Ready.")
            return True

        return False

    def _handle_tool_leaks(self, msg):
        """Intercepts raw local model tool leaks and executes matching functions dynamically."""
        if msg.content and "<|tool_call>" in msg.content:
            print("\n[System] Intercepted raw tool call leak. Attempting regex parse...")
            match = re.search(r'<\|tool_call\>call:([a-zA-Z0-9_]+)\{(.*?)\}<tool_call\|\>', msg.content)
        
            if match:
                func_name = match.group(1)
                raw_args = match.group(2)
            
                # Parse arguments clean format
                clean_args = raw_args.replace('<|"|>', '"')
                args_dict = {}
                for param in clean_args.split(','):
                    if ':' in param:
                        k, v = param.split(':', 1)
                        args_dict[k.strip().strip('"')] = v.strip().strip('"')

                # Dynamically execute tool function if it exists in my_tools4 module
                if hasattr(sys.modules['my_tools4'], func_name):
                    func = getattr(sys.modules['my_tools4'], func_name)
                    try:
                        tool_res = func(**args_dict) if args_dict else func()
                        self.conversation_history.append({
                            "role": "tool",
                            "name": func_name,
                            "content": str(tool_res)
                        })
                        msg.content = f"Executed {func_name} successfully."
                        return True
                    except Exception as e:
                        print(f"[System Error] Tool leak execution failed: {e}")
        return False

    def run_agent(self, user_prompt):
        if self.CURRENT_PROVIDER == "gemini":
            previous_model = self.ACTIVE_MODEL
            self.ACTIVE_MODEL = self.auto_route_gemini(user_prompt)
            if previous_model != self.ACTIVE_MODEL:
                print(f"🔄 [Auto-Router]: Switched engine to {self.ACTIVE_MODEL}")

        self.conversation_history.append({"role": "user", "content": user_prompt})
        
        try:
            response = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=self.conversation_history, tools=tools)
            msg = response.choices[0].message
            self.conversation_history.append(msg)
            
            # 1. Check for local model format leaks
            self._handle_tool_leaks(msg)

            # 2. Check for standard JSON tool calls
            if msg.tool_calls:
                for tool in msg.tool_calls:
                    name = tool.function.name
                    args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                    print(f"--- [Action]: {name} ---")
                    
                    tool_res = ""
                    if name == "lock_screen": tool_res = lock_screen()
                    elif name == "get_system_stats": tool_res = get_system_stats()
                    elif name == "open_application": tool_res = open_application(args.get("app_name"))
                    elif name == "list_project_files": tool_res = list_project_files()
                    elif name == "read_text_file": tool_res = read_text_file(args.get("filename"))
                    elif name == "append_to_memory": tool_res = append_to_memory(args.get("info_to_save"))
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
                            v_res = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=v_msg)
                            description = v_res.choices[0].message.content
                            tool_res = f"Image saved as {filename}. Description of what you see: {description}"
                    elif name == "analyze_saved_image":
                        b64_img = analyze_saved_image(args.get("filename"))
                        if "Error" in b64_img: tool_res = b64_img
                        else:
                            filename = args.get('filename', '')
                            mime_type = "image/png" if filename.endswith(".png") else "image/jpeg"
                            v_msg = [{"role": "user", "content": [{"type": "text", "text": f"Analyze {filename}"}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}]}]
                            v_res = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=v_msg)
                            tool_res = v_res.choices[0].message.content
                    elif name == "write_text_file": 
                        tool_res = write_text_file(args.get("filename"), args.get("content"))
                    elif name == "edit_text_file":
                        tool_res = edit_text_file(args.get("filename"), args.get("find_text"), args.get("replace_text"))
                            
                    self.conversation_history.append({"role": "tool", "tool_call_id": tool.id, "name": name, "content": str(tool_res)})

                final = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=self.conversation_history)
                answer = final.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": answer})
            else:
                answer = msg.content

            print(f"{self.CURRENT_PROVIDER.capitalize()}: {answer}")
            self.speak(answer)

            if len(self.conversation_history) > self.MAX_MEMORY_LENGTH:
                keep_count = self.MAX_MEMORY_LENGTH - 1
                tail = self.conversation_history[-keep_count:]
                
                first_msg = tail[0]
                is_tool = (isinstance(first_msg, dict) and first_msg.get("role") == "tool") or \
                          (hasattr(first_msg, "role") and getattr(first_msg, "role") == "tool")
                
                if is_tool:
                    keep_count += 1
                    tail = self.conversation_history[-keep_count:]
                    
                self.conversation_history = [self.conversation_history[0]] + tail
            
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                roast_msg = "Sorry, but Gemini seems to have died. Time to kill your computer as well."
                print(f"\n[System Warning]: {roast_msg}")
                self.speak(roast_msg)
        
                # Auto-switch provider config to local
                print("\n[Auto-Switching]: Shifting AI provider to LOCAL (LM Studio)...")
                self.CURRENT_PROVIDER = "local"
                config = AI_PROVIDERS["local"]
        
                self.client = OpenAI(
                    base_url=config["base_url"],
                    api_key=config["api_key"],
                    timeout=45.0
                )
        
                # Automatically grab the first available local model or fall back safely
                try:
                    models_response = self.client.models.list()
                    models = [m.id for m in models_response.data]
                    self.ACTIVE_MODEL = models[0] if models else "local-model"
                except Exception:
                    self.ACTIVE_MODEL = "local-model"
            
                self.reset_conversation(clear_history=False)
                print(f"✅ [Successfully auto-switched to LOCAL using model: {self.ACTIVE_MODEL}]")
                self.speak("Switched to local mode.")

                # Clean last user prompt attempt and retry automatically with Local AI
                if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                    self.conversation_history.pop()
                return self.run_agent(user_prompt)
        
            else:
                print(f"\n[System Error]: The AI provider took too long or dropped connection. ({e})")
                self.speak("I lost connection to the server.")
        
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()

    def wake_agent_voice(self):
        print("\n[Voice Mode Activated]")
        self.speak("I am listening.")  
        
        while True:
            prompt = self.get_voice_input()
            if prompt:
                if prompt.strip().lower() == self.STOP_WORD:
                    print(f"\n[Stop Word '{self.STOP_WORD}' Detected. Going to sleep.]")
                    self.speak("Goodbye.")
                    break  
                
                handled_locally = self.intercept_command(prompt)
                if not handled_locally:
                    self.run_agent(prompt)
                print("\n[Continuing conversation... waiting for next command or stop word.]")

    def wake_agent_text(self):
        print("\n[Text Active] Awaiting manual input...")
        prompt = self.get_text_input()
        if prompt: 
            print(f"You (Text): {prompt}")  # 👈 Added this line!
            handled_locally = self.intercept_command(prompt)
            if not handled_locally:
                self.run_agent(prompt)

# =======================================================
# ⚙️ MAIN EXECUTION & SAFETY NET
# =======================================================
if __name__ == "__main__":  
    print("\n" + "="*40)
    print("🚀 LOCAL COMMAND CENTER: ACTIVATING...")
    print("="*40)
    print("this is the 6th goddaym version of command center agent, with improved error handling and auto-switching between Gemini and Local AI.\n")

    task_queue = queue.Queue()
    def trigger_voice(): task_queue.put("voice")
    def trigger_text():
        while not task_queue.empty():
            try: task_queue.get_nowait()
            except queue.Empty: break
        task_queue.put("text")

    try:
        agent = CommandCenterAgent() 
        
        print("\n🎤 Voice Hotkey: 'F9'")
        print("⌨️  Text Hotkey: 'F10'")
        print(f"🛑 Say exactly '{agent.STOP_WORD}' to end a voice conversation.")
        print("Hold 'esc' to safely shut down.\n")

        keyboard.add_hotkey('f9', trigger_voice)
        keyboard.add_hotkey('f10', trigger_text)

        while True:
            if keyboard.is_pressed('esc'):
                print("\nShutting down Command Center.")
                break
            
            try:
                task = task_queue.get(timeout=0.1)
                if task == "text": 
                    agent.wake_agent_text()
                elif task == "voice": 
                    agent.wake_agent_voice()
            except queue.Empty: 
                pass
                
    except Exception as e:
        print(f"\n[CRITICAL ERROR]: An unhandled error occurred: {e}")

    finally:
        print("\n[CLEANUP INITIATED] Releasing all hardware resources...")
        keyboard.unhook_all()
        try:
            winsound.MessageBeep(1000) 
        except:
            pass
        print("Cleanup complete. Safe to close.")