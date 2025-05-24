# main_app.py
import numpy as np
import pandas as pd
from PIL import Image, ImageFont, ImageTk
import cv2 as cv
import pytesseract

import threading
from tkinter import Tk, Label, Button, filedialog, PhotoImage, StringVar, OptionMenu, Entry, Checkbutton, scrolledtext
from tkinter import ttk
from tkinter import messagebox
import traceback

from translation_api import translate_en_to_fa_api
from config import (FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE, LANGUAGE_OPTIONS,
                    MIN_FONT_SIZE, MAX_FONT_SIZE, DEFAULT_OCR_LANG,
                    DEFAULT_OCR_PSM_CONFIG, # برای مقدار اولیه PSM
                    PSM_OPTIONS, # دیکشنری گزینه‌های PSM
                    DEFAULT_Y_TOLERANCE_FACTOR_MANUAL_LINES,
                    WORD_CONFIDENCE_THRESHOLD_DEFAULT,
                    GAUSSIAN_BLUR_KERNEL_SIZE_DEFAULT,
                    ADAPTIVE_THRESHOLD_BLOCK_SIZE_DEFAULT,
                    ADAPTIVE_THRESHOLD_C_DEFAULT)
from ocr_utils import (get_structured_ocr_data,
                       extract_ocr_text_for_display) # manually_segment_lines دیگر برای نمایش نهایی خطوط استفاده نمی‌شود
from drawing_utils import draw_text_on_cv_image, resize_pil_image_for_tk

import warnings
warnings.filterwarnings("ignore")

global_font_instance_check = None
try:
    if FONT_PATH and FONT_PATH.strip() != "":
        global_font_instance_check = ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
    else:
        print("Hoshdar جدی: Masir font (FONT_PATH) dar config.py ta'rif nashode ya khali ast...")
except IOError:
    print(f"Khataye IO hengam barresi avaliye font az masir '{FONT_PATH}'...")
except Exception as e:
    print(f"Khataye nashnakhte hengam barresi avaliye font az masir '{FONT_PATH}': {e}")


