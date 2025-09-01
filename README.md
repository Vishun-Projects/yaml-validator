# Audit Validator (minimal)

A small validator which:
- reads YAML configs (allowed lists)
- reads device snapshot JSON
- checks membership (allowed lists), reports mismatches and closest matches
- writes JSON + Excel report
- includes a FastAPI endpoint for automation

## Quickstart (local)

1. Create a virtualenv and install:
python -m venv venv
source venv/bin/activate # or venv\Scripts\activate on Windows
pip install -r requirements.txt

2. Run the CLI:
python -m audit_validator.cli --config examples/sample_config.yaml --snapshot examples/snapshot.json --out-json out/report.json --out-xlsx out/report.xlsx

Note: If you don't provide --config, the CLI will attempt to use a `monika/` directory in the project root which contains the YAML catalogs used by this project.

3. Run the API:
uvicorn audit_validator.api:app --reload --port 8000

POST `multipart/form-data` with:
- `config_yaml` (file) -> single YAML file or Excel (.xlsx) file (optional if server has `monika/`)
- `snapshot_json` (file) -> snapshot JSON

GUI: A minimal GUI is available at `audit_validator/gui.py`. It lets you pick an Excel/YAML config and a snapshot JSON, runs validation, and writes `gui_report.json`.

You will get a ZIP containing `report.json` and `report.xlsx`.

## How it handles "wrong YAML used for device"
- If more than 50% of fields are mismatched, the report sets `meta.likely_wrong_yaml: true`.
- Each field includes its `closest_match` and a `similarity` score (0..1) for debugging.

## Next steps (recommended)
1. Integrate this API into n8n:
   - Cron at 11:00 (Asia/Kolkata)
   - For each device, run SSH to collect snapshot JSON
   - Attach the config YAML file (per device) and snapshot to `/validate`
2. Add Groq/OpenAI call to summarize the JSON report and produce remediation text.
3. Add inventory spreadsheet and map devices -> config YAMLs.
