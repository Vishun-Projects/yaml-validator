#!/usr/bin/env python3
"""
ai_audit_gui_validator.py

Local validator: improved normalization, aliases, user@host detection, plus optional
interactive UI and installed-app collectors for Windows (theme, monitors, resolution,
DPI per-monitor, pointing devices, installed apps).

Usage: python ai_audit_gui_validator.py
"""
from __future__ import annotations
import os
import json
import yaml
import platform
import subprocess
import threading
import time
import re
from typing import Dict, Any, Optional, Tuple, List
import PySimpleGUI as sg
import psutil
import difflib

# Optional pandas support for Excel->YAML
try:
    import pandas as pd
except Exception:
    pd = None

# ---------- Config ----------
REPORT_FILENAME = "audit_report.json"
FUZZY_MATCH_THRESHOLD = 0.85

# ---------- Normalization helpers ----------

def normalize_key(s: Optional[str]) -> str:
    if s is None:
        return ""
    # remove all non-alphanumeric characters and lowercase
    return re.sub(r'[^0-9a-z]', '', str(s).lower())

def normalize_value_for_match(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        try:
            return normalize_key(json.dumps(v, sort_keys=True))
        except Exception:
            return ""
    return normalize_key(str(v))

def fuzzy_ratio(a: str, b: str) -> float:
    try:
        return difflib.SequenceMatcher(None, a, b).ratio()
    except Exception:
        return 0.0

# ---------- Deep lookup ----------

def deep_find_by_normalized_key(obj: Any, target_norm: str, max_depth: int = 8, _visited=None):
    """Recursively search nested dict/list for a key with normalized name == target_norm."""
    if _visited is None:
        _visited = set()
    try:
        oid = id(obj)
        if oid in _visited:
            return None
        _visited.add(oid)
    except Exception:
        pass
    if obj is None or max_depth < 0:
        return None
    if isinstance(obj, dict):
        # direct key normalized match
        for k, v in obj.items():
            if isinstance(k, str) and normalize_key(k) == target_norm:
                return v
        # recurse values
        for v in obj.values():
            res = deep_find_by_normalized_key(v, target_norm, max_depth - 1, _visited)
            if res is not None:
                return res
        return None
    if isinstance(obj, list):
        for item in obj:
            res = deep_find_by_normalized_key(item, target_norm, max_depth - 1, _visited)
            if res is not None:
                return res
        return None
    return None

def deep_search_value_contains(obj: Any, token_norm: str, max_depth: int = 8, _visited=None) -> bool:
    """Return True if token_norm appears in any value (normalized) inside obj."""
    if _visited is None:
        _visited = set()
    try:
        oid = id(obj)
        if oid in _visited:
            return False
        _visited.add(oid)
    except Exception:
        pass
    if obj is None or max_depth < 0:
        return False
    if isinstance(obj, dict):
        for v in obj.values():
            if deep_search_value_contains(v, token_norm, max_depth - 1, _visited):
                return True
        return False
    if isinstance(obj, list):
        for item in obj:
            if deep_search_value_contains(item, token_norm, max_depth - 1, _visited):
                return True
        return False
    try:
        return token_norm in normalize_value_for_match(obj)
    except Exception:
        return False

# ---------- Snapshot dotted-key access (robust) ----------

def get_value_from_snapshot(snapshot: Any, dotted_key: str) -> Optional[Any]:
    """
    Support dotted-key access with:
     - direct key
     - case-insensitive
     - normalized key (strip punctuation/spaces)
     - deep normalized fallback
    """
    if not dotted_key:
        return None
    parts = dotted_key.split(".")
    cur = snapshot
    try:
        for idx, p in enumerate(parts):
            if cur is None:
                return None
            # list indexing attempt
            if isinstance(cur, list):
                try:
                    i = int(p)
                    cur = cur[i]
                    continue
                except Exception:
                    # search each element for remaining path
                    for item in cur:
                        res = get_value_from_snapshot(item, ".".join(parts[idx:]))
                        if res is not None:
                            return res
                    return None
            # dict access
            if isinstance(cur, dict):
                # direct
                if p in cur:
                    cur = cur[p]
                    continue
                # case-insensitive exact
                low = p.lower()
                found_ci = None
                for k, v in cur.items():
                    if isinstance(k, str) and k.lower() == low:
                        found_ci = v
                        break
                if found_ci is not None:
                    cur = found_ci
                    continue
                # normalized exact
                nk = normalize_key(p)
                for k, v in cur.items():
                    if isinstance(k, str) and normalize_key(k) == nk:
                        cur = v
                        break
                else:
                    # fallback: deep normalized key in this dict
                    found = deep_find_by_normalized_key(cur, normalize_key(p))
                    return found
                continue
            # scalar - can't traverse
            return None
        return cur
    except Exception:
        # last-resort deep search
        return deep_find_by_normalized_key(snapshot, normalize_key(dotted_key))

# ---------- Collectors (unchanged + extended) ----------

def _run_powershell_json(ps_script: str, timeout: int = 30) -> Any:
    """
    Helper to run a PowerShell script that outputs JSON via ConvertTo-Json.
    Returns parsed JSON on success, or None on failure.
    """
    try:
        cmd = ["powershell", "-NoProfile", "-Command", ps_script]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=timeout).decode("utf-8", errors="ignore")
        if not out:
            return None
        try:
            return json.loads(out)
        except Exception:
            s = out.strip()
            try:
                return json.loads(s)
            except Exception:
                return None
    except Exception:
        return None

