import cv2
import pytesseract
import re
from difflib import get_close_matches

# ==============================
# IMAGE PREPROCESSING
# ==============================
def preprocess_image(image_path):
    """Load and preprocess image for better OCR."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image file not found: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

# ==============================
# OCR EXTRACTION
# ==============================
def extract_text(image):
    """Run OCR using Tesseract."""
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(image, config=custom_config, lang='eng+hin')
    return text

# ==============================
# TEXT CLEANING
# ==============================
def clean_text(text):
    """Fix common OCR errors and normalize text for easier matching."""
    text_lower = text.lower()

    # Normalize 'firstclass' to 'first class'
    text_lower = text_lower.replace("firstclass", "first class")

    corrections = {
        "finstciass": "first class",
        "f1rst class": "first class",
        "pirst class": "first class",
        "distinccion": "distinction",
        "distincion": "distinction",
        "disticntion": "distinction",
        "distinclion": "distinction",
        "passs": "pass",
    }

    for wrong, correct in corrections.items():
        text_lower = text_lower.replace(wrong, correct)

    return text_lower

# ==============================
# EXTRACT CERTIFICATE DATA
# ==============================
def extract_certificate_data(ocr_text):
    """Extract Name, Registration Number, and Grade."""
    combined_text = " ".join(ocr_text.split())
    cleaned_text = clean_text(combined_text)

    # -------- Registration Number --------
    reg_match = re.search(r"(Reg\.?No\.?:?\s*)(\d{5,15})", combined_text, re.IGNORECASE)
    registration_number = reg_match.group(2) if reg_match else None

    if registration_number is None:
        # Fallback: find any 8-12 digit number
        alt_match = re.search(r"\b\d{8,12}\b", combined_text)
        registration_number = alt_match.group(0) if alt_match else None

    # -------- Grade Extraction --------
    possible_grades = [
        "first class distinction",
        "first class",
        "second class",
        "pass"
    ]

    grade_found = None
    for grade in possible_grades:
        if grade in cleaned_text:
            grade_found = grade.upper()
            break
        # Fuzzy matching
        words = cleaned_text.split()
        matches = get_close_matches(grade, words, n=1, cutoff=0.8)
        if matches:
            grade_found = grade.upper()
            break

    # -------- Name Extraction --------
    name_match = re.search(r"\bon\s+([A-Z][A-Z\s]+[A-Z])", combined_text)
    if name_match:
        name = name_match.group(1).strip()
    else:
        # Get uppercase text blocks
        candidates = re.findall(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b", combined_text)
        blacklist = [
            "FIRST CLASS", "DISTINCTION", "SECOND CLASS", "PASS",
            "STATE BOARD", "UNIVERSITY", "TECHNICAL", "EDUCATION",
            "DIPLOMA", "EXAMINATION", "REGISTRAR", "CERTIFICATE",
            "JHARKHAND", "GOVERNMENT POLYTECHNIC"
        ]
        filtered_candidates = [c for c in candidates if not any(b in c for b in blacklist)]
        name = max(filtered_candidates, key=len) if filtered_candidates else None

    return {
        "Name": name,
        "Registration Number": registration_number,
        "Grade": grade_found
    }

# ==============================
# MAIN PIPELINE FUNCTION
# ==============================
def process_certificate(image_path):
    """Full pipeline: preprocess, OCR, extract data."""
    processed_image = preprocess_image(image_path)
    ocr_text = extract_text(processed_image)
    return extract_certificate_data(ocr_text)
