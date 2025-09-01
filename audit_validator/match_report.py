import json
import csv
from typing import Dict, Any, List, Tuple, Optional
from .validator import (
    flatten_snapshot_leaves,
    find_all_matches,
    search_allowed_in_snapshot,
    normalize_value_for_match,
)


def parse_device_description(desc: str) -> Dict[str, str]:
    # Very small heuristic parser: split by commas and assign semantic keys
    parts = [p.strip() for p in desc.split(',') if p and p.strip()]
    out = {}
    if parts:
        out['summary'] = parts[0]
    for p in parts[1:]:
        # heuristics
        pl = p.lower()
        if 'windows' in pl or 'linux' in pl or 'mac' in pl:
            out['os'] = p
        elif 'intel' in pl or 'amd' in pl or 'ryzen' in pl or 'xeon' in pl:
            out['cpu'] = p
        elif 'nvidia' in pl or 'radeon' in pl or 'geforce' in pl or 'rx' in pl:
            out['gpu'] = p
        elif 'ram' in pl or 'gb' in pl:
            out['memory'] = p
        elif 'ssd' in pl or 'hdd' in pl or 'disk' in pl:
            out['storage'] = p
        else:
            # append to misc
            out.setdefault('misc', []).append(p)
    # join misc
    if 'misc' in out:
        out['misc'] = ', '.join(out['misc'])
    return out


def generate_match_report(snapshot: Dict[str, Any], config: Dict[str, List[str]], min_sim: float = 0.2) -> Dict[str, Any]:
    """Generates a detailed match report per config key.

    report structure:
      key -> {
        allowed: [...],
        exact_matches: [{path, value}],
        fuzzy_best: {allowed_value, similarity, source_path, source_value},
        all_matches: [{path, value, best_allowed, similarity}],
        device_details: {...}  # optional for deviceandmodel
      }
    """
    leaves = flatten_snapshot_leaves(snapshot)
    report: Dict[str, Any] = {}

    for key, allowed in config.items():
        exact = []
        # exact: any leaf value equals allowed (case-insensitive)
        for path, val in leaves:
            for a in allowed:
                try:
                    if str(val).strip().lower() == str(a).strip().lower():
                        exact.append({'path': path, 'value': val, 'allowed': a})
                except Exception:
                    pass

        # fuzzy best (which allowed matches some snapshot value best)
        best_allowed, best_score, best_src = search_allowed_in_snapshot(snapshot, allowed)
        fuzzy_best = None
        if best_allowed:
            fuzzy_best = {
                'allowed_value': best_allowed,
                'similarity': best_score,
                'source_value': best_src,
            }
            # find source path for that source_value
            for p, v in leaves:
                if str(v) == str(best_src):
                    fuzzy_best['source_path'] = p
                    break

        # all matches: for each leaf compute best similarity against allowed list
        all_matches: List[Dict[str, Any]] = []
        for path, val in leaves:
            best_for_leaf = ('', 0.0)
            best_allowed_for_leaf = ''
            for a in allowed:
                try:
                    s = 0.0
                    if isinstance(val, str):
                        s = __import__('difflib').SequenceMatcher(None, str(a).lower(), val.lower()).ratio()
                    if s > best_for_leaf[1]:
                        best_for_leaf = (a, s)
                        best_allowed_for_leaf = a
                except Exception:
                    pass
            if best_for_leaf[1] >= min_sim:
                all_matches.append({'path': path, 'value': val, 'best_allowed': best_allowed_for_leaf, 'similarity': round(best_for_leaf[1], 4)})

        entry: Dict[str, Any] = {
            'allowed': allowed,
            'exact_matches': exact,
            'fuzzy_best': fuzzy_best,
            'all_matches': sorted(all_matches, key=lambda x: x['similarity'], reverse=True),
        }

        # If deviceandmodel, and we have a match, parse device description for nicer format
        if key == 'deviceandmodel':
            chosen = None
            if exact:
                chosen = exact[0]['value']
            elif fuzzy_best and fuzzy_best.get('allowed_value'):
                chosen = fuzzy_best.get('allowed_value')
            if chosen:
                entry['device_details'] = parse_device_description(chosen)

        report[key] = entry

    return report


def save_report(report: Dict[str, Any], out_json: str = 'match_report.json', out_csv: str = 'match_table.csv') -> None:
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # write a CSV summary: one row per key with best fuzzy
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['config_key', 'best_allowed', 'similarity', 'source_path', 'source_value', 'exact_match'])
        for k, v in report.items():
            best = v.get('fuzzy_best') or {}
            exact = bool(v.get('exact_matches'))
            writer.writerow([k, best.get('allowed_value') if best else '', best.get('similarity') if best else '', best.get('source_path') if best else '', best.get('source_value') if best else '', exact])


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Usage: python -m audit_validator.match_report <snapshot.json> <config_path_or_dir>')
        sys.exit(1)
    snap_path = sys.argv[1]
    cfg_path = sys.argv[2]
    from .validator import load_config, load_snapshot
    snap = load_snapshot(snap_path)
    cfg = load_config(cfg_path)
    rpt = generate_match_report(snap, cfg)
    save_report(rpt, out_json='match_report.json', out_csv='match_table.csv')
    print('Wrote match_report.json and match_table.csv')
