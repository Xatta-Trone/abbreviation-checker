# Abbreviation Checker Project Notes

This document is the working handoff for the Streamlit abbreviation checker app. Use it when returning to the project later so you do not need to reconstruct the plan from scratch.

## App Goal

The app lets a user upload a PDF, extract abbreviations and possible full forms, export the results to Excel, and download a highlighted PDF where found full forms are marked.

Current user flow:

1. User opens the Streamlit app.
2. App identifies the browser user using URL `uid`.
3. App checks active-user capacity.
4. User uploads a PDF.
5. App validates file size and page count.
6. App saves the upload into a user-specific temporary folder.
7. App extracts page text and abbreviation data.
8. App writes Excel output.
9. App creates highlighted PDF output.
10. User downloads Excel and highlighted PDF.
11. Temporary files are deleted after inactivity/cleanup.

## Tech Stack

- Python
- Streamlit
- Streamlit Shadcn UI
- PyMuPDF (`pymupdf`)
- pandas
- openpyxl
- filelock
- python-dotenv
- URL query params for browser/session identity

## Main Files

- `streamlit_app.py` - Main Streamlit UI and processing flow.
- `pipeline_utils.py` - PDF text extraction, abbreviation matching, Excel export, and PDF highlighting.
- `session_manager.py` - Active users, queue, inactivity timeout, runtime JSON state.
- `file_manager.py` - Safe folders, temp output folders, file cleanup, user path validation.
- `app_config.py` - Loads settings from `.env`.
- `english_stopwords.txt` - Stop words used by abbreviation matching.
- `.env` - Local runtime configuration.
- `.env.example` - Example config for future setup/deployment.
- `.streamlit/config.toml` - Streamlit server config, including upload size.
- `requirements.txt` - Python dependencies.
- `README.md` - Basic run instructions.
- `PROJECT_NOTES.md` - This handoff document.

## Local Setup

From the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Current local URL:

```text
http://localhost:8501
```

## Runtime Configuration

Settings are loaded from `.env` by `app_config.py`.

Current config:

```env
APP_TITLE="Abbreviation Checker"
MAX_ACTIVE_USERS=5
MAX_PDF_SIZE_MB=20
MAX_PAGES=100
INACTIVITY_TIMEOUT_MINUTES=5
CLEANUP_MAX_FILE_AGE_MINUTES=5
QUEUE_POLL_SECONDS=60
ACTIVE_HEARTBEAT_SECONDS=60
```

Important: if `MAX_PDF_SIZE_MB` changes, also update `.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 20
```

Otherwise Streamlit's upload widget text may not match the app's validation limit.

## User Identity

The app currently uses URL-based browser identity:

1. URL query param: `?uid=<user_id>`
2. Existing Streamlit-readable cookie if available
3. New generated ID if no existing identity is found

This prevents normal refreshes from consuming multiple active-user slots. To reuse the same app user in a new tab/window, keep the generated `uid` in the URL.

Expected behavior:

- Same URL/new tab: same user ID.
- Same URL/new window: same user ID.
- Different browser: different user ID.
- Incognito/private window: different user ID.
- URL without `uid` and no readable cookie: new user ID.
- Shared URL with `uid`: opens that same app user state unless overwritten later.

## Active User And Queue System

Configured by:

```env
MAX_ACTIVE_USERS=5
```

Behavior:

- If fewer than 5 active users exist, the user becomes active.
- If 5 active users exist, the user enters the queue.
- Queue position is shown on screen.
- Queue status auto-polls every `QUEUE_POLL_SECONDS` seconds.
- Active open sessions heartbeat every `ACTIVE_HEARTBEAT_SECONDS` seconds.
- Inactive users are removed after the configured timeout.
- When an active slot opens, the first queued user is promoted.

Runtime state files:

```text
runtime/active_users.json
runtime/queue.json
runtime/session.lock
```

These are ignored by Git.

## Temporary Output Structure

Generated files live under:

