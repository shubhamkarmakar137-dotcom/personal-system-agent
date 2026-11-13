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
import sys
from dotenv import load_dotenv

load_dotenv()
import my_tools4
from my_tools4 import tools 

# Build a security whitelist from your defined schema
VALID_TOOLS = {t["function"]["name"] for t in tools}

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
        self.check_birthday_on_launch()

    def check_birthday_on_launch(self):
        """Checks memory.txt on startup and wishes Happy Birthday if dates match."""
        import datetime
        today_str = datetime.datetime.now().strftime("%B %d")
    
        if os.path.exists("memory.txt"):
            try:
                with open("memory.txt", "r", encoding="utf-8") as f:
                    memory_content = f.read()
                
                if "birthday" in memory_content.lower() and today_str in memory_content:
                    wish = f"🎉 Happy Birthday, Shubham! Wishing you an awesome day!"
                    print(f"\n[BIRTHDAY NOTIFICATION]: {wish}\n")
                    self.speak(wish)
            except Exception as e:
                print(f"[Warning: Failed to check birthday on launch: {e}]")

    def reset_conversation(self, clear_history=True):
        """Updates the dynamic system prompt, loading long-term memory facts if available."""
        identity = "You are Gemini, an advanced AI connected via Google API." if self.CURRENT_PROVIDER == "gemini" else "You are Gemma, a highly intelligent local AI running on the user's hardware."

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
2. Use strict JSON formatting for tools. Never output raw tags."""

        if clear_history or not self.conversation_history:
            self.conversation_history = [{"role": "system", "content": system_prompt}]
        else:
            self.conversation_history[0] = {"role": "system", "content": system_prompt}

    def select_local_model(self):
        """Fetches local models if LM Studio is selected."""
        try:
            print("\n[Fetching available local models from LM Studio...]")
            models_response = self.client.models.list()
            models = [m.id for m in models_response.data]
            if not models: return "local-model"
                
            print("\n=== AVAILABLE LOCAL MODELS ===")
            for i, model_id in enumerate(models):
                print(f"[{i + 1}] {model_id}")
                
            choice = input("\nEnter model number (or press Enter for default): ")
            if not choice.strip(): return models[0]
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
        self.client = OpenAI(base_url=config["base_url"], api_key=config["api_key"], timeout=45.0)
        self.CURRENT_PROVIDER = selected
        self.ACTIVE_MODEL = self.select_local_model() if selected == "local" else config["default_model"]
            
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
            except (sr.UnknownValueError, sr.WaitTimeoutError, Exception):
                return None

    def get_text_input(self):
        self.gui_root.attributes('-topmost', True)  
        return simpledialog.askstring("Command Center", "Type your command:", parent=self.gui_root)

    def speak(self, text):
        if USE_VOICE_RESPONSE and hasattr(self, 'speaker') and self.speaker:
            try:
                clean_text = re.sub(r'[^\x00-\x7F]+', '', text).replace('*', '').replace('#', '').replace('_', '')
                if clean_text.strip(): self.speaker.Speak(clean_text)
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
            self.speak(my_tools4.get_current_time())
            return True
        if text in ["lock my screen", "lock the computer"]:
            print("--- [Instant Action]: lock_screen ---")
            self.speak("Locking the computer now.")
            my_tools4.lock_screen()
            return True
        if text in ["switch ai", "change ai", "change provider", "switch model"]:
            print("--- [Instant Action]: switch_ai_provider ---")
            self.speak("Switching A.I. Check your terminal to select the provider.")
            self.switch_ai_provider() 
            self.speak("Ready.")
            return True
        return False

    def _handle_tool_leaks(self, msg):
        """Intercepts raw local model tool leaks and executes them safely."""
        if msg.content and "<|tool_call>" in msg.content:
            print("\n[System] Intercepted raw tool call leak. Attempting parse...")
            match = re.search(r'<\|tool_call\>call:([a-zA-Z0-9_]+)\{(.*?)\}<tool_call\|\>', msg.content)
            
            if match:
                func_name = match.group(1)
                raw_args = match.group(2)
                
                # Security check against schema whitelist
                if func_name not in VALID_TOOLS:
                    print(f"[System Security Warning] AI attempted to call unauthorized tool: {func_name}")
                    return False
                    
                clean_args = raw_args.replace('<|"|>', '"').strip()
                args_dict = {}
                
                if clean_args:
                    try:
                        args_dict = json.loads(f"{{{clean_args}}}")
                    except json.JSONDecodeError:
                        pairs = re.findall(r'([a-zA-Z0-9_]+)\s*:\s*(".*?"|\'.*?\'|[^,]+)', clean_args)
                        for k, v in pairs:
                            args_dict[k] = v.strip().strip('\'"')

                if hasattr(my_tools4, func_name):
                    func = getattr(my_tools4, func_name)
                    try:
                        print(f"--- [Action Intercepted]: {func_name} ---")
                        tool_res = func(**args_dict) if args_dict else func()
                        self.conversation_history.append({
                            "role": "user",
                            "content": f"[SYSTEM TOOL EXECUTION OUTPUT FOR '{func_name}']: {tool_res}"
                        })
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
            was_leaked = self._handle_tool_leaks(msg)

            # 2. Check for standard JSON tool calls
            if msg.tool_calls:
                for tool in msg.tool_calls:
                    name = tool.function.name
                    if name not in VALID_TOOLS:
                        print(f"--- [Security Warning]: Ignored unauthorized tool '{name}' ---")
                        continue
                        
                    try:
                        args = json.loads(tool.function.arguments) if tool.function.arguments else {}
                    except json.JSONDecodeError:
                        args = {}
                        print(f"[System Warning] Malformed JSON arguments from tool '{name}'")
                        
                    print(f"--- [Action]: {name} ---")
                    tool_res = ""
                    
                    if name == "capture_image":
                        filename, b64_img = my_tools4.capture_image()
                        if b64_img is None: tool_res = filename  
                        else:
                            try:
                                v_msg = [{"role": "user", "content": [{"type": "text", "text": "Describe this photo."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}]
                                v_res = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=v_msg)
                                tool_res = f"Image saved as {filename}. Description: {v_res.choices[0].message.content}"
                            except Exception as e:
                                tool_res = f"Image saved as {filename} but vision analysis failed: {e}"

                    elif name == "analyze_saved_image":
                        b64_img = my_tools4.analyze_saved_image(args.get("filename"))
                        if "Error" in b64_img: tool_res = b64_img
                        else:
                            try:
                                filename = args.get('filename', '')
                                mime_type = "image/png" if filename.endswith(".png") else "image/jpeg"
                                v_msg = [{"role": "user", "content": [{"type": "text", "text": f"Analyze {filename}"}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}]}]
                                v_res = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=v_msg)
                                tool_res = v_res.choices[0].message.content
                            except Exception as e:
                                tool_res = f"Failed to analyze image with vision model: {e}"

                    else:
                        if hasattr(my_tools4, name):
                            func = getattr(my_tools4, name)
                            try:
                                tool_res = func(**args) if args else func()
                            except TypeError as e:
                                tool_res = f"Error: Incorrect arguments provided to '{name}'. Details: {e}"
                            except Exception as e:
                                tool_res = f"Error executing '{name}': {e}"
                        else:
                            tool_res = f"Error: Tool function '{name}' not found."
                            
                    self.conversation_history.append({"role": "tool", "tool_call_id": tool.id, "name": name, "content": str(tool_res)})

            # 3. Final Completion Generation
            if was_leaked or msg.tool_calls:
                final = self.client.chat.completions.create(model=self.ACTIVE_MODEL, messages=self.conversation_history)
                answer = final.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": answer})
            else:
                answer = msg.content

            if answer:
                print(f"{self.CURRENT_PROVIDER.capitalize()}: {answer}")
                self.speak(answer)

            # 4. Safe Memory Truncation (Prevents API 400 Errors)
            while len(self.conversation_history) > self.MAX_MEMORY_LENGTH:
                # Never pop the system prompt (index 0)
                popped_msg = self.conversation_history.pop(1)
                
                # Check if we just deleted an AI message that contained tool calls
                is_assistant_with_tools = (isinstance(popped_msg, dict) and popped_msg.get("role") == "assistant" and popped_msg.get("tool_calls")) or \
                                          (hasattr(popped_msg, "role") and getattr(popped_msg, "role") == "assistant" and getattr(popped_msg, "tool_calls", None))
                
                # If we did, we MUST also delete the corresponding tool responses that follow it to prevent orphans
                if is_assistant_with_tools:
                    while len(self.conversation_history) > 1:
                        next_msg = self.conversation_history[1]
                        is_tool = (isinstance(next_msg, dict) and next_msg.get("role") == "tool") or \
                                  (hasattr(next_msg, "role") and getattr(next_msg, "role") == "tool")
                        if is_tool:
                            self.conversation_history.pop(1)
                        else:
                            break
            
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                roast_msg = "Sorry, but Gemini seems to have died. Time to kill your computer as well."
                print(f"\n[System Warning]: {roast_msg}")
                self.speak(roast_msg)
        
                print("\n[Auto-Switching]: Shifting AI provider to LOCAL (LM Studio)...")
                self.CURRENT_PROVIDER = "local"
                config = AI_PROVIDERS["local"]
                self.client = OpenAI(base_url=config["base_url"], api_key=config["api_key"], timeout=45.0)
        
                try:
                    models_response = self.client.models.list()
                    models = [m.id for m in models_response.data]
                    self.ACTIVE_MODEL = models[0] if models else "local-model"
                except Exception:
                    self.ACTIVE_MODEL = "local-model"
            
                self.reset_conversation(clear_history=False)
                print(f"✅ [Successfully auto-switched to LOCAL using model: {self.ACTIVE_MODEL}]")
                self.speak("Switched to local mode.")

                if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                    self.conversation_history.pop()
                return self.run_agent(user_prompt)
        
            else:
                print(f"\n[System Error]: The AI provider threw an error: ({e})")
                self.speak("I lost connection to the server or encountered an error.")
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
                if not self.intercept_command(prompt):
                    self.run_agent(prompt)
                print("\n[Continuing conversation... waiting for next command or stop word.]")

    def wake_agent_text(self):
        print("\n[Text Active] Awaiting manual input...")
        prompt = self.get_text_input()
        if prompt: 
            print(f"You (Text): {prompt}")
            if not self.intercept_command(prompt):
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
                if task == "text": agent.wake_agent_text()
                elif task == "voice": agent.wake_agent_voice()
            except queue.Empty: pass
                
    except Exception as e:
        print(f"\n[CRITICAL ERROR]: An unhandled error occurred: {e}")

    finally:
        print("\n[CLEANUP INITIATED] Releasing all hardware resources...")
        keyboard.unhook_all()
        try: winsound.MessageBeep(1000) 
        except: pass
        print("Cleanup complete. Safe to close.")