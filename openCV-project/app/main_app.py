# main_app.py
import numpy as np
import pandas as pd
# استفاده مستقیم از Image, ImageFont, ImageTk از PIL
from PIL import Image, ImageFont, ImageTk
import cv2 as cv
import pytesseract # برای استفاده از pytesseract.Output

import threading
from tkinter import Tk, Label, Button, filedialog, PhotoImage, StringVar, OptionMenu, Entry, Checkbutton, scrolledtext
from tkinter import ttk
from tkinter import messagebox
# io و csv دیگر مستقیماً در اینجا استفاده نمی‌شوند (به ocr_utils منتقل شده‌اند)
import traceback # برای چاپ کامل خطاها

# --- ایمپورت توابع از ماژول‌های جدید ---
from translation_api import translate_en_to_fa_api
from config import (FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE, LANGUAGE_OPTIONS,
                    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_OCR_LANG,
                    DEFAULT_OCR_PSM_CONFIG, DEFAULT_Y_TOLERANCE_FACTOR_MANUAL_LINES,
                    WORD_CONFIDENCE_THRESHOLD) # ثابت‌های جدید از config
from ocr_utils import (preprocess_image_for_ocr, get_structured_ocr_data,
                       extract_ocr_text_for_display, manually_segment_lines)
from drawing_utils import draw_text_on_cv_image, resize_pil_image_for_tk
# --- پایان ایمپورت‌ها ---

import warnings
warnings.filterwarnings("ignore")

