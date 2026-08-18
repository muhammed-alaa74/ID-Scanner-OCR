import re
import streamlit as st
from PIL import Image
import numpy as np
import pytesseract

# ---- Tesseract path (Windows) ----
ocr_path = r"E:\C_Progs\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = ocr_path

st.set_page_config(page_title="ID Scanner OCR", page_icon="🪪", layout="centered")

# ---------------- CSS ----------------
st.markdown("""
<style>
    .stApp {
        background: #f5ead9;
        color: #4a3625;
    }

    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        text-align: center;
        color: #c8631c;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        text-align: center;
        color: #8a7259;
        margin-bottom: 1.8rem;
        font-size: 0.92rem;
    }

    [data-testid="stFileUploader"] {
        background: #fbf3e7;
        border: 1.5px dashed #d98a4a;
        border-radius: 12px;
        padding: 1rem;
        transition: border-color 0.2s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #c8631c;
    }

    .info-card {
        background: #fbf3e7;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-top: 1rem;
        border: 1px solid #e6d3b8;
    }

    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 0.55rem 0.3rem;
        border-bottom: 1px solid #ecdfc9;
        border-radius: 6px;
        transition: background 0.2s ease;
    }
    .info-row:last-child { border-bottom: none; }
    .info-row:hover {
        background: #f2e2c8;
    }

    .info-label {
        color: #b8641f;
        font-weight: 600;
    }
    .info-value {
        color: #4a3625;
        font-weight: 400;
        text-align: right;
    }

    .stImage img {
        border-radius: 12px;
        border: 1px solid #e6d3b8;
    }

    .raw-text {
        background: #fbf3e7;
        border-radius: 10px;
        padding: 1rem;
        font-family: monospace;
        color: #7a6650;
        white-space: pre-wrap;
        border: 1px solid #e6d3b8;
    }

    button[kind="secondary"], .stButton button {
        background: #d98a4a !important;
        color: #fff !important;
        border: 1px solid #c8631c !important;
        transition: background 0.2s ease !important;
    }
    button[kind="secondary"]:hover, .stButton button:hover {
        background: #c8631c !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- Header ----------------
st.markdown('<div class="main-title">🪪 ID Scanner</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Upload an ID card image to extract info using OCR</div>', unsafe_allow_html=True)


def extract_text_from_id(image: np.ndarray) -> str:
    return pytesseract.image_to_string(image)


LABELS = ["phone", "email", "address", "website"]


def extract_after_label(label: str, text: str) -> str | None:
    """Grab the text after `label:` up to the next known label (colon optional),
    since not every field on a card is followed by ':'."""
    stop = "|".join(l for l in LABELS if l != label)
    pattern = rf"{label}\s*:?\s*(.*?)(?=\s*(?:{stop})\b|$)"
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    value = m.group(1).strip(" .,'\"<>‘’")
    return value or None


def parse_id_text(raw_text: str) -> dict:
    """Extract fields by keyword/pattern instead of fixed line positions,
    since OCR line-splitting varies a lot between ID layouts."""
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    full_text = " ".join(lines)

    # --- Organization: merge consecutive ALL-CAPS / logo-style lines at the top ---
    org_lines = []
    for line in lines:
        if re.search(r"phone|email|address|www\.|http", line, re.IGNORECASE):
            break
        if re.match(r"^[A-Z0-9&.,'\- ]+$", line):
            org_lines.append(line)
        else:
            break
    organization = " ".join(org_lines) if org_lines else (lines[0] if lines else None)

    # --- Email: allow missing dot (common OCR error) but require @ ---
    email = extract_after_label("email", full_text) or None
    if not email:
        m = re.search(r"[\w.\-]+@[\w.\-]+(?:\.[a-zA-Z]{2,})?", full_text)
        email = m.group(0) if m else None

    # --- Phone: prefer an explicit "Phone:" label over stray digit sequences ---
    m = re.search(r"phone\s*:?\s*(\+?\d[\d\-\s]{6,}\d)", full_text, re.IGNORECASE)
    phone = m.group(1).strip() if m else None
    if not phone:
        m = re.search(r"(\+?\d[\d\-\s]{7,}\d)", full_text)
        phone = m.group(1).strip() if m else None

    # --- Address: stop at the next label instead of at a comma ---
    address = extract_after_label("address", full_text)

    # --- Name: a line with 2-3 REAL words (actual whitespace between them) ---
    name = None
    for line in lines:
        if line in org_lines:
            continue
        if "@" in line or any(k in line.lower() for k in LABELS):
            continue
        if re.match(r"^[A-Z][a-zA-Z']*(?:\s+[A-Z][a-zA-Z']*){1,2}$", line):
            name = line
            break

    return {
        "Organization": organization or "—",
        "Employee Name": name or "—",
        "Phone Number": phone or "—",
        "Email": email or "—",
        "Address": address or "—",
    }


uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image_np = np.array(image)

    st.image(image, caption="Uploaded ID", use_container_width=True)

    with st.spinner("Extracting text..."):
        extracted_text = extract_text_from_id(image_np)

    if not extracted_text.strip():
        st.warning("Couldn't extract any text from this image. Try a clearer photo.")
    else:
        fields = parse_id_text(extracted_text)

        rows_html = "".join(
            f'<div class="info-row"><span class="info-label">{label}</span>'
            f'<span class="info-value">{value}</span></div>'
            for label, value in fields.items()
        )
        st.markdown(f'<div class="info-card">{rows_html}</div>', unsafe_allow_html=True)

        with st.expander("Show raw extracted text"):
            st.markdown(f'<div class="raw-text">{extracted_text}</div>', unsafe_allow_html=True)