```text
temp_outputs/user_<user_id>/<pdf_name>_<timestamp>/
```

Typical run folder:

```text
uploaded.pdf
page_texts/
  page_1.txt
  page_2.txt
<original_pdf_name>_abbr_results_<timestamp>.xlsx
<original_pdf_name>_highlighted_<timestamp>.pdf
```

`file_manager.py` validates that download paths belong to the current user's folder before showing download buttons.

## Pipeline Summary

`pipeline_utils.py` contains:

- `split_abbreviation_v2()`
- `generate_combinations()`
- `find_full_form_v2()`
- `string_to_light_color_hex()`
- `hex_to_rgb01()`
- `process_pdf()`
- `export_to_excel()`
- `highlight_terms_in_pdf()`
- `collection_to_highlight_items()`

Processing steps:

1. Open PDF with PyMuPDF.
2. Check max page count.
3. Extract text page by page.
4. Save page text files.
5. Find abbreviation patterns like `Full Form (ABC)`.
6. Try to match abbreviation letters to preceding context.
7. Store abbreviation, full form, page numbers, and deterministic color.
8. Export results to Excel.
9. Highlight found full forms in PDF.

## UI Notes

Current UI uses:

- Shadcn metric cards for limits.
- Custom CSS chips for feature badges.
- Black/white/gray button styling to match badge language.
- Red toast/error text for invalid file notifications.
- Red error cards for processing/validation errors.
- Large full-width upload drop zone for PDF drag/drop.
- Streamlit file uploader.
- Full-page processing overlay while jobs run.
- Footer credit link.

First-screen limits shown:

- Active users
- Max PDF file size
- Max page count
- Inactivity/session expiration

Feature chips:

- PDF only
- Private temp files
- Excel export
- Highlighted PDF

Output download names:

- `<filename>_abbr_results_<YYYYMMDD_HHMMSS>.xlsx`
- `<filename>_highlighted_<YYYYMMDD_HHMMSS>.pdf`

Upload behavior:

- The uploader is configured for one file at a time.
- The UI hides Streamlit's extra add-file control when possible.
- The uploader keeps `type=["pdf"]` as the native accept filter.
- File type validation is also checked app-side as a defensive fallback.
- Validation/processing errors use a red error card.

## Requirements

Current `requirements.txt`:

```txt
streamlit
pymupdf
pandas
openpyxl
filelock
python-dotenv
streamlit-shadcn-ui
```

## Edge Cases To Preserve

### Same user opens a new tab

Expected: same user ID is reused if the tab includes the same `uid` in the URL.

### Same user refreshes the app

Expected: same user ID and current state remain.

### App reaches active-user limit

Expected: extra users see queue position instead of upload UI, and the queue screen polls automatically every 60 seconds by default.

### User is inactive for too long

Expected: user is removed from active list/queue, files are cleaned up, and their slot is freed. Open active tabs heartbeat every 60 seconds by default, while closed tabs stop heartbeating and expire after 5 minutes by default.

### Uploaded PDF is too large

Expected: app rejects before processing.

### User uploads a non-PDF file

Expected: app shows an unsupported-file alert/toast and stops before processing.

### User tries to upload multiple files

Expected: app shows a one-file-only alert/toast and stops before processing.

### Uploaded PDF has too many pages

Expected: `process_pdf()` raises a readable error and partial run folder is deleted.

### PDF is corrupted or unreadable

Expected: app shows readable processing error and deletes partial outputs.

### PDF has no abbreviations

Expected: Excel still generates with a "No abbreviations found" row.

### Full form is not found

Expected: abbreviation can still appear in Excel with blank full form; highlighter skips that item.

### Multiple users update runtime files at once

Expected: `filelock` protects JSON reads/writes.

### User tries to access another user's files

Expected: app only shows download buttons after path ownership validation.

## Original Plan Coverage

Implemented from the pasted plan:

