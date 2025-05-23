# ocr_utils.py
import pandas as pd
import pytesseract
import cv2 as cv # برای توابع OpenCV
from PIL import Image as pl_image # برای جلوگیری از تداخل نام با Image از PIL

def preprocess_image_for_ocr(img_cv_original):
    """یک تصویر OpenCV را برای بهبود OCR پیش‌پردازش می‌کند."""
    if img_cv_original is None:
        print("هشدار: تصویر ورودی برای پیش‌پردازش خالی است (در ocr_utils).")
        return None

    processed_img = img_cv_original
    try:
        if len(processed_img.shape) == 3 and processed_img.shape[2] == 3:
            processed_img = cv.cvtColor(processed_img, cv.COLOR_BGR2GRAY)
        elif len(processed_img.shape) != 2:
            print("هشدار: فرمت تصویر برای تبدیل به خاکستری نامشخص است (در ocr_utils).")
            return processed_img

        blurred = cv.GaussianBlur(processed_img, (5, 5), 0)
        # THRESH_BINARY_INV (متن سفید، پس‌زمینه سیاه) معمولا برای تسراکت بهتر است
        thresh = cv.adaptiveThreshold(blurred, 255,
                                     cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv.THRESH_BINARY_INV,
                                     21, 4) # این مقادیر ممکن است نیاز به تنظیم داشته باشند
        return thresh
    except Exception as e:
        print(f"خطا در پیش‌پردازش تصویر (ocr_utils): {e}")
        return img_cv_original # در صورت خطا، تصویر اصلی را برگردان (یا None)


def get_structured_ocr_data(ocr_input_image_cv, lang='eng', psm_config='--psm 6'):
    """اجرای OCR روی تصویر OpenCV ورودی و برگرداندن DataFrame تمیز شده."""
    if ocr_input_image_cv is None:
        # print("DEBUG: تصویر ورودی به get_structured_ocr_data خالی است.")
        return pd.DataFrame()

    try:
        # تبدیل تصویر OpenCV (احتمالاً خاکستری یا دودویی) به PIL برای Pytesseract
        if len(ocr_input_image_cv.shape) == 2:
            img_pil_for_tesseract = pl_image.fromarray(ocr_input_image_cv)
        elif len(ocr_input_image_cv.shape) == 3 and ocr_input_image_cv.shape[2] == 3:
            img_pil_for_tesseract = pl_image.fromarray(cv.cvtColor(ocr_input_image_cv, cv.COLOR_BGR2RGB))
        else:
            raise ValueError(f"فرمت کانال تصویر ورودی به OCR نامشخص است: {ocr_input_image_cv.shape}")

        df = pytesseract.image_to_data(img_pil_for_tesseract, lang=lang,
                                       output_type=pytesseract.Output.DATAFRAME,
                                       config=psm_config)
    except pytesseract.TesseractError as tess_err: # خطاهای مربوط به خود اجرا Tesseract
        print(f"خطای اجرایی Tesseract در get_structured_ocr_data: {tess_err}")
        raise # این خطا باید در main_app گرفته شود
    except Exception as e: # سایر خطاها در این تابع
        print(f"خطای ناشناخته هنگام اجرای image_to_data در ocr_utils: {e}")
        raise

    if df is None or df.empty:
        return pd.DataFrame()

    df.dropna(subset=['text'], inplace=True)
    df = df[df['text'].astype(str).str.strip() != '']
    if df.empty: return pd.DataFrame()

    df['conf'] = pd.to_numeric(df['conf'], errors='coerce').fillna(-1).astype(int)

    structural_cols = ['level','page_num','block_num','par_num','line_num','word_num','left','top','width','height']
    for col in structural_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            # این حالت نباید با output_type=DATAFRAME رخ دهد مگر اینکه خروجی تسراکت ناقص باشد
            raise ValueError(f"ستون ساختاری حیاتی '{col}' در خروجی Tesseract یافت نشد (ocr_utils).")
    return df


def extract_ocr_text_for_display(df_ocr):
    """استخراج و فرمت‌بندی متن OCR از DataFrame برای نمایش."""
    ocr_full_text = ""
    if df_ocr.empty or not (df_ocr['level'] == 5).any(): # اگر DataFrame خالی است یا هیچ کلمه‌ای ندارد
        return ""

    df_words = df_ocr[df_ocr['level'] == 5].copy()
    if df_words.empty:
        return ""

    # گروه‌بندی کلمات بر اساس ساختارشان برای بازسازی خطوط
    grouped_for_text = df_words.groupby(
        ['page_num', 'block_num', 'par_num', 'line_num'], sort=True # sort=True برای حفظ ترتیب
    )
    for _, group in grouped_for_text:
        # کلمات هر خط را با فاصله به هم بچسبان (با حفظ ترتیب اصلی کلمات)
        line_text = " ".join(group.sort_values(by='word_num')['text'].astype(str).tolist())
        ocr_full_text += line_text + "\n" # اضافه کردن خط جدید بعد از هر خط متنی
    return ocr_full_text.strip()


def manually_segment_lines(df_words, y_tolerance_factor=0.7):
    """کلمات را بر اساس نزدیکی عمودی به خطوط دستی تقسیم می‌کند."""
    if df_words.empty:
        return []

    # اطمینان از وجود و عددی بودن ستون‌های لازم
    required_cols_types = {'top': pd.api.types.is_numeric_dtype,
                           'left': pd.api.types.is_numeric_dtype,
                           'height': pd.api.types.is_numeric_dtype,
                           'word_num': pd.api.types.is_numeric_dtype}
    for col, type_check_func in required_cols_types.items():
        if col not in df_words.columns or not type_check_func(df_words[col]):
            print(f"هشدار: ستون '{col}' برای تقسیم‌بندی دستی خطوط در ocr_utils معتبر نیست.")
            return []

    # مرتب‌سازی کلمات برای پردازش ترتیبی
    df_words_sorted = df_words.sort_values(by=['top', 'left', 'word_num'], ascending=[True, True, True])

    all_lines = []
    current_line_words_indices = [] # لیست ایندکس‌های کلمات در خط فعلی

    if df_words_sorted.empty: return []

    for index, word_series in df_words_sorted.iterrows():
        word_top = int(word_series['top'])
        word_height = int(word_series['height'])
        if word_height <= 0: continue # از کلمات با ارتفاع صفر یا منفی صرف نظر کن
        word_center_y = word_top + (word_height / 2.0)

        if not current_line_words_indices:
            current_line_words_indices.append(index)
        else:
            last_word_index = current_line_words_indices[-1]
            last_word_series = df_words_sorted.loc[last_word_index]

            last_word_top = int(last_word_series['top'])
            last_word_height = int(last_word_series['height'])
            if last_word_height <=0: # نباید اتفاق بیفتد اگر کلمات با ارتفاع صفر فیلتر شده‌اند
                 all_lines.append([df_words_sorted.loc[i] for i in current_line_words_indices])
                 current_line_words_indices = [index]
                 continue

            last_word_center_y = last_word_top + (last_word_height / 2.0)

            y_threshold = max(word_height, last_word_height) * y_tolerance_factor

            if abs(word_center_y - last_word_center_y) < y_threshold:
                current_line_words_indices.append(index)
            else:
                all_lines.append([df_words_sorted.loc[i] for i in current_line_words_indices])
                current_line_words_indices = [index]

    if current_line_words_indices: # اضافه کردن آخرین خط
        all_lines.append([df_words_sorted.loc[i] for i in current_line_words_indices])

    return all_lines





