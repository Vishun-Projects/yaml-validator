import argparse
import sys
import os
from .validator import load_config, load_snapshot, validate_snapshot
from .reports import write_json, to_excel

def main():
    ap = argparse.ArgumentParser(prog="audit-validator", description="Validate a snapshot against YAML config(s)")
    ap.add_argument("--config", required=False, help="Path to YAML file or a directory of YAML files (defaults to 'monika' in project root if present)")
    ap.add_argument("--snapshot", required=True, help="Path to snapshot JSON")
    ap.add_argument("--out-json", default="report.json", help="Output JSON report")
    ap.add_argument("--out-xlsx", default="report.xlsx", help="Output Excel report")
    args = ap.parse_args()

    if args.config:
        if not os.path.exists(args.config):
            print("Config path not found:", args.config)
            sys.exit(2)
        cfg_path = args.config
    else:
        # try monika directory near this package
        possible = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monika")
        if os.path.isdir(possible):
            cfg_path = possible
            print("Using config directory:", cfg_path)
        else:
            print("No config provided and 'monika' directory not found. Provide --config")
            sys.exit(2)
    if not os.path.exists(args.snapshot):
        print("Snapshot file not found:", args.snapshot)
        sys.exit(2)

    config = load_config(cfg_path)
    snapshot = load_snapshot(args.snapshot)
    report = validate_snapshot(snapshot, config)

    write_json(report, args.out_json)
    to_excel(report, args.out_xlsx)
    print("Wrote:", args.out_json, args.out_xlsx)
    if report["meta"]["likely_wrong_yaml"]:
        print("Warning: majority of fields mismatched -> possible wrong YAML used for validation.")


if __name__ == "__main__":
    main()
