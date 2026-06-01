# Abbreviation Checker

Streamlit app for extracting abbreviations from uploaded PDFs, exporting results to Excel, and creating a highlighted PDF.

## Project Files

- `streamlit_app.py` - Streamlit user interface.
- `pipeline_utils.py` - PDF text extraction, abbreviation detection, Excel export, and PDF highlighting.
- `session_manager.py` - User identity, active-user limit, queue, and inactivity timeout.
- `file_manager.py` - User folders, safe filenames, cleanup, and path validation.
- `app_config.py` - Loads runtime limits from `.env`.
- `english_stopwords.txt` - Stopword list used by abbreviation matching.
- `requirements.txt` - Python dependencies.
- `.env` - Local limit settings used by the app.
- `PROJECT_NOTES.md` - Full project handoff, edge cases, and implementation notes.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Generated user files are stored under `temp_outputs/` and runtime queue/session files under `runtime/`. Both are ignored by Git.

The current version uses URL `uid` as the reliable browser/session identity. Keep the generated `uid` in the URL when opening another tab or window to reuse the same app user.

## Limits

Edit `.env` to change runtime limits:

```env
MAX_ACTIVE_USERS=5
MAX_PDF_SIZE_MB=20
MAX_PAGES=100
INACTIVITY_TIMEOUT_MINUTES=5
CLEANUP_MAX_FILE_AGE_MINUTES=5
QUEUE_POLL_SECONDS=60
ACTIVE_HEARTBEAT_SECONDS=60
```

If you change `MAX_PDF_SIZE_MB`, also update `.streamlit/config.toml` so Streamlit's uploader text matches the app limit.

## Full Notes

See `PROJECT_NOTES.md` before continuing development. It includes the tech stack, app flow, edge cases, known limitations, and next steps.
