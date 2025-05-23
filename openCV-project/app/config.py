# config.py

# مسیر فونت
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

# تنظیمات پیش‌فرض برای OCR و تقسیم‌بندی خطوط
DEFAULT_OCR_LANG = 'eng'
DEFAULT_OCR_PSM_CONFIG = '--psm 6' # PSM مناسب برای تصاویر پیش‌پردازش شده و تشخیص کلمات
DEFAULT_Y_TOLERANCE_FACTOR_MANUAL_LINES = 0.7 # برای تقسیم‌بندی دستی خطوط
WORD_CONFIDENCE_THRESHOLD = 20 # حداقل اطمینان برای پردازش یا نمایش یک کلمه

WORD_CONFIDENCE_THRESHOLD_DEFAULT = 20 # مقدار پیش‌فرض برای حداقل اطمینان کلمات (0-100)