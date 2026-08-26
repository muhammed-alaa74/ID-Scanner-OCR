import re
import streamlit as st
from PIL import Image
import numpy as np
import pytesseract
import os
import shutil
import html
from PIL import Image, ImageEnhance, ImageFilter



# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ID Scanner OCR",
    page_icon="🪪",
    layout="centered"
)


# ============================================================
# TESSERACT CONFIGURATION
# Streamlit Cloud + Windows Local
# ============================================================

def setup_tesseract():
    # Streamlit Cloud / Linux
    tesseract_path = shutil.which("tesseract")

    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return True

    # Windows local fallback
    local_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"E:\C_Progs\tesseract.exe",
    ]

    for path in local_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True

    return False


if not setup_tesseract():
    st.error(
        "Tesseract OCR was not found.\n\n"
        "For Streamlit Cloud, make sure you have a file named "
        "`packages.txt` containing:\n\n"
        "tesseract-ocr\n"
        "tesseract-ocr-eng\n"
        "tesseract-ocr-ara"
    )
    st.stop()


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
        align-items: flex-start;
        gap: 20px;
        padding: 0.7rem 0.3rem;
        border-bottom: 1px solid #ecdfc9;
        border-radius: 6px;
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
        min-width: 130px;
    }

    .info-value {
        color: #4a3625;
        font-weight: 400;
        text-align: right;
        word-break: break-word;
    }

    .raw-text {
        background: #fbf3e7;
        border-radius: 10px;
        padding: 1rem;
        font-family: monospace;
        color: #7a6650;
        white-space: pre-wrap;
        border: 1px solid #e6d3b8;
        overflow-x: auto;
    }

    .ocr-status {
        background: #fbf3e7;
        border: 1px solid #e6d3b8;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-top: 1rem;
        color: #7a6650;
        text-align: center;
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
    'Upload an ID card or business card image to extract information using OCR'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image: Image.Image) -> np.ndarray:

    # Convert to RGB
    image = image.convert("RGB")

    # -----------------------------------------
    # Upscale small images
    # -----------------------------------------

    width, height = image.size

    if width < 1600:
        scale = 1600 / width
        new_width = int(width * scale)
        new_height = int(height * scale)

        image = image.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

    # -----------------------------------------
    # Grayscale
    # -----------------------------------------

    gray = image.convert("L")

    # -----------------------------------------
    # Contrast
    # -----------------------------------------

    gray = ImageEnhance.Contrast(gray).enhance(1.8)

    # -----------------------------------------
    # Sharpness
    # -----------------------------------------

    gray = ImageEnhance.Sharpness(gray).enhance(1.5)

    # -----------------------------------------
    # Slight denoise
    # -----------------------------------------

    gray = gray.filter(
        ImageFilter.SHARPEN
    )

    return np.array(gray)


# ============================================================
# OCR
# ============================================================

def extract_text_from_id(image: Image.Image) -> str:

    processed = preprocess_image(image)

    texts = []

    # -----------------------------------------
    # OCR Pass 1
    # -----------------------------------------

    try:

        text1 = pytesseract.image_to_string(
            processed,
            lang="eng+ara",
            config="--oem 3 --psm 6"
        )

        if text1.strip():
            texts.append(text1)

    except Exception:
        pass

    # -----------------------------------------
    # OCR Pass 2
    # -----------------------------------------

    try:

        text2 = pytesseract.image_to_string(
            processed,
            lang="eng+ara",
            config="--oem 3 --psm 11"
        )

        if text2.strip():
            texts.append(text2)

    except Exception:
        pass

    # -----------------------------------------
    # Choose the best OCR result
    # -----------------------------------------

    if not texts:
        return ""

    # Prefer the result containing more useful labels
    def score(text):

        score_value = len(text)

        useful_words = [
            "phone",
            "email",
            "address",
            "website",
            "mobile",
            "tel",
        ]

        for word in useful_words:
            if word.lower() in text.lower():
                score_value += 100

        return score_value

    return max(
        texts,
        key=score
    )