def collect_windows_ui_info_advanced() -> Dict[str, Any]:
    """
    Collect display(s), theme, dpi (best-effort per-monitor), and pointing devices on Windows.
    NOTE: reads HKCU, so must run as the interactive user (or load user's hive).
    """
    ps = r'''
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue | Out-Null
    $out = @{}


    # Try to enumerate screens and per-monitor DPI using shcore/GetDpiForMonitor if available, plus WMI fallback
    try {
        $monitorList = @()
        [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
            $device = $_
            $entry = @{
                DeviceName = $device.DeviceName
                Width = $device.Bounds.Width
                Height = $device.Bounds.Height
                Primary = $device.Primary
            }
            $monitorList += $entry
        }
        # attempt to add per-monitor DPI using shcore if present
        $dpiList = @()
        try {
            $code = @"
using System;
using System.Runtime.InteropServices;
using System.Drawing;
public static class DpiNative {
    [DllImport(\"user32.dll\")]
    public static extern IntPtr MonitorFromPoint(Point pt, uint flags);
    [DllImport(\"shcore.dll\")]
    public static extern int GetDpiForMonitor(IntPtr hmonitor, int dpiType, out uint dpiX, out uint dpiY);
}
"@
            Add-Type -TypeDefinition $code -Language CSharp -ErrorAction Stop
            foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
                $ptX = $s.Bounds.X + [math]::Floor($s.Bounds.Width/2)
                $ptY = $s.Bounds.Y + [math]::Floor($s.Bounds.Height/2)
                $pt = New-Object System.Drawing.Point($ptX, $ptY)
                $h = [DpiNative]::MonitorFromPoint($pt, 2)
                $dx = 0
                $dy = 0
                $refx = [ref]$dx
                $refy = [ref]$dy
                $res = [DpiNative]::GetDpiForMonitor($h, 0, $refx, $refy)
                $entry = @{
                    DeviceName = $s.DeviceName
                    Width = $s.Bounds.Width
                    Height = $s.Bounds.Height
                    Primary = $s.Primary
                    DpiX = $refx.Value
                    DpiY = $refy.Value
                }
                $dpiList += $entry
            }
        } catch {
            $dpiList = @()
        }
        # WMI fallback for monitor info
        $wmiMonitors = Get-WmiObject Win32_DesktopMonitor -ErrorAction SilentlyContinue | Select-Object Name, ScreenWidth, ScreenHeight, PNPDeviceID
        $out.wmi_monitors = $wmiMonitors
        $out.displays = @{
            Screens = $monitorList
            PerMonitorDPI = $dpiList
        }
    } catch {
        $out.displays = $null
    }

    # Keyboard layout via registry and PowerShell
    try {
        $kl = (Get-ItemProperty -Path 'HKCU:\Keyboard Layout\Preload' -ErrorAction SilentlyContinue)."1"
        $langList = (Get-WinUserLanguageList -ErrorAction SilentlyContinue) | Select-Object -ExpandProperty LanguageTag
        $out.keyboard_layout = @{
            Registry = $kl
            WinUserLanguageList = $langList
        }
    } catch {
        $out.keyboard_layout = $null
    }

    # Mouse: WMI, registry, and PnP fallback
    try {
        $m = Get-CimInstance Win32_PointingDevice -ErrorAction SilentlyContinue | Select-Object Name, Manufacturer, Description
        if ($m) {
            $out.mouse = $m
        } else {
            try {
                $p = Get-PnpDevice -Class Mouse -ErrorAction SilentlyContinue | Select-Object FriendlyName, Status
                $out.mouse = $p
            } catch {
                $out.mouse = $null
            }
        }
    } catch {
        $out.mouse = $null
    }

    # Theme (per-user)
    try {
        $themeKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        $apps = (Get-ItemProperty -Path $themeKey -Name 'AppsUseLightTheme' -ErrorAction SilentlyContinue).AppsUseLightTheme
        $system = (Get-ItemProperty -Path $themeKey -Name 'SystemUsesLightTheme' -ErrorAction SilentlyContinue).SystemUsesLightTheme
        if ($null -eq $apps -and $null -eq $system) {
            $out.theme = $null
        } else {
            $out.theme = @{ Apps = $apps; System = $system }
        }
    } catch {
        $out.theme = $null
    }

    # DPI fallback: per-user registry or SystemInformation
    try {
        $dpi = $null
        $dpi = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop' -Name 'LogPixels' -ErrorAction SilentlyContinue).LogPixels
        if (-not $dpi) {
            $dpi = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name 'AppliedDPI' -ErrorAction SilentlyContinue).AppliedDPI
        }
        if (-not $dpi) {
            try { $dpi = [System.Windows.Forms.SystemInformation]::DpiX } catch {}
        }
        $out.dpi = $dpi
    } catch {
        $out.dpi = $null
    }

    # Pointing devices (mouse)
    try {
        $m = Get-CimInstance Win32_PointingDevice -ErrorAction SilentlyContinue | Select-Object Name, Manufacturer, Description
        if ($m) {
            $out.mouse = $m
        } else {
            # fallback to PnP
            try {
                $p = Get-PnpDevice -Class Mouse -ErrorAction SilentlyContinue | Select-Object FriendlyName, Status
                $out.mouse = $p
            } catch {
                $out.mouse = $null
            }
        }
    } catch {
        $out.mouse = $null
    }

    # Video controller info for HDR/SDR and advanced color support (best-effort)
    try {
        $vc = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Select-Object Name, AdapterCompatibility, VideoModeDescription, CurrentBitsPerPixel
        $out.video_controllers = $vc
    } catch {
        $out.video_controllers = $null
    }

    # Convert to JSON
    $out | ConvertTo-Json -Depth 6
    '''
    res = _run_powershell_json(ps, timeout=30)
    return res or {}

def collect_installed_programs() -> List[Dict[str, Any]]:
    """
    Best-effort installed programs collector via registry uninstall keys (HKLM/HKCU 32/64-bit).
    Returns list of dicts: Name, DisplayVersion, Publisher, InstallLocation
    Note: this may be heavy; use opt-in.
    """
    ps = r'''
    $items = @()

    $keys = @(
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($k in $keys) {
        try {
            Get-ItemProperty -Path $k -ErrorAction SilentlyContinue | ForEach-Object {
                if ($_.DisplayName) {
                    $items += @{
                        DisplayName = $_.DisplayName
                        DisplayVersion = ($_.DisplayVersion -as [string])
                        Publisher = ($_.Publisher -as [string])
                        InstallLocation = ($_.InstallLocation -as [string])
                    }
                }
            }
        } catch {}
    }
    # de-dupe by DisplayName
    $uniq = $items | Group-Object DisplayName | ForEach-Object { $_.Group[0] }
    $uniq | ConvertTo-Json -Depth 3
    '''
    res = _run_powershell_json(ps, timeout=40)
    if isinstance(res, list):
        return res
    return []

