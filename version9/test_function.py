import datetime

def custom_diagnostic():
    now = datetime.datetime.now()
    print("=== ULTRON / JARVIS CUSTOM FUNCTION TEST ===")
    print(f"Current System Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate countdown to Shubham's Birthday (July 17)
    current_year = now.year
    bday = datetime.datetime(current_year, 7, 17)
    if now > bday:
        bday = datetime.datetime(current_year + 1, 7, 17)
    
    days_until_bday = (bday - now).days
    
    print(f"Countdown to Shubham's Birthday (July 17): {days_until_bday} days")
    print("Self-Test Result: Custom script created and executed flawlessly.")
    print("===========================================")

if __name__ == "__main__":
    custom_diagnostic()