# ============================================================
# LABELS
# ============================================================

LABELS = [
    "phone",
    "email",
    "address",
    "website",
    "mobile",
    "tel"
]


# ============================================================
# NORMALIZE OCR TEXT
# ============================================================

def normalize_text(text: str) -> str:

    replacements = {
        "E-mail": "Email",
        "e-mail": "Email",
        "EMAIL": "Email",
        "PHONE": "Phone",
        "ADDRESS": "Address",
        "MOBILE": "Mobile",
        "WEBSITE": "Website",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ============================================================
# EXTRACT AFTER LABEL
# ============================================================

def extract_after_label(
    label: str,
    text: str
) -> str | None:

    stop_labels = [
        l for l in LABELS
        if l.lower() != label.lower()
    ]

    stop_pattern = "|".join(
        re.escape(x)
        for x in stop_labels
    )

    pattern = (
        rf"{re.escape(label)}"
        rf"\s*[:<\-]?\s*"
        rf"(.*?)"
        rf"(?=\s*(?:{stop_pattern})\b|$)"
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
# EMAIL EXTRACTION
# ============================================================

def extract_email(text: str):

    # First: normal email pattern
    match = re.search(
        r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+",
        text
    )

    if match:
        return match.group(0)

    # Second: allow OCR to miss the final dot
    match = re.search(
        r"[\w.+\-]+@[\w\-]+",
        text
    )

    if match:
        return match.group(0)

    return None


# ============================================================
# PHONE EXTRACTION
# ============================================================

def extract_phone(text: str):

    # Prefer phone label
    match = re.search(
        r"(?:phone|mobile|tel)"
        r"\s*[:<\-]?\s*"
        r"(\+?\d[\d\s().\-]{7,}\d)",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    # Fallback: any phone-like number
    matches = re.findall(
        r"\+?\d[\d\s().\-]{7,}\d",
        text
    )

    if matches:

        # Remove obviously short/noisy numbers
        valid = [
            x.strip()
            for x in matches
            if len(re.sub(r"\D", "", x)) >= 8
        ]

        if valid:
            return valid[0]

    return None


# ============================================================
# ADDRESS EXTRACTION
# ============================================================

def extract_address(text: str):

    address = extract_after_label(
        "address",
        text
    )

    if address:
        return address

    # Try common OCR variation
    match = re.search(
        r"(?:address|addres)"
        r"\s*[:<\-]?\s*(.*?)(?="
        r"\s+(?:phone|email|mobile|website|tel)\b"
        r"|$)",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip(
            """ .,'"< >‘’"""
        )

    return None


# ============================================================
# ORGANIZATION EXTRACTION
# ============================================================

def extract_organization(lines):

    if not lines:
        return None

    candidates = []

    for line in lines[:5]:

        cleaned = line.strip()

        if not cleaned:
            continue

        lower = cleaned.lower()

        # Ignore contact information
        if (
            "phone" in lower
            or "email" in lower
            or "address" in lower
            or "@" in cleaned
            or re.search(r"\d{4,}", cleaned)
        ):
            continue

        # Ignore obvious job titles
        title_words = [
            "director",
            "manager",
            "developer",
            "designer",
            "engineer",
            "officer",
            "executive",
            "founder",
            "ceo",
            "president"
        ]

        if any(
            word in lower
            for word in title_words
        ):
            continue

        # Strong candidate:
        # mostly uppercase
        uppercase_count = sum(
            c.isupper()
            for c in cleaned
        )

        letters_count = sum(
            c.isalpha()
            for c in cleaned
        )

        if letters_count > 0:

            uppercase_ratio = (
                uppercase_count /
                letters_count
            )

            if uppercase_ratio > 0.65:
                candidates.append(cleaned)

    if candidates:
        return candidates[0]

    return lines[0].strip()


# ============================================================
# NAME EXTRACTION
# ============================================================

def extract_name(lines):

    for line in lines:

        cleaned = line.strip()

        if not cleaned:
            continue

        lower = cleaned.lower()

        # Skip contact information
        if (
            "@" in cleaned
            or re.search(r"\+?\d[\d\s().\-]{7,}", cleaned)
            or any(
                label in lower
                for label in LABELS
            )
        ):
            continue

        # Skip organization-looking lines
        if re.fullmatch(
            r"[A-Z0-9&.,'\- ]+",
            cleaned
        ):
            continue

        # Skip common job titles
        title_words = [
            "director",
            "manager",
            "developer",
            "designer",
            "engineer",
            "officer",
            "executive",
            "founder",
            "ceo",
            "president",
            "creative"
        ]

        if any(
            word in lower
            for word in title_words
        ):
            continue

        # Name: 2-4 words
        words = cleaned.split()

        if 2 <= len(words) <= 4:

            valid_words = 0

            for word in words:

                word = re.sub(
                    r"[^A-Za-zÀ-ÿ'-]",
                    "",
                    word
                )

                if len(word) >= 2:
                    valid_words += 1

            if valid_words >= 2:
                return cleaned

    return None


# ============================================================
# PARSE OCR TEXT
# ============================================================

def parse_id_text(raw_text: str) -> dict:

    raw_text = normalize_text(
        raw_text
    )

    lines = [
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    ]

    full_text = " ".join(lines)

    # -----------------------------------------
    # Organization
    # -----------------------------------------

    organization = extract_organization(
        lines
    )

    # -----------------------------------------
    # Employee Name
    # -----------------------------------------

    name = extract_name(
        lines
    )

    # -----------------------------------------
    # Phone
    # -----------------------------------------

    phone = extract_phone(
        full_text
    )

    # -----------------------------------------
    # Email
    # -----------------------------------------

    email = extract_email(
        full_text
    )

    # -----------------------------------------
    # Address
    # -----------------------------------------

    address = extract_address(
        full_text
    )

    # -----------------------------------------
    # Return
    # -----------------------------------------

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
# MAIN PROCESSING
# ============================================================

if uploaded_file is not None:

    try:

        # -----------------------------------------
        # Load image
        # -----------------------------------------

        image = Image.open(
            uploaded_file
        )

        # -----------------------------------------
        # Display image
        # -----------------------------------------

        st.image(
            image,
            caption="Uploaded ID",
            use_container_width=True
        )

        # -----------------------------------------
        # OCR
        # -----------------------------------------

        with st.spinner(
            "Extracting text..."
        ):

            extracted_text = (
                extract_text_from_id(
                    image
                )
            )

        # -----------------------------------------
        # Check result
        # -----------------------------------------

        if not extracted_text.strip():

            st.warning(
                "Couldn't extract any text "
                "from this image. "
                "Try a clearer photo."
            )

        else:

            # -------------------------------------
            # Parse data
            # -------------------------------------

            fields = parse_id_text(
                extracted_text
            )

            # -------------------------------------
            # Build safe HTML
            # -------------------------------------

            rows_html = ""

            for label, value in fields.items():

                safe_label = html.escape(
                    str(label)
                )

                safe_value = html.escape(
                    str(value)
                )

                rows_html += f"""
                <div class="info-row">
                    <span class="info-label">
                        {safe_label}
                    </span>

                    <span class="info-value">
                        {safe_value}
                    </span>
                </div>
                """

            # -------------------------------------
            # Display results
            # -------------------------------------

            st.markdown(
                f"""
                <div class="info-card">
                    {rows_html}
                </div>
                """,
                unsafe_allow_html=True
            )

            # -------------------------------------
            # Raw OCR
            # -------------------------------------

            with st.expander(
                "Show raw extracted text"
            ):

                safe_raw_text = html.escape(
                    extracted_text
                )

                st.markdown(
                    f"""
                    <div class="raw-text">
                        {safe_raw_text}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    except Exception as e:

        st.error(
            f"Could not process the image: {e}"
        )