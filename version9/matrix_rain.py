import random
import time
import os
import sys

# Color codes for terminal
GREEN = "\033[32m"
BRIGHT_GREEN = "\033[92m"
WHITE = "\033[97m"
RESET = "\033[0m"

# Kana & ASCII character set for authentic matrix rain effect
CHARS = "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ1234567890ABCDEF@#$%&*+<>?"

def main():
    # Enable ANSI escape sequences on Windows
    os.system('')
    
    # Get terminal size
    try:
        columns, rows = os.get_terminal_size()
    except OSError:
        columns, rows = 80, 24
        
    drops = [0] * columns
    
    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    print(WHITE + "=== MATRIX STREAM INITIATED (Press Ctrl+C to exit) ===" + RESET)
    time.sleep(1)
    
    try:
        while True:
            line = []
            for i in range(columns):
                if drops[i] == 0:
                    if random.random() > 0.95:
                        drops[i] = random.randint(5, rows)
                        line.append(WHITE + random.choice(CHARS))
                    else:
                        line.append(" ")
                else:
                    drops[i] -= 1
                    if drops[i] == 1:
                        line.append(BRIGHT_GREEN + random.choice(CHARS))
                    else:
                        line.append(GREEN + random.choice(CHARS))
                        
            sys.stdout.write("".join(line) + "\n")
            sys.stdout.flush()
            time.sleep(0.04)
            
    except KeyboardInterrupt:
        # Restore cursor
        sys.stdout.write("\033[?25h" + RESET)
        sys.stdout.flush()
        print("\n[!] Matrix connection terminated.")

if __name__ == "__main__":
    main()