def collect_windows_full_dump() -> Dict[str, Any]:
    final = {}
    try:
        ps_cmd = ["powershell", "-NoProfile", "-Command", "Get-ComputerInfo | ConvertTo-Json -Depth 3"]
        out = subprocess.check_output(ps_cmd, stderr=subprocess.DEVNULL, timeout=40).decode("utf-8", errors="ignore")
        try:
            final = json.loads(out)
        except Exception:
            final = {"get_computerinfo_raw": out}
    except Exception as e:
        final = {"error": f"windows_dump_failed: {str(e)}"}

    return final

def collect_lshw_json() -> Dict[str, Any]:
    try:
        out = subprocess.check_output(["lshw", "-json"], stderr=subprocess.DEVNULL, timeout=40).decode("utf-8", errors="ignore")
        return json.loads(out)
    except Exception as e:
        return {"error": f"lshw_failed: {str(e)}", "fallback": collect_generic_snapshot()}

def collect_generic_snapshot() -> Dict[str, Any]:
    try:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "swap_total": psutil.swap_memory().total,
            "disk_partitions": [],
            "net_if_addrs": {},
            "boot_time": psutil.boot_time(),
        }
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                usage_d = usage._asdict()
            except Exception:
                usage_d = None
            info["disk_partitions"].append({"device": p.device, "mountpoint": p.mountpoint, "fstype": p.fstype, "opts": p.opts, "usage": usage_d})
        for name, addrs in psutil.net_if_addrs().items():
            info["net_if_addrs"][name] = [{"family": str(a.family), "address": a.address, "netmask": a.netmask, "ptp": a.ptp} for a in addrs]
        return info
    except Exception as e:
        return {"error": f"generic_snapshot_failed: {str(e)}"}

def collect_full_snapshot(interactive_ui: bool = False, collect_apps_flag: bool = False) -> Dict[str, Any]:
    system = platform.system().lower()
    snap = {}
    if system.startswith("win"):
        snap = collect_windows_full_dump()
        # optionally attach UI info (theme, displays, DPI, mouse)
        if interactive_ui:
            try:
                ui = collect_windows_ui_info_advanced()
                if ui:
                    snap.setdefault("ui", {})
                    for k, v in ui.items():
                        snap["ui"][k] = v
            except Exception:
                pass
        # optionally attach installed apps
        if collect_apps_flag:
            try:
                apps = collect_installed_programs()
                if apps:
                    snap["installed_programs"] = apps
            except Exception:
                pass
    elif system.startswith("linux"):
        try:
            snap = collect_lshw_json()
        except Exception:
            snap = collect_generic_snapshot()
    elif system.startswith("darwin"):
        snap = collect_generic_snapshot()
    else:
        snap = collect_generic_snapshot()
    return snap

# ---------- Masking utilities (kept) ----------

def mask_snapshot(snapshot: Dict[str, Any], mask_mac=True, mask_users=True, mask_bios=True, remove_installed=True) -> Dict[str, Any]:
    s = json.loads(json.dumps(snapshot))
    if mask_mac:
        try:
            if "net_if_addrs" in s:
                for iface, addrs in s["net_if_addrs"].items():
                    for a in addrs:
                        if "address" in a and (len(str(a["address"]).split(":")) == 6 or "-" in str(a["address"])):
                            a["address"] = "[MASKED_MAC]"
        except Exception:
            pass
    if mask_users:
        try:
            for k in list(s.keys()):
                if isinstance(s[k], str) and ("user" in k.lower() or "username" in k.lower()):
                    s[k] = "[MASKED_USER]"
            # also mask common nested fields
            def mask_recursive(o):
                if isinstance(o, dict):
                    for kk in list(o.keys()):
                        if isinstance(o[kk], str) and ("user" in kk.lower() or "username" in kk.lower()):
                            o[kk] = "[MASKED_USER]"
                        else:
                            mask_recursive(o[kk])
                elif isinstance(o, list):
                    for it in o:
                        mask_recursive(it)
            mask_recursive(s)
        except Exception:
            pass
    if mask_bios:
        for key in list(s.keys()):
            if key and ("bios" in key.lower() or "dmidecode" in key.lower()):
                s[key] = "[REMOVED_FOR_PRIVACY]"
    if remove_installed:
        for key in list(s.keys()):
            if key and ("installed" in key.lower() or "packages" in key.lower()):
                s[key] = "[REMOVED_PACKAGE_LIST]"
        # also mask installed_programs if present (unless user opted out)
        if "installed_programs" in s:
            s["installed_programs"] = "[REMOVED_PACKAGE_LIST]"
    return s

# ---------- Alias map & special user@host check ----------

ALIAS_MAP = {
    # normalized expected -> list of likely snapshot keys (also normalized)
    "seriesno": ["biosserialnumber", "csname", "osregistereduser", "osregisteredowner", "csprimaryownername"],
    "devicemodel": ["processor", "platform", "release", "machine", "csmodel", "csmanufacturer", "product", "productname", "model", "systemproductname", "osname", "csprocessors", "cstotalphysicalmemory"],
    "oslanguage": ["oslanguage", "os_locale", "oslocale", "osmuilanguages"],
    "applanguage": ["osmuilanguages", "oslanguage", "osmuilanguages"],
    "keyboardinputlayout": ["keyboardlayout", "keyboardlayoutname"],
    "network": ["csnetworkadapters", "ipaddresses", "connectionid", "net_if_addrs"],
    "userlicense": ["osregistereduser", "csprimaryownername"],
    "installmethod": ["installationtype", "windowsinstallationtype"],
    "installlocation": ["oswindowsdirectory", "ossystemdirectory", "disk_partitions"],
    "userdirectorylocation": ["homedirectory", "userprofile", "userdirectory"],
    "ostheme": ["theme", "ostheme", "ui.theme"],
    "resolution": ["resolution", "screenresolution", "displayresolution", "ui.displays"],
    "dpiscaling": ["dpiscale", "dpiscaling", "scaling", "ui.dpi", "ui.displays"],
    "monitors": ["monitors", "display", "screens", "ui.displays"],
    "inputdevice": ["inputdevice", "mouse", "keyboard", "ui.mouse"],
    "branchbetastable": ["branch", "release", "channel", "branch-beta-stable"],
    # direct mappings for your config keys
    "test": ["tester"],
    "seriesno": ["seriesno", "biosserialnumber", "csname"],
    "devicemodel": ["devicemodel", "processor", "platform", "release", "machine"],
    "oslanguage": ["oslanguage", "os_locale"],
    "applanguage": ["applanguage", "osmuilanguages"],
    "keyboardinputlayout": ["keyboardinputlayout", "keyboardlayout", "keyboardlayoutname"],
    "network": ["network", "net_if_addrs"],
    "userlicense": ["userlicense", "osregistereduser"],
    "installmethod": ["installmethod", "installationtype"],
    "installlocation": ["installlocation", "oswindowsdirectory"],
    "userdirectorylocation": ["userdirectorylocation", "userprofile"],
    "ostheme": ["ostheme", "ui.theme"],
    "resolution": ["resolution", "ui.displays"],
    "dpiscaling": ["dpiscaling", "ui.dpi"],
    "monitors": ["monitors", "ui.displays"],
    "inputdevice": ["inputdevice", "ui.mouse"],
    "branchbetastable": ["branchbetastable", "release"]
}

