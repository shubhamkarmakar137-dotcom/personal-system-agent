import os
import subprocess
import pyautogui
import psutil
import ctypes
import cv2
import base64
import webbrowser
import time
import datetime
import requests
import pynvml
import traceback

# --- CONFIGURATION ---
MEDIA_FOLDER = "agent_captures"
MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1MB limit for reading text files
os.makedirs(MEDIA_FOLDER, exist_ok=True)
# Add this to my_tools4.py

def append_to_memory(info_to_save):
    """Appends important information or notes to long-term memory."""
    try:
        memory_file = "memory.txt"
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(f"- {info_to_save.strip()}\n")
        return f"Successfully saved to memory: {info_to_save}"
    except Exception as e:
        return f"Error writing to memory file: {str(e)}"
    
def search_project_files(keyword):
    """Searches all text files in the folder for a keyword and returns their content."""
    allowed_extensions = {'.txt', '.py', '.md', '.json', '.csv'}
    found_content = []
    
    try:
        for filename in os.listdir('.'):
            _, ext = os.path.splitext(filename)
            if not os.path.isfile(filename) or ext.lower() not in allowed_extensions:
                continue
                
            if os.path.getsize(filename) > MAX_FILE_SIZE_BYTES:
                continue

            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if keyword.lower() in content.lower():
                        found_content.append(f"--- FILE: {filename} ---\n{content[:2000]}") 
            except Exception:
                pass 
                    
        if found_content:
            return f"Found '{keyword}' in the following files:\n\n" + "\n\n".join(found_content)
        else:
            return f"No files found containing the keyword '{keyword}'."
            
    except Exception as e:
        print("\n[Tool Error - search_project_files]:")
        traceback.print_exc()
        return f"Error searching files: {str(e)}"
    
def get_weather(location="Howrah"):
    """Gets the current weather for a specified city."""
    try:
        clean_loc = location.strip('"').strip("'")
        url = f"https://wttr.in/{clean_loc}?format=%C,+with+a+temperature+of+%t"
        response = requests.get(url)
        
        if response.status_code == 200:
            return f"The weather in {clean_loc} is {response.text}."
        else:
            return f"Error: Could not check weather for {clean_loc}."
    except Exception as e:
        print("\n[Tool Error - get_weather]:")
        traceback.print_exc()
        return f"Error getting weather: {str(e)}"
    
def get_current_time():
    """Returns the current real-world date and time."""
    now = datetime.datetime.now()
    return now.strftime("The current date and time is %A, %B %d, %Y at %I:%M %p.")

def list_project_files():
    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    return f"Files in your folder: {', '.join(files)}"

