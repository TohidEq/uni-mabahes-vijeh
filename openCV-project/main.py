import numpy as np
import pandas as pd
import PIL as pl
from PIL import ImageFont, ImageDraw, Image, ImageTk # ImageTk برای نمایش تصویر در Tkinter
import cv2 as cv
import pytesseract as ts
import requests
import json # برای پردازش پاسخ JSON

import os
from glob import glob
import threading # برای اجرای عملیات طولانی در پس زمینه
from tkinter import Tk, Label, Button, filedialog, PhotoImage, Toplevel, StringVar, OptionMenu # برای GUI
from tkinter import ttk # برای ProgressBar (لودینگ)
from tkinter import messagebox # برای نمایش پیغام خطا

import warnings
warnings.filterwarnings("ignore")

# --- Define the translation function using the provided Google Translate API ---
def translate_en_to_fa_api(text, target_lang='fa'):
    if not text.strip():
        return ""
    base_url = 'https://translate.googleapis.com/translate_a/single'
    params = {
        'client': 'gtx',
        'sl': 'en',
        'tl': target_lang, # زبان مقصد متغیر است
        'dt': 't',
        'q': text
    }
    try:
        response = requests.get(base_url, params=params, timeout=10) # Timeout افزایش یافت
        response.raise_for_status()
        translation_data = response.json()
        if translation_data and len(translation_data) > 0 and len(translation_data[0]) > 0 and len(translation_data[0][0]) > 0:
            return translation_data[0][0][0]
        else:
            return text # بازگشت به متن اصلی در صورت عدم استخراج ترجمه
    except requests.exceptions.RequestException as e:
        print(f"Translation API error for '{text}': {e}")
        return text # بازگشت به متن اصلی در صورت خطای API
# --- End of translation function ---

# Define the font path (updated with your username)
# مطمئن شوید این مسیر دقیق و صحیح است
fontPath = "/home/tohid-eq/Desktop/vazirmatn/fonts/ttf/Vazirmatn-Light.ttf"
try:
    # اندازه فونت را کمی بزرگتر انتخاب کنید تا بهتر دیده شود
    global_font = ImageFont.truetype(fontPath, 28)
except IOError:
    print(f"Error: Could not load font from {fontPath}. Please check the path.")
    global_font = None # Handle case where font is not loaded

