import numpy as np
import pandas as pd
import PIL as pl
from PIL import ImageFont, ImageDraw, Image, ImageTk # ImageTk baraye namayesh tasvir dar Tkinter
import cv2 as cv
import pytesseract as ts
import requests
import json # baraye pardazesh pasokh JSON

import os
from glob import glob
import threading # baraye ejraye amaliyate toolani dar pas zamine
from tkinter import Tk, Label, Button, filedialog, PhotoImage, Toplevel, StringVar, OptionMenu, Entry, Checkbutton, scrolledtext
from tkinter import ttk # baraye ProgressBar (loading)
from tkinter import messagebox # baraye namayesh peygham khatar

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
        'tl': target_lang, # zaban maghsad motaghayyer ast
        'dt': 't',
        'q': text
    }
    try:
        response = requests.get(base_url, params=params, timeout=10) # Timeout afzayesh yaft
        response.raise_for_status()
        translation_data = response.json()
        if translation_data and len(translation_data) > 0 and len(translation_data[0]) > 0 and len(translation_data[0][0]) > 0:
            return translation_data[0][0][0]
        else:
            return text # bazgasht be matn asli dar صورت عدم استخراج ترجمه
    except requests.exceptions.RequestException as e:
        print(f"Translation API error for '{text}': {e}")
        return text # بازگشت به matn asli dar صورت khataye API
# --- End of translation function ---

# Define the font path (updated with your username)
# Motmaen bashid in masir daghigh va sahih ast
fontPath = "/home/tohid-eq/Desktop/vazirmatn/fonts/ttf/Vazirmatn-Light.ttf"
try:
    global_font_default_size = 28 # Default size
    global_font = ImageFont.truetype(fontPath, global_font_default_size)
except IOError:
    print(f"Error: Could not load font from {fontPath}. Please check the path.")
    global_font = None # Handle case where font is not loaded

