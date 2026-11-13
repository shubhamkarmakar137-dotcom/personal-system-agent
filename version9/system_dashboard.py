import os
import sys
import time
import subprocess
import platform

def get_cpu_ram():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        return cpu, ram.percent, ram.used / (1024**3), ram.total / (1024**3)
    except ImportError:
        try:
            output = subprocess.check_output("wmic cpu get LoadPercentage", shell=True).decode(errors='ignore')
            lines = [line.strip() for line in output.split('\n') if line.strip().isdigit()]
            cpu = float(lines[0]) if lines else 0.0
        except Exception:
            cpu = 0.0
        try:
            output = subprocess.check_output("wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /Value", shell=True).decode(errors='ignore')
            lines = [l.strip() for l in output.split('\n') if '=' in l]
            kv = dict(l.split('=', 1) for l in lines)
            total_kb = float(kv.get('TotalVisibleMemorySize', 1))
            free_kb = float(kv.get('FreePhysicalMemory', 0))
            used_gb = (total_kb - free_kb) / (1024**2)
            total_gb = total_kb / (1024**2)
            ram_pct = ((total_kb - free_kb) / total_kb) * 100
        except Exception:
            ram_pct, used_gb, total_gb = 0.0, 0.0, 0.0
        return cpu, ram_pct, used_gb, total_gb

def get_gpu_info():
    try:
        output = subprocess.check_output("nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits", shell=True).decode(errors='ignore')
        name, temp, util, mem_used, mem_total = [x.strip() for x in output.strip().split(',')]
        return f"{name}\n            Temperature: {temp}C | Core Load: {util}%\n            VRAM Usage:  {mem_used} MB / {mem_total} MB"
    except Exception:
        return "NVIDIA GPU stats offline or integrated graphics in use."

def main():
    cpu, ram_pct, ram_used, ram_total = get_cpu_ram()
    gpu_info = get_gpu_info()
    
    print("\n" + "="*60)
    print("          SYSTEM HEALTH & PERFORMANCE DASHBOARD          ")
    print("="*60)
    print(f" Platform:   {platform.system()} {platform.release()} ({platform.machine()})")
    print(f" CPU Load:   [{'#' * int(cpu // 5)}{'-' * (20 - int(cpu // 5))}] {cpu:.1f}%")
    print(f" RAM Load:   [{'#' * int(ram_pct // 5)}{'-' * (20 - int(ram_pct // 5))}] {ram_pct:.1f}% ({ram_used:.2f} GB / {ram_total:.2f} GB)")
    print(f" GPU Info:   {gpu_info}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
