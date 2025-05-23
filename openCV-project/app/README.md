## 1. اندازه کرنل گوسین بلور 🌫️

**توضیح**:
فیلتر GaussianBlur با میانگین‌گیری از پیکسل‌های همسایه، تصویر را نرم و نویزهای ریز را کاهش می‌دهد. اندازه کرنل محدوده این همسایگی را مشخص می‌کند.

**تأثیرات**:

- ✅ **مقادیر کم (1-3)**:
  - حذف نویز جزئی
  - مناسب برای تصاویر با کیفیت بالا
- 🔹 **مقادیر متوسط (3-7)**:
  - تعادل مناسب بین نرم‌سازی و حفظ جزئیات
  - پیشنهاد اصلی برای اکثر تصاویر
- ❌ **مقادیر زیاد (15+)**:
  - تار شدن بیش از حد تصویر
  - از بین رفتن حروف نازک

**پیشنهادات**:

- همیشه از اعداد فرد استفاده کنید (3, 5, 7)
- مقدار پیش‌فرض: 5
- برای تصاویر پرنویز: 5 یا 7
- برای تصاویر تمیز: 3

## 2. اندازه بلاک برای آستانه‌گیری تطبیقی ⬜⬛

**توضیح**:
این پارامتر اندازه ناحیه محاسبه آستانه محلی را برای تبدیل تصویر به سیاه و سفید تعیین می‌کند.

**راهنمای انتخاب**:

```python
if حروف_کوچک:
    block_size = 11-21
elif حروف_بزرگ:
    block_size = 31-51
else:
    block_size = 21  # مقدار پیش‌فرض
```

**هشدارها**:

- ⚠️ مقادیر خیلی کوچک: حساسیت به نویز افزایش می‌یابد
- ⚠️ مقادیر خیلی بزرگ: از دست دادن جزئیات متن

**مقادیر پیشنهادی**:

- حداقل: 11
- پیش‌فرض: 21
- حروف بزرگ: 31-51

## 3. مقدار ثابت C در آستانه‌گیری تطبیقی ➕➖

**توضیح**:
این مقدار برای تنظیم دقیق آستانه از میانگین محلی کم می‌شود.

**راهکار تنظیم**:

- اگر متن نازک/کمرنگ است → کاهش C
  (حتی مقادیر منفی)
- اگر پس‌زمینه مزاحم است → افزایش C

**جدول راهنما**:

| وضعیت تصویر    | مقدار پیشنهادی C | تأثیر                 |
| -------------- | ---------------- | --------------------- |
| متن ضعیف       | -2 تا 2          | بهبود تشخیص حروف نازک |
| حالت استاندارد | 2-5              | تعادل مناسب           |
| نویز زیاد      | 5-10             | کاهش اثر پس‌زمینه     |

**نکته نهایی**:
مقدار پیش‌فرض: 4 (برای شروع مناسب است)
