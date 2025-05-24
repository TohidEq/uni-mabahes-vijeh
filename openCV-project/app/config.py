# config.py

# Font Path
FONT_PATH = "/home/tohid-eq/Desktop/vazirmatn/fonts/ttf/Vazirmatn-Light.ttf" #
GLOBAL_FONT_DEFAULT_SIZE = 28 #
MIN_FONT_SIZE = 10 #
MAX_FONT_SIZE = 60 #

LANGUAGE_OPTIONS = {
    "Farsi (Persian)": "fa",
    "Arabi (Arabic)": "ar", #
    "Faransavi (French)": "fr", #
    "Espaniyayi (Spanish)": "es", #
    "Almani (German)": "de", #
    "Chini (Chinese)": "zh-CN", #
    "Rusi (Russian)": "ru", #
    "Engilisi (English)": "en" #
}

# Default OCR and Line Segmentation Settings
DEFAULT_OCR_LANG = 'eng' #
DEFAULT_OCR_PSM_CONFIG = '--psm 6' # PSM suitable for preprocessed images and word detection #
DEFAULT_Y_TOLERANCE_FACTOR_MANUAL_LINES = 0.7 # For manual line segmentation #
WORD_CONFIDENCE_THRESHOLD_DEFAULT = 20 # Default minimum confidence for words (0-100) #

# Default Preprocessing Parameters
GAUSSIAN_BLUR_KERNEL_SIZE_DEFAULT = 5 # Must be odd
ADAPTIVE_THRESHOLD_BLOCK_SIZE_DEFAULT = 21 # Must be odd
ADAPTIVE_THRESHOLD_C_DEFAULT = 4