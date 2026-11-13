import torch
import sounddevice as sd
import re

print("Loading TTS model into VRAM...")
# Force GPU usage for the RTX 4060
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load Silero TTS from PyTorch Hub
model, example_text = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                     model='silero_tts',
                                     language='en',
                                     speaker='v3_en')
model.to(device)

def test_voice(text, speaker_id):
    print(f"Playing voice: {speaker_id}...")
    # Clean the text using your existing regex and replaces
    clean_text = re.sub(r'[^\x00-\x7F]+', '', text).replace('*', '').replace('#', '').replace('_', '')
    
    if clean_text.strip():
        try:
            # Generate the audio tensor on the GPU
            audio = model.apply_tts(text=clean_text, 
                                    speaker=speaker_id, 
                                    sample_rate=48000)
            
            # Play the audio and block until it finishes
            sd.play(audio.cpu().numpy(), 48000)
            sd.wait()
            
        except ValueError as ve:
            print(f"[Error] Speaker {speaker_id} might not exist. Try a number between 0 and 117.")
        except Exception as e:
            print(f"[Audio Engine Error: {e}]")

if __name__ == "__main__":
    print("\nModel loaded successfully! Type 'q' at any time to quit.")
    
    default_text = "Hello Shubham, this is a test to see how my voice sounds on your setup."
    
    while True:
        # Prompt for a speaker number
        user_input = input("\nEnter a speaker number (0-117) or 'q' to quit: ").strip()
        
        if user_input.lower() == 'q':
            print("Exiting voice tester.")
            break
            
        if not user_input.isdigit():
            print("Please enter a valid number.")
            continue
            
        speaker_id = f"en_{user_input}"
        
        # Optional: uncomment the next two lines if you want to type custom text for each test
        # custom_text = input("Enter text to say (press Enter to use default): ").strip()
        # text_to_speak = custom_text if custom_text else default_text
        
        text_to_speak = default_text
        test_voice(text_to_speak, speaker_id)