# normalize alias map keys so lookup by normalized YAML key works
ALIAS_MAP = {normalize_key(k): v for k, v in ALIAS_MAP.items()}

def split_user_host(expected: str) -> Optional[Tuple[str, str]]:
    if "@" not in expected:
        return None
    left, right = expected.split("@", 1)
    left = left.split("\\")[-1].split("/")[-1].strip()
    right = right.strip()
    if not left or not right:
        return None
    return left, right

def check_user_host_in_snapshot(expected: str, snapshot: Dict[str, Any]) -> Tuple[str, str, str]:
    pair = split_user_host(expected)
    if not pair:
        return "mismatch", "high", f"Expected user@host pattern but not found: {expected}"
    user_tok, host_tok = pair
    # gather user candidates
    candidates_user = []
    for key in ("CsUserName", "OsRegisteredUser", "CsPrimaryOwnerName", "OsRegisteredOwner"):
        v = get_value_from_snapshot(snapshot, key)
        if v:
            candidates_user.append(v)
    user_found = False
    for cand in candidates_user:
        try:
            s = str(cand)
            username = s.split("\\")[-1].split("/")[-1]
            if normalize_key(username) == normalize_key(user_tok):
                user_found = True
                break
        except Exception:
            continue
    # host candidates
    host_candidates = []
    for key in ("CsName", "CsDNSHostName", "ComputerName", "DnsHostName"):
        v = get_value_from_snapshot(snapshot, key)
        if v:
            host_candidates.append(v)
    host_found = False
    for cand in host_candidates:
        if normalize_key(str(cand)) == normalize_key(host_tok):
            host_found = True
            break
    if user_found and host_found:
        return "match", "low", f"Found user ({user_tok}) and host ({host_tok}) in snapshot"
    if user_found or host_found:
        return "partial", "medium", f"Found {'user' if user_found else 'host'} only"
    return "mismatch", "high", f"Neither user nor host found for expected {expected}"

# ---------- Synthesize device/model info ----------

def synthesize_device_model(snapshot: Dict[str, Any]) -> Optional[str]:
    try:
        parts = []
        manu = get_value_from_snapshot(snapshot, "CsManufacturer") or get_value_from_snapshot(snapshot, "BiosManufacturer")
        if manu:
            parts.append(str(manu))
        model = get_value_from_snapshot(snapshot, "CsModel") or get_value_from_snapshot(snapshot, "BiosCaption")
        if model:
            parts.append(str(model))
        osn = get_value_from_snapshot(snapshot, "OsName") or get_value_from_snapshot(snapshot, "WindowsProductName")
        if osn:
            parts.append(str(osn))
        # CPU
        cpu = None
        cpus = get_value_from_snapshot(snapshot, "CsProcessors")
        if isinstance(cpus, list) and cpus:
            first = cpus[0]
            cpu = first.get("Name") if isinstance(first, dict) else str(first)
        else:
            cpu = get_value_from_snapshot(snapshot, "Processor") or get_value_from_snapshot(snapshot, "processor")
        if cpu:
            parts.append(str(cpu))
        # Memory
        mem = get_value_from_snapshot(snapshot, "CsTotalPhysicalMemory") or get_value_from_snapshot(snapshot, "OsTotalVisibleMemorySize") or get_value_from_snapshot(snapshot, "memory_total")
        try:
            if mem:
                mnum = int(mem)
                if mnum > 1024 ** 3:
                    parts.append(f"{round(mnum / (1024 ** 3))} GB RAM")
                elif mnum > 1024 ** 2:
                    parts.append(f"{round(mnum / (1024 ** 2))} MB RAM")
                else:
                    parts.append(f"{mnum} RAM")
        except Exception:
            parts.append(str(mem))
        # Disk: try to sum partition usage totals if present
        total_gb = None
        disks = get_value_from_snapshot(snapshot, "disk_partitions") or get_value_from_snapshot(snapshot, "DiskDrive") or get_value_from_snapshot(snapshot, "PhysicalMedia")
        if isinstance(disks, list):
            try:
                ssum = 0
                found_any = False
                for d in disks:
                    if isinstance(d, dict):
                        for k in ("size", "capacity", "size_bytes"):
                            if k in d and isinstance(d[k], (int, float)):
                                ssum += int(d[k])
                                found_any = True
                    if isinstance(d, dict) and "usage" in d and isinstance(d["usage"], dict):
                        u = d["usage"].get("total") or d["usage"].get("total_bytes") or d["usage"].get("total")
                        if isinstance(u, (int, float)):
                            ssum += int(u)
                            found_any = True
                if found_any:
                    total_gb = round(ssum / (1024 ** 3))
                    parts.append(f"{total_gb} GB disk")
            except Exception:
                pass
        if parts:
            return ", ".join([p for p in parts if p])
    except Exception:
        return None
    return None

# ---------- Comparison (improved) ----------

