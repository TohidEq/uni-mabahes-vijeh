# Text detection

- Tohid Eghdami, Mabahes Vijeh, 25 December 2024

## 1: Install dependencies

In my OS(Manjaro) we can simply run:

```bash
# to install numpy, pandas, scipy, matplotlib, pytesseract, jupyter-notebook and opencv:
yay -S python-numpy python-pandas python-scipy python-matplotlib python-pytesseract jupyter-notebook python-opencv
# to install tesseract and tesseract-data-eng:
sudo pacman -S tesseract tesseract-data-eng
```

## 2: Create project

Create a new folder that named `myApp` and go inside it:

```bash
mkdir myApp
cd myApp
```

## 3: Open jupyter-notebook

After navigate to your project folder, run `jupyter-notebook` and your browser will open a local web app like this (you can change your theme by selecting `Settings > Theme > JupyterLab Dark`):

![jupyter-notebook page](./readme-assets/images/2024-12-25-012619_894x375_scrot.png)

## 4: Check dependencies

After running jupyter-notebook, in a new `python 3(ipykernel)` run:

```python
import numpy as np
import pandas as pd
import PIL as pl
import cv2 as cv
import pytesseract as ts
```

No errors means everything is ok.

## 5: Collect images

Create new folder `mkdir images` in your root project directory.

Search `templates business cards` and in `images` tab, download a few images in your `yourproject/images/` directory

Just like this:

```txt
.
├── images
│   ├── img-01.png
│   ├── img-02.png
│   ├── img-03.png
│   └── img-04.png
```

### Get all images in python

Import new stuff to get all images and ignore possible warnings:

```python
import os
from glob import glob
from tqdm import tqdm

import warnings
warnings.filterwarnings('ignore')
```

Create a new var and use `glob()` to get all images in `./images` directory:

```python
imgPaths = glob('./images/*.png')
```

To see result u can just add a new cell and write your var name like this:
![all image import result](./readme-assets/images/all-img-import-result.png)

## 6

#
