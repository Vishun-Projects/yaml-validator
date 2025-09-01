import os
import json
try:
    import PySimpleGUI as sg
except Exception:
    sg = None
from .validator import load_config, load_snapshot, validate_snapshot

# Attempt to import the legacy collectors to auto-collect a snapshot at GUI startup
collected_snapshot = None
try:
    import ai_audit_gui
    # best-effort: non-interactive, skip heavy app collection
    try:
        collected_snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=False, collect_apps_flag=False)
    except Exception:
        collected_snapshot = None
except Exception:
    collected_snapshot = None

if sg is None:
    raise RuntimeError('PySimpleGUI is required for the GUI. Install with: pip install PySimpleGUI')


def build_gui(snapshot_preview: str = ''):
    layout = [
        [sg.Text('Config file (YAML or Excel)'), sg.Input(key='-CFG-'), sg.FileBrowse(file_types=(('YAML', '*.yml;*.yaml'), ('Excel', '*.xlsx;*.xls')))],
        [sg.Text('Optional: Upload snapshot JSON to override collected snapshot'), sg.Input(key='-SNAP-'), sg.FileBrowse(file_types=(('JSON', '*.json'),))],
        [sg.Text('Auto-collected snapshot (preview):')],
        [sg.Multiline(snapshot_preview, size=(100,10), key='-PREVIEW-')],
        [sg.Button('Run'), sg.Button('Exit')],
        [sg.Text('Output:')],
        [sg.Multiline(key='-OUT-', size=(100,10))]
    ]
    return sg.Window('Audit Validator GUI', layout)


def main():
    global collected_snapshot
    # prepare a compact preview of collected snapshot
    preview = ''
    try:
        if collected_snapshot:
            preview = json.dumps(collected_snapshot, indent=2)[:400]
        else:
            preview = 'No auto-collected snapshot available on this host.'
    except Exception:
        preview = 'Snapshot preview unavailable.'

    window = build_gui(preview)
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        if event == 'Run':
            cfg = values.get('-CFG-')
            snap_file = values.get('-SNAP-')
            # prefer uploaded snapshot file if provided, else use collected_snapshot
            if snap_file and os.path.exists(snap_file):
                try:
                    snapshot = load_snapshot(snap_file)
                except Exception as e:
                    window['-OUT-'].print('Failed to load uploaded snapshot: ' + str(e))
                    continue
            else:
                if collected_snapshot is None:
                    window['-OUT-'].print('No collected snapshot and no uploaded snapshot provided')
                    continue
                snapshot = collected_snapshot

            if not cfg or not os.path.exists(cfg):
                window['-OUT-'].print('Config file missing')
                continue

            try:
                config = load_config(cfg)
            except Exception as e:
                window['-OUT-'].print('Failed to load config: ' + str(e))
                continue

            try:
                report = validate_snapshot(snapshot, config)
                out_path = os.path.join(os.getcwd(), 'gui_report.json')
                with open(out_path, 'w', encoding='utf-8') as fh:
                    json.dump(report, fh, indent=2)
                window['-OUT-'].print(f'Report written to {out_path}')
            except Exception as e:
                window['-OUT-'].print('Validation error: ' + str(e))
    window.close()


if __name__ == '__main__':
    main()
