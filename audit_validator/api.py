import io
import json
import tempfile
import os
import zipfile
import yaml
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from .validator import validate_snapshot, load_config
from .reports import to_excel, write_json

app = FastAPI(title="Audit Validator API", version="0.1.0")

@app.post("/validate")
async def validate_endpoint(config_yaml: UploadFile = File(None), snapshot_json: UploadFile = File(...)):
    """
    Accepts:
      - snapshot_json: device snapshot JSON file (required)
      - config_yaml: single YAML file (optional). If not provided, the API expects preloaded config on disk (not implemented).
    Returns a ZIP with report.json and report.xlsx
    """
    # load snapshot
    snapshot_bytes = await snapshot_json.read()
    snapshot = json.loads(snapshot_bytes.decode("utf-8", errors="ignore"))

    # load config: if uploaded use it, else try to use monika/ directory in repo
    if config_yaml is not None:
        # support uploaded YAML or Excel
        cfg_name = config_yaml.filename or "uploaded"
        suffix = os.path.splitext(cfg_name)[1] or ".yaml"
        tmp_cfg = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        cfg_bytes = await config_yaml.read()
        tmp_cfg.write(cfg_bytes)
        tmp_cfg.flush()
        tmp_cfg.close()
        try:
            config = load_config(tmp_cfg.name)
        finally:
            try:
                os.unlink(tmp_cfg.name)
            except Exception:
                pass
    else:
        # try to find a monika directory next to this package
        possible = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monika")
        if os.path.isdir(possible):
            config = load_config(possible)
        else:
            return JSONResponse({"error": "Please upload a config_yaml file (single YAML) for this API endpoint or include a 'monika' folder on the server."}, status_code=400)

    report = validate_snapshot(snapshot, config)

    # write to temp files then zip
    tmp_json = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp_xlsx = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    try:
        write_json(report, tmp_json.name)
        to_excel(report, tmp_xlsx.name)

        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
            with open(tmp_json.name, "rb") as rj:
                zf.writestr("report.json", rj.read())
            with open(tmp_xlsx.name, "rb") as rx:
                zf.writestr("report.xlsx", rx.read())
        bundle.seek(0)
        headers = {"Content-Disposition": 'attachment; filename="validation_bundle.zip"'}
        return StreamingResponse(bundle, media_type="application/zip", headers=headers)
    finally:
        try:
            os.unlink(tmp_json.name)
        except Exception:
            pass
        try:
            os.unlink(tmp_xlsx.name)
        except Exception:
            pass

@app.get("/health")
async def health():
    return JSONResponse({"ok": True})