def compare_values_improved(expected: Any, actual: Any, snapshot: Dict[str, Any], key_name: str) -> Tuple[str, str, str]:
    # Robust/fuzzy logic for specific fields
    nk = normalize_key(key_name)

    # Network: check for 'Offline' or 'Online' by IPs
    if nk == "network":
        # Accept 'Offline' if no IPv4 addresses except loopback
        if isinstance(actual, dict):
            all_ips = []
            for iface, addrs in actual.items():
                for a in addrs:
                    ip = a.get('address')
                    if ip and isinstance(ip, str) and not ip.startswith('127.') and ':' not in ip:
                        all_ips.append(ip)
            if expected.strip().lower() == 'offline' and not all_ips:
                return "match", "low", "No active IPv4 addresses, considered offline"
            if expected.strip().lower() == 'online' and all_ips:
                return "match", "low", f"Active IPv4 addresses found: {all_ips}"
            if not all_ips:
                return "partial", "medium", "No active IPv4 addresses, but expected: " + expected
            return "mismatch", "medium", f"Active IPs: {all_ips}, expected: {expected}"

    # Install Location/User Directory Location: accept 'Default' if common Windows paths present
    if nk in ("installlocation", "userdirectorylocation"):
        if expected.strip().lower() == "default":
            win_paths = ["c:\\users", "c:\\windows", "c:\\program files"]
            if isinstance(actual, str):
                for wp in win_paths:
                    if actual.lower().startswith(wp):
                        return "match", "low", f"Default location detected: {actual}"
            # Try snapshot keys
            for k in ["OsWindowsDirectory", "UserProfile"]:
                v = get_value_from_snapshot(snapshot, k)
                if v and any(str(v).lower().startswith(wp) for wp in win_paths):
                    return "match", "low", f"Default location inferred from {k}: {v}"
            return "partial", "medium", "Default location not directly found"

    # OS Theme: accept 'Dark' if AppsUseLightTheme==0 or similar
    if nk == "ostheme":
        ui_theme = get_value_from_snapshot(snapshot, "ui.theme")
        if isinstance(ui_theme, dict):
            apps = ui_theme.get("Apps")
            if expected.strip().lower().startswith("dark") and str(apps) in ("0","False","false"):
                return "match", "low", f"Theme matched (AppsUseLightTheme={apps})"
            if expected.strip().lower().startswith("light") and str(apps) in ("1","True","true"):
                return "match", "low", f"Theme matched (AppsUseLightTheme={apps})"
        return "mismatch", "high", f"Expected theme '{expected}' not found in snapshot"

    # Resolution: accept 'FHD' if 1920x1080 found
    if nk == "resolution":
        displays = get_value_from_snapshot(snapshot, "ui.displays")
        if isinstance(displays, dict):
            screens = displays.get("Screens") or displays.get("PerMonitorDPI")
            if isinstance(screens, list):
                for s in screens:
                    w = s.get("Width") if isinstance(s, dict) else None
                    h = s.get("Height") if isinstance(s, dict) else None
                    if expected.strip().upper() == "FHD" and w == 1920 and h == 1080:
                        return "match", "low", "Found 1920x1080 (FHD)"
                    token = f"{w}x{h}" if w and h else ""
                    if expected.strip().lower() in token.lower():
                        return "match", "low", f"Resolution matched ({token})"
        return "mismatch", "high", f"Expected resolution '{expected}' not found"

    # DPI Scaling: accept 100% if DPI is 96, etc.
    if nk == "dpiscaling":
        ui_dpi = get_value_from_snapshot(snapshot, "ui.dpi")
        if ui_dpi:
            try:
                val = int(ui_dpi)
                pct_actual = round((val / 96.0) * 100)
                if expected.strip().endswith("%"):
                    pct = int(expected.strip().rstrip("%"))
                    if pct_actual == pct:
                        return "match", "low", f"DPI scaling matched ({val} -> {pct_actual}%)"
            except Exception:
                pass
        return "mismatch", "high", f"Expected DPI '{expected}' not found"

    # Monitors: accept 'SDR' if video controller info does not mention HDR
    if nk == "monitors":
        vc = get_value_from_snapshot(snapshot, "video_controllers")
        if isinstance(vc, list):
            for v in vc:
                desc = str(v)
                if expected.strip().upper() == "SDR" and "hdr" not in desc.lower():
                    return "match", "low", "SDR monitor detected"
                if expected.strip().upper() == "HDR" and "hdr" in desc.lower():
                    return "match", "low", "HDR monitor detected"
        return "partial", "medium", f"Monitor info: {vc}"

    # Input Device: accept 'Mouse' if mouse present
    if nk == "inputdevice":
        mouse = get_value_from_snapshot(snapshot, "ui.mouse")
        if mouse:
            return "match", "low", f"Mouse detected: {mouse}"
        return "mismatch", "high", "No mouse detected"
    if actual is None:
        return "mismatch", "high", f"Key missing in snapshot (expected: {expected})"

    # Device & Model: allow partial/fuzzy match for all tokens
    if normalize_key(key_name) in ("devicemodel", "deviceandmodel") and isinstance(expected, str) and isinstance(actual, str):
        expected_tokens = [t.strip() for t in re.split(r",|;|\n", expected) if t.strip()]
        actual_lc = actual.lower()
        found = []
        missed = []
        for tok in expected_tokens:
            if tok.lower() in actual_lc:
                found.append(tok)
            else:
                missed.append(tok)
        if not missed:
            return "match", "low", f"All device/model tokens matched: {found}"
        elif found:
            return "partial", "medium", f"Partial device/model match: found {found}, missing {missed}"
        else:
            return "mismatch", "high", f"No device/model tokens matched. Expected: {expected}, actual: {actual}"

    # numeric expected
    if isinstance(expected, (int, float)):
        try:
            a_num = float(actual)
            if a_num > 1024 ** 3:
                a_gb = a_num / (1024 ** 3)
                if a_gb >= float(expected):
                    return "match", "low", f"Actual {round(a_gb,2)} GB >= expected {expected} GB"
                else:
                    return "mismatch", "high", f"Actual {round(a_gb,2)} GB < expected {expected} GB"
            else:
                if a_num >= float(expected):
                    return "match", "low", f"Actual {a_num} >= expected {expected}"
                else:
                    return "mismatch", "medium", f"Actual {a_num} < expected {expected}"
        except Exception:
            return "partial", "medium", f"Could not interpret numeric (actual: {actual})"

    # list expected -> subset
    if isinstance(expected, list):
        if not isinstance(actual, (list, tuple)):
            return "partial", "medium", "Expected list; snapshot value not a list"
        missed = [e for e in expected if e not in actual]
        if not missed:
            return "match", "low", "All expected items present"
        return "partial", "medium", f"Missing items: {missed}"

    # dict -> recurse
    if isinstance(expected, dict):
        nested_details = []
        severity = "low"
        for subk, subv in expected.items():
            aval = None
            if isinstance(actual, dict):
                aval = get_value_from_snapshot(actual, subk)
            st, sev, expl = compare_values_improved(subv, aval, snapshot, subk)
            nested_details.append((subk, st))
            if sev == "high":
                severity = "high"
            elif sev == "medium" and severity != "high":
                severity = "medium"
        any_mismatch = any(d[1] != "match" for d in nested_details)
        return ("partial" if any_mismatch else "match", severity, f"Nested checks: {nested_details}")

    # string matching
    if isinstance(expected, str):
        # If snapshot gave us a list (e.g., languages), map common patterns
        if isinstance(actual, list):
            if expected.strip().lower().startswith("english") and any(str(x).lower().startswith("en") for x in actual):
                return "match", "low", f"Language shorthand matched ({actual})"
            na = normalize_value_for_match(actual)
            ne = normalize_value_for_match(expected)
            if ne and ne in na:
                return "match", "low", "Expected token contained in actual list"
            if deep_search_value_contains(snapshot, ne):
                return "partial", "medium", "Expected token found elsewhere in snapshot"
            return "partial", "medium", "Type mismatch: expected string, snapshot has composite"

        if isinstance(actual, (list, dict)):
            if deep_search_value_contains(snapshot, normalize_key(expected)):
                return "partial", "medium", "Expected token found elsewhere in snapshot"
            return "partial", "medium", "Type mismatch: expected string, snapshot has composite"

        # exact / normalized
        if str(actual).strip().lower() == expected.strip().lower():
            return "match", "low", "Exact (case-insensitive) match"
        if normalize_key(str(actual)) == normalize_key(expected):
            return "match", "low", "Normalized exact match"

        ne = normalize_value_for_match(expected)
        na = normalize_value_for_match(actual)
        if ne and ne in na:
            return "match", "low", "Expected token contained in actual"
        if na and na in ne:
            return "match", "low", "Actual token contained in expected"

        # Language shorthand: "English" <-> "en-*"
        if re.match(r'^en', na) and expected.strip().lower().startswith("english"):
            return "match", "low", f"Language shorthand matched ({actual})"

        # Install location heuristic
        if expected.strip().lower() == "default":
            if isinstance(actual, str) and ("windows" in actual.lower() or "users" in actual.lower() or actual.lower().startswith("c:\\")):
                return "match", "low", f"Default location assumed by presence of {actual}"
            if get_value_from_snapshot(snapshot, "OsWindowsDirectory") or get_value_from_snapshot(snapshot, "UserProfile"):
                return "match", "low", "Default location (inferred from snapshot dirs)"

        # Install method heuristic
        if "clean" in expected.lower() and ("admin" in expected.lower() or "as admin" in expected.lower()):
            reguser = get_value_from_snapshot(snapshot, "OsRegisteredUser") or get_value_from_snapshot(snapshot, "CsPrimaryOwnerName")
            if reguser and "admin" in str(reguser).lower():
                return "partial", "medium", f"Inferred admin install from OsRegisteredUser ({reguser})"
            return "partial", "medium", "Install method not directly present; inferred not available"

        # Theme / resolution / dpi / monitors heuristics
        if key_name and normalize_key(key_name) in ("ostheme",):
            # check ui.theme if present
            ui_theme = get_value_from_snapshot(snapshot, "ui.theme")
            if isinstance(ui_theme, dict):
                apps = ui_theme.get("Apps")
                system = ui_theme.get("System")
                # AppsUseLightTheme == 0 -> dark
                if apps is not None:
                    apps_val = str(apps)
                    if expected.strip().lower().startswith("dark") and apps_val in ("0","False","false"):
                        return "match", "low", f"Theme matched (AppsUseLightTheme={apps_val})"
                    if expected.strip().lower().startswith("light") and apps_val in ("1","True","true"):
                        return "match", "low", f"Theme matched (AppsUseLightTheme={apps_val})"
            return "mismatch", "high", f"Expected theme '{expected}' not found in snapshot"

        if key_name and normalize_key(key_name) in ("resolution",):
            displays = get_value_from_snapshot(snapshot, "ui.displays")
            # two structures: Screens or PerMonitorDPI
            if isinstance(displays, dict):
                screens = displays.get("Screens") or displays.get("PerMonitorDPI")
                if isinstance(screens, list) and screens:
                    # check if any screen has width corresponding to FHD or expected token
                    ne = normalize_value_for_match(expected)
                    for s in screens:
                        w = s.get("Width") if isinstance(s, dict) else None
                        h = s.get("Height") if isinstance(s, dict) else None
                        token = f"{w}x{h}" if w and h else ""
                        if ne and normalize_key(token).find(ne) != -1:
                            return "match", "low", f"Resolution matched ({token})"
                    # also allow FHD -> 1920x1080 token check
                    if expected.strip().upper() == "FHD":
                        for s in screens:
                            if int(s.get("Width",0)) == 1920 and int(s.get("Height",0)) == 1080:
                                return "match", "low", "Found 1920x1080"
            return "mismatch", "high", f"Expected resolution '{expected}' not found"

        if key_name and normalize_key(key_name) in ("dpiscaling",):
            ui_dpi = get_value_from_snapshot(snapshot, "ui.dpi") or get_value_from_snapshot(snapshot, "ui.displays.PerMonitorDPI")
            if ui_dpi:
                # Compare numeric strings or percentages
                try:
                    if isinstance(ui_dpi, int) or isinstance(ui_dpi, float):
                        # typical LogPixels 96==100% baseline -> map to 100%, 120->125% etc (best-effort)
                        val = int(ui_dpi)
                        if expected.strip().endswith("%"):
                            pct = int(expected.strip().rstrip("%"))
                            # convert pixels per inch to percentage approx (96==100%)
                            pct_actual = round((val / 96.0) * 100)
                            if pct_actual == pct:
                                return "match", "low", f"DPI scaling matched ({val} -> {pct_actual}%)"
                    # if per-monitor list
                    if isinstance(ui_dpi, list):
                        for entry in ui_dpi:
                            if isinstance(entry, dict) and ("DpiX" in entry or "DpiY" in entry):
                                dx = int(entry.get("DpiX") or 0)
                                if expected.strip().endswith("%"):
                                    pct = int(expected.strip().rstrip("%"))
                                    pct_actual = round((dx / 96.0) * 100) if dx>0 else None
                                    if pct_actual == pct:
                                        return "match", "low", f"Per-monitor DPI matched ({dx} -> {pct_actual}%)"
                except Exception:
                    pass
            return "mismatch", "high", f"Expected DPI '{expected}' not found"

        # fuzzy
        if fuzzy_ratio(ne, na) >= FUZZY_MATCH_THRESHOLD:
            return "partial", "medium", "Fuzzy match (near)"

        if deep_search_value_contains(snapshot, ne):
            return "partial", "medium", "Expected token found elsewhere in snapshot"

        return "mismatch", "high", f"Expected '{expected}', found '{actual}'"

    # fallback equality
    try:
        if expected == actual:
            return "match", "low", "Exact match"
        else:
            return "mismatch", "medium", f"Expected {expected}, actual {actual}"
    except Exception:
        return "partial", "medium", "Could not compare values"

