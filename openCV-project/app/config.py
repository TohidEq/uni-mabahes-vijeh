# config.py

# Font Path
FONT_PATH = "/home/tohid-eq/Desktop/vazirmatn/fonts/ttf/Vazirmatn-Light.ttf"
GLOBAL_FONT_DEFAULT_SIZE = 28
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 60

LANGUAGE_OPTIONS = {
    "Farsi (Persian)": "fa",
    "Arabi (Arabic)": "ar",
    "Faransavi (French)": "fr",
    "Espaniyayi (Spanish)": "es",
    "Almani (German)": "de",
    "Chini (Chinese)": "zh-CN",
    "Rusi (Russian)": "ru",
    "Engilisi (English)": "en"
}

# Default OCR and Line Segmentation Settings
DEFAULT_OCR_LANG = 'eng'
DEFAULT_OCR_PSM_CONFIG = '--psm 6' # مقدار پیش‌فرض اولیه برای منوی کشویی PSM

# گزینه‌های Page Segmentation Mode برای UI
# توضیحات مختصر برای هر گزینه:
# PSM 0: Orientation and script detection (OSD) only.
# PSM 1: Automatic page segmentation with OSD.
# PSM 3: Fully automatic page segmentation, but no OSD. (Default Tesseract)
# PSM 4: Assume a single column of text of variable sizes.
# PSM 5: Assume a single uniform block of vertically aligned text.
# PSM 6: Assume a single uniform block of text. (پیش‌فرض فعلی شما)
# PSM 7: Treat the image as a single text line.
# PSM 8: Treat the image as a single word.
# PSM 9: Treat the image as a single word in a circle.
# PSM 10: Treat the image as a single character.
# PSM 11: Sparse text. Find as much text as possible in no particular order.
# PSM 12: Sparse text with OSD.
# PSM 13: Raw line. Treat the image as a single text line, bypassing hacks.
PSM_OPTIONS = {
    "PSM 3 (Auto Full Page)": "--psm 3",
    "PSM 4 (Single Column)": "--psm 4",
    "PSM 6 (Single Block - Default)": "--psm 6", # پیش‌فرض برنامه
    "PSM 7 (Single Line)": "--psm 7",
    "PSM 8 (Single Word)": "--psm 8",
    "PSM 10 (Single Char)": "--psm 10",
    "PSM 11 (Sparse Text)": "--psm 11",
    "PSM 12 (Sparse Text OSD)": "--psm 12",
    "PSM 13 (Raw Line)": "--psm 13",
    "PSM 1 (Auto OSD)": "--psm 1",
    "PSM 0 (OSD Only)": "--psm 0"
}


DEFAULT_Y_TOLERANCE_FACTOR_MANUAL_LINES = 0.7
WORD_CONFIDENCE_THRESHOLD_DEFAULT = 20

# Default Preprocessing Parameters
GAUSSIAN_BLUR_KERNEL_SIZE_DEFAULT = 5
ADAPTIVE_THRESHOLD_BLOCK_SIZE_DEFAULT = 21
ADAPTIVE_THRESHOLD_C_DEFAULT = 4