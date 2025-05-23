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

# Import translation function and configuration from separate files
# طبق درخواست شما، این ایمپورت باقی می‌ماند
from translation_api import translate_en_to_fa_api
from config import FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE, LANGUAGE_OPTIONS, MIN_FONT_SIZE, MAX_FONT_SIZE

import warnings
warnings.filterwarnings("ignore")

# بررسی اولیه فونت (برای اطمینان از وجود مسیر در config)
try:
    if FONT_PATH:
        # این فقط یک چک اولیه است، خود فونت دیگر برای کشیدن روی تصویر استفاده نمی‌شود
        ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
    else:
        print("هشدار: مسیر فونت (FONT_PATH) در config.py تعریف نشده است.")
except IOError:
    print(f"خطا هنگام بررسی اولیه فونت از مسیر {FONT_PATH}. مسیر را بررسی کنید.")
except Exception as e:
    print(f"خطای ناشناخته هنگام بررسی اولیه فونت: {e}")


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
            if code == "fa":
                default_lang_key = key
                break
        self.selected_language_name.set(default_lang_key)
        self.language_options = LANGUAGE_OPTIONS

        self.translate_checkbox_var = StringVar(master, value="1")
        self.font_size_var = StringVar(master, value=str(GLOBAL_FONT_DEFAULT_SIZE))

        # --- UI Elements (unchanged as requested) ---
        # متغیر و گزینه‌ها برای انتخاب سطح کادکشی
        self.selected_draw_level_name = StringVar(master)
        self.draw_level_options = {
            "Kadr Nakeshid (None)": 0,
            "Kalame (Word)": 5,
            "Khat/Jomle (Line)": 4,
            "Paragraph": 3,
            "Block Matn (Block)": 2
        }
        self.selected_draw_level_name.set("Khat/Jomle (Line)")  # انتخاب پیش‌فرض

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


        # لیبل و منوی انتخاب سطح کادکشی (این قسمت جدید است)
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

        self.status_frame = ttk.Frame(master, padding="5")
        self.status_frame.pack(side="bottom", fill="x")
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=200, mode="indeterminate")
        self.status_label = Label(self.status_frame, text="Amadeh", fg="white", bg="gray25")
        self.status_label.pack(side="left", padx=10)

    def on_setting_change(self, *args):
        if self.current_image_path:
            self.status_label.config(text="Dar hale taghir tanzimat va pardazesh mojadad...")
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self.process_image, args=(self.current_image_path,), daemon=True).start()
        else:
            self.status_label.config(text="Amadeh")

    def select_image(self):
        file_path = filedialog.askopenfilename(title="Entekhab Tasvir", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.current_image_path = file_path
            self.status_label.config(text="Dar hale pardazesh ...")
            if not self.progress_bar.winfo_ismapped():
                self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self.process_image, args=(file_path,), daemon=True).start()

    # --- Helper Functions for process_image ---
    def _load_images_from_path(self, img_path):
        """بارگذاری تصویر با PIL و OpenCV از مسیر داده شده."""
        try:
            img_pil = pl.Image.open(img_path)
            img_cv = cv.imread(img_path)
            if img_cv is None:
                raise ValueError("OpenCV نتوانست تصویر را بارگذاری کند (ممکن است مسیر اشتباه یا فایل خراب باشد).")
            return img_pil, img_cv
        except FileNotFoundError:
            raise ValueError(f"فایل تصویر در مسیر '{img_path}' یافت نشد.")
        except Exception as e:
            raise ValueError(f"خطا در بارگذاری تصویر '{img_path}': {e}")

    def _get_structured_ocr_data(self, img_pil, psm_config='--psm 1'):
        """اجرای OCR و برگرداندن DataFrame تمیز شده."""
        try:
            # استفاده از psm_config که کاربر در کد قبلی به 1 تغییر داده بود
            df = pytesseract.image_to_data(img_pil, lang='eng', output_type=pytesseract.Output.DATAFRAME, config=psm_config)
        except pytesseract.TesseractError as tess_err:
            # خطاهای مربوط به خود Tesseract (مثلا پیدا نشدن زبان)
            print(f"خطای اجرایی Tesseract: {tess_err}")
            raise  # دوباره خطا را ایجاد کن تا در process_image گرفته شود
        except Exception as e:
            print(f"خطای ناشناخته هنگام اجرای image_to_data: {e}")
            raise # دوباره خطا را ایجاد کن

        if df is None or df.empty:
            # print("DEBUG: Tesseract DataFrame خالی برگرداند.")
            return pd.DataFrame()

        # پاک‌سازی اولیه DataFrame
        df.dropna(subset=['text'], inplace=True) # حذف ردیف‌هایی که متن ندارند
        # حذف ردیف‌هایی که متن آنها فقط فضای خالی است
        df = df[df['text'].astype(str).str.strip() != '']

        if df.empty: # بررسی مجدد پس از حذف متن‌های خالی
            # print("DEBUG: DataFrame پس از حذف متن‌های خالی، خالی شد.")
            return pd.DataFrame()

        df['conf'] = pd.to_numeric(df['conf'], errors='coerce').fillna(-1).astype(int)

        structural_cols = ['level', 'page_num', 'block_num', 'par_num', 'line_num', 'word_num', 'left', 'top', 'width', 'height']
        for col in structural_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            else:
                # اگر ستون ساختاری حیاتی وجود نداشته باشد، یک DataFrame خالی برمی‌گردانیم یا خطا ایجاد می‌کنیم
                # print(f"هشدار: ستون ساختاری '{col}' در خروجی Tesseract یافت نشد.")
                raise ValueError(f"ستون ساختاری حیاتی '{col}' در خروجی Tesseract یافت نشد.")
        return df

    def _extract_ocr_text_for_display(self, df_ocr):
        """استخراج و فرمت‌بندی متن OCR برای نمایش در جعبه متن."""
        ocr_full_text = ""
        if df_ocr.empty or not (df_ocr['level'] == 5).any():
            return "" # اگر DataFrame خالی است یا هیچ کلمه‌ای ندارد

        # فقط کلمات (level 5) برای نمایش در جعبه متن OCR استفاده می‌شوند
        df_words = df_ocr[df_ocr['level'] == 5].copy()
        if df_words.empty:
            return ""

        # گروه‌بندی بر اساس ساختار برای حفظ ترتیب خطوط و پاراگراف‌ها
        grouped_for_text = df_words.groupby(
            ['page_num', 'block_num', 'par_num', 'line_num'], sort=True
        )
        for _, group in grouped_for_text:
            # کلمات هر خط را با فاصله به هم بچسبان
            line_text = " ".join(group.sort_values(by='word_num')['text'].astype(str).tolist())
            ocr_full_text += line_text + "\n" # اضافه کردن خط جدید بعد از هر خط متنی
        return ocr_full_text.strip() # حذف خط جدید اضافی از انتها

    def _resize_image_for_tk(self, pil_img, target_widget):
        """تغییر اندازه تصویر PIL برای نمایش در ویجت Tkinter."""
        try:
            container_width = target_widget.winfo_width()
            container_height = target_widget.winfo_height()

            # اگر ابعاد ویجت هنوز مشخص نشده (معمولاً در اولین رندر)
            if container_width < 50 or container_height < 50:
                # استفاده از ابعاد master به عنوان تخمین بزرگتر
                master_width = target_widget.master.winfo_width() if target_widget.master else 500
                master_height = target_widget.master.winfo_height() if target_widget.master else 400

                # چون image_container در یک ستون گرید با وزن ۱ است، عرض آن نصف عرض main_content_frame خواهد بود
                # main_content_frame هم عرض master را می‌گیرد (منهای padding)
                parent_width_estimate = master_width * 0.48 # حدود نصف
                parent_height_estimate = master_height * 0.9 # حدود کل ارتفاع موجود

                container_width = int(parent_width_estimate)
                container_height = int(parent_height_estimate)
                if container_width < 50: container_width = 300 # حداقل مقدار قابل قبول
                if container_height < 50: container_height = 300


            img_copy = pil_img.copy() # کار روی کپی برای thumbnail
            if img_copy.width > container_width or img_copy.height > container_height:
                img_copy.thumbnail((container_width, container_height), pl.Image.Resampling.LANCZOS)
            return img_copy
        except Exception as e:
            print(f"خطا در تغییر اندازه تصویر: {e}")
            return pil_img # در صورت خطا، تصویر اصلی را برگردان

    def process_image(self, img_path):
        try:
            # ۱. بارگذاری تصاویر
            img_pil_original, img_cv_original = self._load_images_from_path(img_path)

            # ۲. ایجاد کپی و پیش‌پردازش تصویر برای OCR
            img_cv_for_preprocessing = img_cv_original.copy()
            preprocessed_cv_image = self._preprocess_image_for_ocr(img_cv_for_preprocessing)

            psm_to_use = '--psm 6' # یا هر PSM مناسب دیگر

            if preprocessed_cv_image is None: # اگر پیش‌پردازش ناموفق بود
                df_ocr_processed = self._get_structured_ocr_data(img_cv_original, psm_config='--psm 1')
            else:
                df_ocr_processed = self._get_structured_ocr_data(preprocessed_cv_image, psm_config=psm_to_use)

            # ۳. استخراج متن OCR (از تصویر پیش‌پردازش شده) برای نمایش در جعبه متن بالایی
            ocr_display_text = self._extract_ocr_text_for_display(df_ocr_processed)
            self.master.after(0, self.update_ocr_text_widget, ocr_display_text)

            # --- بخش ۴: منطق ترجمه و آماده‌سازی متن برای جعبه متن پایینی ---
            translated_output_for_widget = ""

            should_translate = self.translate_checkbox_var.get() == "1"
            current_target_lang_code = self.language_options[self.selected_language_name.get()]

            selected_level_name = self.selected_draw_level_name.get()
            level_to_draw = self.draw_level_options.get(selected_level_name, 0)

            if should_translate and current_target_lang_code != 'en':
                # اگر حالت "Khat/Jomle (Line)" (تقسیم‌بندی دستی) انتخاب شده بود
                if level_to_draw == 4:
                    df_words_for_segmentation = df_ocr_processed[df_ocr_processed['level'] == 5].copy()
                    if not df_words_for_segmentation.empty:
                        manually_segmented_lines = self._manually_segment_lines(df_words_for_segmentation, y_tolerance_factor=0.7)
                        temp_translated_text_list = []
                        if manually_segmented_lines: # اگر خطی پیدا شد
                            for line_of_word_series in manually_segmented_lines:
                                if not line_of_word_series: continue
                                # متن اصلی خط را از سری‌های پانداس استخراج می‌کنیم
                                line_text_original = " ".join(str(s['text']).strip() for s in line_of_word_series if str(s['text']).strip())

                                if line_text_original.strip():
                                    # print(f"DEBUG: Translating manual line: '{line_text_original}'")
                                    translated_line = translate_en_to_fa_api(line_text_original, target_lang=current_target_lang_code)
                                    temp_translated_text_list.append(translated_line)
                                # else: # اگر خط خالی بود، یک خط خالی در ترجمه هم بگذار
                                #    temp_translated_text_list.append("")
                            translated_output_for_widget = "\n".join(temp_translated_text_list)
                        else: # اگر هیچ خطی به صورت دستی پیدا نشد
                             if ocr_display_text.strip(): # کل متن OCR شده را ترجمه کن
                                # print(f"DEBUG: No manual lines, translating full OCR text: '{ocr_display_text[:50]}...'")
                                translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                             else:
                                translated_output_for_widget = "[متنی برای ترجمه خط به خط یافت نشد]"
                    else: # اگر کلمه‌ای برای تقسیم‌بندی وجود نداشت
                        if ocr_display_text.strip(): # کل متن OCR شده را ترجمه کن
                            # print(f"DEBUG: No words for segmentation, translating full OCR text: '{ocr_display_text[:50]}...'")
                            translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                        else:
                            translated_output_for_widget = "[متنی برای ترجمه یافت نشد]"

                else: # برای سایر حالت‌های کادکشی (کلمه، پاراگراف، بلوک، یا عدم کادکشی)
                    if ocr_display_text.strip(): # اگر متن OCR شده‌ای وجود دارد
                        # print(f"DEBUG: Translating full OCR text for other modes: '{ocr_display_text[:50]}...'")
                        translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    else:
                        translated_output_for_widget = "[متنی برای ترجمه وجود ندارد]"
            else: # اگر ترجمه خاموش است یا زبان مقصد انگلیسی است
                translated_output_for_widget = ocr_display_text # متن اصلی را در جعبه "ترجمه شده" نمایش بده
                if current_target_lang_code == 'en' and should_translate:
                     translated_output_for_widget = ocr_display_text # + "\n[متن اصلی - زبان مقصد انگلیسی است]" # این پیام اختیاری است

            self.master.after(0, self.update_translated_text_widget, translated_output_for_widget.strip())


            # --- بخش ۵: آماده‌سازی تصویر اصلی و کشیدن کادرها ---
            image_with_boxes_cv = img_cv_original.copy()
            if level_to_draw > 0 and not df_ocr_processed.empty: # کادکشی فقط اگر سطحی انتخاب شده باشد
                if level_to_draw == 4: # کادکشی برای خطوط دستی
                    df_words_for_segmentation = df_ocr_processed[df_ocr_processed['level'] == 5].copy()
                    if not df_words_for_segmentation.empty:
                        manually_segmented_lines = self._manually_segment_lines(df_words_for_segmentation, y_tolerance_factor=0.7)
                        line_box_color = (34, 139, 34)
                        for line_of_word_series in manually_segmented_lines:
                            if not line_of_word_series: continue
                            min_x = min(int(s['left']) for s in line_of_word_series)
                            min_y = min(int(s['top']) for s in line_of_word_series)
                            max_x_coord = max(int(s['left']) + int(s['width']) for s in line_of_word_series)
                            max_y_coord = max(int(s['top']) + int(s['height']) for s in line_of_word_series)
                            if max_x_coord > min_x and max_y_coord > min_y:
                                 cv.rectangle(image_with_boxes_cv, (min_x, min_y), (max_x_coord, max_y_coord), line_box_color, 2)
                else: # کادرکشی برای سطوح تشخیص داده شده توسط تسراکت (کلمه، پاراگراف، بلوک)
                    elements_to_draw = df_ocr_processed[df_ocr_processed['level'] == level_to_draw]
                    color_map = {5: (0,0,255), 3: (255,165,0), 2: (128,0,128)}
                    box_color = color_map.get(level_to_draw, (255,0,0))
                    for _, ocr_element in elements_to_draw.iterrows():
                        if int(ocr_element['width']) > 0 and int(ocr_element['height']) > 0 :
                            x,y,w,h = int(ocr_element['left']),int(ocr_element['top']),int(ocr_element['width']),int(ocr_element['height'])
                            cv.rectangle(image_with_boxes_cv, (x, y), (x + w, y + h), box_color, 2)

            image_to_show_pil = pl.Image.fromarray(cv.cvtColor(image_with_boxes_cv, cv.COLOR_BGR2RGB))
            resized_pil_image = self._resize_image_for_tk(image_to_show_pil, self.image_container)
            self.master.after(0, self.update_image_display, resized_pil_image)

        except ValueError as ve:
            print(f"ValueError در process_image: {ve}")
            self.master.after(0, lambda: messagebox.showerror("خطای ورودی/مقدار", f"{ve}"))
        except pytesseract.TesseractError as tess_err:
            print(f"TesseractError در process_image: {tess_err}")
            self.master.after(0, lambda: messagebox.showerror("خطای Tesseract", f"{tess_err}"))
        except Exception as e:
            print(f"خطای عمومی در process_image: {e}")
            import traceback
            traceback.print_exc()
            self.master.after(0, lambda: messagebox.showerror("خطای کلی در پردازش", f"یک خطای پیش‌بینی نشده رخ داد: {e}"))
        finally:
            self.master.after(0, self.stop_loading_and_update_status)

    def update_image_display(self, img_pil):
        try:
            self.translated_image_tk = ImageTk.PhotoImage(image=img_pil)
            self.image_label.config(image=self.translated_image_tk)
            self.image_label.image = self.translated_image_tk
        except Exception as e:
            print(f"خطا در به‌روزرسانی نمایش تصویر: {e}")

    def _manually_segment_lines(self, df_words, y_tolerance_factor=0.7):
        """
        کلمات (DataFrame ورودی شامل level 5) را بر اساس نزدیکی عمودی به خطوط دستی تقسیم می‌کند.
        y_tolerance_factor: ضریبی از ارتفاع کلمه برای تعیین حداکثر فاصله عمودی مجاز بین مراکز دو کلمه در یک خط.
        خروجی: لیستی از لیست‌ها، که هر لیست داخلی شامل ردیف‌های DataFrame کلمات یک خط است.
        """
        if df_words.empty:
            return []

        # کلمات باید بر اساس مختصات عمودی (top) و سپس افقی (left) مرتب شوند
        # این به پردازش ترتیبی کمک می‌کند
        # اطمینان حاصل می‌کنیم که ستون‌های مورد نیاز عددی هستند
        for col in ['top', 'left', 'height', 'word_num']: # word_num برای مرتب‌سازی ثانویه در صورت y یکسان
            if col not in df_words.columns or not pd.api.types.is_numeric_dtype(df_words[col]):
                print(f"هشدار: ستون '{col}' برای تقسیم‌بندی دستی خطوط موجود نیست یا عددی نیست.")
                # یک مرتب‌سازی پایه انجام می‌دهیم اگر ستون‌ها موجود نباشند
                df_words = df_words.sort_values(by=df_words.columns[0]) # یک مرتب‌سازی خیلی ساده
                break
        else: # اگر حلقه بدون break تمام شد یعنی همه ستون‌ها بودند
            df_words = df_words.sort_values(by=['top', 'left', 'word_num'], ascending=[True, True, True])


        all_lines = []
        current_line_words = []

        if df_words.empty: # اگر پس از مرتب‌سازی یا به هر دلیلی خالی شد
            return []

        for index, word_series in df_words.iterrows():
            word_top = int(word_series['top'])
            word_height = int(word_series['height'])
            word_center_y = word_top + (word_height / 2)

            if not current_line_words: # اگر این اولین کلمه در خط فعلی است
                current_line_words.append(word_series)
            else:
                # میانگین مرکز عمودی کلمات در خط فعلی را محاسبه کن
                # یا از آخرین کلمه خط فعلی استفاده کن
                last_word_in_line = current_line_words[-1]
                last_word_top = int(last_word_in_line['top'])
                last_word_height = int(last_word_in_line['height'])
                last_word_center_y = last_word_top + (last_word_height / 2)

                # آستانه تحمل: ضریبی از ارتفاع کلمه فعلی یا کلمه قبلی
                # یا یک مقدار ثابت کوچک، یا ترکیبی
                y_threshold = max(word_height, last_word_height) * y_tolerance_factor

                if abs(word_center_y - last_word_center_y) < y_threshold:
                    # کلمه به خط فعلی تعلق دارد
                    current_line_words.append(word_series)
                else:
                    # کلمه به خط جدیدی تعلق دارد
                    all_lines.append(current_line_words) # خط قبلی را ذخیره کن
                    current_line_words = [word_series] # خط جدید را با این کلمه شروع کن

        # آخرین خط جمع‌آوری شده را اضافه کن
        if current_line_words:
            all_lines.append(current_line_words)

        # print(f"DEBUG: Manually segmented into {len(all_lines)} lines.")
        return all_lines

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

    def _preprocess_image_for_ocr(self, img_cv):
        """یک تصویر OpenCV را برای بهبود OCR پیش‌پردازش می‌کند."""
        if img_cv is None:
            print("هشدار: تصویر ورودی برای پیش‌پردازش خالی است.")
            return None

        # ۱. تبدیل به خاکستری
        try:
            if len(img_cv.shape) == 3 and img_cv.shape[2] == 3: # اگر تصویر رنگی است
                gray = cv.cvtColor(img_cv, cv.COLOR_BGR2GRAY)
            elif len(img_cv.shape) == 2: # اگر از قبل خاکستری است
                gray = img_cv
            else: # فرمت ناشناخته
                print("هشدار: فرمت تصویر برای تبدیل به خاکستری نامشخص است.")
                return img_cv # تصویر اصلی را برمی‌گرداند
        except Exception as e:
            print(f"خطا در تبدیل تصویر به خاکستری: {e}")
            return img_cv # در صورت خطا، تصویر اصلی را برمی‌گرداند

        # ۲. اعمال Gaussian Blur (برای کاهش نویز)
        # مقادیر (7,7) و 0 مقادیر رایج هستند، ممکن است نیاز به تنظیم داشته باشند
        blurred = cv.GaussianBlur(gray, (5, 5), 0) # کمی ملایم‌تر از (7,7) برای شروع

        # ۳. اعمال Adaptive Thresholding (برای دو دویی کردن تصویر)
        # 255: مقدار ماکزیمم برای پیکسل‌های سفید
        # cv.ADAPTIVE_THRESH_GAUSSIAN_C: روش محاسبه آستانه
        # cv.THRESH_BINARY: نوع آستانه‌گذاری (پیکسل‌ها یا 0 یا 255 می‌شوند)
        # 21: اندازه همسایگی برای محاسبه آستانه (باید فرد باشد)
        # 4: ثابتی که از میانگین وزنی کم می‌شود (C)
        # این مقادیر (21, 4) از مثال شما هستند و ممکن است نیاز به تنظیم دقیق برای تصاویر مختلف داشته باشند
        try:
            thresh = cv.adaptiveThreshold(blurred, 255,
                                         cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv.THRESH_BINARY_INV, # استفاده از INV ممکن است برای برخی تصاویر بهتر باشد (متن سفید، پس‌زمینه سیاه)
                                         21, 4)
        except Exception as e:
            print(f"خطا در اعمال adaptiveThreshold: {e}")
            return blurred # در صورت خطا، تصویر بلور شده را برمی‌گرداند (یا gray)

        # print("DEBUG: Preprocessing applied (Grayscale, GaussianBlur, AdaptiveThreshold).")
        return thresh # تصویر دودویی شده (سیاه و سفید)


if __name__ == "__main__":
    root = Tk()
    app = OCRTranslatorApp(root)
    root.mainloop()