class OCRTranslatorApp:
    def __init__(self, master):
        self.master = master
        master.title("OCR Text Translator")
        master.geometry("800x600")  # andazeh avaliye panjere

        self.current_image_path = None
        self.translated_image_tk = None

        # motaghayer baraye entekhab zaban
        self.selected_language = StringVar(master)
        self.selected_language.set("Farsi (Persian)")  # pishfarz farsi
        self.language_options = {
            "Farsi (Persian)": "fa",
            "Arabi (Arabic)": "ar",
            "Faransavi (French)": "fr",
            "Espaniyayi (Spanish)": "es",
            "Almani (German)": "de",
            "Chini (Chinese)": "zh-CN",
            "Rusi (Russian)": "ru"
        }


        # Frame baraye dokmeh-ha va entekhab zaban
        self.control_frame = ttk.Frame(master, padding="10")
        self.control_frame.pack(side="top", fill="x")

        self.select_button = Button(self.control_frame, text="Entekhab Tasvir", command=self.select_image)
        self.select_button.pack(side="left", padx=5, pady=5)

        self.language_menu = OptionMenu(self.control_frame, self.selected_language, *self.language_options.keys())
        self.language_menu.pack(side="left", padx=5, pady=5)
        # vaghti zaban taghir mikonad, agar aksi baz ast, an ra dobare pardazesh konad
        self.selected_language.trace_add("write", self.on_language_change)

        self.exit_button = Button(self.control_frame, text="Khorooj", command=master.quit)
        self.exit_button.pack(side="right", padx=5, pady=5)

        # Label baraye namayesh tasvir
        self.image_label = Label(master, bd=2, relief="groove")
        self.image_label.pack(side="bottom", fill="both", expand=True, padx=10, pady=10)

        # ProgressBar baraye namayesh loading
        self.progress_bar = ttk.Progressbar(master, orient="horizontal", length=200, mode="indeterminate")

        # Label baraye namayesh vaziyat
        self.status_label = Label(master, text="", fg="blue")
        self.status_label.pack(side="bottom", pady=5)

    def on_language_change(self, *args):
        if self.current_image_path:
            self.process_image(self.current_image_path)

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="انتخاب فایل تصویر",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
        )
        if file_path:
            self.current_image_path = file_path
            # شروع پردازش در یک ترد جداگانه
            self.status_label.config(text="Darhale pardazesh o tarjomeh ...")
            self.progress_bar.pack(side="bottom", pady=5)
            self.progress_bar.start()

            threading.Thread(target=self.process_image, args=(file_path,), daemon=True).start()

    def process_image(self, img_path):
        try:
            # Prepare images
            img_pl = pl.Image.open(img_path)
            img_cv = cv.imread(img_path)
            if img_cv is None:
                raise ValueError("Could not read image with OpenCV. Check file path or corruption.")

            # Extract data
            data = ts.image_to_data(img_pl)
            dataList = list(map(lambda x: x.split("\t"), data.split("\n")))
            df = pd.DataFrame(dataList[1:], columns=dataList[0])
            df.dropna(inplace=True)
            df['conf'] = pd.to_numeric(df['conf'], errors='coerce') # تبدیل به عدد
            df = df[df['conf'] > 30] # فیلتر کردن کلمات با اطمینان پایین (اختیاری)

            processed_image = img_cv.copy()

            # پیدا کردن زبان انتخاب شده
            current_target_lang_key = self.selected_language.get()
            current_target_lang_code = self.language_options[current_target_lang_key]

            for l, x, y, w, h, c, t in df[
                ["level", "left", "top", "width", "height", "conf", "text"]
            ].values:
                l = int(l)
                x = int(x)
                y = int(y)
                w = int(w)
                h = int(h)
                # c = float(c) # conf قبلا به numeric تبدیل شده

                if l == 5 and str(t).strip() != "": # Process only words with text
                    cv.rectangle(
                        processed_image,
                        (x, y),
                        (x + w, y + h),
                        (0, 0, 255), # آبی برای کادر کلمه
                        1,
                    )

                    translated_text = t
                    if current_target_lang_code != 'en': # اگر زبان مقصد انگلیسی نیست، ترجمه کن
                        translated_text = translate_en_to_fa_api(t, target_lang=current_target_lang_code)

                    if global_font:
                        pil_img = Image.fromarray(cv.cvtColor(processed_image, cv.COLOR_BGR2RGB))
                        draw = ImageDraw.Draw(pil_img)

                        bbox = draw.textbbox((0, 0), translated_text, font=global_font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]

                        text_y_position = y - text_height - 5
                        if text_y_position < 0:
                            text_y_position = y

                        outline_thickness = 2
                        for dx in range(-outline_thickness, outline_thickness + 1):
                            for dy in range(-outline_thickness, outline_thickness + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((x + dx, text_y_position + dy), translated_text, font=global_font, fill=(0, 0, 0)) # Black outline
                        draw.text((x, text_y_position), translated_text, font=global_font, fill=(250, 250, 250)) # White text

                        processed_image = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)
                    else:
                        cv.putText(processed_image, translated_text, (x, y), cv.FONT_HERSHEY_COMPLEX, 0.8, (250, 250, 250), 1, cv.LINE_AA)
                        cv.putText(processed_image, translated_text, (x, y), cv.FONT_HERSHEY_COMPLEX, 0.8, (0, 0, 0), 2, cv.LINE_AA)

            # تبدیل تصویر پردازش شده برای نمایش در Tkinter
            img_rgb = cv.cvtColor(processed_image, cv.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)

            # تغییر اندازه تصویر برای جا شدن در Label
            # ابعاد لیبل را به دست آورید
            label_width = self.image_label.winfo_width()
            label_height = self.image_label.winfo_height()

            # اگر ابعاد لیبل هنوز صفر است (یعنی پنجره هنوز کاملاً رندر نشده)، از ابعاد پیش فرض استفاده کنید
            if label_width == 1 and label_height == 1: # Tkinter returns 1,1 before full render
                label_width = 780 # تقریبی
                label_height = 500 # تقریبی

            if img_pil.width > label_width or img_pil.height > label_height:
                ratio_w = label_width / img_pil.width
                ratio_h = label_height / img_pil.height
                ratio = min(ratio_w, ratio_h)
                new_width = int(img_pil.width * ratio)
                new_height = int(img_pil.height * ratio)
                img_pil = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)

            self.translated_image_tk = ImageTk.PhotoImage(image=img_pil)
            self.image_label.config(image=self.translated_image_tk)
            self.image_label.image = self.translated_image_tk # برای جلوگیری از جمع آوری زباله

        except Exception as e:
            messagebox.showerror("Error", f"Error dar pardazesh tasvir: {e}")
            print(f"Error during image processing: {e}")
        finally:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.status_label.config(text="آماده")

# Main application setup
if __name__ == "__main__":
    root = Tk()
    app = OCRTranslatorApp(root)
    root.mainloop()