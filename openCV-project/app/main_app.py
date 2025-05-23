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
            # ۱. بارگذاری تصویر اصلی (هم PIL هم OpenCV)
            img_pil_original, img_cv_original = self._load_images_from_path(img_path)

            # ۲. ایجاد یک کپی از تصویر OpenCV برای پیش‌پردازش
            img_cv_for_preprocessing = img_cv_original.copy()

            # ۳. پیش‌پردازش تصویر برای OCR
            preprocessed_cv_image = self._preprocess_image_for_ocr(img_cv_for_preprocessing)

            if preprocessed_cv_image is None:
                # print("DEBUG: Preprocessing failed, using original image for OCR.")
                # اگر پیش‌پردازش ناموفق بود، می‌توانیم از تصویر اصلی برای OCR استفاده کنیم یا خطا دهیم
                # فعلا از تصویر اصلی PIL استفاده می‌کنیم (بدون پیش‌پردازش)
                # یا می‌توانید در اینجا خطا ایجاد کنید و ادامه ندهید
                df_ocr_processed = self._get_structured_ocr_data(img_cv_original, psm_config='--psm 1') # یا img_pil_original
            else:
                # ۴. اجرای OCR روی تصویر پیش‌پردازش شده و دریافت DataFrame
                # با PSM 6 یا PSM دیگری که فکر می‌کنید مناسب است، آزمایش کنید
                df_ocr_processed = self._get_structured_ocr_data(preprocessed_cv_image, psm_config='--psm 6')


            # ۵. استخراج متن OCR (از تصویر پیش‌پردازش شده) برای نمایش در جعبه متن
            ocr_display_text = self._extract_ocr_text_for_display(df_ocr_processed)
            self.master.after(0, self.update_ocr_text_widget, ocr_display_text)

            # ۶. پاک کردن جعبه متن ترجمه شده
            self.master.after(0, self.update_translated_text_widget, "")

            # ۷. آماده‌سازی تصویر اصلی OpenCV برای کشیدن کادرها
            # کادرها روی کپی تصویر اصلی کشیده می‌شوند تا تصویر اصلی دست نخورده بماند
            image_with_boxes_cv = img_cv_original.copy()

            # خواندن سطح انتخابی برای کادکشی از UI
            selected_level_name = self.selected_draw_level_name.get()
            level_to_draw = self.draw_level_options.get(selected_level_name, 0)

            # print(f"DEBUG: Selected level to draw: {selected_level_name} (Value: {level_to_draw})")
            # print(f"DEBUG: Number of rows in df_ocr_processed: {len(df_ocr_processed)}")


            if level_to_draw > 0 and not df_ocr_processed.empty:
                elements_to_draw = df_ocr_processed[df_ocr_processed['level'] == level_to_draw]

                # print(f"DEBUG: Number of elements found for level {level_to_draw}: {len(elements_to_draw)}")

                color_map = {5: (0,0,255), 4: (34,139,34), 3: (255,165,0), 2: (128,0,128)}
                box_color = color_map.get(level_to_draw, (255,0,0))

                for _, ocr_element in elements_to_draw.iterrows():
                    if int(ocr_element['width']) > 0 and int(ocr_element['height']) > 0 :
                        x, y, w, h = int(ocr_element['left']), int(ocr_element['top']), int(ocr_element['width']), int(ocr_element['height'])
                        # کادرها روی image_with_boxes_cv (که کپی تصویر اصلی است) کشیده می‌شوند
                        cv.rectangle(image_with_boxes_cv, (x, y), (x + w, y + h), box_color, 2)

            # تبدیل تصویر OpenCV (که حالا کادرها را دارد) به فرمت PIL برای نمایش
            # این تصویر، تصویر *اصلی* است که رویش کادر کشیده شده
            image_to_show_pil = pl.Image.fromarray(cv.cvtColor(image_with_boxes_cv, cv.COLOR_BGR2RGB))

            # ۸. تغییر اندازه تصویر برای نمایش در UI
            resized_pil_image = self._resize_image_for_tk(image_to_show_pil, self.image_container)

            # ۹. نمایش تصویر در UI
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