# ---------- Validator ----------

def validate_against_yaml(yaml_text: str, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    try:
        expected = yaml.safe_load(yaml_text)
    except Exception as e:
        return {"error": f"Failed to parse YAML: {e}"}
    if expected is None:
        return {"error": "YAML empty or invalid"}

    checks: List[Tuple[str, Any]] = []
    if isinstance(expected, dict):
        for k, v in expected.items():
            checks.append((k, v))
    elif isinstance(expected, list):
        for it in expected:
            if isinstance(it, dict) and len(it) == 1:
                key = next(iter(it.keys()))
                checks.append((key, it[key]))
            elif isinstance(it, str):
                checks.append((it, None))
    else:
        return {"error": "Unsupported YAML structure; top-level mapping expected."}

    details = []
    match_count = 0
    for key, exp_val in checks:
        nk = normalize_key(key)

        # If expected is a user@host token and key is 'series*', check that BEFORE bios serial lookup
        if isinstance(exp_val, str) and "@" in exp_val and nk.startswith("series"):
            status, severity, explanation = check_user_host_in_snapshot(exp_val, snapshot)
            details.append({"key": key, "expected": exp_val, "actual": None, "status": status, "severity": severity, "explanation": explanation})
            if status == "match":
                match_count += 1
            continue

        # build candidate keys (raw + aliases)
        cand_keys = [key]
        aliases = ALIAS_MAP.get(nk, [])
        for alias in aliases:
            if alias not in cand_keys:
                cand_keys.append(alias)

        actual = None
        found_key = None
        for cand in cand_keys:
            val = get_value_from_snapshot(snapshot, cand)
            if val is not None:
                actual = val
                found_key = cand
                break

        # fallback deep normalized search
        if actual is None:
            actual = deep_find_by_normalized_key(snapshot, normalize_key(key))

        # special handling: synthesize device & model if expected is big composite and actual not present
        if actual is None and ("devicemodel" in nk or "deviceandmodel" in nk or ("device" in nk and "model" in nk)):
            synthesized = synthesize_device_model(snapshot)
            if synthesized:
                actual = synthesized
                found_key = "synthesized_device_model"

        # special-series handling (if still not consumed earlier)
        if actual is None and isinstance(exp_val, str) and "@" in exp_val and nk.startswith("series"):
            status, severity, explanation = check_user_host_in_snapshot(exp_val, snapshot)
            details.append({"key": key, "expected": exp_val, "actual": None, "status": status, "severity": severity, "explanation": explanation})
            if status == "match":
                match_count += 1
            continue

        status, severity, explanation = compare_values_improved(exp_val, actual, snapshot, key)
        details.append({
            "key": key,
            "expected": exp_val,
            "actual": actual,
            "status": status,
            "severity": severity,
            "explanation": explanation + (f" (matched_key={found_key})" if found_key else "")
        })
        if status == "match":
            match_count += 1

    total = len(details)
    match_pct = int((match_count / total) * 100) if total else 0
    recs = []
    for d in details:
        if d["status"] != "match":
            recs.append({"key": d["key"], "suggestion": f"Review expected {d['expected']}; actual: {d['actual']}", "impact": d["severity"]})
    return {"summary": f"Validation performed: {match_pct}% checks matched", "match_percentage": match_pct, "details": details, "recommendations": recs}

# ---------- Diagnostics ----------

def run_network_diagnostics() -> str:
    lines = []
    system = platform.system().lower()
    lines.append(f"Diagnostics run on {platform.node()} ({platform.platform()})")
    try:
        if system.startswith("win"):
            cmd = ["ping", "-n", "3", "8.8.8.8"]
        else:
            cmd = ["ping", "-c", "3", "8.8.8.8"]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=15).decode(errors="ignore")
        lines.append("\n--- ping 8.8.8.8 ---\n" + out)
    except Exception as e:
        lines.append(f"\nPing check failed: {e}")
    return "\n".join(lines)

