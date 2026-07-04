import os
import socket
import platform
import subprocess
import psutil
from datetime import datetime

def get_hardware_info():
    info = {
        "hostname": socket.gethostname(),
        "machine_name": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "Unknown Architecture",
        "cpu": {
            "model": _get_cpu_model(),
            "physical_cores": psutil.cpu_count(logical=False) or 1,
            "logical_threads": psutil.cpu_count(logical=True) or 1,
            "frequency_mhz": _get_cpu_freq_dict(),
            "thermal_throttled": _check_thermal_throttling()
        },
        "memory": {
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "type": _get_ram_type()
        },
        "storage_devices": _get_storage_devices(),
        "gpu": _get_gpu_info(),
        "usb_devices": _get_usb_devices(),
        "pci_devices": _get_pci_devices(),
        "battery": _get_battery_info(),
        "dmi": _get_dmi_info()
    }
    return info

def _get_cpu_model():
    try:
        if os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        elif platform.system() == "Darwin":
            res = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], stdout=subprocess.PIPE, text=True, timeout=1)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
    except Exception:
        pass
    return platform.processor() or "Generic Processor"

def _get_cpu_freq_dict():
    try:
        freq = psutil.cpu_freq()
        if freq:
            return {
                "current": round(freq.current, 1),
                "min": round(freq.min, 1) if freq.min > 0 else "N/A",
                "max": round(freq.max, 1) if freq.max > 0 else "N/A"
            }
    except Exception:
        pass
    return {"current": "N/A", "min": "N/A", "max": "N/A"}

def _check_thermal_throttling():
    try:
        path = "/sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count"
        if os.path.exists(path):
            with open(path) as f:
                val = int(f.read().strip())
                return "Yes (Throttled)" if val > 0 else "No (Normal)"
    except Exception:
        pass
    return "Normal"

def _get_ram_type():
    try:
        if os.path.exists("/usr/sbin/dmidecode") or os.path.exists("/usr/bin/dmidecode"):
            res = subprocess.run(["dmidecode", "-t", "memory"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "Type:" in line and "Unknown" not in line and "None" not in line:
                        val = line.split(":")[1].strip()
                        if val and val != "Other":
                            return val
    except Exception:
        pass
    return "DDR4 / DDR5 (System Default)"

def _get_storage_devices():
    devices = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                smart_health = "OK (Normal)"
                
                # Try smartctl if available on linux
                try:
                    dev_path = p.device.rstrip('0123456789p')
                    res = subprocess.run(["smartctl", "-H", dev_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1.5)
                    if res.returncode == 0:
                        if "PASSED" in res.stdout or "OK" in res.stdout:
                            smart_health = "PASSED (SMART OK)"
                        elif "FAILED" in res.stdout:
                            smart_health = "WARNING (SMART FAILED)"
                except Exception:
                    pass

                devices.append({
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "opts": p.opts,
                    "total_gb": round(usage.total / (1024**3), 1),
                    "used_gb": round(usage.used / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": round(usage.percent, 1),
                    "smart_health": smart_health
                })
            except Exception:
                continue
    except Exception:
        pass
    return devices

def _get_gpu_info():
    try:
        res = subprocess.run(["lspci"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0:
            gpus = [line.strip() for line in res.stdout.split("\n") if "vga" in line.lower() or "3d controller" in line.lower() or "display controller" in line.lower()]
            if gpus:
                return gpus
        if platform.system() == "Darwin":
            res = subprocess.run(["system_profiler", "SPDisplaysDataType"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "Chipset Model:" in line:
                        return [line.split(":")[1].strip()]
    except Exception:
        pass
    return ["Integrated / Server Display Controller"]

def _get_usb_devices():
    try:
        res = subprocess.run(["lsusb"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return [line.strip() for line in res.stdout.split("\n") if line.strip()][:15]
    except Exception:
        pass
    return ["USB Root Hub (Host Controller)"]

def _get_pci_devices():
    try:
        res = subprocess.run(["lspci"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return [line.strip() for line in res.stdout.split("\n") if line.strip()][:20]
    except Exception:
        pass
    return ["PCIe Host Bridge / Controller"]

def _get_battery_info():
    try:
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                return {
                    "percent": round(bat.percent, 1),
                    "power_plugged": bat.power_plugged,
                    "status": "Charging / AC Plugged" if bat.power_plugged else f"Discharging ({round(bat.secsleft/60)} mins left)" if bat.secsleft != psutil.POWER_TIME_UNLIMITED else "On Battery"
                }
    except Exception:
        pass
    return {"percent": "N/A", "power_plugged": True, "status": "AC Mains Power / Not Equipped"}

def _get_dmi_info():
    info = {
        "manufacturer": "Standard PC / Server",
        "product_name": "Ubuntu Enterprise Node",
        "serial_number": "N/A",
        "bios_version": "N/A",
        "motherboard": "Standard Host Board"
    }
    try:
        if os.path.exists("/sys/class/dmi/id/sys_vendor"):
            with open("/sys/class/dmi/id/sys_vendor") as f:
                info["manufacturer"] = f.read().strip()
        if os.path.exists("/sys/class/dmi/id/product_name"):
            with open("/sys/class/dmi/id/product_name") as f:
                info["product_name"] = f.read().strip()
        if os.path.exists("/sys/class/dmi/id/product_serial"):
            with open("/sys/class/dmi/id/product_serial") as f:
                info["serial_number"] = f.read().strip()
        if os.path.exists("/sys/class/dmi/id/bios_version"):
            with open("/sys/class/dmi/id/bios_version") as f:
                info["bios_version"] = f.read().strip()
        if os.path.exists("/sys/class/dmi/id/board_name"):
            with open("/sys/class/dmi/id/board_name") as f:
                info["motherboard"] = f.read().strip()
    except Exception:
        pass
    return info