class OCRTranslatorApp:
    def __init__(self, master):
        self.master = master
        master.title("OCR Text Translator")
        master.geometry("1200x750") # Andazeh panjere ro kami bozorgtar kardam

        self.current_image_path = None
        self.translated_image_tk = None

        # Variables for UI controls
        self.selected_language_name = StringVar(master)
        self.selected_language_name.set("Farsi (Persian)") # Pishfarz Farsi
        self.language_options = {
            "Farsi (Persian)": "fa",
            "Arabi (Arabic)": "ar",
            "Faransavi (French)": "fr",
            "Espaniyayi (Spanish)": "es",
            "Almani (German)": "de",
            "Chini (Chinese)": "zh-CN",
            "Rusi (Russian)": "ru",
            "Engilisi (English)": "en" # Ezafe kardane Engilisi baraye halate bedone tarjome
        }

        self.translate_checkbox_var = StringVar(master, value="1") # 1 means checked (translate)
        self.translate_sentence_var = StringVar(master, value="0") # 0 means unchecked (word by word)
        self.font_size_var = StringVar(master, value="28") # Default font size

        # --- Control Frame ---
        self.control_frame = ttk.Frame(master, padding="10")
        self.control_frame.pack(side="top", fill="x")

        # Select Image Button
        self.select_button = Button(self.control_frame, text="Entekhab Tasvir", command=self.select_image)
        self.select_button.pack(side="left", padx=5, pady=5)

        # Language Selection
        ttk.Label(self.control_frame, text="Zaban Tarjomeh:").pack(side="left", padx=(10, 2), pady=5)
        self.language_menu = OptionMenu(self.control_frame, self.selected_language_name, *self.language_options.keys())
        self.language_menu.pack(side="left", padx=5, pady=5)
        self.selected_language_name.trace_add("write", self.on_setting_change)

        # Translate Checkbox (Tarjome Kon)
        self.translate_checkbox = Checkbutton(self.control_frame, text="Tarjome Kon", variable=self.translate_checkbox_var, onvalue="1", offvalue="0", command=self.on_setting_change)
        self.translate_checkbox.pack(side="left", padx=10, pady=5)

        # Translate Sentence by Sentence Checkbox (Tarjome Jomle be Jomle)
        self.translate_sentence_checkbox = Checkbutton(self.control_frame, text="Tarjome Jomle be Jomle",
                                                       variable=self.translate_sentence_var, onvalue="1", offvalue="0",
                                                       command=self.on_setting_change)
        self.translate_sentence_checkbox.pack(side="left", padx=10, pady=5)

        # Font Size Input
        ttk.Label(self.control_frame, text="Font Size (10-60):").pack(side="left", padx=(10, 2), pady=5)
        self.font_size_entry = Entry(self.control_frame, textvariable=self.font_size_var, width=5)
        self.font_size_entry.pack(side="left", padx=5, pady=5)
        self.font_size_entry.bind("<Return>", self.on_setting_change) # Update on Enter key
        self.font_size_entry.bind("<FocusOut>", self.on_setting_change) # Update when focus leaves

        # Exit Button
        self.exit_button = Button(self.control_frame, text="Khorooj", command=master.quit)
        self.exit_button.pack(side="right", padx=5, pady=5)

        # --- Main Content Frame ---
        self.main_content_frame = ttk.Frame(master, padding="10")
        self.main_content_frame.pack(side="top", fill="both", expand=True)

        # Left side: Image Display
        self.image_label = Label(self.main_content_frame, bd=2, relief="groove")
        self.image_label.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Right side: Text Boxes Frame
        self.text_boxes_frame = ttk.Frame(self.main_content_frame, padding="5")
        self.text_boxes_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Original Text Box
        self.ocr_text_frame = ttk.LabelFrame(self.text_boxes_frame, text="Matn Shenasayi Shode", padding="5")
        self.ocr_text_frame.pack(side="top", fill="both", expand=True, pady=5)
        self.ocr_text_widget = scrolledtext.ScrolledText(self.ocr_text_frame, wrap='word', height=10, width=40)
        self.ocr_text_widget.pack(fill="both", expand=True)

        # Translated Text Box
        self.translated_text_frame = ttk.LabelFrame(self.text_boxes_frame, text="Matn Tarjome Shode", padding="5")
        self.translated_text_frame.pack(side="bottom", fill="both", expand=True, pady=5)
        self.translated_text_widget = scrolledtext.ScrolledText(self.translated_text_frame, wrap='word', height=10, width=40)
        self.translated_text_widget.pack(fill="both", expand=True)


        # --- Status Bar (bottom) ---
        self.status_frame = ttk.Frame(master, padding="5")
        self.status_frame.pack(side="bottom", fill="x")

        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=200, mode="indeterminate")
        self.progress_bar.pack(side="left", padx=5)

        self.status_label = Label(self.status_frame, text="Amadeh", fg="blue")
        self.status_label.pack(side="left", padx=10)

    def on_setting_change(self, *args):
        if self.current_image_path:
            self.status_label.config(text="Dar hale taghir tanzimat va pardazesh mojadad...")
            self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()
            threading.Thread(target=self.process_image, args=(self.current_image_path,), daemon=True).start()
        else:
            self.status_label.config(text="Amadeh")


    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Entekhab Tasvir",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
        )
        if file_path:
            self.current_image_path = file_path
            self.status_label.config(text="Dar hale pardazesh o tarjomeh ...")
            self.progress_bar.pack(side="left", padx=5)
            self.progress_bar.start()

            threading.Thread(target=self.process_image, args=(file_path,), daemon=True).start()

    def process_image(self, img_path):
        try:
            # Get current settings
            try:
                font_size = int(self.font_size_var.get())
                if not (10 <= font_size <= 60):
                    raise ValueError("Font size bayad bein 10 ta 60 bashe.")
            except ValueError as e:
                messagebox.showwarning("Khataye Voroodi", f"Khataye font size: {e}\n\nFont size pishfarz estefadeh shod.")
                font_size = global_font_default_size # Fallback to default
                self.font_size_var.set(str(global_font_default_size)) # Update UI with default

            if global_font: # Reload font with new size
                current_font = ImageFont.truetype(fontPath, font_size)
            else:
                current_font = None


            img_pl = pl.Image.open(img_path)
            img_cv = cv.imread(img_path)
            if img_cv is None:
                raise ValueError("Tasvir ba OpenCV khoondeh nashod. Masir ya kharabi file ro check konid.")

            data = ts.image_to_data(img_pl)
            dataList = list(map(lambda x: x.split("\t"), data.split("\n")))
            df = pd.DataFrame(dataList[1:], columns=dataList[0])
            df.dropna(inplace=True)
            df['conf'] = pd.to_numeric(df['conf'], errors='coerce')
            df = df[df['conf'] > 30] # Filter kardan kalemat ba etminan pain (ekhtiyari)

            processed_image = img_cv.copy()

            current_target_lang_code = self.language_options[self.selected_language_name.get()]
            should_translate = self.translate_checkbox_var.get() == "1"
            is_sentence_translation = self.translate_sentence_var.get() == "1" # New variable

            # Prepare OCR text for the text box (Original)
            ocr_full_text = ""
            for _, row in df.iterrows():
                level = int(row['level'])
                text = str(row['text']).strip()
                if level == 5 and text: # Check for words
                    ocr_full_text += text + " "
                elif level == 4: # End of line
                    ocr_full_text += "\n"
                elif level == 3: # End of paragraph
                    ocr_full_text += "\n\n"
            self.master.after(0, self.update_ocr_text_widget, ocr_full_text)

            # Prepare Translated text for its text box
            translated_full_text = ""

            # --- Logic for Word vs. Line/Sentence Translation ---
            if is_sentence_translation: # Translate line by line
                lines_df = df[df['level'] == 4].copy()

                for _, line_row in lines_df.iterrows():
                    line_text_original = ""
                    words_in_line_df = df[(df['page_num'] == line_row['page_num']) &
                                           (df['block_num'] == line_row['block_num']) &
                                           (df['par_num'] == line_row['par_num']) &
                                           (df['line_num'] == line_row['line_num']) &
                                           (df['level'] == 5)]

                    if not words_in_line_df.empty:
                        line_text_original = " ".join(words_in_line_df['text'].dropna().tolist())

                    line_x = int(line_row['left'])
                    line_y = int(line_row['top'])
                    line_w = int(line_row['width'])
                    line_h = int(line_row['height'])

                    cv.rectangle(
                        processed_image,
                        (line_x, line_y),
                        (line_x + line_w, line_y + line_h),
                        (255, 165, 0), # Orange for line bounding box
                        1,
                    )

                    text_to_display_on_image = line_text_original
                    translated_segment = line_text_original # default for translated_full_text

                    if should_translate and current_target_lang_code != 'en':
                        translated_segment = translate_en_to_fa_api(line_text_original, target_lang=current_target_lang_code)
                        text_to_display_on_image = translated_segment

                    translated_full_text += translated_segment + "\n"

                    if current_font:
                        pil_img = Image.fromarray(cv.cvtColor(processed_image, cv.COLOR_BGR2RGB))
                        draw = ImageDraw.Draw(pil_img)

                        bbox = draw.textbbox((0, 0), text_to_display_on_image, font=current_font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]

                        text_y_position = line_y - text_height - 5
                        if text_y_position < 0:
                            text_y_position = line_y

                        outline_thickness = 2
                        for dx in range(-outline_thickness, outline_thickness + 1):
                            for dy in range(-outline_thickness, outline_thickness + 1):
                                if dx != 0 or dy != 0:
                                    draw.text((line_x + dx, text_y_position + dy), text_to_display_on_image, font=current_font, fill=(0, 0, 0))
                        draw.text((line_x, text_y_position), text_to_display_on_image, font=current_font, fill=(250, 250, 250))

                        processed_image = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)
            else: # Word by Word Translation
                for l, x, y, w, h, c, t in df[
                    ["level", "left", "top", "width", "height", "conf", "text"]
                ].values:
                    l = int(l)
                    x = int(x)
                    y = int(y)
                    w = int(w)
                    h = int(h)

                    if l == 5 and str(t).strip() != "":
                        cv.rectangle(
                            processed_image,
                            (x, y),
                            (x + w, y + h),
                            (0, 0, 255), # Blue for word bounding box
                            1,
                        )

                        text_to_display_on_image = t
                        translated_segment = t # default for translated_full_text

                        if should_translate and current_target_lang_code != 'en':
                            translated_segment = translate_en_to_fa_api(t, target_lang=current_target_lang_code)
                            text_to_display_on_image = translated_segment

                        translated_full_text += translated_segment + " "
                        if l == 4: # End of line (assuming word level 5 also provides line info)
                            translated_full_text += "\n"


                        if current_font:
                            pil_img = Image.fromarray(cv.cvtColor(processed_image, cv.COLOR_BGR2RGB))
                            draw = ImageDraw.Draw(pil_img)

                            bbox = draw.textbbox((0, 0), text_to_display_on_image, font=current_font)
                            text_width = bbox[2] - bbox[0]
                            text_height = bbox[3] - bbox[1]

                            text_y_position = y - text_height - 5
                            if text_y_position < 0:
                                text_y_position = y

                            outline_thickness = 2
                            for dx in range(-outline_thickness, outline_thickness + 1):
                                for dy in range(-outline_thickness, outline_thickness + 1):
                                    if dx != 0 or dy != 0:
                                        draw.text((x + dx, text_y_position + dy), text_to_display_on_image, font=current_font, fill=(0, 0, 0))
                            draw.text((x, text_y_position), text_to_display_on_image, font=current_font, fill=(250, 250, 250))

                            processed_image = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)
                        else:
                            cv.putText(processed_image, text_to_display_on_image, (x, y), cv.FONT_HERSHEY_COMPLEX, 0.8, (250, 250, 250), 1, cv.LINE_AA)
                            cv.putText(processed_image, text_to_display_on_image, (x, y), cv.FONT_HERSHEY_COMPLEX, 0.8, (0, 0, 0), 2, cv.LINE_AA)
            # --- End Logic ---

            # Update Translated text widget on the main thread
            self.master.after(0, self.update_translated_text_widget, translated_full_text)

            img_rgb = cv.cvtColor(processed_image, cv.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)

            # Resize image to fit label while maintaining aspect ratio
            label_width = self.image_label.winfo_width()
            label_height = self.image_label.winfo_height()

            # Fallback if label dimensions are not yet available (e.g., first run)
            if label_width < 10 or label_height < 10:
                label_width = self.main_content_frame.winfo_width() / 2 - 10
                label_height = self.main_content_frame.winfo_height() - 10
                if label_width < 10: label_width = 400
                if label_height < 10: label_height = 400


            if img_pil.width > label_width or img_pil.height > label_height:
                ratio_w = label_width / img_pil.width
                ratio_h = label_height / img_pil.height
                ratio = min(ratio_w, ratio_h)
                new_width = int(img_pil.width * ratio)
                new_height = int(img_pil.height * ratio)
                img_pil = img_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Update the image display on the main thread
            self.master.after(0, self.update_image_display, img_pil)

        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Khataye Pardazesh", f"Khataye dar pardazesh tasvir: {e}\n\nMotmaen shavid Tesseract nasb shode va masir font sahih ast."))
            print(f"Error during image processing: {e}")
        finally:
            self.master.after(0, self.stop_loading_and_update_status)

    def update_image_display(self, img_pil):
        self.translated_image_tk = ImageTk.PhotoImage(image=img_pil)
        self.image_label.config(image=self.translated_image_tk)
        self.image_label.image = self.translated_image_tk # Prevent garbage collection

    def update_ocr_text_widget(self, text):
        self.ocr_text_widget.delete('1.0', 'end') # Clear previous text
        self.ocr_text_widget.insert('1.0', text) # Insert new text

    def update_translated_text_widget(self, text):
        self.translated_text_widget.delete('1.0', 'end') # Clear previous text
        self.translated_text_widget.insert('1.0', text) # Insert new text

    def stop_loading_and_update_status(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.config(text="Amadeh")


# Main application setup
if __name__ == "__main__":
    root = Tk()
    app = OCRTranslatorApp(root)
    root.mainloop()