# main_app.py
import numpy as np
import pandas as pd
import PIL as pl
from PIL import ImageFont, ImageDraw, Image, ImageTk
import cv2 as cv
import pytesseract # برای استفاده از pytesseract.Output

import threading
from tkinter import Tk, Label, Button, filedialog, PhotoImage, StringVar, OptionMenu, Entry, Checkbutton, scrolledtext
from tkinter import ttk
from tkinter import messagebox
from io import StringIO
import csv
import traceback # برای چاپ کامل خطاها

# Import translation function and configuration from separate files
from translation_api import translate_en_to_fa_api
from config import FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE, LANGUAGE_OPTIONS, MIN_FONT_SIZE, MAX_FONT_SIZE

import warnings
warnings.filterwarnings("ignore")


# --- بررسی اولیه و سراسری فونت هنگام شروع برنامه ---
# global_font_instance_check: یک متغیر سراسری برای نگهداری نتیجه اولین تلاش برای بارگذاری فونت.
global_font_instance_check = None # مقدار اولیه
try:
    if FONT_PATH and FONT_PATH.strip() != "": # بررسی اینکه مسیر فونت خالی نباشد
        # تلاش برای بارگذاری فونت با اندازه پیش‌فرض جهانی
        global_font_instance_check = ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
        # print(f"DEBUG: Initial font check successful. Font object: {global_font_instance_check}")
    else:
        print("هشدار جدی: مسیر فونت (FONT_PATH) در config.py تعریف نشده یا خالی است. متن روی تصویر نمایش داده نخواهد شد.")
except IOError:
    print(f"خطای IO هنگام بررسی اولیه فونت از مسیر '{FONT_PATH}'. لطفاً مسیر و دسترسی فایل را بررسی کنید.")
except Exception as e:
    print(f"خطای ناشناخته هنگام بررسی اولیه فونت از مسیر '{FONT_PATH}': {e}")
# --- پایان بررسی اولیه فونت ---