# ---------- GUI worker & GUI ----------

def run_audit_worker(yaml_text: str, window: sg.Window, progress_key: str, output_key: str,
                     mask_mac: bool, mask_users: bool, mask_bios: bool, remove_installed: bool,
                     interactive_ui: bool, collect_apps_flag: bool):
    try:
        window[progress_key].update("Collecting full snapshot...")
        snapshot = collect_full_snapshot(interactive_ui=interactive_ui, collect_apps_flag=collect_apps_flag)
        window[progress_key].update("Snapshot collected; applying masking/filtering...")
        snapshot_for_send = mask_snapshot(snapshot, mask_mac=mask_mac, mask_users=mask_users, mask_bios=mask_bios, remove_installed=remove_installed)
        window[progress_key].update("Validating snapshot against YAML...")
        analysis = validate_against_yaml(yaml_text, snapshot_for_send)
        report = {
            "timestamp": time.time(),
            "yaml_text": yaml_text,
            "snapshot_sent_masked": snapshot_for_send,
            "analysis": analysis,
            "agent": {"version": "gui-validator-1.4", "collector": platform.platform()},
        }
        out_path = os.path.join(os.getcwd(), REPORT_FILENAME)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        if isinstance(analysis, dict) and "details" in analysis:
            out_display = json.dumps(analysis, indent=2)
        else:
            out_display = "Validation error or unexpected result:\n" + json.dumps(analysis, indent=2)
        window[output_key].update(out_display)
        window[progress_key].update(f"Validation complete. Report saved to {out_path}")
    except Exception as e:
        window[output_key].update(f"Error during validation: {str(e)}")
        window[progress_key].update("Failed")