- Upload PDF.
- Extract abbreviations and possible full forms.
- Save page-wise extracted text.
- Generate Excel output.
- Generate highlighted PDF output.
- Download both output files.
- User-specific temporary folders.
- Active-user limit.
- Queue for extra users.
- Inactivity timeout cleanup.
- Old temporary file cleanup on app load/refresh.
- Same-session identity using URL `uid`.
- JSON runtime state for active users and queue.
- `filelock` around runtime JSON reads/writes.
- File access validation before download buttons.
- Footer credit link.
- `.env` configuration for limits.
- First-screen display of limits.
- Streamlit Shadcn UI cards/alerts plus custom styled chips/buttons.

Different from the pasted plan:

- The original package suggestion was `streamlit-cookies-manager`. That package timed out with the current Streamlit version during testing.
- The Python local-storage/cookie components caused startup blocking in some reload states, and `st.components.v1.html` is no longer safe on current Streamlit Cloud. The app no longer injects browser scripts during render.
- User identity now prefers a valid URL `uid`, then an existing Streamlit-readable cookie if available, then a newly generated ID.
- Streamlit uploader max size is also configured in `.streamlit/config.toml` because `.env` cannot change Streamlit's built-in uploader text by itself.
- This URL-first approach trades automatic same-browser tab syncing for reliable rendering on Streamlit Cloud and normal browsers.

Still pending or partial from the pasted plan:

- The expired-session screen is not a dedicated page yet. Expired users are removed and files are cleaned up, but the same browser identity can start fresh on the next load.
- Processing uses a full-page loading overlay and polling refresh, but it does not provide detailed step-by-step progress for extraction, detection, Excel export, and PDF highlighting.
- There is no true authentication; identity is browser-level convenience only.
- There is no always-running background cleanup worker. Cleanup happens on app load/refresh, which matches the recommended Streamlit Community Cloud approach.
- Orphan-folder cleanup is age-based at the `user_*` folder level. It does not deeply reconcile every possible orphaned run against runtime JSON state.

## Known Limitations

- The app does not yet have true login/authentication.
- Browser identity is not security-grade identity; it is session convenience.
- Pure Streamlit does not provide a reliable server-side tab-close event. Users are removed through heartbeat/inactivity timeout cleanup rather than immediate browser-close detection.
- Background cleanup is request-driven, not a continuously running worker.
- Streamlit Community Cloud may reset runtime/temp files.
- Cookie/local-storage behavior can differ in privacy-restricted browsers.
- Highlighting currently highlights full forms, not abbreviations.
- Very complex PDFs may have imperfect text extraction depending on PyMuPDF output.
- A dedicated expired-session message is not implemented yet.
- Step-by-step progress messages are not implemented yet (overlay + polling is implemented).

## Deployment Notes

For Streamlit deployment:

1. Keep `.env.example` in Git.
2. Add actual environment variables in deployment settings.
3. Keep `runtime/` and `temp_outputs/` out of Git.
4. Make sure `.streamlit/config.toml` upload size matches `MAX_PDF_SIZE_MB`.
5. Confirm dependency install works from `requirements.txt`.

## Useful Commands

Run app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Install/update dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Syntax check:

```powershell
.\.venv\Scripts\python.exe -m compileall .
```

Reset local runtime state:

```powershell
Set-Content -Path runtime\active_users.json -Value '{}' -Encoding UTF8
Set-Content -Path runtime\queue.json -Value '[]' -Encoding UTF8
```

## Good Next Steps

1. Add a sample PDF test run and verify generated Excel/PDF output.
2. Add dedicated expired-session page/message.
3. Add step-by-step progress messages for extraction, detection, Excel export, and highlighting.
4. Add lightweight unit tests for `safe_folder_name()`, `path_belongs_to_user()`, and abbreviation matching.
5. Move cookie/local-storage identity helper into its own module if `streamlit_app.py` grows more.
6. Add a "clear my files" or "end session" button.
7. Add output preview table before downloads.
8. Add deployment instructions for Streamlit Community Cloud.
