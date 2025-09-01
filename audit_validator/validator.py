import os
import yaml
try:
    import pandas as pd
except Exception:
    pd = None
import json
import difflib
import re
from typing import Dict, Any, List, Tuple, Optional

# --- Normalization helpers (inspired by legacy ai_audit_gui) ---
def normalize_key(s: Optional[str]) -> str:
    if s is None:
        return ""
    return re.sub(r'[^0-9a-z]', '', str(s).lower())

def normalize_value_for_match(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join([str(x) for x in v])
    if isinstance(v, dict):
        return json.dumps(v, sort_keys=True)
    return str(v)

def _similarity(a: str, b: str) -> float:
    try:
        return difflib.SequenceMatcher(None, a, b).ratio()
    except Exception:
        return 0.0

# Alias map from legacy code - helps map YAML keys to snapshot variants
ALIAS_MAP = {
    "seriesno": ["biosserialnumber", "biosseralnumber", "csusername", "csname", "osregistereduser", "osregisteredowner", "csprimaryownername"],
    "deviceandmodel": ["csmodel", "csmanufacturer", "product", "productname", "model", "systemproductname", "osname", "csprocessors", "cstotalphysicalmemory"],
    "oslanguage": ["oslanguage", "os_locale", "oslocale", "osmuilanguages"],
    "applanguage": ["osmuilanguages", "oslanguage"],
    "keyboardinputlayout": ["keyboardlayout", "keyboardlayoutname"],
    "network": ["csnetworkadapters", "ipaddresses", "connectionid"],
    "userlicense": ["osregistereduser", "csprimaryownername"],
    "installmethod": ["installationtype", "windowsinstallationtype"],
    "installlocation": ["oswindowsdirectory", "ossystemdirectory"],
    "userdirectorylocation": ["homedirectory", "userprofile", "userdirectory"],
    "ostheme": ["theme", "ostheme", "ui.theme"],
    "resolution": ["resolution", "screenresolution", "displayresolution", "ui.displays"],
    "dpiscaling": ["dpiscale", "dpiscaling", "scaling", "ui.dpi", "ui.displays"],
    "monitors": ["monitors", "display", "screens", "ui.displays"],
    "inputdevice": ["inputdevice", "mouse", "keyboard", "ui.mouse"],
    "branchbetastable": ["branch", "release", "channel", "branch-beta-stable"],
}

ALIAS_MAP = {k: v for k, v in ALIAS_MAP.items()}


def deep_find_by_normalized_key(obj: Any, target_norm: str, max_depth: int = 8, _visited=None):
    if _visited is None:
        _visited = set()
    try:
        obj_id = id(obj)
        if obj_id in _visited:
            return None
        _visited.add(obj_id)
    except Exception:
        pass

    if obj is None or max_depth < 0:
        return None

    if isinstance(obj, dict):
        for k, v in obj.items():
            if normalize_key(k) == target_norm:
                return v
        for v in obj.values():
            found = deep_find_by_normalized_key(v, target_norm, max_depth - 1, _visited)
            if found is not None:
                return found

    if isinstance(obj, list):
        for item in obj:
            found = deep_find_by_normalized_key(item, target_norm, max_depth - 1, _visited)
            if found is not None:
                return found

    return None


def get_value_from_snapshot(snapshot: Any, dotted_key: str) -> Optional[Any]:
    if not dotted_key:
        return None
    # try dotted access first
    parts = dotted_key.split(".")
    cur = snapshot
    try:
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                raise KeyError()
        return cur
    except Exception:
        # fallback: normalized key direct or deep search
        norm = normalize_key(dotted_key)
        # try top-level normalized match
        if isinstance(snapshot, dict):
            for k, v in snapshot.items():
                if normalize_key(k) == norm:
                    return v
        # alias map
        if norm in ALIAS_MAP:
            for cand in ALIAS_MAP[norm]:
                found = deep_find_by_normalized_key(snapshot, normalize_key(cand))
                if found is not None:
                    return found
        # deep search
        return deep_find_by_normalized_key(snapshot, norm)


def flatten_snapshot_keys(obj: Any, parent: str = '') -> List[str]:
    """Return list of dotted key paths for dict/list snapshot structures."""
    out: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{parent}.{k}" if parent else k
            out.append(path)
            out.extend(flatten_snapshot_keys(v, path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{parent}[{i}]" if parent else f"[{i}]"
            out.append(path)
            out.extend(flatten_snapshot_keys(item, path))
    return out


def _deep_search_for_normalized_key(obj: Any, target_norm: str, _visited=None) -> Optional[Tuple[Any, str]]:
    """Like deep_find_by_normalized_key but returns (value, found_key_name).
    found_key_name is the actual key string that matched (leaf key).
    """
    if _visited is None:
        _visited = set()
    try:
        oid = id(obj)
        if oid in _visited:
            return None
        _visited.add(oid)
    except Exception:
        pass

    if obj is None:
        return None

    if isinstance(obj, dict):
        for k, v in obj.items():
            if normalize_key(k) == target_norm:
                return (v, k)
        for v in obj.values():
            found = _deep_search_for_normalized_key(v, target_norm, _visited)
            if found is not None:
                return found

    if isinstance(obj, list):
        for item in obj:
            found = _deep_search_for_normalized_key(item, target_norm, _visited)
            if found is not None:
                return found

    return None


def find_value_and_found_key(snapshot: Any, dotted_key: str, key_map: Optional[Dict[str, str]] = None) -> Tuple[Optional[Any], Optional[str]]:
    """Find a value for a config key and return (value, actual_found_key).

    If key_map is provided and maps the config key to a snapshot key path, that is tried first.
    """
    # If explicit mapping provided, try it first
    if key_map and dotted_key in key_map and key_map[dotted_key]:
        mapped = key_map[dotted_key]
        # try dotted access for mapped value
        parts = str(mapped).split('.')
        cur = snapshot
        try:
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    raise KeyError()
            return (cur, mapped)
        except Exception:
            # fallback to deep search for mapped normalized key
            found = _deep_search_for_normalized_key(snapshot, normalize_key(mapped))
            if found:
                return found

    # try dotted access first
    if dotted_key:
        parts = dotted_key.split('.')
        cur = snapshot
        try:
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    raise KeyError()
            # return the value and the final key used
            return (cur, parts[-1] if parts else None)
        except Exception:
            pass

    # fallback: normalized key direct or deep search
    norm = normalize_key(dotted_key)
    # try top-level normalized match
    if isinstance(snapshot, dict):
        for k, v in snapshot.items():
            if normalize_key(k) == norm:
                return (v, k)
    # alias map
    if norm in ALIAS_MAP:
        for cand in ALIAS_MAP[norm]:
            found = _deep_search_for_normalized_key(snapshot, normalize_key(cand))
            if found is not None:
                return found
    # deep search
    found = _deep_search_for_normalized_key(snapshot, norm)
    if found is not None:
        return found
    return (None, None)


def suggest_mappings(config: Dict[str, List[str]], snapshot: Any, threshold: float = 0.45) -> Dict[str, Tuple[str, float]]:
    """Suggest snapshot key (dotted path) for each config key using fuzzy matching.

    Returns mapping: config_key -> (suggested_snapshot_key, similarity)
    """
    # flatten snapshot dotted keys
    dotted_keys = flatten_snapshot_keys(snapshot)
    # also include top-level keys
    if isinstance(snapshot, dict):
        for k in snapshot.keys():
            if k not in dotted_keys:
                dotted_keys.append(k)

    suggestions: Dict[str, Tuple[str, float]] = {}
    for cfg_key in config.keys():
        best_k = ""
        best_s = 0.0
        for dk in dotted_keys:
            s = _similarity(normalize_key(cfg_key), normalize_key(dk))
            if s > best_s:
                best_s = s
                best_k = dk
        if best_s >= threshold:
            suggestions[cfg_key] = (best_k, round(best_s, 4))
    return suggestions


def flatten_snapshot_values(obj: Any, _visited=None) -> List[str]:
    """Return list of stringified leaf values from the snapshot for fuzzy scanning."""
    if _visited is None:
        _visited = set()
    out: List[str] = []
    try:
        oid = id(obj)
        if oid in _visited:
            return out
        _visited.add(oid)
    except Exception:
        pass

    if obj is None:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten_snapshot_values(v, _visited))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(flatten_snapshot_values(item, _visited))
    else:
        try:
            s = normalize_value_for_match(obj)
            if s:
                out.append(s)
        except Exception:
            pass
    return out


def search_allowed_in_snapshot(snapshot: Any, allowed: List[str]) -> Tuple[Optional[str], float, Optional[str]]:
    """Search the snapshot values for the best-matching allowed value.

    Returns (best_allowed_value, similarity, source_snippet).
    """
    if not allowed:
        return (None, 0.0, None)
    vals = flatten_snapshot_values(snapshot)
    best_allowed = None
    best_score = 0.0
    best_src = None
    for a in allowed:
        a_n = a.lower()
        for v in vals:
            try:
                score = _similarity(a_n, v.lower())
            except Exception:
                score = 0.0
            if score > best_score:
                best_score = score
                best_allowed = a
                best_src = v
    return (best_allowed, round(best_score, 4), best_src)


def find_snapshot_key_for_value(obj: Any, target_value: str, parent: str = '', _visited=None) -> Optional[str]:
    """Return dotted path to the first leaf whose stringified value contains target_value (case-insensitive)."""
    if _visited is None:
        _visited = set()
    try:
        oid = id(obj)
        if oid in _visited:
            return None
        _visited.add(oid)
    except Exception:
        pass

    if obj is None:
        return None
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{parent}.{k}" if parent else k
            # check primitive
            if not isinstance(v, (dict, list)):
                try:
                    s = normalize_value_for_match(v)
                    if target_value.lower() in s.lower():
                        return path
                except Exception:
                    pass
            # recurse
            found = find_snapshot_key_for_value(v, target_value, path, _visited)
            if found:
                return found
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{parent}[{i}]" if parent else f"[{i}]"
            if not isinstance(item, (dict, list)):
                try:
                    s = normalize_value_for_match(item)
                    if target_value.lower() in s.lower():
                        return path
                except Exception:
                    pass
            found = find_snapshot_key_for_value(item, target_value, path, _visited)
            if found:
                return found
    return None


def flatten_snapshot_leaves(obj: Any, parent: str = '', _visited=None) -> List[Tuple[str, str]]:
    """Return list of (dotted_path, stringified_leaf_value) for all leaves in snapshot."""
    if _visited is None:
        _visited = set()
    out: List[Tuple[str, str]] = []
    try:
        oid = id(obj)
        if oid in _visited:
            return out
        _visited.add(oid)
    except Exception:
        pass

    if obj is None:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{parent}.{k}" if parent else k
            if not isinstance(v, (dict, list)):
                try:
                    s = normalize_value_for_match(v)
                    out.append((path, s))
                except Exception:
                    pass
            else:
                out.extend(flatten_snapshot_leaves(v, path, _visited))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{parent}[{i}]" if parent else f"[{i}]"
            if not isinstance(item, (dict, list)):
                try:
                    s = normalize_value_for_match(item)
                    out.append((path, s))
                except Exception:
                    pass
            else:
                out.extend(flatten_snapshot_leaves(item, path, _visited))
    else:
        try:
            s = normalize_value_for_match(obj)
            out.append((parent or 'root', s))
        except Exception:
            pass
    return out


def find_all_matches(obj: Any, query: str, min_similarity: float = 0.45) -> List[Tuple[str, str, float]]:
    """Return list of (path, value, similarity) where value best matches the query."""
    leaves = flatten_snapshot_leaves(obj)
    qn = str(query).lower()
    results: List[Tuple[str, str, float]] = []
    for path, val in leaves:
        try:
            sim = _similarity(qn, val.lower())
        except Exception:
            sim = 0.0
        if qn in val.lower() or sim >= min_similarity:
            results.append((path, val, round(sim, 4)))
    # sort by similarity desc
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def load_yaml_file(path: str) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    out: Dict[str, List[str]] = {}

    # If file defines categories (monika style)
    if isinstance(data, dict) and "categories" in data and isinstance(data["categories"], list):
        for cat in data["categories"]:
            if not isinstance(cat, dict):
                continue
            name = cat.get("category") or cat.get("name")
            choices = cat.get("choices") or []
            norm = normalize_key(name)
            out[norm] = [str(x[0]) if isinstance(x, (list, tuple)) else str(x) for x in choices]
        return out

    # If file defines names: treat as name/deviceandmodel list
    if isinstance(data, dict) and "names" in data and isinstance(data["names"], list):
        out["deviceandmodel"] = [str(x) for x in data["names"]]
        return out

    # If top-level has mapping of fields -> choices
    if isinstance(data, dict):
        # heuristically convert any list values into allowed lists
        for k, v in data.items():
            if isinstance(v, list):
                out[normalize_key(k)] = [str(x) for x in v]
            elif isinstance(v, dict):
                # try to extract 'choices' or similar
                choices = v.get("choices") if isinstance(v.get("choices"), list) else None
                if choices is not None:
                    out[normalize_key(k)] = [str(x[0]) if isinstance(x, (list, tuple)) else str(x) for x in choices]
    return out


def load_config(path_or_dir: str) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {}
    if os.path.isdir(path_or_dir):
        # prefer Excel files if present (user asked to use XLSX as primary)
        files = sorted(os.listdir(path_or_dir))
        excel_files = [f for f in files if f.lower().endswith(('.xls', '.xlsx'))]
        if excel_files and pd:
            for fname in excel_files:
                p = os.path.join(path_or_dir, fname)
                # reuse single-file excel loader
                try:
                    merged.update(load_config(p))
                except Exception:
                    pass
            return merged
        # otherwise fall back to YAML files
        for fname in files:
            if fname.lower().endswith((".yml", ".yaml")):
                p = os.path.join(path_or_dir, fname)
                merged.update(load_yaml_file(p))
        return merged
    else:
        # support Excel files as config input (each column = category, values = choices)
        if pd and str(path_or_dir).lower().endswith(('.xls', '.xlsx')):
            def load_excel_file(p: str) -> Dict[str, List[str]]:
                out: Dict[str, List[str]] = {}
                try:
                    df = pd.read_excel(p, sheet_name=0, dtype=str)
                except Exception:
                    return out
                # if sheet has 'category' and 'choices' columns, parse rows
                cols = [c.lower() for c in df.columns]
                if 'category' in cols and 'choices' in cols:
                    for _, row in df.iterrows():
                        cat = row.get('category') or row.get('Category')
                        ch = row.get('choices') or row.get('Choices')
                        if pd.isna(cat) or pd.isna(ch):
                            continue
                        out[normalize_key(str(cat))] = [c.strip() for c in str(ch).split(',') if c.strip()]
                    return out
                # otherwise, treat each column as a category and collect unique non-null values
                for col in df.columns:
                    vals = df[col].dropna().astype(str).map(str.strip).unique().tolist()
                    out[normalize_key(str(col))] = vals
                return out

        if str(path_or_dir).lower().endswith(('.xls', '.xlsx')) and pd:
            return load_excel_file(path_or_dir)
        return load_yaml_file(path_or_dir)


def load_snapshot(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def best_match(value: str, allowed: List[str]) -> Tuple[str, float]:
    if not allowed:
        return "", 0.0
    value_n = value.lower()
    best = ("", 0.0)
    for cand in allowed:
        try:
            score = _similarity(value_n, cand.lower())
        except Exception:
            score = 0.0
        if score > best[1]:
            best = (cand, score)
    return best


def is_allowed(value: str, allowed: List[str]) -> bool:
    if value is None:
        return False
    v = str(value).strip().lower()
    for a in allowed:
        a_n = str(a).strip().lower()
        if v == a_n:
            return True
        if len(v) >= 3 and (v in a_n or a_n in v):
            return True
    return False


def validate_snapshot(snapshot: Dict[str, Any], config: Dict[str, List[str]], key_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    total = 0
    mismatches = 0

    # Primary: iterate config keys so report is deterministic and covers expected fields
    for cfg_key, allowed in config.items():
        total += 1
        found, found_actual_key = find_value_and_found_key(snapshot, cfg_key, key_map=key_map)
        value_str = normalize_value_for_match(found)
        status = "missing"
        closest = ""
        sim = 0.0
        explanation = ""

        # Special handling for Input Device (mouse)
        if normalize_key(cfg_key) in ["inputdevice", "input_device"]:
            mouse_info = None
            if "ui" in snapshot and "mouse" in snapshot["ui"]:
                mouse_info = snapshot["ui"]["mouse"]
            elif "mouse" in snapshot:
                mouse_info = snapshot["mouse"]
            if mouse_info:
                if isinstance(mouse_info, dict):
                    value_str = mouse_info.get("Name") or str(mouse_info)
                elif isinstance(mouse_info, list) and mouse_info:
                    value_str = mouse_info[0].get("Name") or str(mouse_info[0])
                else:
                    value_str = str(mouse_info)
                explanation = f"Detected mouse: {value_str}"
                # If config expects 'Mouse' (case-insensitive), any detected mouse is a match
                if any(str(a).strip().lower() == "mouse" for a in allowed) and value_str:
                    status = "ok"
                else:
                    status = "ok" if is_allowed(value_str, allowed) else "mismatch"
                if status == "mismatch":
                    mismatches += 1
                closest, sim = best_match(value_str, allowed)
            else:
                value_str = ""
                explanation = "No mouse detected"
                status = "missing"
        else:
            if found is None or (isinstance(found, (str, list, dict)) and value_str == ""):
                status = "missing"
                explanation = f"Key missing in snapshot (expected: {allowed})"
            else:
                if is_allowed(value_str, allowed):
                    status = "ok"
                else:
                    status = "mismatch"
                    mismatches += 1
                closest, sim = best_match(value_str, allowed)
                if status == "mismatch":
                    explanation = f"Expected {allowed}, found '{value_str}'"

        fields[cfg_key] = {
            "found_key": found_actual_key,
            "value": value_str,
            "status": status,
            "allowed": allowed,
            "closest_match": closest,
            "similarity": round(sim, 4),
            "explanation": explanation,
        }

    # Secondary: include snapshot-only keys (unknown to YAML)
    for k, v in snapshot.items():
        norm_k = normalize_key(k)
        if norm_k in fields:
            # annotate found_key for the config entry
            fields[norm_k]["found_key"] = k
            continue
        # record unknown snapshot key
        total += 1
        vstr = normalize_value_for_match(v)
        fields[norm_k] = {
            "found_key": k,
            "value": vstr,
            "status": "unknown",
            "allowed": [],
            "closest_match": "",
            "similarity": 0.0,
        }

    mismatch_ratio = (mismatches / total) if total > 0 else 0.0
    likely_wrong_yaml = mismatch_ratio >= 0.5

    meta = {
        "total_fields": total,
        "mismatches": mismatches,
        "mismatch_ratio": round(mismatch_ratio, 4),
        "likely_wrong_yaml": bool(likely_wrong_yaml),
    }

    return {"meta": meta, "fields": fields}
