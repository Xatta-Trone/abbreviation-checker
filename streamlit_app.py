from __future__ import annotations

import shutil
import re
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
import streamlit_shadcn_ui as ui

from app_config import APP_TITLE, INACTIVITY_TIMEOUT_MINUTES, MAX_ACTIVE_USERS, MAX_PAGES, MAX_PDF_SIZE_BYTES, MAX_PDF_SIZE_MB
from file_manager import cleanup_old_files, create_run_dir, path_belongs_to_user, safe_folder_name, save_uploaded_file
from pipeline_utils import collection_to_highlight_items, export_to_excel, highlight_terms_in_pdf, process_pdf
from session_manager import clear_user_state, get_or_create_user_state, get_usage_summary, new_user_id, update_user_state


USER_COOKIE_NAME = "abbreviation_checker_user_id"
USER_STORAGE_KEY = "abbreviation_checker_user_id"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30

st.set_page_config(page_title=APP_TITLE, page_icon=":page_facing_up:", layout="centered")

st.markdown(
    """
    <style>
    .block-container {
        max-width: 920px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stFileUploader"] section {
        border-radius: 8px;
        border: 1.5px dashed #9ca3af;
        background: #f8fafc;
        min-height: 10rem;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: #111827;
        background: #f3f4f6;
    }
    div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #334155;
    }
    div[data-testid="stFileUploader"] button {
        border-color: #111827;
        background: #111827;
        color: #ffffff;
        font-weight: 700;
    }
    div[data-testid="stFileUploader"] button[title="Add file"],
    div[data-testid="stFileUploader"] button[aria-label="Add file"],
    div[data-testid="stFileUploader"] button[aria-label="Add files"] {
        display: none;
    }
    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button {
        border-radius: 8px;
        min-height: 2.65rem;
        font-weight: 600;
        transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }
    div[data-testid="stButton"] button {
        border-color: #111827;
        background: #111827;
        color: #ffffff;
    }
    div[data-testid="stButton"] button:hover {
        border-color: #111827;
        background: #000000;
        color: #ffffff;
        box-shadow: 0 8px 18px rgba(17, 24, 39, 0.08);
        transform: translateY(-1px);
    }
    div[data-testid="stButton"] button[kind="primary"] {
        border-color: #111827;
        background: #111827;
        color: white;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        border-color: #000000;
        background: #000000;
        color: white;
        box-shadow: 0 10px 22px rgba(17, 24, 39, 0.18);
    }
    div[data-testid="stButton"] button:disabled,
    div[data-testid="stButton"] button:disabled:hover {
        border-color: #e2e8f0;
        background: #f8fafc;
        color: #94a3b8;
        box-shadow: none;
        transform: none;
    }
    div[data-testid="stDownloadButton"] button {
        border-color: #111827;
        background: #111827;
        color: white;
        min-height: 3rem;
        box-shadow: 0 10px 22px rgba(17, 24, 39, 0.16);
    }
    div[data-testid="stDownloadButton"] button:hover {
        border-color: #000000;
        background: #000000;
        color: white;
        box-shadow: 0 12px 26px rgba(17, 24, 39, 0.22);
        transform: translateY(-1px);
    }
    .app-footer {
        text-align: center;
        font-size: 0.88rem;
        color: #64748b;
        margin-top: 2rem;
    }
    .app-footer a {
        color: #2563eb;
        text-decoration: none;
    }
    .feature-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0;
    }
    .feature-badge {
        display: inline-flex;
        align-items: center;
        min-height: 1.75rem;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        border: 1px solid #e2e8f0;
        background: #f8fafc;
        color: #0f172a;
        font-size: 0.86rem;
        font-weight: 600;
        line-height: 1;
        white-space: nowrap;
    }
    .feature-badge.primary {
        background: #111827;
        border-color: #111827;
        color: white;
    }
    .upload-callout {
        margin: 0.5rem 0 0.75rem;
        padding: 0.95rem 1rem;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #fafafa;
        color: #334155;
    }
    .upload-callout strong {
        display: block;
        color: #0f172a;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }
    .upload-callout span {
        display: block;
        font-size: 0.9rem;
    }
    .error-card {
        margin: 0.75rem 0 1rem;
        padding: 0.95rem 1rem;
        border: 1px solid #fecaca;
        border-left: 5px solid #dc2626;
        border-radius: 8px;
        background: #fef2f2;
        color: #7f1d1d;
    }
    .error-card strong {
        display: block;
        color: #991b1b;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }
    .error-card span {
        display: block;
        font-size: 0.92rem;
        line-height: 1.45;
    }
    div[data-testid="stToast"] p {
        color: #b91c1c !important;
        font-weight: 600;
    }
    .processing-overlay {
        position: fixed;
        inset: 0;
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.78);
        backdrop-filter: blur(5px);
    }
    .processing-panel {
        width: min(92vw, 420px);
        border: 1px solid #d1d5db;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 24px 70px rgba(17, 24, 39, 0.16);
        padding: 1.4rem;
        color: #111827;
    }
    .processing-panel strong {
        display: block;
        font-size: 1.05rem;
        margin-bottom: 0.35rem;
    }
    .processing-panel span {
        display: block;
        color: #4b5563;
        font-size: 0.92rem;
        line-height: 1.45;
        margin-bottom: 1rem;
    }
    .processing-bar {
        position: relative;
        height: 0.5rem;
        overflow: hidden;
        border-radius: 999px;
        background: #e5e7eb;
    }
    .processing-bar::after {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 42%;
        border-radius: 999px;
        background: #111827;
        animation: processing-slide 1.15s ease-in-out infinite;
    }
    @keyframes processing-slide {
        0% { transform: translateX(-105%); }
        50% { transform: translateX(75%); }
        100% { transform: translateX(245%); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def is_valid_user_id(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[a-f0-9]{32}", value))


def sync_browser_identity(user_id: str) -> None:
    components.html(
        f"""
        <script>
        const uid = "{user_id}";
        localStorage.setItem("{USER_STORAGE_KEY}", uid);
        document.cookie = "{USER_COOKIE_NAME}=" + uid + "; path=/; max-age={COOKIE_MAX_AGE_SECONDS}; SameSite=Lax";
        </script>
        """,
        height=0,
    )


def get_browser_user_id() -> str:
    query_user_id = st.query_params.get("uid")
    if is_valid_user_id(query_user_id):
        st.session_state.user_id = query_user_id
        sync_browser_identity(query_user_id)
        return query_user_id

    pending_user_id = st.session_state.get("user_id") or new_user_id()
    st.session_state.user_id = pending_user_id

    components.html(
        f"""
        <script>
        const storageKey = "{USER_STORAGE_KEY}";
        const cookieName = "{USER_COOKIE_NAME}";
        const fallbackUid = "{pending_user_id}";
        const cookieMatch = document.cookie.match(new RegExp("(^| )" + cookieName + "=([^;]+)"));
        const cookieUid = cookieMatch ? cookieMatch[2] : null;
        const storedUid = localStorage.getItem(storageKey);
        const valid = (value) => /^[a-f0-9]{{32}}$/.test(value || "");
        const uid = valid(storedUid) ? storedUid : (valid(cookieUid) ? cookieUid : fallbackUid);
        localStorage.setItem(storageKey, uid);
        document.cookie = cookieName + "=" + uid + "; path=/; max-age={COOKIE_MAX_AGE_SECONDS}; SameSite=Lax";
        const url = new URL(window.location.href);
        url.searchParams.set("uid", uid);
        window.location.replace(url.toString());
        </script>
        """,
        height=0,
    )
    st.stop()


def show_processing_overlay() -> None:
    st.markdown(
        """
        <div class="processing-overlay">
            <div class="processing-panel">
                <strong>Processing your PDF</strong>
                <span>Extracting text, building Excel results, and preparing the highlighted PDF. Please keep this tab open.</span>
                <div class="processing-bar"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_error_card(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="error-card">
            <strong>{title}</strong>
            <span>{description}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mount_client_pdf_guard() -> None:
    components.html(
        """
        <script>
        (function () {
          if (window.__pdfGuardMounted) return;
          window.__pdfGuardMounted = true;

          const toastId = "pdf-guard-toast";

          function showToast(message) {
            let toast = document.getElementById(toastId);
            if (!toast) {
              toast = document.createElement("div");
              toast.id = toastId;
              toast.style.position = "fixed";
              toast.style.right = "16px";
              toast.style.bottom = "16px";
              toast.style.zIndex = "1000000";
              toast.style.maxWidth = "360px";
              toast.style.padding = "12px 14px";
              toast.style.borderRadius = "8px";
              toast.style.background = "#ffffff";
              toast.style.border = "1px solid #fecaca";
              toast.style.borderLeft = "5px solid #dc2626";
              toast.style.color = "#b91c1c";
              toast.style.fontWeight = "600";
              toast.style.boxShadow = "0 12px 28px rgba(17,24,39,0.15)";
              toast.style.fontFamily = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
              document.body.appendChild(toast);
            }
            toast.textContent = message;
            toast.style.display = "block";
            clearTimeout(window.__pdfGuardToastTimer);
            window.__pdfGuardToastTimer = setTimeout(() => {
              toast.style.display = "none";
            }, 2600);
          }

          function filesHaveNonPdf(fileList) {
            if (!fileList || !fileList.length) return false;
            for (const file of fileList) {
              const name = (file.name || "").toLowerCase();
              const mime = (file.type || "").toLowerCase();
              const looksPdf = name.endsWith(".pdf") || mime === "application/pdf";
              if (!looksPdf) return true;
            }
            return false;
          }

          function clearAllUploaderInputs() {
            document.querySelectorAll('input[type="file"]').forEach((input) => {
              try {
                input.value = "";
              } catch (e) {}
            });
          }

          function rejectIfInvalid(fileList, evt) {
            if (!filesHaveNonPdf(fileList)) return false;
            if (evt) {
              evt.preventDefault();
              evt.stopPropagation();
              if (typeof evt.stopImmediatePropagation === "function") {
                evt.stopImmediatePropagation();
              }
            }
            clearAllUploaderInputs();
            showToast("Only PDF files are accepted. Please choose a PDF.");
            return true;
          }

          document.addEventListener("drop", (evt) => {
            rejectIfInvalid(evt.dataTransfer && evt.dataTransfer.files, evt);
          }, true);

          document.addEventListener("dragover", (evt) => {
            const files = evt.dataTransfer && evt.dataTransfer.files;
            if (filesHaveNonPdf(files)) {
              evt.preventDefault();
            }
          }, true);

          document.addEventListener("change", (evt) => {
            const target = evt.target;
            if (!target || target.tagName !== "INPUT" || target.type !== "file") return;
            rejectIfInvalid(target.files, evt);
          }, true);
        })();
        </script>
        """,
        height=0,
    )


user_id = get_browser_user_id()
cleanup_old_files()
status, state, queue_position = get_or_create_user_state(user_id)
usage = get_usage_summary()

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

if st.session_state.pop("show_invalid_file_toast", False):
    st.toast("Only PDF files are accepted. Please choose a PDF.")

st.title(APP_TITLE)
st.caption("Upload a PDF, extract abbreviation results into Excel, and download a highlighted PDF.")

limit_cols = st.columns(4)
with limit_cols[0]:
    ui.metric_card(title="Active users", content=f"{usage['active_users']}/{MAX_ACTIVE_USERS}", description="Concurrent processing slots", key="active_users_card")
with limit_cols[1]:
    ui.metric_card(title="File size", content=f"{MAX_PDF_SIZE_MB} MB", description="Maximum PDF upload", key="file_size_card")
with limit_cols[2]:
    ui.metric_card(title="Page limit", content=str(MAX_PAGES), description="Maximum PDF pages", key="page_limit_card")
with limit_cols[3]:
    ui.metric_card(title="Session", content=f"{INACTIVITY_TIMEOUT_MINUTES} min", description="Inactive files expire", key="session_limit_card")

badge_col, spacer_col, action_col = st.columns([3.2, 1.1, 1.3], vertical_alignment="center")
with badge_col:
    st.markdown(
        """
        <div class="feature-badges">
            <span class="feature-badge">PDF only</span>
            <span class="feature-badge">Private temp files</span>
            <span class="feature-badge">Excel export</span>
            <span class="feature-badge">Highlighted PDF</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with action_col:
    start_new = st.button("Start new session", use_container_width=True)

if status == "queued":
    ui.alert(
        title="The app is currently full",
        description=f"Your queue position is {queue_position}. Please keep this tab open and refresh status when a slot opens.",
        key="queued_alert",
    )
    st.button("Refresh status")
    st.stop()

if start_new:
    clear_user_state(user_id)
    st.rerun()

if state and state.get("processing"):
    show_processing_overlay()
    ui.alert(title="Processing your PDF", description="Extracting text, creating Excel results, and preparing the highlighted PDF.", key="processing_alert")
    ui.progress(75, key="processing_progress")
    time.sleep(2)
    st.rerun()
    st.stop()

if state and state.get("error"):
    show_error_card("Processing failed", str(state["error"]))

if state and state.get("completed"):
    ui.alert(title="Processing completed", description="Your Excel results and highlighted PDF are ready to download.", key="complete_alert")

    excel_path = Path(state["excel_path"]) if state.get("excel_path") else None
    pdf_path = Path(state["pdf_path"]) if state.get("pdf_path") else None

    download_cols = st.columns(2)
    if excel_path and excel_path.exists() and path_belongs_to_user(excel_path, user_id):
        with download_cols[0]:
            st.download_button(
                "Download Excel Results",
                data=excel_path.read_bytes(),
                file_name=excel_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    if pdf_path and pdf_path.exists() and path_belongs_to_user(pdf_path, user_id):
        with download_cols[1]:
            st.download_button(
                "Download Highlighted PDF",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
                use_container_width=True,
            )

    st.stop()

st.markdown(
    f"""
    <div class="upload-callout">
        <strong>Drag and drop your PDF into the highlighted area</strong>
        <span>PDF only, {MAX_PDF_SIZE_MB} MB max, {MAX_PAGES} pages max. Temporary files are isolated per browser user.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

mount_client_pdf_guard()

uploaded_file = st.file_uploader(
    "Upload PDF",
    type=["pdf"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key=f"pdf_uploader_{st.session_state.uploader_key}",
)

if isinstance(uploaded_file, list):
    show_error_card("Only one PDF can be uploaded", "Please remove extra files and keep one PDF for this run.")
    st.toast("Only one PDF can be uploaded at a time.")
    st.stop()

if uploaded_file and not uploaded_file.name.lower().endswith(".pdf"):
    st.session_state.uploader_key += 1
    st.session_state.show_invalid_file_toast = True
    st.rerun()

if uploaded_file and uploaded_file.size > MAX_PDF_SIZE_BYTES:
    show_error_card("PDF is too large", f"Please upload a file smaller than {MAX_PDF_SIZE_MB} MB.")
    st.stop()

process_cols = st.columns([1, 2])
with process_cols[0]:
    process_clicked = st.button("Process PDF", type="primary", disabled=uploaded_file is None, use_container_width=True)

if uploaded_file and process_clicked:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base_name = safe_folder_name(uploaded_file.name, max_length=80)
    run_dir = create_run_dir(user_id, uploaded_file.name, timestamp=timestamp)
    uploaded_pdf_path = run_dir / "uploaded.pdf"
    excel_path = run_dir / f"{output_base_name}_abbr_results_{timestamp}.xlsx"
    highlighted_pdf_path = run_dir / f"{output_base_name}_highlighted_{timestamp}.pdf"

    update_user_state(
        user_id,
        current_run_dir=str(run_dir),
        processing=True,
        completed=False,
        error=None,
        excel_path=None,
        pdf_path=None,
    )
    show_processing_overlay()

    try:
        save_uploaded_file(uploaded_file, uploaded_pdf_path)
        collection = process_pdf(uploaded_pdf_path, run_dir, max_pages=MAX_PAGES)
        export_to_excel(collection, excel_path)
        highlight_terms_in_pdf(uploaded_pdf_path, highlighted_pdf_path, collection_to_highlight_items(collection))
        update_user_state(
            user_id,
            processing=False,
            completed=True,
            excel_path=str(excel_path),
            pdf_path=str(highlighted_pdf_path),
            error=None,
        )
    except Exception as exc:
        shutil.rmtree(run_dir, ignore_errors=True)
        update_user_state(user_id, processing=False, completed=False, error=str(exc))

    st.rerun()

st.markdown(
    """
    <hr>
    <div class="app-footer">
        Developed and maintained by
        <a href="https://github.com/Xatta-Trone" target="_blank">Monzurul Islam</a>
    </div>
    """,
    unsafe_allow_html=True,
)