def read_text_file(filename):
    try:
        clean_path = os.path.basename(filename.strip('"').strip("'"))
        
        # Fuzzy check: If exact path doesn't exist, try matching normalized filenames in current folder
        if not os.path.exists(clean_path):
            existing_files = [f for f in os.listdir('.') if os.path.isfile(f)]
            normalized_target = clean_path.replace('.', '').replace('_', '').lower()
            for f in existing_files:
                if f.replace('.', '').replace('_', '').lower() == normalized_target:
                    clean_path = f
                    break

        if os.path.getsize(clean_path) > MAX_FILE_SIZE_BYTES:
             return f"Error: File '{clean_path}' is too large to read."
        with open(clean_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print("\n[Tool Error - read_text_file]:")
        traceback.print_exc()
        return f"Error reading {filename}: {str(e)}"

def analyze_saved_image(filename):
    try:
        clean_name = os.path.basename(filename.strip('"').strip("'"))
        target_path = os.path.join(MEDIA_FOLDER, clean_name)
        
        with open(target_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print("\n[Tool Error - analyze_saved_image]:")
        traceback.print_exc()
        return f"Error: Could not open {filename}. Details: {str(e)}"

def delete_file(filename):
    try:
        clean_name = os.path.basename(filename.strip('"').strip("'"))
        if os.path.exists(clean_name):
            os.remove(clean_name)
            return f"Successfully deleted {clean_name}."
            
        media_path = os.path.join(MEDIA_FOLDER, clean_name)
        if os.path.exists(media_path):
            os.remove(media_path)
            return f"Successfully deleted {media_path}."
            
        return f"Error: File {filename} not found."
    except Exception as e:
        print("\n[Tool Error - delete_file]:")
        traceback.print_exc()
        return f"Error deleting file: {str(e)}"
    
def capture_image():
    cam = cv2.VideoCapture(0)
    ret, frame = cam.read()
    if not ret:
        cam.release()
        return "Error: Could not access webcam.", None
    
    timestamp = int(time.time())
    filename = f"webcam_{timestamp}.jpg"
    filepath = os.path.join(MEDIA_FOLDER, filename)
    
    cv2.imwrite(filepath, frame)
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_string = base64.b64encode(buffer).decode('utf-8')
    cam.release()
    return filepath, encoded_string

def capture_screen():
    try:
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(MEDIA_FOLDER, filename)
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        return f"Screenshot saved as {filepath}"
    except Exception as e:
        print("\n[Tool Error - capture_screen]:")
        traceback.print_exc()
        return f"Error capturing screen: {str(e)}"

def lock_screen():
    if "win" in os.sys.platform:
        ctypes.windll.user32.LockWorkStation()
        return "Computer locked."
    return "Not supported on this OS."

def get_system_stats():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return f"CPU is at {cpu} percent and RAM is at {ram} percent."

def get_gpu_stats():
    """Fetches NVIDIA GPU temperature and utilization."""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0) 
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        pynvml.nvmlShutdown()
        
        return f"GPU core temperature is {temp}°C with {util.gpu}% utilization."
    except Exception as e:
        print("\n[Tool Error - get_gpu_stats]:")
        traceback.print_exc()
        return f"Error reading GPU stats. Make sure you have an NVIDIA GPU and drivers installed. Details: {str(e)}"
    
def open_application(app_name):
    app_map = {
        "calculator": "calc", "excel": "excel", "word": "winword", 
        "powerpoint": "powerpnt", "file explorer": "explorer", 
        "notepad": "notepad", "chrome": "chrome", "browser": "msedge",
        "vs code": "code", "code": "code", "visual studio code": "code", "vscode": "code"
    }
    clean_name = app_name.lower().strip()
    target = app_map.get(clean_name, clean_name)    
    try:
        if any(target.startswith(prefix) for prefix in ["http://", "https://", "www."]):
            webbrowser.open(app_name)
            return f"Successfully opened URL: {target}"
        if "win" in os.sys.platform:
            exit_code = os.system(f'start "" "{target}"')
            if exit_code != 0: return f"Error: Could not find or open '{app_name}'."
            return f"Successfully opened {app_name}"
        else:
            subprocess.Popen(["open", "-a", app_name])
            return f"Successfully opened {app_name}"
    except Exception as e:
        print("\n[Tool Error - open_application]:")
        traceback.print_exc()
        return f"Error: {str(e)}"
def write_text_file(filename, content):
    """Creates a new text file or overwrites an existing one with the given content."""
    try:
        clean_path = os.path.basename(filename.strip('"').strip("'"))
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote content to file '{clean_path}'."
    except Exception as e:
        print("\n[Tool Error - write_text_file]:")
        traceback.print_exc()
        return f"Error writing to file {filename}: {str(e)}"

def edit_text_file(filename, find_text, replace_text):
    """Finds specific text in an existing file and replaces it with new text."""
    try:
        clean_path = os.path.basename(filename.strip('"').strip("'"))

        # Fuzzy check: match close filename if exact path doesn't exist
        if not os.path.exists(clean_path):
            existing_files = [f for f in os.listdir('.') if os.path.isfile(f)]
            normalized_target = clean_path.replace('.', '').replace('_', '').lower()
            for f in existing_files:
                if f.replace('.', '').replace('_', '').lower() == normalized_target:
                    clean_path = f
                    break

        if not os.path.exists(clean_path):
            return f"Error: File '{clean_path}' not found."

        with open(clean_path, "r", encoding="utf-8") as f:
            content = f.read()

        if find_text not in content:
            return f"Error: Could not find the text '{find_text}' inside '{clean_path}'."

        new_content = content.replace(find_text, replace_text)

        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Successfully updated '{clean_path}'."

    except Exception as e:
        print("\n[Tool Error - edit_text_file]:")
        traceback.print_exc()
        return f"Error editing file {filename}: {str(e)}"
# --- TOOL LIST ---
tools = [
    {"type": "function", "function": {"name": "lock_screen", "description": "Locks the PC"}},
    {"type": "function", "function": {"name": "get_system_stats", "description": "Checks CPU/RAM"}},
    {"type": "function", "function": {"name": "capture_image", "description": "Takes a photo from webcam"}},
    {"type": "function", "function": {"name": "capture_screen", "description": "Captures a screenshot"}},
    {"type": "function", "function": {"name": "list_project_files", "description": "Lists all files"}},
    {"type": "function", "function": {"name": "read_text_file", "description": "Reads a text file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "analyze_saved_image", "description": "Analyzes an image.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "open_application", "description": "Opens Windows apps or URLs.", "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Deletes a specified file.", "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}}},
    {"type": "function", "function": {"name": "get_current_time", "description": "Gets the current real-world time and date."}},
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets the current real-world weather for a specified location.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "The city to check the weather for."}},
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_project_files",
            "description": "Searches all text-based files in the folder for a specific keyword and reads their contents.",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "The topic, word, or phrase to search for."}},
                "required": ["keyword"]
            }
        }
    },
    {"type": "function", "function": {"name": "get_gpu_stats", "description": "Checks GPU core temperature and utilization."}},
    {
    "type": "function",
    "function": {
        "name": "append_to_memory",
        "description": "Saves key long-term facts, user preferences, or important notes to a file so they persist across resets.",
        "parameters": {
            "type": "object",
            "properties": {
                "info_to_save": {
                    "type": "string", 
                    "description": "The exact fact or note to save."
                }
            },
            "required": ["info_to_save"]
        }
    }
    },
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": "Creates a new text file or overwrites an existing file with specified text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the file to save (e.g. 'notes.txt', 'script.py')."
                    },
                    "content": {
                        "type": "string",
                        "description": "The exact text content to write into the file."
                    }
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_text_file",
            "description": "Finds specific text in an existing file and replaces it with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the file to edit."
                    },
                    "find_text": {
                        "type": "string",
                        "description": "The exact existing text or block of code to find and replace."
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "The new text or block of code to insert in its place."
                    }
                },
                "required": ["filename", "find_text", "replace_text"]
            }
        }
    },
]