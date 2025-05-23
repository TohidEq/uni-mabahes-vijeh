# drawing_utils.py
import cv2 as cv
import numpy as np
from PIL import Image as pl_image, ImageDraw, ImageFont # برای جلوگیری از تداخل نام

def draw_text_on_cv_image(cv_image_input, text_to_write,
                           base_x, base_y_of_box_top,
                           font_object,
                           text_color=(250,250,250), outline_color=(0,0,0),
                           padding_above_box=3):
    """متن را با فونت و حاشیه روی تصویر OpenCV می‌نویسد."""
    if not text_to_write or font_object is None:
        return cv_image_input

    try:
        # تبدیل تصویر OpenCV به PIL برای نوشتن متن
        # ابتدا چک می‌کنیم آیا تصویر قبلا BGR بوده یا GRAY (از پیش‌پردازش)
        if len(cv_image_input.shape) == 2: # اگر GRAY است
            pil_img_for_text_draw = pl_image.fromarray(cv_image_input).convert("RGB")
        elif len(cv_image_input.shape) == 3 and cv_image_input.shape[2] == 3: # اگر BGR است
            pil_img_for_text_draw = pl_image.fromarray(cv.cvtColor(cv_image_input, cv.COLOR_BGR2RGB))
        else:
            print(f"هشدار: فرمت تصویر ورودی به draw_text_on_cv_image نامشخص است: {cv_image_input.shape}")
            return cv_image_input


        draw_on_pil = ImageDraw.Draw(pil_img_for_text_draw)

        try:
            text_bbox = draw_on_pil.textbbox((0,0), text_to_write, font=font_object)
            text_height = text_bbox[3] - text_bbox[1] # textbbox [left, top, right, bottom]
        except AttributeError: # Fallback for older Pillow
            text_size = draw_on_pil.textsize(text_to_write, font=font_object) # (width, height)
            text_height = text_size[1]

        text_x_position = base_x
        text_y_position = base_y_of_box_top - text_height - padding_above_box

        if text_y_position < 0:
            text_y_position = base_y_of_box_top + padding_above_box

        outline_thickness = max(1, font_object.size // 18) + 1 # کمی ضخیم‌تر
        for dx_o in range(-outline_thickness, outline_thickness + 1):
            for dy_o in range(-outline_thickness, outline_thickness + 1):
                if abs(dx_o) + abs(dy_o) > 0 and abs(dx_o) + abs(dy_o) <= outline_thickness : # بهبود ظاهر حاشیه
                    draw_on_pil.text((text_x_position + dx_o, text_y_position + dy_o),
                                     text_to_write, font=font_object, fill=outline_color)
        draw_on_pil.text((text_x_position, text_y_position), text_to_write,
                         font=font_object, fill=text_color)

        return cv.cvtColor(np.array(pil_img_for_text_draw), cv.COLOR_RGB2BGR)
    except Exception as draw_err:
        print(f"خطا در نوشتن متن '{text_to_write[:20]}...' روی تصویر (drawing_utils): {draw_err}")
        return cv_image_input


def resize_pil_image_for_tk(pil_img, container_width, container_height):
    """تصویر PIL را برای نمایش در ابعاد مشخص شده تغییر اندازه می‌دهد."""
    if pil_img is None: return None
    try:
        img_copy = pil_img.copy()
        # اگر ابعاد کانتینر هنوز خیلی کوچک است (قبل از رندر کامل UI)
        if container_width < 50: container_width = 300
        if container_height < 50: container_height = 300

        if img_copy.width > container_width or img_copy.height > container_height:
            img_copy.thumbnail((container_width, container_height), pl_image.Resampling.LANCZOS)
        return img_copy
    except Exception as e:
        print(f"خطا در تغییر اندازه تصویر (drawing_utils): {e}")
        return pil_img # در صورت خطا، تصویر اصلی را برگردان