class OCRTranslatorApp:
    def __init__(self, master):
        self.master = master
        master.title("OCR Text Translator")
        master.geometry("1200x800")

        self.current_image_path = None
        self.translated_image_tk = None

        self.selected_language_name = StringVar(master)
        default_lang_key = "Engilisi (English)"
        for key, code in LANGUAGE_OPTIONS.items():
            if code == "fa": # زبان پیش‌فرض فارسی
                default_lang_key = key
                break
        self.selected_language_name.set(default_lang_key)
        self.language_options = LANGUAGE_OPTIONS

        self.translate_checkbox_var = StringVar(master, value="1")
        self.font_size_var = StringVar(master, value=str(GLOBAL_FONT_DEFAULT_SIZE))

        # متغیر و گزینه‌ها برای انتخاب سطح کادکشی
        self.selected_draw_level_name = StringVar(master)
        self.draw_level_options = {
            "Kadr Nakeshid (None)": 0,
            "Kalame (Word)": 5,
            "Khat/Jomle (Line)": 4, # این گزینه از تقسیم‌بندی دستی خطوط استفاده خواهد کرد
            "Paragraph (Tesseract)": 3, # غیر فعال
            "Block Matn (Tesseract)": 2 # غیر فعال
        }
        self.selected_draw_level_name.set("Khat/Jomle (Line)")

        # --- متغیرهای جدید برای ذخیره وضعیت و داده‌های پردازش قبلی ---
        self.last_img_cv_original = None
        self.last_df_ocr_processed = None # DataFrame کامل OCR شده
        self.last_render_segments = []    # لیستی از دیکشنری‌ها برای کشیدن کادر و متن
                                          # هر دیکشنری: {'rect': (x,y,w,h), 'text': "متن نمایشی", 'draw_text': True/False, 'color': (r,g,b)}
        self.last_ocr_display_text = ""   # متن برای جعبه OCR
        self.last_translated_output_for_widget = "" # متن برای جعبه ترجمه شده

        # ذخیره تنظیمات قبلی برای تشخیص نوع تغییر
        self.prev_font_size = self.font_size_var.get()
        self.prev_language_name = self.selected_language_name.get()
        self.prev_translate_enabled = self.translate_checkbox_var.get()
        self.prev_draw_level = self.selected_draw_level_name.get()


        # --- Control Frame ---
        self.control_frame = ttk.Frame(master, padding="10")
        self.control_frame.pack(side="top", fill="x")

        self.select_button = Button(self.control_frame, text="Entekhab Tasvir", command=self.select_image)
        self.select_button.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame, text="Zaban Tarjomeh:").pack(side="left", padx=(10, 2), pady=5)
        self.language_menu = OptionMenu(self.control_frame, self.selected_language_name, *self.language_options.keys())
        self.language_menu.pack(side="left", padx=5, pady=5)
        self.selected_language_name.trace_add("write", self.on_setting_change)

        self.translate_checkbox = Checkbutton(self.control_frame, text="Tarjome Kon", variable=self.translate_checkbox_var, onvalue="1", offvalue="0", command=self.on_setting_change)
        self.translate_checkbox.pack(side="left", padx=10, pady=5)

        ttk.Label(self.control_frame, text="Kadr Dore:").pack(side="left", padx=(10,2), pady=5)
        self.draw_level_menu = OptionMenu(self.control_frame, self.selected_draw_level_name, *self.draw_level_options.keys())
        self.draw_level_menu.pack(side="left", padx=5, pady=5)
        self.selected_draw_level_name.trace_add("write", self.on_setting_change)

        ttk.Label(self.control_frame, text=f"Font Size ({MIN_FONT_SIZE}-{MAX_FONT_SIZE}):").pack(side="left", padx=(10, 2), pady=5)
        self.font_size_entry = Entry(self.control_frame, textvariable=self.font_size_var, width=5)
        self.font_size_entry.pack(side="left", padx=5, pady=5)
        self.font_size_entry.bind("<Return>", self.on_setting_change)
        self.font_size_entry.bind("<FocusOut>", self.on_setting_change)

        self.exit_button = Button(self.control_frame, text="Khorooj", command=master.quit)
        self.exit_button.pack(side="right", padx=5, pady=5)

        # --- Main Content Frame ---
        self.main_content_frame = ttk.Frame(master, padding="10")
        self.main_content_frame.pack(side="top", fill="both", expand=True)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(1, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

        self.image_container = ttk.Frame(self.main_content_frame)
        self.image_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.image_label = Label(self.image_container, bd=2, relief="groove")
        self.image_label.pack(fill="both", expand=True)

        self.text_boxes_frame = ttk.Frame(self.main_content_frame, padding="5")
        self.text_boxes_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.text_boxes_frame.grid_rowconfigure(0, weight=1)
        self.text_boxes_frame.grid_rowconfigure(1, weight=1)
        self.text_boxes_frame.grid_columnconfigure(0, weight=1)

        self.ocr_text_frame = ttk.LabelFrame(self.text_boxes_frame, text="Matn Shenasayi Shode", padding="5")
        self.ocr_text_frame.grid(row=0, column=0, sticky="nsew", pady=(0,2))
        self.ocr_text_widget = scrolledtext.ScrolledText(self.ocr_text_frame, wrap='word', height=10, width=30, font=("tahoma", 9))
        self.ocr_text_widget.pack(fill="both", expand=True)

        self.translated_text_frame = ttk.LabelFrame(self.text_boxes_frame, text="Matn Tarjome Shode", padding="5")
        self.translated_text_frame.grid(row=1, column=0, sticky="nsew", pady=(2,0))
        self.translated_text_widget = scrolledtext.ScrolledText(self.translated_text_frame, wrap='word', height=10, width=30, font=("tahoma", 9))
        self.translated_text_widget.pack(fill="both", expand=True)

        # --- Status Bar ---
        self.status_frame = ttk.Frame(master, padding="5")
        self.status_frame.pack(side="bottom", fill="x")
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=200, mode="indeterminate")
        self.status_label = Label(self.status_frame, text="Amadeh", fg="white", bg="gray25")
        self.status_label.pack(side="left", padx=10)

    def on_setting_change(self, *args):
        if not self.current_image_path:
            self.status_label.config(text="Amadeh")
            return

        current_font_size = self.font_size_var.get()
        current_language_name = self.selected_language_name.get()
        current_translate_enabled = self.translate_checkbox_var.get()
        current_draw_level = self.selected_draw_level_name.get()

        font_changed_only = (
            current_font_size != self.prev_font_size and
            current_language_name == self.prev_language_name and
            current_translate_enabled == self.prev_translate_enabled and
            current_draw_level == self.prev_draw_level
        )

        # اگر فقط فونت تغییر کرده و داده‌های پردازش قبلی برای تصویر موجود است
        if font_changed_only and self.last_img_cv_original is not None and self.last_df_ocr_processed is not None:
            self.status_label.config(text="در حال اعمال فونت جدید روی تصویر...")
            # self.prev_font_size = current_font_size # به‌روزرسانی بلافاصله قبل از ترد
                                                  # یا در انتهای _rerender_image_annotations

            # نمایش progress_bar برای عملیات بازترسیمی هم خوب است
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()

            threading.Thread(target=self._rerender_image_annotations,
                             args=(current_font_size,), # ارسال اندازه فونت جدید
                             daemon=True).start()
        else: # اگر تنظیمات دیگری تغییر کرده یا اولین پردازش است
            self.status_label.config(text="در حال پردازش مجدد با تنظیمات جدید...")

            # ذخیره تمام تنظیمات فعلی به عنوان تنظیمات قبلی برای مقایسه بعدی
            # این کار باید قبل از شروع ترد process_image انجام شود تا در صورت تغییر سریع کاربر،
            # مقادیر درست برای مقایسه بعدی ذخیره شوند.
            # self.prev_font_size = current_font_size
            # self.prev_language_name = current_language_name
            # self.prev_translate_enabled = current_translate_enabled
            # self.prev_draw_level = current_draw_level
            # بهتر است اینها در انتهای process_image یا _rerender به‌روز شوند.

            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()

            # اجرای پردازش کامل
            threading.Thread(target=self.process_image, args=(self.current_image_path,), daemon=True).start()

    def select_image(self):
        file_path = filedialog.askopenfilename(title="Entekhab Tasvir", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.current_image_path = file_path
            self.status_label.config(text="Dar hale pardazesh ...")
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self.process_image, args=(file_path,), daemon=True).start()

    # --- Helper Functions ---
    def _load_current_font(self):
        """ فونت را با اندازه انتخاب شده توسط کاربر بارگذاری می‌کند. """
        try:
            font_size_str = self.font_size_var.get()
            if not font_size_str.isdigit(): # اگر ورودی عدد نیست
                raise ValueError("اندازه فونت باید عدد باشد.")
            font_size = int(font_size_str)

            if not (MIN_FONT_SIZE <= font_size <= MAX_FONT_SIZE):
                # اگر کاربر اندازه نامعتبر وارد کرد، به اندازه پیش‌فرض برمی‌گردیم
                # self.master.after(0, lambda: messagebox.showwarning("اندازه فونت نامعتبر", f"اندازه فونت باید بین {MIN_FONT_SIZE} و {MAX_FONT_SIZE} باشد. از اندازه پیش‌فرض استفاده شد."))
                font_size = GLOBAL_FONT_DEFAULT_SIZE
                self.font_size_var.set(str(GLOBAL_FONT_DEFAULT_SIZE))

            # global_font_instance_check فقط برای این بود که بدانیم FONT_PATH از ابتدا معتبر بوده یا نه
            if FONT_PATH and global_font_instance_check:
                return ImageFont.truetype(FONT_PATH, font_size)
            else:
                if not FONT_PATH or not FONT_PATH.strip():
                    print("هشدار: FONT_PATH در config.py تعریف نشده است.")
                elif not global_font_instance_check:
                     print(f"هشدار: فونت اولیه از مسیر '{FONT_PATH}' بارگذاری نشده. متن روی تصویر نمایش داده نمی‌شود.")
                return None
        except ValueError as ve: # اگر کاربر چیزی غیر از عدد برای اندازه فونت وارد کرد
            # print(f"خطای مقدار برای اندازه فونت: {ve}")
            self.font_size_var.set(str(GLOBAL_FONT_DEFAULT_SIZE)) # برگرداندن به پیش‌فرض
            if FONT_PATH and global_font_instance_check: # تلاش مجدد با پیش‌فرض
                try:
                    return ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
                except Exception as e_inner:
                    print(f"خطا در بارگذاری فونت پیش‌فرض پس از ورودی نامعتبر: {e_inner}")
            return None
        except Exception as e:
            print(f"خطای ناشناخته در بارگذاری فونت با اندازه دلخواه: {e}")
            return None

    def _load_images_from_path(self, img_path):
        try:
            img_pil = pl.Image.open(img_path)
            # تبدیل به RGB اگر RGBA یا P باشد (برای سازگاری با OpenCV)
            if img_pil.mode == 'RGBA' or img_pil.mode == 'P':
                img_pil = img_pil.convert('RGB')
            img_cv = cv.imread(img_path)
            if img_cv is None:
                raise ValueError("OpenCV نتوانست تصویر را بارگذاری کند.")
            return img_pil, img_cv
        except FileNotFoundError:
            raise ValueError(f"فایل تصویر '{img_path}' یافت نشد.")
        except Exception as e:
            raise ValueError(f"خطا در بارگذاری تصویر '{img_path}': {e}")

    def _preprocess_image_for_ocr(self, img_cv):
        if img_cv is None: return None
        try:
            if len(img_cv.shape) == 3: gray = cv.cvtColor(img_cv, cv.COLOR_BGR2GRAY)
            else: gray = img_cv

            blurred = cv.GaussianBlur(gray, (5, 5), 0)
            # استفاده از THRESH_BINARY_INV ممکن است برای برخی تصاویر بهتر باشد (متن سفید، پس‌زمینه سیاه)
            # یا THRESH_BINARY (متن سیاه، پس‌زمینه سفید)
            thresh = cv.adaptiveThreshold(blurred, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv.THRESH_BINARY_INV, 21, 4)
            return thresh
        except Exception as e:
            print(f"خطا در پیش‌پردازش تصویر: {e}")
            return img_cv # در صورت خطا، تصویر اصلی (یا خاکستری شده) را برگردان

    def _get_structured_ocr_data(self, ocr_input_image_cv, psm_config='--psm 6'):
        if ocr_input_image_cv is None: return pd.DataFrame()
        try:
            if len(ocr_input_image_cv.shape) == 2: # خاکستری یا دودویی
                img_pil_for_tesseract = pl.Image.fromarray(ocr_input_image_cv)
            elif len(ocr_input_image_cv.shape) == 3: # رنگی (که نباید پس از پیش‌پردازش باشد)
                img_pil_for_tesseract = pl.Image.fromarray(cv.cvtColor(ocr_input_image_cv, cv.COLOR_BGR2RGB))
            else: raise ValueError("فرمت کانال تصویر ورودی به OCR نامشخص است.")

            df = pytesseract.image_to_data(img_pil_for_tesseract, lang='eng',
                                           output_type=pytesseract.Output.DATAFRAME,
                                           config=psm_config)
        except pytesseract.TesseractError as tess_err:
            print(f"خطای اجرایی Tesseract در _get_structured_ocr_data: {tess_err}")
            raise
        except Exception as e:
            print(f"خطای ناشناخته هنگام اجرای image_to_data: {e}")
            raise

        if df is None or df.empty: return pd.DataFrame()
        df.dropna(subset=['text'], inplace=True)
        df = df[df['text'].astype(str).str.strip() != '']
        if df.empty: return pd.DataFrame()

        df['conf'] = pd.to_numeric(df['conf'], errors='coerce').fillna(-1).astype(int)
        structural_cols = ['level','page_num','block_num','par_num','line_num','word_num','left','top','width','height']
        for col in structural_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            else: raise ValueError(f"ستون حیاتی '{col}' در خروجی Tesseract نیست.")
        return df

    def _extract_ocr_text_for_display(self, df_ocr):
        ocr_full_text = ""
        if df_ocr.empty or not (df_ocr['level'] == 5).any(): return ""
        df_words = df_ocr[df_ocr['level'] == 5].copy()
        if df_words.empty: return ""
        grouped_for_text = df_words.groupby(['page_num','block_num','par_num','line_num'], sort=True)
        for _, group in grouped_for_text:
            line_text = " ".join(group.sort_values(by='word_num')['text'].astype(str).tolist())
            ocr_full_text += line_text + "\n"
        return ocr_full_text.strip()

    def _manually_segment_lines(self, df_words, y_tolerance_factor=0.7):
        if df_words.empty: return []
        # اطمینان از وجود و عددی بودن ستون‌های لازم
        required_cols = {'top':0, 'left':0, 'height':0, 'word_num':0, 'text':""}
        for col, default_val in required_cols.items():
            if col not in df_words.columns:
                print(f"هشدار جدی: ستون '{col}' برای تقسیم‌بندی دستی خطوط موجود نیست.")
                return [] # یا یک خطا ایجاد کن
            if not pd.api.types.is_numeric_dtype(df_words[col]) and col != 'text':
                df_words[col] = pd.to_numeric(df_words[col], errors='coerce').fillna(default_val)
                # print(f"هشدار: ستون '{col}' عددی نبود و تبدیل شد.")

        df_words = df_words.sort_values(by=['top', 'left', 'word_num'], ascending=[True, True, True])
        all_lines, current_line_words = [], []
        if df_words.empty: return []

        for _, word_series in df_words.iterrows():
            word_top, word_height = int(word_series['top']), int(word_series['height'])
            word_center_y = word_top + (word_height / 2)
            if not current_line_words:
                current_line_words.append(word_series)
            else:
                last_word_in_line = current_line_words[-1]
                last_word_top, last_word_height = int(last_word_in_line['top']), int(last_word_in_line['height'])
                last_word_center_y = last_word_top + (last_word_height / 2)
                y_threshold = max(word_height, last_word_height) * y_tolerance_factor
                if abs(word_center_y - last_word_center_y) < y_threshold:
                    current_line_words.append(word_series)
                else:
                    all_lines.append(current_line_words)
                    current_line_words = [word_series]
        if current_line_words: all_lines.append(current_line_words)
        return all_lines

    def _resize_image_for_tk(self, pil_img, target_widget):
        try:
            container_width, container_height = target_widget.winfo_width(), target_widget.winfo_height()
            if container_width < 50 or container_height < 50:
                master_width = target_widget.winfo_toplevel().winfo_width()
                master_height = target_widget.winfo_toplevel().winfo_height()
                # تخمین بر اساس اینکه کانتینر عکس در یک ستون گرید با وزن ۱ (از ۲ ستون) قرار دارد
                container_width = int(master_width * 0.48)
                container_height = int(master_height * 0.85) # ارتفاع بیشتری می‌گیرد
                if container_width < 50: container_width = 300
                if container_height < 50: container_height = 300

            img_copy = pil_img.copy()
            if img_copy.width > container_width or img_copy.height > container_height:
                img_copy.thumbnail((container_width, container_height), pl.Image.Resampling.LANCZOS)
            return img_copy
        except Exception as e:
            print(f"خطا در تغییر اندازه تصویر: {e}")
            return pil_img

    def _rerender_image_annotations(self, new_font_size_str): # یا مستقیم شیء فونت را بگیرد
        """فقط کادرها و متون را با استفاده از داده‌های قبلی و فونت جدید روی تصویر بازترسیمی می‌کند."""
        try:
            self.status_label.config(text="اعمال فونت جدید...")

            # ۱. بارگذاری فونت جدید
            # تابع _load_current_font از self.font_size_var.get() استفاده می‌کند.
            # باید مطمئن شویم self.font_size_var با new_font_size_str به‌روز شده یا مستقیم از آن استفاده کنیم.
            # چون on_setting_change قبل از این ترد اجرا شده، self.font_size_var.get() باید مقدار جدید را بدهد.
            new_font = self._load_current_font()
            if new_font is None and global_font_instance_check: # اگر فونت جدید لود نشد اما قبلا فونت داشتیم
                print("هشدار: فونت جدید بارگذاری نشد، از فونت پیش‌فرض اولیه استفاده می‌شود (اگر موجود باشد).")
                new_font = global_font_instance_check # بازگشت به فونت اولیه بررسی شده

            if self.last_img_cv_original is None or not self.last_render_segments:
                print("DEBUG: داده‌های قبلی برای بازترسیمی موجود نیست.")
                self.master.after(0, self.stop_loading_and_update_status)
                return

            image_to_annotate_cv = self.last_img_cv_original.copy()

            # ۲. بازترسیمی کادرها و متون از self.last_render_segments
            for segment in self.last_render_segments:
                rect = segment.get('rect')
                text_on_image = segment.get('text_on_image', "")
                should_draw_text = segment.get('draw_text', False)
                box_color = segment.get('color', (255,0,0)) # قرمز پیش‌فرض

                if rect:
                    x, y, w, h = rect
                    cv.rectangle(image_to_annotate_cv, (x, y), (x + w, y + h), box_color, 2)

                if should_draw_text and text_on_image.strip() and new_font:
                    # استفاده از تابع کمکی _draw_text_on_cv_image برای نوشتن متن
                    image_to_annotate_cv = self._draw_text_on_cv_image(
                        image_to_annotate_cv, text_on_image,
                        x, y, # مختصات بالای کادر به عنوان مبنا
                        new_font
                    )

            # ۳. تبدیل و نمایش تصویر
            final_image_pil = pl.Image.fromarray(cv.cvtColor(image_to_annotate_cv, cv.COLOR_BGR2RGB))
            resized_pil_image = self._resize_image_for_tk(final_image_pil, self.image_container)
            self.master.after(0, self.update_image_display, resized_pil_image)

            # ۴. به‌روزرسانی مقدار قبلی فونت (چون فقط فونت تغییر کرده)
            self.prev_font_size = new_font_size_str # یا self.font_size_var.get()

        except Exception as e:
            print(f"خطا در بازترسیمی با فونت جدید: {e}")
            traceback.print_exc()
            self.master.after(0, lambda: messagebox.showerror("خطا", "خطا در اعمال فونت جدید."))
        finally:
            self.master.after(0, self.stop_loading_and_update_status)

    # Main Image Processing Logic
    def process_image(self, img_path):
        # --- بخش ذخیره‌سازی در انتهای process_image ---
        # این بخش باید در انتهای بلوک try (قبل از finally) و پس از تمام پردازش‌ها و نمایش‌ها قرار گیرد
        # تا فقط در صورت موفقیت کامل، داده‌ها و تنظیمات قبلی به‌روز شوند.

        # متغیر list_of_segments_for_rendering برای جمع‌آوری اطلاعات ترسیمی
        list_of_segments_for_rendering = []

        try:
            current_font_for_drawing = self._load_current_font()
            # ... (بارگذاری تصویر، پیش‌پردازش، OCR -> df_ocr_processed ... دقیقا مثل قبل) ...
            img_pil_original, img_cv_original = self._load_images_from_path(img_path)
            # ... ( بقیه کد تا قبل از حلقه اصلی کادکشی و ترجمه، مشابه قبل است ) ...
            img_cv_for_preprocessing = img_cv_original.copy()
            preprocessed_cv_image = self._preprocess_image_for_ocr(img_cv_for_preprocessing)
            psm_to_use = '--psm 6'
            ocr_input_for_df = preprocessed_cv_image if preprocessed_cv_image is not None else img_cv_original
            df_ocr_processed = self._get_structured_ocr_data(ocr_input_for_df, psm_config=psm_to_use)
            ocr_display_text = self._extract_ocr_text_for_display(df_ocr_processed)
            self.master.after(0, self.update_ocr_text_widget, ocr_display_text)

            translated_output_for_widget = ""
            should_translate = self.translate_checkbox_var.get() == "1"
            current_target_lang_code = self.language_options[self.selected_language_name.get()]
            selected_level_name = self.selected_draw_level_name.get()
            level_to_draw = self.draw_level_options.get(selected_level_name, 0)
            image_with_annotations_cv = img_cv_original.copy()


            # --- منطق اصلی برای کادکشی، ترجمه، و آماده‌سازی self.last_render_segments ---
            if level_to_draw == 4: # حالت "Khat/Jomle (Line)"
                df_words_for_segmentation = df_ocr_processed[df_ocr_processed['level'] == 5].copy()
                if not df_words_for_segmentation.empty:
                    manually_segmented_lines = self._manually_segment_lines(df_words_for_segmentation)
                    temp_translated_list_for_textbox = []
                    for line_of_word_series in manually_segmented_lines:
                        if not line_of_word_series: continue
                        min_x = min(int(s['left']) for s in line_of_word_series)
                        min_y = min(int(s['top']) for s in line_of_word_series)
                        max_x_coord = max(int(s['left']) + int(s['width']) for s in line_of_word_series)
                        max_y_coord = max(int(s['top']) + int(s['height']) for s in line_of_word_series)

                        if max_x_coord <= min_x or max_y_coord <= min_y: continue

                        current_rect = (min_x, min_y, max_x_coord - min_x, max_y_coord - min_y) # (x,y,w,h)
                        current_box_color = (34,139,34) # ForestGreen for lines
                        cv.rectangle(image_with_annotations_cv, (min_x, min_y), (max_x_coord, max_y_coord), current_box_color, 2)

                        line_text_original = " ".join(str(s['text']).strip() for s in line_of_word_series if str(s['text']).strip())
                        text_to_show_on_image = line_text_original
                        current_segment_for_textbox = line_text_original

                        if line_text_original.strip():
                            if should_translate and current_target_lang_code != 'en':
                                translated_line = translate_en_to_fa_api(line_text_original, target_lang=current_target_lang_code)
                                text_to_show_on_image = translated_line
                                current_segment_for_textbox = translated_line

                            if current_font_for_drawing and text_to_show_on_image.strip():
                                image_with_annotations_cv = self._draw_text_on_cv_image(
                                    image_with_annotations_cv, text_to_show_on_image,
                                    min_x, min_y, current_font_for_drawing
                                )

                        list_of_segments_for_rendering.append({
                            'rect': current_rect, 'text_on_image': text_to_show_on_image,
                            'draw_text': True, 'color': current_box_color
                        })
                        temp_translated_list_for_textbox.append(current_segment_for_textbox)
                    translated_output_for_widget = "\n".join(temp_translated_list_for_textbox)
                # Fallback translation
                elif should_translate and current_target_lang_code != 'en':
                    if ocr_display_text.strip(): translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    else: translated_output_for_widget = "[متنی برای ترجمه یافت نشد]"
                else: translated_output_for_widget = ocr_display_text

            elif level_to_draw == 5: # حالت "Kalame (Word)"
                words_to_process = df_ocr_processed[(df_ocr_processed['level'] == 5) & (df_ocr_processed['conf'] > 10)].copy()
                temp_textbox_lines_dict = {}
                current_box_color = (0,0,255) # Blue for words

                for _, word_row in words_to_process.iterrows():
                    original_word = str(word_row['text']).strip()
                    if not original_word or not (int(word_row['width']) > 0 and int(word_row['height']) > 0):
                        continue

                    x,y,w,h = int(word_row['left']),int(word_row['top']),int(word_row['width']),int(word_row['height'])
                    current_rect = (x,y,w,h)
                    cv.rectangle(image_with_annotations_cv, (x, y), (x + w, y + h), current_box_color, 1)

                    text_to_show_on_image = original_word
                    current_word_for_textbox = original_word

                    if should_translate and current_target_lang_code != 'en':
                        translated_word = translate_en_to_fa_api(original_word, target_lang=current_target_lang_code)
                        text_to_show_on_image = translated_word if translated_word and translated_word.strip() else original_word
                        current_word_for_textbox = translated_word if translated_word and translated_word.strip() else original_word

                    if current_font_for_drawing and text_to_show_on_image.strip():
                        image_with_annotations_cv = self._draw_text_on_cv_image(
                            image_with_annotations_cv, text_to_show_on_image,
                            x, y, current_font_for_drawing, padding_above_box=1
                        )

                    list_of_segments_for_rendering.append({
                        'rect': current_rect, 'text_on_image': text_to_show_on_image,
                        'draw_text': True, 'color': current_box_color
                    })

                    line_key = (word_row['page_num'], word_row['block_num'], word_row['par_num'], word_row['line_num'])
                    if line_key not in temp_textbox_lines_dict: temp_textbox_lines_dict[line_key] = []
                    temp_textbox_lines_dict[line_key].append({'word_num': int(word_row['word_num']), 'text': current_word_for_textbox})

                sorted_line_keys = sorted(temp_textbox_lines_dict.keys())
                final_textbox_lines = [" ".join(item['text'] for item in sorted(temp_textbox_lines_dict[key], key=lambda i: i['word_num'])) for key in sorted_line_keys]
                translated_output_for_widget = "\n".join(final_textbox_lines)

            else: # برای سایر سطوح (پاراگراف، بلوک) یا عدم کادکشی
                if level_to_draw > 0 and not df_ocr_processed.empty:
                    elements_to_draw = df_ocr_processed[df_ocr_processed['level'] == level_to_draw]
                    color_map = {3: (255,165,0), 2: (128,0,128)} # رنگ برای پاراگراف و بلوک
                    current_box_color = color_map.get(level_to_draw, (200,200,200))
                    for _, ocr_element in elements_to_draw.iterrows():
                        if int(ocr_element['width']) > 0 and int(ocr_element['height']) > 0 :
                            x,y,w,h = int(ocr_element['left']),int(ocr_element['top']),int(ocr_element['width']),int(ocr_element['height'])
                            current_rect = (x,y,w,h)
                            cv.rectangle(image_with_annotations_cv, (x, y), (x + w, y + h), current_box_color, 2)
                            list_of_segments_for_rendering.append({
                                'rect': current_rect, 'text_on_image': "", # متنی روی تصویر برای این سطوح نمی‌نویسیم
                                'draw_text': False, 'color': current_box_color
                            })

                if should_translate and current_target_lang_code != 'en':
                    if ocr_display_text.strip(): translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    else: translated_output_for_widget = "[متنی برای ترجمه وجود ندارد]"
                else: translated_output_for_widget = ocr_display_text

            self.master.after(0, self.update_translated_text_widget, translated_output_for_widget.strip())

            final_image_to_show_pil = pl.Image.fromarray(cv.cvtColor(image_with_annotations_cv, cv.COLOR_BGR2RGB))
            resized_pil_image = self._resize_image_for_tk(final_image_to_show_pil, self.image_container)
            self.master.after(0, self.update_image_display, resized_pil_image)

            # --- ذخیره نتایج و تنظیمات فعلی برای استفاده در بازترسیمی ---
            self.last_img_cv_original = img_cv_original.copy() # ذخیره کپی از تصویر اصلی
            self.last_df_ocr_processed = df_ocr_processed.copy() if df_ocr_processed is not None else None
            self.last_render_segments = list_of_segments_for_rendering # این شامل اطلاعات کادر و متن روی تصویر است
            self.last_ocr_display_text = ocr_display_text
            self.last_translated_output_for_widget = translated_output_for_widget

            # به‌روزرسانی تنظیمات قبلی پس از پردازش موفق
            self.prev_font_size = self.font_size_var.get()
            self.prev_language_name = self.selected_language_name.get()
            self.prev_translate_enabled = self.translate_checkbox_var.get()
            self.prev_draw_level = self.selected_draw_level_name.get()
            # --- پایان ذخیره‌سازی ---

        except ValueError as ve:
            print(f"ValueError در process_image: {ve}") # ادامه خطاها مثل قبل
            self.master.after(0, lambda: messagebox.showerror("خطای ورودی/مقدار", f"{ve}"))
        except pytesseract.TesseractError as tess_err:
            print(f"TesseractError در process_image: {tess_err}")
            self.master.after(0, lambda: messagebox.showerror("خطای Tesseract", f"{tess_err}"))
        except Exception as e:
            print(f"خطای عمومی در process_image: {e}")
            traceback.print_exc()
            self.master.after(0, lambda: messagebox.showerror("خطای کلی در پردازش", f"یک خطای پیش‌بینی نشده رخ داد: {e}"))
        finally:
            self.master.after(0, self.stop_loading_and_update_status)

    def _draw_text_on_cv_image(self, cv_image_input, text_to_write,
                               base_x, base_y_of_box_top,
                               font_object,
                               text_color=(250,250,250), outline_color=(0,0,0),
                               padding_above_box=3):
        """
        متن را با فونت و حاشیه مشخص شده روی تصویر OpenCV (ورودی) می‌نویسد.
        base_y_of_box_top: مختصات Y بالای کادری است که متن باید بالای آن نوشته شود.
        خروجی: تصویر OpenCV با متن نوشته شده روی آن.
        """
        if not text_to_write or font_object is None:
            return cv_image_input # اگر متنی برای نوشتن نیست یا فونت موجود نیست، تصویر اصلی را برگردان

        try:
            # تبدیل تصویر OpenCV به PIL برای نوشتن متن
            pil_img_for_text_draw = pl.Image.fromarray(cv.cvtColor(cv_image_input, cv.COLOR_BGR2RGB))
            draw_on_pil = pl.ImageDraw.Draw(pil_img_for_text_draw)

            # محاسبه اندازه متن و موقعیت دقیق
            try: # textbbox برای Pillow مدرن
                text_bbox = draw_on_pil.textbbox((0,0), text_to_write, font=font_object)
                text_height = text_bbox[3] - text_bbox[0] # ارتفاع واقعی متن ارائه شده توسط فونت
            except AttributeError: # Fallback برای Pillow قدیمی‌تر
                text_size = draw_on_pil.textsize(text_to_write, font=font_object)
                text_height = text_size[1]

            text_x_position = base_x
            text_y_position = base_y_of_box_top - text_height - padding_above_box

            # اگر متن از بالای تصویر بیرون زد، آن را کمی پایین‌تر (داخل یا لبه بالایی کادر) قرار بده
            if text_y_position < 0:
                text_y_position = base_y_of_box_top + padding_above_box

            # کشیدن حاشیه (outline)
            outline_thickness = max(1, font_object.size // 15) # ضخامت حاشیه متناسب با اندازه فونت
            for dx_o in range(-outline_thickness, outline_thickness + 1):
                for dy_o in range(-outline_thickness, outline_thickness + 1):
                    if dx_o != 0 or dy_o != 0: # خود متن اصلی را به عنوان حاشیه نکش
                        draw_on_pil.text((text_x_position + dx_o, text_y_position + dy_o),
                                         text_to_write, font=font_object, fill=outline_color)
            # کشیدن متن اصلی
            draw_on_pil.text((text_x_position, text_y_position), text_to_write,
                             font=font_object, fill=text_color)

            # تبدیل بازگشت به فرمت OpenCV
            return cv.cvtColor(np.array(pil_img_for_text_draw), cv.COLOR_RGB2BGR)
        except Exception as draw_err:
            print(f"خطا در نوشتن متن '{text_to_write[:20]}...' روی تصویر: {draw_err}")
            return cv_image_input # در صورت خطا، تصویر ورودی را برگردان

    def update_image_display(self, img_pil):
        try:
            self.translated_image_tk = ImageTk.PhotoImage(image=img_pil)
            self.image_label.config(image=self.translated_image_tk)
            self.image_label.image = self.translated_image_tk
        except Exception as e:
            print(f"خطا در به‌روزرسانی نمایش تصویر: {e}")
            traceback.print_exc()

    def update_ocr_text_widget(self, text):
        self.ocr_text_widget.config(state='normal')
        self.ocr_text_widget.delete('1.0', 'end')
        self.ocr_text_widget.insert('1.0', text)
        self.ocr_text_widget.config(state='disabled')

    def update_translated_text_widget(self, text):
        self.translated_text_widget.config(state='normal')
        self.translated_text_widget.delete('1.0', 'end')
        self.translated_text_widget.insert('1.0', text)
        self.translated_text_widget.config(state='disabled')

    def stop_loading_and_update_status(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.config(text="Amadeh")


if __name__ == "__main__":
    root = Tk()
    app = OCRTranslatorApp(root)
    root.mainloop()