class OCRTranslatorApp:
    def __init__(self, master):
        self.master = master
        master.title("OCR Text Translator")
        master.geometry("1200x880")

        self.current_image_path = None
        self.translated_image_tk = None
        self.last_pil_original = None
        self.last_img_cv_original = None
        self.img_cv_grayscale_debug = None
        self.img_cv_blurred_debug = None
        self.img_cv_binary_debug = None
        self._current_cv_grayscale = None
        self._current_cv_blurred = None
        self._current_cv_binary = None
        self.last_df_ocr_processed = None
        self.last_render_segments = []
        self.last_ocr_display_text = ""
        self.last_translated_output_for_widget = ""
        self._last_displayed_annotated_pil = None

        self.selected_language_name = StringVar(master)
        default_lang_key = "Engilisi (English)"
        for key, code in LANGUAGE_OPTIONS.items():
            if code == "fa": default_lang_key = key; break
        self.selected_language_name.set(default_lang_key)
        self.language_options = LANGUAGE_OPTIONS

        self.translate_checkbox_var = StringVar(master, value="1")
        self.font_size_var = StringVar(master, value=str(GLOBAL_FONT_DEFAULT_SIZE))
        self.word_confidence_threshold_var = StringVar(master, value=str(WORD_CONFIDENCE_THRESHOLD_DEFAULT))

        self.selected_draw_level_name = StringVar(master)
        self.draw_level_options = {
            "Bedoon Kadr (None)": 0, "Kalame (Word)": 5,
            "Khat (Line)": 4, "Paragraph (Tesseract)": 3,
            "Block (Tesseract)": 2
        }
        self.selected_draw_level_name.set("Khat (Line)")

        self.gaussian_kernel_var = StringVar(master, value=str(GAUSSIAN_BLUR_KERNEL_SIZE_DEFAULT))
        self.adaptive_block_size_var = StringVar(master, value=str(ADAPTIVE_THRESHOLD_BLOCK_SIZE_DEFAULT))
        self.adaptive_c_var = StringVar(master, value=str(ADAPTIVE_THRESHOLD_C_DEFAULT))

        self.psm_options_ui_map = PSM_OPTIONS
        self.selected_psm_config_str = StringVar(master)
        initial_psm_key = DEFAULT_OCR_PSM_CONFIG
        for key, val_str in self.psm_options_ui_map.items():
            if val_str == DEFAULT_OCR_PSM_CONFIG:
                initial_psm_key = key
                break
        self.selected_psm_config_str.set(initial_psm_key)


        # --- UI Elements ---
        self.control_frame_top = ttk.Frame(master, padding="5")
        self.control_frame_top.pack(side="top", fill="x")

        self.control_frame_middle = ttk.Frame(master, padding="5")
        self.control_frame_middle.pack(side="top", fill="x")

        self.control_frame_bottom = ttk.Frame(master, padding="5")
        self.control_frame_bottom.pack(side="top", fill="x")

        self.control_frame_debug_views = ttk.Frame(master, padding="5")
        self.control_frame_debug_views.pack(side="top", fill="x")

        self.select_button = Button(self.control_frame_top, text="Entekhab Tasvir", command=self.select_image)
        self.select_button.pack(side="left", padx=5, pady=5)

        self.apply_button = Button(self.control_frame_top, text="Amal va Pardazesh", command=self.apply_settings_and_process)
        self.apply_button.pack(side="left", padx=10, pady=5)

        ttk.Label(self.control_frame_top, text="Zaban Tarjomeh:").pack(side="left", padx=(10, 2), pady=5)
        self.language_menu = OptionMenu(self.control_frame_top, self.selected_language_name, *self.language_options.keys())
        self.language_menu.pack(side="left", padx=5, pady=5)

        self.translate_checkbox = Checkbutton(self.control_frame_top, text="Tarjome Kon", variable=self.translate_checkbox_var, onvalue="1", offvalue="0")
        self.translate_checkbox.pack(side="left", padx=10, pady=5)

        self.exit_button = Button(self.control_frame_top, text="Khorooj", command=master.quit)
        self.exit_button.pack(side="right", padx=5, pady=5)

        ttk.Label(self.control_frame_middle, text="Kadr Dore:").pack(side="left", padx=(0,2), pady=5)
        self.draw_level_menu = OptionMenu(self.control_frame_middle, self.selected_draw_level_name, *self.draw_level_options.keys())
        self.draw_level_menu.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_middle, text=f"Font Size ({MIN_FONT_SIZE}-{MAX_FONT_SIZE}):").pack(side="left", padx=(10, 2), pady=5)
        self.font_size_entry = Entry(self.control_frame_middle, textvariable=self.font_size_var, width=5)
        self.font_size_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_middle, text=f"Deghat Kalame ({0}-{100}):").pack(side="left", padx=(10, 2), pady=5)
        self.word_confidence_entry = Entry(self.control_frame_middle, textvariable=self.word_confidence_threshold_var, width=5)
        self.word_confidence_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_middle, text="OCR PSM Mode:").pack(side="left", padx=(10,2), pady=5)
        self.psm_menu = OptionMenu(self.control_frame_middle, self.selected_psm_config_str, self.selected_psm_config_str.get(), *self.psm_options_ui_map.keys())
        self.psm_menu.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_bottom, text="Gaussian Kernel (odd):").pack(side="left", padx=(0, 2), pady=5)
        self.gaussian_kernel_entry = Entry(self.control_frame_bottom, textvariable=self.gaussian_kernel_var, width=5)
        self.gaussian_kernel_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_bottom, text="Adapt. Block (odd, >1):").pack(side="left", padx=(10, 2), pady=5)
        self.adaptive_block_entry = Entry(self.control_frame_bottom, textvariable=self.adaptive_block_size_var, width=5)
        self.adaptive_block_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_bottom, text="Adapt. C:").pack(side="left", padx=(10, 2), pady=5)
        self.adaptive_c_entry = Entry(self.control_frame_bottom, textvariable=self.adaptive_c_var, width=5)
        self.adaptive_c_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.control_frame_debug_views, text="Namayesh Marhale Pishpardazesh:").pack(side="left", padx=(0, 5), pady=5)
        self.show_original_button = Button(self.control_frame_debug_views, text="Asli (RGB)", command=self.show_original_image_debug)
        self.show_original_button.pack(side="left", padx=2, pady=5)
        self.show_grayscale_button = Button(self.control_frame_debug_views, text="Khakestari", command=self.show_grayscale_image_debug)
        self.show_grayscale_button.pack(side="left", padx=2, pady=5)
        self.show_blurred_button = Button(self.control_frame_debug_views, text="Blur Shodeh", command=self.show_blurred_image_debug)
        self.show_blurred_button.pack(side="left", padx=2, pady=5)
        self.show_binary_button = Button(self.control_frame_debug_views, text="Binary (Siah/Sefid)", command=self.show_binary_image_debug)
        self.show_binary_button.pack(side="left", padx=2, pady=5)
        self.show_final_annotated_button = Button(self.control_frame_debug_views, text="Nahayi (Ba Tarjomeh)", command=self.show_final_annotated_image_debug)
        self.show_final_annotated_button.pack(side="left", padx=2, pady=5)

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
        self.ocr_text_frame = ttk.LabelFrame(self.text_boxes_frame, text="Matn Shenasayi Shodeh", padding="5")
        self.ocr_text_frame.grid(row=0, column=0, sticky="nsew", pady=(0,2))
        self.ocr_text_widget = scrolledtext.ScrolledText(self.ocr_text_frame, wrap='word', height=10, width=30, font=("tahoma", 9))
        self.ocr_text_widget.pack(fill="both", expand=True)
        self.translated_text_frame = ttk.LabelFrame(self.text_boxes_frame, text="Matn Tarjome Shodeh", padding="5")
        self.translated_text_frame.grid(row=1, column=0, sticky="nsew", pady=(2,0))
        self.translated_text_widget = scrolledtext.ScrolledText(self.translated_text_frame, wrap='word', height=10, width=30, font=("tahoma", 9))
        self.translated_text_widget.pack(fill="both", expand=True)

        self.status_frame = ttk.Frame(master, padding="5")
        self.status_frame.pack(side="bottom", fill="x")
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=200, mode="indeterminate")
        self.status_label = Label(self.status_frame, text="Amadeh", fg="white", bg="gray25")
        self.status_label.pack(side="left", padx=10)


    def _display_cv_image_in_label(self, cv_img, conversion_code=None):
        if cv_img is None:
            messagebox.showinfo("Etela", "Tasviri baraye namayesh dar in marhale vojood nadarad. Lotfan avval 'Amal va Pardazesh' ra anjam dahid.")
            return
        try:
            if conversion_code is not None:
                pil_img = Image.fromarray(cv.cvtColor(cv_img, conversion_code))
            else:
                pil_img = Image.fromarray(cv_img)

            container_width = self.image_container.winfo_width()
            container_height = self.image_container.winfo_height()
            resized_pil_image = resize_pil_image_for_tk(pil_img, container_width, container_height)
            self.update_image_display(resized_pil_image)
        except Exception as e:
            print(f"Khata dar namayesh tasvir CV: {e}")
            messagebox.showerror("Khata", "Moshkeli dar tabdil ya namayesh tasvir pish amad.")

    def show_original_image_debug(self):
        if self.last_pil_original is None:
            messagebox.showinfo("Etela", "Lotfan avval yek tasvir entekhab konid va pardazesh konid.")
            return
        self.update_image_display(resize_pil_image_for_tk(self.last_pil_original, self.image_container.winfo_width(), self.image_container.winfo_height()))
        self.status_label.config(text="Namayesh: Tasvir Asli (RGB)")

    def show_grayscale_image_debug(self):
        self._display_cv_image_in_label(self.img_cv_grayscale_debug)
        if self.img_cv_grayscale_debug is not None: self.status_label.config(text="Namayesh: Tasvir Khakestari")

    def show_blurred_image_debug(self):
        self._display_cv_image_in_label(self.img_cv_blurred_debug)
        if self.img_cv_blurred_debug is not None: self.status_label.config(text="Namayesh: Tasvir Blur Shodeh")

    def show_binary_image_debug(self):
        self._display_cv_image_in_label(self.img_cv_binary_debug)
        if self.img_cv_binary_debug is not None: self.status_label.config(text="Namayesh: Tasvir Binary")

    def show_final_annotated_image_debug(self):
        if self._last_displayed_annotated_pil:
            self.update_image_display(resize_pil_image_for_tk(self._last_displayed_annotated_pil, self.image_container.winfo_width(), self.image_container.winfo_height()))
            self.status_label.config(text="Namayesh: Tasvir Nahayi (Ba Tarjomeh)")
        else:
            messagebox.showinfo("Etela", "Hanooz tasvir nahayi pardazesh nashode ast.")

    def apply_settings_and_process(self):
        if not self.current_image_path:
            messagebox.showwarning("Hoshdar", "Lotfan avval yek tasvir entekhab konid.")
            self.status_label.config(text="Amadeh")
            return

        self.status_label.config(text="Dar hale pardazesh ba tanzimat jadid...")
        if not self.progress_bar.winfo_ismapped(): self.progress_bar.pack(side="left", padx=5)
        self.progress_bar.start()
        self.img_cv_grayscale_debug = None
        self.img_cv_blurred_debug = None
        self.img_cv_binary_debug = None
        self._last_displayed_annotated_pil = None
        threading.Thread(target=self.process_image, args=(self.current_image_path,), daemon=True).start()

    def select_image(self):
        file_path = filedialog.askopenfilename(title="Entekhab Tasvir", filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.current_image_path = file_path
            try:
                self.last_pil_original, self.last_img_cv_original = self._load_images_from_path(file_path)
                self.last_df_ocr_processed = None
                self.last_render_segments = []
                self.ocr_text_widget.config(state='normal'); self.ocr_text_widget.delete('1.0', 'end'); self.ocr_text_widget.config(state='disabled')
                self.translated_text_widget.config(state='normal'); self.translated_text_widget.delete('1.0', 'end'); self.translated_text_widget.config(state='disabled')
                self.img_cv_grayscale_debug = None
                self.img_cv_blurred_debug = None
                self.img_cv_binary_debug = None
                self._last_displayed_annotated_pil = None
                self.status_label.config(text="Tasvir entekhab shod. Baraye pardazesh dokmeye 'Amal va Pardazesh' ra bezanid.")
                container_width = self.image_container.winfo_width()
                container_height = self.image_container.winfo_height()
                resized_pil_image = resize_pil_image_for_tk(self.last_pil_original, container_width, container_height)
                self.master.after(0, self.update_image_display, resized_pil_image)
            except Exception as e:
                print(f"Khata dar bargozari ya namayesh avaliye tasvir: {e}")
                messagebox.showerror("Khata", f"Moshkeli dar bargozari tasvir pish amad: {e}")
                self.current_image_path = None
                self.last_pil_original = None
                self.last_img_cv_original = None
                self.status_label.config(text="Khata dar bargozari tasvir.")
            finally:
                if self.progress_bar.winfo_ismapped(): self.progress_bar.stop(); self.progress_bar.pack_forget()

    def _load_current_font(self):
        try:
            font_size_str = self.font_size_var.get()
            if not font_size_str.isdigit(): raise ValueError("Andazeye font bayad adad bashad.")
            font_size = int(font_size_str)
            if not (MIN_FONT_SIZE <= font_size <= MAX_FONT_SIZE):
                font_size = GLOBAL_FONT_DEFAULT_SIZE
                self.font_size_var.set(str(GLOBAL_FONT_DEFAULT_SIZE))
            if FONT_PATH and global_font_instance_check:
                return ImageFont.truetype(FONT_PATH, font_size)
            return None
        except ValueError as ve:
            messagebox.showerror("Khataye Voroodi", str(ve))
            self.font_size_var.set(str(GLOBAL_FONT_DEFAULT_SIZE))
            if FONT_PATH and global_font_instance_check:
                try: return ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
                except Exception: pass
            return None
        except Exception: return None

    def _load_images_from_path(self, img_path):
        try:
            img_pil = Image.open(img_path)
            if img_pil.mode == 'RGBA' or img_pil.mode == 'P': img_pil = img_pil.convert('RGB')
            img_cv = cv.cvtColor(np.array(img_pil), cv.COLOR_RGB2BGR)
            if img_cv is None: raise ValueError("Tabdil tasvir PIL be OpenCV namovafagh bood.")
            return img_pil, img_cv
        except FileNotFoundError: raise ValueError(f"File tasvir '{img_path}' yaft nashod.")
        except Exception as e: raise ValueError(f"Khata dar bargozari tasvir '{img_path}': {e}")

    def process_image(self, img_path_should_be_self_current):
        try:
            if self.last_img_cv_original is None:
                self.master.after(0, lambda: messagebox.showerror("Khata", "Tasvir asli baraye pardazesh vojood nadarad."))
                return

            current_font_for_drawing = self._load_current_font()
            if current_font_for_drawing is None and global_font_instance_check :
                 current_font_for_drawing = ImageFont.truetype(FONT_PATH, GLOBAL_FONT_DEFAULT_SIZE)
            elif current_font_for_drawing is None:
                print("Hoshdar: Font baraye neveshtan rooye tasvir bargozari nashod.")

            try:
                g_kernel = int(self.gaussian_kernel_var.get())
                if g_kernel < 1 : g_kernel = 1
                elif g_kernel % 2 == 0: g_kernel +=1
            except ValueError:
                g_kernel = GAUSSIAN_BLUR_KERNEL_SIZE_DEFAULT
                self.master.after(0, lambda: self.gaussian_kernel_var.set(str(g_kernel)))

            try:
                a_block = int(self.adaptive_block_size_var.get())
                if a_block <= 1 : a_block = 3
                elif a_block % 2 == 0: a_block += 1
            except ValueError:
                a_block = ADAPTIVE_THRESHOLD_BLOCK_SIZE_DEFAULT
                self.master.after(0, lambda: self.adaptive_block_size_var.set(str(a_block)))

            try:
                a_c = int(self.adaptive_c_var.get())
            except ValueError:
                a_c = ADAPTIVE_THRESHOLD_C_DEFAULT
                self.master.after(0, lambda: self.adaptive_c_var.set(str(a_c)))

            try:
                word_confidence_threshold = int(self.word_confidence_threshold_var.get())
                if not (0 <= word_confidence_threshold <= 100):
                    raise ValueError("Deghat kalame bayad beyn 0 va 100 bashad.")
            except ValueError as ve:
                self.master.after(0, lambda: messagebox.showerror("Khataye Voroodi", str(ve)))
                word_confidence_threshold = WORD_CONFIDENCE_THRESHOLD_DEFAULT
                self.master.after(0, lambda: self.word_confidence_threshold_var.set(str(WORD_CONFIDENCE_THRESHOLD_DEFAULT)))

            selected_psm_key = self.selected_psm_config_str.get()
            current_psm_config = self.psm_options_ui_map.get(selected_psm_key, DEFAULT_OCR_PSM_CONFIG)

            img_cv_to_process = self.last_img_cv_original.copy()
            if len(img_cv_to_process.shape) == 3 and img_cv_to_process.shape[2] == 3:
                self._current_cv_grayscale = cv.cvtColor(img_cv_to_process, cv.COLOR_BGR2GRAY)
            else:
                self._current_cv_grayscale = img_cv_to_process.copy()
            self.img_cv_grayscale_debug = self._current_cv_grayscale.copy()
            self._current_cv_blurred = cv.GaussianBlur(self._current_cv_grayscale, (g_kernel, g_kernel), 0)
            self.img_cv_blurred_debug = self._current_cv_blurred.copy()
            self._current_cv_binary = cv.adaptiveThreshold(self._current_cv_blurred, 255,
                                                         cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                         cv.THRESH_BINARY_INV,
                                                         a_block, a_c)
            self.img_cv_binary_debug = self._current_cv_binary.copy()
            ocr_input_for_df = self._current_cv_binary

            df_ocr_processed = get_structured_ocr_data(ocr_input_for_df,
                                                       lang=DEFAULT_OCR_LANG,
                                                       psm_config=current_psm_config)

            ocr_display_text = extract_ocr_text_for_display(df_ocr_processed)
            self.master.after(0, self.update_ocr_text_widget, ocr_display_text)

            list_of_segments_for_rendering = []
            translated_output_for_widget = ocr_display_text

            should_translate = self.translate_checkbox_var.get() == "1"
            current_target_lang_code = self.language_options[self.selected_language_name.get()]
            selected_level_name = self.selected_draw_level_name.get()
            level_to_draw = self.draw_level_options.get(selected_level_name, 0)

            image_with_annotations_cv = self.last_img_cv_original.copy()


            if level_to_draw == 4: # حالت نمایش خط (با استفاده از ساختار خطوط Tesseract و اعمال دقت کلمه)
                temp_translated_list_for_textbox = []
                if df_ocr_processed is not None and not df_ocr_processed.empty:
                    # ابتدا تمام کلمات سطح 5 را استخراج می‌کنیم
                    df_all_words_level5 = df_ocr_processed[df_ocr_processed['level'] == 5].copy()
                    # سپس کلمات را بر اساس آستانه دقت فیلتر می‌کنیم
                    df_confident_words = df_all_words_level5[df_all_words_level5['conf'] > word_confidence_threshold].copy()

                    if not df_confident_words.empty:
                        # خطوط را از کلمات با دقت بالا گروه‌بندی می‌کنیم
                        grouped_lines_ocr = df_confident_words.groupby(
                            ['page_num', 'block_num', 'par_num', 'line_num'], sort=True
                        )
                        for _, line_words_df in grouped_lines_ocr:
                            current_line_words_sorted = line_words_df.sort_values(by='word_num')
                            if current_line_words_sorted.empty:
                                continue

                            min_x = int(current_line_words_sorted['left'].min())
                            min_y = int(current_line_words_sorted['top'].min())
                            max_x_coord = int((current_line_words_sorted['left'] + current_line_words_sorted['width']).max())
                            max_y_coord = int((current_line_words_sorted['top'] + current_line_words_sorted['height']).max())

                            if max_x_coord <= min_x or max_y_coord <= min_y: continue

                            current_rect = (min_x, min_y, max_x_coord - min_x, max_y_coord - min_y)
                            current_box_color = (34,139,34) # سبز برای خط
                            cv.rectangle(image_with_annotations_cv, (min_x, min_y), (max_x_coord, max_y_coord), current_box_color, 2)

                            line_text_original = " ".join(current_line_words_sorted['text'].astype(str).str.strip().tolist())
                            text_to_show_on_image = line_text_original
                            current_segment_for_textbox = line_text_original

                            if line_text_original.strip():
                                if should_translate and current_target_lang_code != 'en':
                                    translated_line = translate_en_to_fa_api(line_text_original, target_lang=current_target_lang_code)
                                    text_to_show_on_image = translated_line
                                    current_segment_for_textbox = translated_line

                                if current_font_for_drawing and text_to_show_on_image.strip():
                                    image_with_annotations_cv = draw_text_on_cv_image(
                                        image_with_annotations_cv, text_to_show_on_image,
                                        min_x, min_y, current_font_for_drawing
                                    )
                            list_of_segments_for_rendering.append({
                                'rect': current_rect, 'text_on_image': text_to_show_on_image,
                                'draw_text': True, 'color': current_box_color,
                                'base_x': min_x, 'base_y_box_top': min_y
                            })
                            temp_translated_list_for_textbox.append(current_segment_for_textbox)

                        if temp_translated_list_for_textbox :
                            translated_output_for_widget = "\n".join(temp_translated_list_for_textbox)
                        elif not temp_translated_list_for_textbox and should_translate and current_target_lang_code != 'en':
                             if ocr_display_text.strip():
                                 translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                             elif not translated_output_for_widget:
                                 translated_output_for_widget = "[Matni baraye tarjome yaft nashod]"
                    # اگر هیچ کلمه با دقتی یافت نشد، اما ترجمه فعال است
                    elif should_translate and current_target_lang_code != 'en':
                        if ocr_display_text.strip():
                            translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                        else:
                            translated_output_for_widget = "[Matni baraye tarjome yaft nashod]"
                # اگر اصلا OCR ای نبود ولی ترجمه فعال بود
                elif should_translate and current_target_lang_code != 'en':
                    if ocr_display_text.strip(): translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    elif not translated_output_for_widget: translated_output_for_widget = "[Matni baraye tarjome yaft nashod]"


            elif level_to_draw == 5: # حالت نمایش کلمه (دقت کلمه اینجا اعمال می‌شود)
                words_to_process = df_ocr_processed[(df_ocr_processed['level'] == 5) & (df_ocr_processed['conf'] > word_confidence_threshold)].copy()
                temp_textbox_lines_dict = {}
                current_box_color = (0,0,255) # آبی برای کلمه

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

            else: # سایر سطوح (پارگراف، بلوک) یا بدون کادر
                if level_to_draw > 0 and df_ocr_processed is not None and not df_ocr_processed.empty:
                    # برای سطوح پاراگراف و بلوک، دقت کلمه اعمال نمی‌کنیم، چون اینها ساختارهای بزرگتری هستند
                    elements_to_draw = df_ocr_processed[df_ocr_processed['level'] == level_to_draw]
                    color_map = {3: (255,165,0), 2: (128,0,128)} # نارنجی برای پاراگراف، بنفش برای بلوک
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
                if should_translate and current_target_lang_code != 'en' and translated_output_for_widget == ocr_display_text:
                    if ocr_display_text.strip(): translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                    else: translated_output_for_widget = "[Matni baraye tarjome vojud nadarad]"


            if translated_output_for_widget == ocr_display_text and should_translate and current_target_lang_code != 'en':
                 if ocr_display_text.strip():
                     translated_output_for_widget = translate_en_to_fa_api(ocr_display_text, target_lang=current_target_lang_code)
                 else:
                     translated_output_for_widget = "[Matni baraye tarjome nabood]"


            self.master.after(0, self.update_translated_text_widget, translated_output_for_widget.strip())
            final_image_to_show_pil = Image.fromarray(cv.cvtColor(image_with_annotations_cv, cv.COLOR_BGR2RGB))
            self._last_displayed_annotated_pil = final_image_to_show_pil.copy()
            container_width = self.image_container.winfo_width()
            container_height = self.image_container.winfo_height()
            resized_pil_image = resize_pil_image_for_tk(final_image_to_show_pil, container_width, container_height)
            self.master.after(0, self.update_image_display, resized_pil_image)
            self.last_df_ocr_processed = df_ocr_processed.copy() if df_ocr_processed is not None and not df_ocr_processed.empty else None
            self.last_render_segments = list_of_segments_for_rendering
            self.last_ocr_display_text = ocr_display_text
            self.last_translated_output_for_widget = translated_output_for_widget

        except ValueError as ve:
            print(f"ValueError dar process_image: {ve}")
            self.master.after(0, lambda: messagebox.showerror("Khataye Voroodi/Meghdar", f"{ve}"))
        except pytesseract.TesseractError as tess_err:
            print(f"TesseractError dar process_image: {tess_err}")
            self.master.after(0, lambda: messagebox.showerror("Khataye Tesseract", f"{tess_err}"))
        except Exception as e:
            print(f"Khataye Omoomi dar process_image: {e}")
            traceback.print_exc()
            self.master.after(0, lambda: messagebox.showerror("Khataye Kolli dar Pardazesh", f"Yek khataye pishbini nashode rokh dad: {e}"))
        finally:
            self.master.after(0, self.stop_loading_and_update_status)

    def update_image_display(self, img_pil):
        if img_pil is None:
            return
        try:
            self.translated_image_tk = ImageTk.PhotoImage(image=img_pil)
            self.image_label.config(image=self.translated_image_tk)
            self.image_label.image = self.translated_image_tk
        except Exception as e:
            print(f"Khata dar beresresani namayesh tasvir: {e}")
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
        if not self.current_image_path:
             self.status_label.config(text="Amadeh")
        elif self.img_cv_binary_debug is None:
            self.status_label.config(text="Tasvir entekhab shod. Baraye pardazesh dokmeye 'Amal va Pardazesh' ra bezanid.")
        else:
            self.status_label.config(text="Pardazesh tamam shod. Amadeh baraye namayesh marhale ya pardazesh mojadad.")


if __name__ == "__main__":
    root = Tk()
    app = OCRTranslatorApp(root)
    root.mainloop()