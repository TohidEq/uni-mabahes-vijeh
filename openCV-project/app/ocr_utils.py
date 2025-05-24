# ocr_utils.py
import pandas as pd
import pytesseract
import cv2 as cv # برای توابع OpenCV #
from PIL import Image as pl_image # برای جلوگیری از تداخل نام با Image از PIL #

def preprocess_image_for_ocr(img_cv_original, gaussian_kernel_size=5, adaptive_block_size=21, adaptive_c=4): #
    """یک تصویر OpenCV را برای بهبود OCR پیش‌پردازش می‌کند.""" #
    if img_cv_original is None:
        print("Hoshdar: Tasvir voroodi baraye pishpardazesh khali ast (dar ocr_utils).")
        return None

    processed_img = img_cv_original
    try:
        if len(processed_img.shape) == 3 and processed_img.shape[2] == 3:
            processed_img = cv.cvtColor(processed_img, cv.COLOR_BGR2GRAY)
        elif len(processed_img.shape) != 2:
            print("Hoshdar: Format tasvir baraye tabdil be khakestari namshakhas ast (dar ocr_utils).")
            return processed_img

        # اطمینان از فرد بودن اندازه کرنل
        if gaussian_kernel_size % 2 == 0:
            gaussian_kernel_size += 1

        # اطمینان از فرد بودن و بزرگتر از 1 بودن اندازه بلاک
        if adaptive_block_size <= 1:
            adaptive_block_size = 3
        elif adaptive_block_size % 2 == 0:
            adaptive_block_size +=1

        blurred = cv.GaussianBlur(processed_img, (gaussian_kernel_size, gaussian_kernel_size), 0) #
        thresh = cv.adaptiveThreshold(blurred, 255, #
                                     cv.ADAPTIVE_THRESH_GAUSSIAN_C, #
                                     cv.THRESH_BINARY_INV, #
                                     adaptive_block_size, adaptive_c) #
        return thresh
    except Exception as e:
        print(f"Khata dar pishpardazesh tasvir (ocr_utils): {e}")
        return img_cv_original


def get_structured_ocr_data(ocr_input_image_cv, lang='eng', psm_config='--psm 6'): #
    """اجرای OCR روی تصویر OpenCV ورودی و برگرداندن DataFrame تمیز شده.""" #
    if ocr_input_image_cv is None:
        return pd.DataFrame()

    try:
        if len(ocr_input_image_cv.shape) == 2:
            img_pil_for_tesseract = pl_image.fromarray(ocr_input_image_cv) #
        elif len(ocr_input_image_cv.shape) == 3 and ocr_input_image_cv.shape[2] == 3:
            img_pil_for_tesseract = pl_image.fromarray(cv.cvtColor(ocr_input_image_cv, cv.COLOR_BGR2RGB)) #
        else:
            raise ValueError(f"Format kanal tasvir voroodi be OCR namshakhas ast: {ocr_input_image_cv.shape}")

        df = pytesseract.image_to_data(img_pil_for_tesseract, lang=lang, #
                                       output_type=pytesseract.Output.DATAFRAME, #
                                       config=psm_config) #
    except pytesseract.TesseractError as tess_err: #
        print(f"Khataye ejrayi Tesseract dar get_structured_ocr_data: {tess_err}") #
        raise
    except Exception as e: #
        print(f"Khataye nashnakhte hengam ejraye image_to_data dar ocr_utils: {e}") #
        raise

    if df is None or df.empty:
        return pd.DataFrame()

    df.dropna(subset=['text'], inplace=True) #
    df = df[df['text'].astype(str).str.strip() != ''] #
    if df.empty: return pd.DataFrame() #

    df['conf'] = pd.to_numeric(df['conf'], errors='coerce').fillna(-1).astype(int) #

    structural_cols = ['level','page_num','block_num','par_num','line_num','word_num','left','top','width','height'] #
    for col in structural_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int) #
        else:
            raise ValueError(f"Sotoon sakhtari hayati '{col}' dar khorooji Tesseract yaft nashod (ocr_utils).") #
    return df


def extract_ocr_text_for_display(df_ocr): #
    """استخراج و فرمت‌بندی متن OCR از DataFrame برای نمایش.""" #
    ocr_full_text = ""
    if df_ocr.empty or not (df_ocr['level'] == 5).any(): #
        return ""

    df_words = df_ocr[df_ocr['level'] == 5].copy() #
    if df_words.empty:
        return ""

    grouped_for_text = df_words.groupby( #
        ['page_num', 'block_num', 'par_num', 'line_num'], sort=True #
    )
    for _, group in grouped_for_text:
        line_text = " ".join(group.sort_values(by='word_num')['text'].astype(str).tolist()) #
        ocr_full_text += line_text + "\n" #
    return ocr_full_text.strip()


def manually_segment_lines(df_words, y_tolerance_factor=0.7): #
    """کلمات را بر اساس نزدیکی عمودی به خطوط دستی تقسیم می‌کند.""" #
    if df_words.empty:
        return []

    required_cols_types = {'top': pd.api.types.is_numeric_dtype, #
                           'left': pd.api.types.is_numeric_dtype, #
                           'height': pd.api.types.is_numeric_dtype, #
                           'word_num': pd.api.types.is_numeric_dtype} #
    for col, type_check_func in required_cols_types.items():
        if col not in df_words.columns or not type_check_func(df_words[col]): #
            print(f"Hoshdar: Sotoon '{col}' baraye taghsimbandi dasti khatoot dar ocr_utils mo'tabar nist.") #
            return []

    df_words_sorted = df_words.sort_values(by=['top', 'left', 'word_num'], ascending=[True, True, True]) #

    all_lines = []
    current_line_words_indices = [] #

    if df_words_sorted.empty: return [] #

    for index, word_series in df_words_sorted.iterrows():
        word_top = int(word_series['top']) #
        word_height = int(word_series['height']) #
        if word_height <= 0: continue #
        word_center_y = word_top + (word_height / 2.0) #

        if not current_line_words_indices:
            current_line_words_indices.append(index) #
        else:
            last_word_index = current_line_words_indices[-1] #
            last_word_series = df_words_sorted.loc[last_word_index] #

            last_word_top = int(last_word_series['top']) #
            last_word_height = int(last_word_series['height']) #
            if last_word_height <=0: #
                 all_lines.append([df_words_sorted.loc[i] for i in current_line_words_indices]) #
                 current_line_words_indices = [index] #
                 continue

            last_word_center_y = last_word_top + (last_word_height / 2.0) #

            y_threshold = max(word_height, last_word_height) * y_tolerance_factor #

            if abs(word_center_y - last_word_center_y) < y_threshold:
                current_line_words_indices.append(index) #
            else:
                all_lines.append([df_words_sorted.loc[i] for i in current_line_words_indices]) #
                current_line_words_indices = [index] #

    if current_line_words_indices: #
        all_lines.append([df_words_sorted.loc[i] for i in current_line_words_indices]) #

    return all_lines