# --- بررسی اولیه و سراسری فونت هنگام شروع برنامه ---
global_font_instance_check = None
try:
    if FONT_PATH and FONT_PATH.strip() != "":
        global_font_instance_check = ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
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

        self.last_img_cv_original = None
        self.last_pil_original = None
        self.last_df_ocr_processed = None
        self.last_render_segments = []
        self.last_ocr_display_text = ""
        self.last_translated_output_for_widget = ""

        self.prev_font_size = str(GLOBAL_FONT_DEFAULT_SIZE)
        self.prev_language_name = ""
        self.prev_translate_enabled = "1"
        self.prev_draw_level = ""

        self.selected_language_name = StringVar(master)
        default_lang_key = "Engilisi (English)"
        for key, code in LANGUAGE_OPTIONS.items():
            if code == "fa": default_lang_key = key; break
        self.selected_language_name.set(default_lang_key)
        self.language_options = LANGUAGE_OPTIONS

        self.translate_checkbox_var = StringVar(master, value="1")
        self.font_size_var = StringVar(master, value=str(GLOBAL_FONT_DEFAULT_SIZE))

        self.selected_draw_level_name = StringVar(master)
        self.draw_level_options = {
            "Kadr Nakeshid (None)": 0, "Kalame (Word)": 5,
            "Khat/Jomle (Line)": 4, "Paragraph (Tesseract)": 3,
            "Block Matn (Tesseract)": 2
        }
        self.selected_draw_level_name.set("Khat/Jomle (Line)")

        self.prev_language_name = self.selected_language_name.get()
        self.prev_draw_level = self.selected_draw_level_name.get()

        # --- UI Elements ---
        self.control_frame = ttk.Frame(master, padding="10")
        self.control_frame.pack(side="top", fill="x")
        # ... (تمام ویجت‌های control_frame مثل قبل اینجا تعریف و pack می‌شوند) ...
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

        if font_changed_only and self.last_img_cv_original is not None:
            self.status_label.config(text="در حال اعمال فونت جدید...")
            if not self.progress_bar.winfo_ismapped(): self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self._rerender_image_annotations, daemon=True).start()
        else:
            self.status_label.config(text="در حال پردازش مجدد...")
            if not self.progress_bar.winfo_ismapped(): self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self.process_image, args=(self.current_image_path,), daemon=True).start()

    def select_image(self):
        file_path = filedialog.askopenfilename(title="Entekhab Tasvir", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.current_image_path = file_path
            self.last_img_cv_original = None # ریست کردن داده‌های قبلی
            self.last_pil_original = None
            self.last_df_ocr_processed = None
            self.last_render_segments = []
            self.status_label.config(text="Dar hale pardazesh ...")
            if not self.progress_bar.winfo_ismapped(): self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self.process_image, args=(file_path,), daemon=True).start()

    def _load_current_font(self):
        try:
            font_size_str = self.font_size_var.get()
            if not font_size_str.isdigit(): raise ValueError("اندازه فونت باید عدد باشد.")
            font_size = int(font_size_str)
            if not (MIN_FONT_SIZE <= font_size <= MAX_FONT_SIZE):
                font_size = GLOBAL_FONT_DEFAULT_SIZE
                self.font_size_var.set(str(GLOBAL_FONT_DEFAULT_SIZE))
            if FONT_PATH and global_font_instance_check:
                return ImageFont.truetype(FONT_PATH, font_size)
            return None
        except ValueError:
            self.font_size_var.set(str(GLOBAL_FONT_DEFAULT_SIZE))
            if FONT_PATH and global_font_instance_check:
                try: return ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
                except Exception: pass
            return None
        except Exception: return None

    def _load_images_from_path(self, img_path):
        try:
            img_pil = Image.open(img_path) # استفاده از Image به جای pl.Image
            if img_pil.mode == 'RGBA' or img_pil.mode == 'P': img_pil = img_pil.convert('RGB')
            img_cv = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
            if img_cv is None: raise ValueError("تبدیل تصویر PIL به OpenCV ناموفق بود.")
            return img_pil, img_cv
        except FileNotFoundError: raise ValueError(f"فایل تصویر '{img_path}' یافت نشد.")
        except Exception as e: raise ValueError(f"خطا در بارگذاری تصویر '{img_path}': {e}")

    def _rerender_image_annotations(self): # دیگر آرگومان فونت سایز نمی‌گیرد، از self.font_size_var می‌خواند
        """فقط کادرها و متون را با استفاده از داده‌های قبلی و فونت جدید بازترسیمی می‌کند."""
        try:
            self.status_label.config(text="اعمال فونت جدید...")
            new_font = self._load_current_font()
            if new_font is None and global_font_instance_check :
                new_font = global_font_instance_check

            if self.last_img_cv_original is None or not self.last_render_segments:
                print("DEBUG: داده‌های قبلی برای بازترسیمی موجود نیست (در _rerender).")
                self.master.after(0, self.stop_loading_and_update_status)
                return

            image_to_annotate_cv = self.last_img_cv_original.copy()

            for segment in self.last_render_segments:
                rect = segment.get('rect')
                text_on_image = segment.get('text_on_image', "")
                should_draw_text = segment.get('draw_text', False)
                box_color = segment.get('color', (255,0,0))

                if rect:
                    x, y, w, h = rect
                    cv.rectangle(image_to_annotate_cv, (x, y), (x + w, y + h), box_color, 2)

                if should_draw_text and text_on_image.strip() and new_font:
                    # مختصات x و y برای draw_text_on_cv_image، مختصات بالای کادر است
                    image_to_annotate_cv = draw_text_on_cv_image(
                        image_to_annotate_cv, text_on_image,
                        x, y, new_font # ارسال x و y کادر
                    )

            final_image_pil = Image.fromarray(cv.cvtColor(image_to_annotate_cv, cv.COLOR_BGR2RGB))
            container_width = self.image_container.winfo_width()
            container_height = self.image_container.winfo_height()
            resized_pil_image = resize_pil_image_for_tk(final_image_pil, container_width, container_height)

            self.master.after(0, self.update_image_display, resized_pil_image)
            self.prev_font_size = self.font_size_var.get()

        except Exception as e:
            print(f"خطا در بازترسیمی با فونت جدید: {e}")
            traceback.print_exc()
            self.master.after(0, lambda: messagebox.showerror("خطا", "خطا در اعمال فونت جدید."))
        finally:
            self.master.after(0, self.stop_loading_and_update_status)

    def process_image(self, img_path):
        try:
            current_font_for_drawing = self._load_current_font()
            if current_font_for_drawing is None:
                print("هشدار جدی: فونت برای نوشتن روی تصویر بارگذاری نشد.")

            img_pil_original, img_cv_original = self._load_images_from_path(img_path)
            img_cv_for_preprocessing = img_cv_original.copy()
            preprocessed_cv_image = preprocess_image_for_ocr(img_cv_for_preprocessing) # از ocr_utils

            ocr_input_for_df = preprocessed_cv_image if preprocessed_cv_image is not None else img_cv_original
            df_ocr_processed = get_structured_ocr_data(ocr_input_for_df, # از ocr_utils
                                                       lang=DEFAULT_OCR_LANG,
                                                       psm_config=DEFAULT_OCR_PSM_CONFIG)

            ocr_display_text = extract_ocr_text_for_display(df_ocr_processed) # از ocr_utils
            self.master.after(0, self.update_ocr_text_widget, ocr_display_text)

            # --- آماده سازی برای ترجمه و رندر ---
            list_of_segments_for_rendering = []
            translated_output_for_widget = ocr_display_text # پیش‌فرض اگر ترجمه خاموش باشد

            should_translate = self.translate_checkbox_var.get() == "1"
            current_target_lang_code = self.language_options[self.selected_language_name.get()]
            selected_level_name = self.selected_draw_level_name.get()
            level_to_draw = self.draw_level_options.get(selected_level_name, 0)

            image_with_annotations_cv = img_cv_original.copy()

            # --- منطق اصلی برای کادکشی، ترجمه، و آماده‌سازی list_of_segments_for_rendering ---
            if level_to_draw == 4: # حالت "Khat/Jomle (Line)" (تقسیم‌بندی دستی)
                df_words_for_segmentation = df_ocr_processed[df_ocr_processed['level'] == 5].copy()
                temp_translated_list_for_textbox = []
                if not df_words_for_segmentation.empty:
                    manually_segmented_lines_data = manually_segment_lines( # از ocr_utils
                        df_words_for_segmentation,
                        y_tolerance_factor=DEFAULT_Y_TOLERANCE_FACTOR_MANUAL_LINES
                    )
                    for line_of_word_series in manually_segmented_lines_data:
                        if not line_of_word_series: continue
                        min_x = min(int(s['left']) for s in line_of_word_series)
                        min_y = min(int(s['top']) for s in line_of_word_series)
                        max_x_coord = max(int(s['left']) + int(s['width']) for s in line_of_word_series)
                        max_y_coord = max(int(s['top']) + int(s['height']) for s in line_of_word_series)

                        if max_x_coord <= min_x or max_y_coord <= min_y: continue

                        current_rect = (min_x, min_y, max_x_coord - min_x, max_y_coord - min_y)
                        current_box_color = (34,139,34)
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
                                image_with_annotations_cv = draw_text_on_cv_image( # از drawing_utils
                                    image_with_annotations_cv, text_to_show_on_image,
                                    min_x, min_y, current_font_for_drawing
                                )

                        list_of_segments_for_rendering.append({
                            'rect': current_rect, 'text_on_image': text_to_show_on_image,
                            'draw_text': True, 'color': current_box_color,
                            # ذخیره مختصات اصلی برای _rerender_image_annotations
                            'base_x': min_x, 'base_y_box_top': min_y
                        })
                        temp_translated_list_for_textbox.append(current_segment_for_textbox)
                    if temp_translated_list_for_textbox : translated_output_for_widget = "\n".join(temp_translated_list_for_textbox)

                # اگر در حالت خط دستی، خطی پیدا نشد یا کلمه‌ای برای تقسیم‌بندی نبود
                # و ترجمه فعال است، کل متن OCR شده را ترجمه کن
                if not temp_translated_list_for_textbox and should_translate and current_target_lang_code != 'en':
                    if ocr_display_text.strip(): translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    elif not translated_output_for_widget: translated_output_for_widget = "[متنی برای ترجمه یافت نشد]"

            elif level_to_draw == 5: # حالت "Kalame (Word)"
                words_to_process = df_ocr_processed[(df_ocr_processed['level'] == 5) & (df_ocr_processed['conf'] > WORD_CONFIDENCE_THRESHOLD)].copy()
                temp_textbox_lines_dict = {}
                current_box_color = (0,0,255)

                for _, word_row in words_to_process.iterrows():
                    original_word = str(word_row['text']).strip()
                    if not original_word or not (int(word_row['width']) > 0 and int(word_row['height']) > 0): continue

                    x,y,w,h = int(word_row['left']),int(word_row['top']),int(word_row['width']),int(word_row['height'])
                    current_rect = (x,y,w,h)
                    cv.rectangle(image_with_annotations_cv, (x, y), (x + w, y + h), current_box_color, 1)

                    text_to_show_on_image = original_word
                    current_word_for_textbox = original_word

                    if should_translate and current_target_lang_code != 'en':
                        translated_word = translate_en_to_fa_api(original_word, target_lang=current_target_lang_code)
                        # اگر ترجمه خالی بود یا فقط فاصله بود، از اصلی استفاده کن
                        text_to_show_on_image = translated_word if translated_word and translated_word.strip() else original_word
                        current_word_for_textbox = translated_word if translated_word and translated_word.strip() else original_word

                    if current_font_for_drawing and text_to_show_on_image.strip():
                        image_with_annotations_cv = draw_text_on_cv_image(
                            image_with_annotations_cv, text_to_show_on_image,
                            x, y, current_font_for_drawing, padding_above_box=1
                        )

                    list_of_segments_for_rendering.append({
                        'rect': current_rect, 'text_on_image': text_to_show_on_image,
                        'draw_text': True, 'color': current_box_color,
                        'base_x': x, 'base_y_box_top': y
                    })

                    line_key = (word_row['page_num'], word_row['block_num'], word_row['par_num'], word_row['line_num'])
                    if line_key not in temp_textbox_lines_dict: temp_textbox_lines_dict[line_key] = []
                    temp_textbox_lines_dict[line_key].append({'word_num': int(word_row['word_num']), 'text': current_word_for_textbox})

                sorted_line_keys = sorted(temp_textbox_lines_dict.keys())
                final_textbox_lines = [" ".join(item['text'] for item in sorted(temp_textbox_lines_dict[key], key=lambda i: i['word_num'])) for key in sorted_line_keys]
                translated_output_for_widget = "\n".join(final_textbox_lines)

            else: # سایر سطوح (پاراگراف، بلوک) یا عدم کادکشی (level_to_draw == 0 یا 2 یا 3)
                if level_to_draw > 0 and not df_ocr_processed.empty: # فقط کادرها
                    elements_to_draw = df_ocr_processed[df_ocr_processed['level'] == level_to_draw]
                    color_map = {3: (255,165,0), 2: (128,0,128)}
                    current_box_color = color_map.get(level_to_draw, (200,200,200))
                    for _, ocr_element in elements_to_draw.iterrows():
                        if int(ocr_element['width']) > 0 and int(ocr_element['height']) > 0 :
                            x,y,w,h = int(ocr_element['left']),int(ocr_element['top']),int(ocr_element['width']),int(ocr_element['height'])
                            current_rect = (x,y,w,h)
                            cv.rectangle(image_with_annotations_cv, (x, y), (x + w, y + h), current_box_color, 2)
                            list_of_segments_for_rendering.append({
                                'rect': current_rect, 'text_on_image': "",
                                'draw_text': False, 'color': current_box_color,
                                'base_x': x, 'base_y_box_top': y
                            })

                # منطق متن برای جعبه پایینی در این حالت‌ها
                if should_translate and current_target_lang_code != 'en':
                    if ocr_display_text.strip(): translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    else: translated_output_for_widget = "[متنی برای ترجمه وجود ندارد]"
                # اگر ترجمه خاموش است، translated_output_for_widget از قبل ocr_display_text است.

            # اگر پس از تمام بررسی‌ها، translated_output_for_widget هنوز مقدار پیش‌فرض (ocr_display_text) را دارد
            # و ترجمه باید انجام می‌شد اما هیچ شرط خاصی آن را پر نکرد، اینجا کل متن را ترجمه می‌کنیم.
            # این حالت بیشتر برای level_to_draw == 0 (عدم کادکشی) یا سطوح 2 و 3 است.
            if translated_output_for_widget == ocr_display_text and should_translate and current_target_lang_code != 'en':
                 if ocr_display_text.strip():
                     translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                 else:
                     translated_output_for_widget = "[متنی برای ترجمه نبود]"


            self.master.after(0, self.update_translated_text_widget, translated_output_for_widget.strip())

            final_image_to_show_pil = Image.fromarray(cv.cvtColor(image_with_annotations_cv, cv.COLOR_BGR2RGB))

            container_width = self.image_container.winfo_width()
            container_height = self.image_container.winfo_height()
            resized_pil_image = resize_pil_image_for_tk(final_image_to_show_pil, container_width, container_height)

            self.master.after(0, self.update_image_display, resized_pil_image)

            # --- ذخیره نتایج و تنظیمات فعلی ---
            self.last_img_cv_original = img_cv_original.copy()
            self.last_pil_original = img_pil_original.copy()
            self.last_df_ocr_processed = df_ocr_processed.copy() if df_ocr_processed is not None and not df_ocr_processed.empty else None
            self.last_render_segments = list_of_segments_for_rendering
            self.last_ocr_display_text = ocr_display_text
            self.last_translated_output_for_widget = translated_output_for_widget

            self.prev_font_size = self.font_size_var.get()
            self.prev_language_name = self.selected_language_name.get()
            self.prev_translate_enabled = self.translate_checkbox_var.get()
            self.prev_draw_level = self.selected_draw_level_name.get()

        except ValueError as ve:
            print(f"ValueError در process_image: {ve}")
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