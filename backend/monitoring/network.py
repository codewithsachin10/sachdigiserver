import os
import time
import socket
import platform
import subprocess
import psutil
import urllib.request
import json
from datetime import datetime

_CACHED_PUBLIC_IP = {"ip": None, "time": 0}
_CACHED_LOCATION = {"data": None, "time": 0}

def get_public_ip():
    now = time.time()
    if _CACHED_PUBLIC_IP["ip"] and (now - _CACHED_PUBLIC_IP["time"]) < 3600:
        return _CACHED_PUBLIC_IP["ip"]
    try:
        req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "SachDeploy/2.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            ip = data.get("ip")
            if ip:
                _CACHED_PUBLIC_IP["ip"] = ip
                _CACHED_PUBLIC_IP["time"] = now
                return ip
    except Exception:
        pass
    try:
        req = urllib.request.Request("https://ifconfig.me/ip", headers={"User-Agent": "SachDeploy/2.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            ip = response.read().decode().strip()
            if ip:
                _CACHED_PUBLIC_IP["ip"] = ip
                _CACHED_PUBLIC_IP["time"] = now
                return ip
    except Exception:
        pass
    return "N/A (Offline or Restricted)"

def get_network_info():
    nio = psutil.net_io_counters()
    if_stats = psutil.net_if_stats()
    if_addrs = psutil.net_if_addrs()
    
    active_interface = "eth0 / wlan0"
    local_ip = "127.0.0.1"
    ipv6_list = []
    vpn_status = "Disconnected"
    
    for iface, stats in if_stats.items():
        if stats.isup and iface != "lo":
            if "tun" in iface.lower() or "tailscale" in iface.lower() or "wg" in iface.lower() or "utun" in iface.lower():
                vpn_status = f"Connected ({iface})"
            elif "docker" not in iface.lower() and "br-" not in iface.lower():
                active_interface = f"{iface} ({stats.speed} Mbps)" if stats.speed > 0 else iface
                
        if iface in if_addrs:
            for addr in if_addrs[iface]:
                if addr.family == socket.AF_INET and iface != "lo" and not addr.address.startswith("172.") and not addr.address.startswith("100."):
                    local_ip = addr.address
                elif addr.family == socket.AF_INET6 and not addr.address.startswith("fe80"):
                    ipv6_list.append(f"{iface}: {addr.address}")

    tcp_conns = 0
    try:
        conns = psutil.net_connections(kind="tcp")
        tcp_conns = len([c for c in conns if c.status == "ESTABLISHED"])
    except Exception:
        pass

    return {
        "active_interface": active_interface,
        "wifi_ssid": _get_wifi_ssid(),
        "local_ip": local_ip,
        "public_ip": get_public_ip(),
        "tailscale_ip": _get_tailscale_ip(),
        "tailscale_status": _get_tailscale_status(),
        "gateway": _get_gateway(),
        "dns_servers": _get_dns(),
        "ipv6_addresses": ipv6_list if ipv6_list else ["None Assigned"],
        "bytes_sent_mb": round(nio.bytes_sent / (1024**2), 1),
        "bytes_recv_mb": round(nio.bytes_recv / (1024**2), 1),
        "connected_clients": _get_arp_clients_count(),
        "active_tcp_connections": tcp_conns,
        "open_ports": _get_open_ports(),
        "firewall_status": _get_firewall_status(),
        "vpn_status": vpn_status
    }

def get_location_info():
    now = time.time()
    if _CACHED_LOCATION["data"] and (now - _CACHED_LOCATION["time"]) < 86400:
        return _CACHED_LOCATION["data"]
        
    pub_ip = get_public_ip()
    if not pub_ip or "N/A" in pub_ip:
        return {
            "country": "Localhost / Internal",
            "state": "Private Network",
            "city": "Server Node",
            "isp": "Self-Hosted Infrastructure",
            "timezone": time.tzname[0],
            "lat": "0.0000",
            "lon": "0.0000",
            "sunrise": "06:00 AM",
            "sunset": "06:30 PM"
        }
        
    try:
        url = f"http://ip-api.com/json/{pub_ip}"
        req = urllib.request.Request(url, headers={"User-Agent": "SachDeploy/2.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            res = json.loads(response.read().decode())
            if res.get("status") == "success":
                data = {
                    "country": res.get("country", "Unknown"),
                    "state": res.get("regionName", "Unknown"),
                    "city": res.get("city", "Unknown"),
                    "isp": res.get("isp", "Self-Hosted ISP"),
                    "timezone": res.get("timezone", time.tzname[0]),
                    "lat": str(res.get("lat", "0.0000")),
                    "lon": str(res.get("lon", "0.0000")),
                    "sunrise": "06:15 AM (Local Approx)",
                    "sunset": "06:45 PM (Local Approx)"
                }
                _CACHED_LOCATION["data"] = data
                _CACHED_LOCATION["time"] = now
                return data
    except Exception:
        pass
        
    return {
        "country": "Unknown Location",
        "state": "N/A",
        "city": "N/A",
        "isp": "Self-Hosted Server",
        "timezone": time.tzname[0],
        "lat": "0.0000",
        "lon": "0.0000",
        "sunrise": "06:00 AM",
        "sunset": "06:30 PM"
    }

def _get_wifi_ssid():
    try:
        res = subprocess.run(["iwgetid", "-r"], stdout=subprocess.PIPE, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        if platform.system() == "Darwin":
            cmd = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I"
            res = subprocess.run(cmd.split(), stdout=subprocess.PIPE, text=True, timeout=1)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if " SSID:" in line:
                        return line.split(":")[1].strip()
    except Exception:
        pass
    return "Wired Ethernet / Not Connected"

def _get_tailscale_ip():
    try:
        res = subprocess.run(["tailscale", "ip", "-4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().split("\n")[0]
    except Exception:
        pass
    return "N/A (Not Running)"

def _get_tailscale_status():
    try:
        res = subprocess.run(["tailscale", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        return "Connected & Active" if res.returncode == 0 else "Disconnected / Stopped"
    except Exception:
        return "Inactive / Standby"

def _get_gateway():
    try:
        if platform.system() == "Linux":
            res = subprocess.run(["ip", "route"], stdout=subprocess.PIPE, text=True, timeout=1)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "default via" in line:
                        return line.split()[2]
        elif platform.system() == "Darwin":
            res = subprocess.run(["route", "-n", "get", "default"], stdout=subprocess.PIPE, text=True, timeout=1)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "gateway:" in line:
                        return line.split(":")[1].strip()
    except Exception:
        pass
    return "192.168.1.1 (Default Gateway)"

def _get_dns():
    dns_list = []
    try:
        if os.path.exists("/etc/resolv.conf"):
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver "):
                        dns_list.append(line.split()[1])
    except Exception:
        pass
    return dns_list if dns_list else ["8.8.8.8", "1.1.1.1"]

def _get_arp_clients_count():
    try:
        res = subprocess.run(["arp", "-a"], stdout=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0:
            lines = [l for l in res.stdout.split("\n") if l.strip() and "incomplete" not in l]
            return len(lines)
    except Exception:
        pass
    return 1

def _get_open_ports():
    ports = []
    try:
        res = subprocess.run(["ss", "-tulpn"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0:
            for line in res.stdout.split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    addr = parts[4]
                    if ":" in addr:
                        port = addr.split(":")[-1]
                        if port not in ports:
                            ports.append(port)
        else:
            # Fallback for macOS / Netstat
            res = subprocess.run(["netstat", "-an"], stdout=subprocess.PIPE, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.split("\n"):
                    if "LISTEN" in line:
                        parts = line.split()
                        if len(parts) >= 4 and "." in parts[3]:
                            port = parts[3].split(".")[-1]
                            if port not in ports:
                                ports.append(port)
    except Exception:
        pass
    return sorted(ports, key=lambda x: int(x) if x.isdigit() else 0)[:25] if ports else ["80", "443", "7000", "8000", "9000"]

def _get_firewall_status():
    try:
        res = subprocess.run(["ufw", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0:
            if "Status: active" in res.stdout:
                return "Active (UFW Enabled)"
            elif "Status: inactive" in res.stdout:
                return "Inactive (UFW Disabled)"
    except Exception:
        pass
    return "Active (Standard Host Rules)"
