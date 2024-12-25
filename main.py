import numpy as np
import pandas as pd
import PIL as pl
import cv2 as cv
import pytesseract as ts

import os
from glob import glob
from tqdm import tqdm

import warnings

warnings.filterwarnings("ignore")

# Get all png images inside ./images directory
imgPaths = glob("./images/*.png")

# cleate or open `ourResult.text` file with append mode
file = open("ourResult.txt", "a")
file.writelines("\n===== start app ======\n")


for img in imgPaths:
    # prepare images
    img_pl = pl.Image.open(img)
    img_cv = cv.imread(img)

    # extract texts and put them in text file:
    text_pl = ts.image_to_string(img_pl)
    file.writelines("\n\n===== start file ======")
    file.writelines(f"\nfile: {img}   content:\n")
    file.writelines(text_pl)
    file.writelines("\n===== end file ======\n\n")

    # prepare data:
    # unreadable data:
    data = ts.image_to_data(img_pl)
    # readable data:
    dataList = list(map(lambda x: x.split("\t"), data.split("\n")))

    # make it readable
    df = pd.DataFrame(dataList[1:], columns=dataList[0])
    df.dropna(inplace=True)  # Drop empty values and rows

    image = img_cv.copy()
    level = "word"

    for l, x, y, w, h, c, t in df[
        ["level", "left", "top", "width", "height", "conf", "text"]
    ].values:
        # convert data (str to number)
        l = int(l)
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        c = float(c)

        if level == "page":
            if l == 1:
                cv.rectangle(
                    image,
                    (x, y),
                    (x + w, y + h),
                    (
                        0,
                        0,
                        0,
                    ),
                    2,
                )
            else:
                continue

        elif level == "block":
            if l == 2:
                cv.rectangle(
                    image,
                    (x, y),
                    (x + w, y + h),
                    (
                        255,
                        0,
                        0,
                    ),
                    1,
                )
            else:
                continue

        elif level == "paragraph":
            if l == 3:
                cv.rectangle(
                    image,
                    (x, y),
                    (x + w, y + h),
                    (
                        0,
                        255,
                        0,
                    ),
                    1,
                )
            else:
                continue

        elif level == "line":
            if l == 4:
                cv.rectangle(
                    image,
                    (x, y),
                    (x + w, y + h),
                    (
                        255,
                        0,
                        51,
                    ),
                    1,
                )
            else:
                continue

        elif level == "word":
            if l == 5:
                cv.rectangle(
                    image,
                    (x, y),
                    (x + w, y + h),
                    (
                        0,
                        0,
                        255,
                    ),
                    1,
                )
                cv.putText(
                    image,
                    t,
                    (x, y),
                    cv.FONT_HERSHEY_COMPLEX_SMALL,
                    1,
                    (255, 255, 255),
                    1,
                )
            else:
                continue

    cv.imshow("bounding box", image)
    cv.waitKey(0)
    cv.destroyAllWindows()
    cv.waitKey(1)

# close text file
file.writelines("\n===== end app ======\n")
file.close()