def build_gui():
    sg.theme("DarkBlue3")
    left_col = [
        [sg.Text("Immutable YAML config (paste or load). Excel -> YAML available too.")],
        [sg.Multiline(key="-YAML-", size=(80,14))],
        [sg.Button("Load YAML File"), sg.Button("Load Excel (first row -> YAML)")],
    ]
    mask_col = [
        [sg.Text("Consent & Masking (required to run locally)")],
        [sg.Checkbox("I confirm I want to validate my local snapshot against the YAML", key="-CONSENT-", default=False)],
        [sg.Checkbox("Mask MAC addresses", key="-MASK_MAC-", default=True)],
        [sg.Checkbox("Mask usernames", key="-MASK_USERS-", default=True)],
        [sg.Checkbox("Remove BIOS/raw dump fields", key="-MASK_BIOS-", default=True)],
        [sg.Checkbox("Remove installed packages lists", key="-REMOVE_PKGS-", default=True)],
        [sg.Text("")],
        [sg.Text("Optional collectors (run as interactive user for HKCU items):")],
        [sg.Checkbox("Collect interactive UI (theme/resolution/DPI/monitors/mouse)", key="-UI_COLLECT-", default=True)],
        [sg.Checkbox("Collect installed programs (registry uninstall keys) - opt-in", key="-COLLECT_APPS-", default=False)],
        [sg.Text("")],
        [sg.Button("Run Validation", button_color=("white","green")), sg.Button("Diagnostics"), sg.Button("Clear YAML")],
    ]
    right_col = [
        [sg.Text("", key="-PROGRESS-", size=(60,1))],
        [sg.Text("Validation Output:")],
        [sg.Multiline(key="-OUTPUT-", size=(120,20))],
        [sg.Button("Save Report As..."), sg.Button("Exit")],
    ]
    layout = [
        [sg.Column(left_col), sg.VerticalSeparator(), sg.Column(mask_col)],
        [sg.HorizontalSeparator()],
        [sg.Column(right_col)]
    ]
    return sg.Window("AI Device Auditor - Local Validator", layout, finalize=True)

def main():
    window = build_gui()
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED or event == "Exit":
            break
        if event == "Load YAML File":
            filename = sg.popup_get_file("Choose YAML", file_types=(("YAML Files", "*.yaml;*.yml"), ("All files","*.*")))
            if filename:
                try:
                    with open(filename, "r", encoding="utf-8") as fh:
                        window["-YAML-"].update(fh.read())
                except Exception as e:
                    sg.popup_error("Failed to load YAML:", e)
        if event == "Load Excel (first row -> YAML)":
            if pd is None:
                sg.popup_error("pandas not installed. Install with: pip install pandas openpyxl")
            else:
                filename = sg.popup_get_file("Choose Excel file", file_types=(("Excel Files","*.xlsx;*.xls"),("All files","*.*")))
                if filename:
                    try:
                        df = pd.read_excel(filename, sheet_name=0, engine="openpyxl")
                        for _, row in df.iterrows():
                            if row.notnull().any():
                                d = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                                y = yaml.safe_dump(d, sort_keys=False)
                                window["-YAML-"].update(y)
                                break
                    except Exception as e:
                        sg.popup_error("Failed to convert Excel to YAML:", e)
        if event == "Run Validation":
            yaml_text = values["-YAML-"].strip()
            if not yaml_text:
                sg.popup_error("Please paste or load the immutable YAML first.")
                continue
            if not values.get("-CONSENT-", False):
                sg.popup_error("You must confirm consent to run local validation.")
                continue
            threading.Thread(
                target=run_audit_worker,
                args=(
                    yaml_text, window, "-PROGRESS-", "-OUTPUT-",
                    values.get("-MASK_MAC-", True),
                    values.get("-MASK_USERS-", True),
                    values.get("-MASK_BIOS-", True),
                    values.get("-REMOVE_PKGS-", True),
                    values.get("-UI_COLLECT-", True),
                    values.get("-COLLECT_APPS-", False),
                ),
                daemon=True
            ).start()
        if event == "Clear YAML":
            window["-YAML-"].update("")
            window["-OUTPUT-"].update("")
            window["-PROGRESS-"].update("")
        if event == "Diagnostics":
            window["-PROGRESS-"].update("Running diagnostics...")
            def run_diag_thread():
                try:
                    res = run_network_diagnostics()
                except Exception as e:
                    res = f"Diagnostics failed: {e}"
                sg.popup_scrolled(res, title="Network Diagnostics (paste to IT)", size=(100,30))
                window["-PROGRESS-"].update("Diagnostics complete.")
            threading.Thread(target=run_diag_thread, daemon=True).start()
        if event == "Save Report As...":
            out = sg.popup_get_file("Save report as...", save_as=True, default_extension=".json", file_types=(("JSON","*.json"),("Text","*.txt")))
            if out:
                try:
                    src = os.path.join(os.getcwd(), REPORT_FILENAME)
                    if os.path.exists(src):
                        with open(src, "r", encoding="utf-8") as fh:
                            data = fh.read()
                        with open(out, "w", encoding="utf-8") as fh:
                            fh.write(data)
                        sg.popup("Saved to", out)
                    else:
                        with open(out, "w", encoding="utf-8") as fh:
                            fh.write(window["-OUTPUT-"].get())
                        sg.popup("Saved to", out)
                except Exception as e:
                    sg.popup_error("Failed to save:", e)
    window.close()

if __name__ == "__main__":
    main()
