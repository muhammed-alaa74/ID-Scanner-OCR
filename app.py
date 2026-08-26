import re
import streamlit as st
from PIL import Image
import numpy as np
import pytesseract
import os
import shutil


# ============================================================
# TESSERACT OCR CONFIGURATION
# Works on Streamlit Cloud (Linux) and local Windows
# ============================================================

tesseract_path = shutil.which("tesseract")

if tesseract_path:
    # Streamlit Cloud / Linux
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

else:
    # Local Windows fallback
    local_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"E:\C_Progs\tesseract.exe",
    ]

    for path in local_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
    else:
        st.error(
            "Tesseract OCR is not installed.\n\n"
            "For Streamlit Cloud, make sure packages.txt contains:\n"
            "tesseract-ocr\n"
            "tesseract-ocr-eng\n"
            "tesseract-ocr-ara"
        )
        st.stop()


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ID Scanner OCR",
    page_icon="🪪",
    layout="centered"
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
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
            gap: 20px;
            padding: 0.55rem 0.3rem;
            border-bottom: 1px solid #ecdfc9;
            border-radius: 6px;
            transition: background 0.2s ease;
        }

        .info-row:last-child {
            border-bottom: none;
        }

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
            word-break: break-word;
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

        button[kind="secondary"],
        .stButton button {
            background: #d98a4a !important;
            color: #fff !important;
            border: 1px solid #c8631c !important;
            transition: background 0.2s ease !important;
        }

        button[kind="secondary"]:hover,
        .stButton button:hover {
            background: #c8631c !important;
        }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🪪 ID Scanner</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Upload an ID card image to extract info using OCR'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# OCR FUNCTION
# ============================================================

def extract_text_from_id(image: np.ndarray) -> str:

    try:
        # Arabic + English OCR
        text = pytesseract.image_to_string(
            image,
            lang="eng+ara"
        )

        return text

    except pytesseract.TesseractNotFoundError:
        st.error(
            "Tesseract OCR was not found. "
            "Please check your Streamlit packages.txt file."
        )
        return ""

    except pytesseract.TesseractError as e:
        st.error(f"Tesseract OCR error: {e}")
        return ""

    except Exception as e:
        st.error(f"OCR failed: {e}")
        return ""


# ============================================================
# LABELS
# ============================================================

LABELS = [
    "phone",
    "email",
    "address",
    "website"
]


# ============================================================
# EXTRACT TEXT AFTER LABEL
# ============================================================

def extract_after_label(label: str, text: str) -> str | None:

    stop = "|".join(
        re.escape(l)
        for l in LABELS
        if l != label
    )

    pattern = (
        rf"{re.escape(label)}"
        rf"\s*:?\s*"
        rf"(.*?)"
        rf"(?=\s*(?:{stop})\b|$)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = match.group(1).strip(
        """ .,'"< >‘’"""
    )

    return value or None


# ============================================================
# PARSE OCR TEXT
# ============================================================

def parse_id_text(raw_text: str) -> dict:

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    full_text = " ".join(lines)

    # --------------------------------------------------------
    # Organization
    # --------------------------------------------------------

    org_lines = []

    for line in lines:

        if re.search(
            r"phone|email|address|www\.|http",
            line,
            re.IGNORECASE
        ):
            break

        if re.match(
            r"^[A-Z0-9&.,'\- ]+$",
            line
        ):
            org_lines.append(line)

        else:
            break

    organization = (
        " ".join(org_lines)
        if org_lines
        else (lines[0] if lines else None)
    )

    # --------------------------------------------------------
    # Email
    # --------------------------------------------------------

    email = extract_after_label(
        "email",
        full_text
    )

    if not email:

        match = re.search(
            r"[\w.\-]+@[\w.\-]+(?:\.[a-zA-Z]{2,})?",
            full_text
        )

        email = (
            match.group(0)
            if match
            else None
        )

    # --------------------------------------------------------
    # Phone
    # --------------------------------------------------------

    match = re.search(
        r"phone\s*:?\s*(\+?\d[\d\-\s]{6,}\d)",
        full_text,
        re.IGNORECASE
    )

    phone = (
        match.group(1).strip()
        if match
        else None
    )

    if not phone:

        match = re.search(
            r"(\+?\d[\d\-\s]{7,}\d)",
            full_text
        )

        phone = (
            match.group(1).strip()
            if match
            else None
        )

    # --------------------------------------------------------
    # Address
    # --------------------------------------------------------

    address = extract_after_label(
        "address",
        full_text
    )

    # --------------------------------------------------------
    # Employee Name
    # --------------------------------------------------------

    name = None

    for line in lines:

        if line in org_lines:
            continue

        if "@" in line:
            continue

        if any(
            keyword in line.lower()
            for keyword in LABELS
        ):
            continue

        if re.match(
            r"^[A-Z][a-zA-Z']*"
            r"(?:\s+[A-Z][a-zA-Z']*){1,2}$",
            line
        ):
            name = line
            break

    # --------------------------------------------------------
    # Return fields
    # --------------------------------------------------------

    return {
        "Organization": organization or "—",
        "Employee Name": name or "—",
        "Phone Number": phone or "—",
        "Email": email or "—",
        "Address": address or "—",
    }


# ============================================================
# FILE UPLOADER
# ============================================================

uploaded_file = st.file_uploader(
    "Choose an image...",
    type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


# ============================================================
# PROCESS IMAGE
# ============================================================

if uploaded_file is not None:

    try:

        image = Image.open(
            uploaded_file
        )

        image_np = np.array(image)

        st.image(
            image,
            caption="Uploaded ID",
            use_container_width=True
        )

        # ----------------------------------------------------
        # OCR
        # ----------------------------------------------------

        with st.spinner(
            "Extracting text..."
        ):

            extracted_text = (
                extract_text_from_id(
                    image_np
                )
            )

        # ----------------------------------------------------
        # No text
        # ----------------------------------------------------

        if not extracted_text.strip():

            st.warning(
                "Couldn't extract any text "
                "from this image. "
                "Try a clearer photo."
            )

        # ----------------------------------------------------
        # Text found
        # ----------------------------------------------------

        else:

            fields = parse_id_text(
                extracted_text
            )

            rows_html = "".join(
                f"""
                <div class="info-row">
                    <span class="info-label">
                        {label}
                    </span>

                    <span class="info-value">
                        {value}
                    </span>
                </div>
                """
                for label, value
                in fields.items()
            )

            st.markdown(
                f"""
                <div class="info-card">
                    {rows_html}
                </div>
                """,
                unsafe_allow_html=True
            )

            # ------------------------------------------------
            # Raw OCR text
            # ------------------------------------------------

            with st.expander(
                "Show raw extracted text"
            ):

                st.markdown(
                    f"""
                    <div class="raw-text">
                        {extracted_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    except Exception as e:

        st.error(
            f"Could not process the image: {e}"
        )