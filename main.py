import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
<<<<<<< HEAD
from typing import Dict
=======
from typing import Dict, Optional
>>>>>>> c8bbe8e (Initial solar backend)

from io import BytesIO

import numpy as np
import cv2
from PIL import Image

import tensorflow as tf
import keras
from keras.preprocessing import image as keras_image
from ultralytics import YOLO

<<<<<<< HEAD
=======
# -----------------------------#
# CONFIG
# -----------------------------#

# Paths are relative to your backend project root
CNN_MODEL_PATH = "models/best_finetuned_model.h5"   # 3‑class CNN (Clean, Dust, Snow)
YOLO_DUST_CLEAN_PATH = "models/yolov8_best.pt"      # YOLO model 1 (Dust, Clean)
YOLO_SNOW_CLEAN_PATH = "models/best_snow_8.pt"      # YOLO model 2 (Snow, Clean)

IMG_SIZE_CNN = (224, 224)

# must match training order of your CNN
CNN_CLASSES = ["Clean", "Dust", "Snow"]

# YOLO class names in weights (lower‑case, edit if needed)
YOLO_DUST_CLEAN_CLASSES = {"clean", "dirty"}   # dust/clean model
YOLO_SNOW_CLEAN_CLASSES = {"clean", "snow"}    # snow/clean model

# which YOLO1 name represents dust
YOLO_DUST_CLASS_NAMES = {"dirty"}

# Minimum fraction of image area that must be covered by solar boxes
MIN_SOLAR_AREA_FRAC = 0.10  # 10 %

# -----------------------------#
# FASTAPI APP + CORS
# -----------------------------#

>>>>>>> c8bbe8e (Initial solar backend)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
<<<<<<< HEAD
    allow_origins=["*"],
=======
    allow_origins=["*"],  # later restrict to your Vercel domain
>>>>>>> c8bbe8e (Initial solar backend)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
=======
# -----------------------------#
# LOAD MODELS (once at startup)
# -----------------------------#

print("Loading CNN model...")
cnn_model = keras.models.load_model(CNN_MODEL_PATH, compile=False)
print("CNN model loaded.")

print("Loading YOLO dust/clean model...")
yolo_dust_clean = YOLO(YOLO_DUST_CLEAN_PATH)
print("YOLO dust/clean loaded.")

print("Loading YOLO snow/clean model...")
yolo_snow_clean = YOLO(YOLO_SNOW_CLEAN_PATH)
print("YOLO snow/clean loaded.")

# -----------------------------#
# UTILS (adapted from your Streamlit app)
# -----------------------------#

def classify_image_cnn_3class(pil_img: Image.Image):
    """3‑class CNN: returns (probs, predicted_label, confidence)."""
    img = pil_img.resize(IMG_SIZE_CNN)
    img_array = keras_image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    probs = cnn_model.predict(img_array, verbose=0)[0]  # shape (3,)
    idx = int(np.argmax(probs))
    label = CNN_CLASSES[idx]
    confidence = float(probs[idx])
    return probs, label, confidence


def run_yolo_and_filter(model, pil_img, allowed_classes_set, conf_thres):
    """Runs YOLO on pil_img and returns only boxes with allowed classes."""
    img_np = np.array(pil_img)
    results = model.predict(
        source=img_np,
        imgsz=640,
        conf=conf_thres,
        verbose=False,
        save=False,
        show=False,
    )
    r = results[0]
    names = model.names
    kept_boxes = []

    for box in r.boxes:
        cls_id = int(box.cls[0])
        cls_name = names[cls_id].lower()
        if cls_name in allowed_classes_set:
            kept_boxes.append((box, cls_name))

    return kept_boxes, img_np, names


def combined_inference(pil_img: Image.Image, conf_thres: float = 0.25):
    """
    Runs YOLO dust/clean and snow/clean + CNN classification.
    Returns:
      overlay_img (np.ndarray RGB) or None if no solar panel,
      stats dict with CNN + YOLO info.
    """
    # ---------- YOLO 1: Dust / Clean ----------
    boxes_dc, img_np, names_dc = run_yolo_and_filter(
        yolo_dust_clean, pil_img, YOLO_DUST_CLEAN_CLASSES, conf_thres
    )

    all_boxes = boxes_dc  # for area + counts

    # if YOLO1 found any dust, do NOT run YOLO2
    found_dust = any(cls_name in YOLO_DUST_CLASS_NAMES for _, cls_name in boxes_dc)

    boxes_sc = []

    # ---------- YOLO 2: Snow / Clean (only if no dust in YOLO1) ----------
    if not found_dust:
        boxes_sc, _, names_sc = run_yolo_and_filter(
            yolo_snow_clean, pil_img, YOLO_SNOW_CLEAN_CLASSES, conf_thres
        )
        all_boxes = boxes_dc + boxes_sc

    # If no solar‑panel classes detected at all -> not a solar image
    if len(all_boxes) == 0:
        return None, None

    # Extra gate: require enough total solar-panel area
    h_img, w_img, _ = img_np.shape
    img_area = h_img * w_img

    solar_area = 0
    for box, _cls_name in all_boxes:
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
        solar_area += max(0, x2 - x1) * max(0, y2 - y1)

    if solar_area < MIN_SOLAR_AREA_FRAC * img_area:
        return None, None

    # ---------- CNN 3‑class classification ----------
    probs, label_cnn, conf_cnn = classify_image_cnn_3class(pil_img)

    # YOLO summary counts
    counts = {}
    for _box, cls_name in all_boxes:
        counts[cls_name] = counts.get(cls_name, 0) + 1

    stats = {
        "cnn_probs": probs,
        "cnn_label": label_cnn,
        "cnn_conf": conf_cnn,
        "yolo_counts": counts,
        "yolo_used_snow_model": bool(boxes_sc),
    }

    return img_np, stats  # we don't return overlay image for API, only stats


# -----------------------------#
# RESPONSE MODEL
# -----------------------------#

>>>>>>> c8bbe8e (Initial solar backend)
class PredictionResponse(BaseModel):
    condition: str
    condition_confidence: float
    p_clean: float
    p_dust: float
    p_snow: float
    dust_level: str
    snow_level: str
    yolo_counts: Dict[str, int]
    yolo_used_snow_model: bool
    is_solar_panel: bool

<<<<<<< HEAD
@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/predict", response_model=PredictionResponse)
async def predict_dummy(
    file: UploadFile = File(...),
    conf_thres: float = 0.25,
):
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Just read the file so we exercise PIL, numpy, etc.
    contents = await file.read()
    _ = Image.open(BytesIO(contents)).convert("RGB")

    return PredictionResponse(
        condition="Clean",
        condition_confidence=1.0,
        p_clean=1.0,
        p_dust=0.0,
        p_snow=0.0,
        dust_level="Low Dust",
        snow_level="Low Snow",
        yolo_counts={},
        yolo_used_snow_model=False,
        is_solar_panel=False,
=======

# -----------------------------#
# API ENDPOINT
# -----------------------------#

def dust_level_from_prob(p_dust: float) -> str:
    if p_dust < 0.3:
        return "Low Dust"
    elif p_dust < 0.7:
        return "Medium Dust"
    else:
        return "Heavy Dust"


def snow_level_from_prob(p_snow: float) -> str:
    if p_snow < 0.3:
        return "Low Snow"
    elif p_snow < 0.7:
        return "Medium Snow"
    else:
        return "Heavy Snow"


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    file: UploadFile = File(...),
    conf_thres: float = 0.25,
):
    # Accept only images
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    try:
        contents = await file.read()
        pil_img = Image.open(BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image")

    img_np, stats = combined_inference(pil_img, conf_thres=conf_thres)

    # If no solar panel detected
    if img_np is None or stats is None:
        # still run CNN alone, so frontend can show something
        probs, label_cnn, conf_cnn = classify_image_cnn_3class(pil_img)
        p_clean, p_dust, p_snow = [float(p) for p in probs]

        return PredictionResponse(
            condition=label_cnn,
            condition_confidence=conf_cnn,
            p_clean=p_clean,
            p_dust=p_dust,
            p_snow=p_snow,
            dust_level=dust_level_from_prob(p_dust),
            snow_level=snow_level_from_prob(p_snow),
            yolo_counts={},
            yolo_used_snow_model=False,
            is_solar_panel=False,
        )

    # If solar panel detected + YOLO ran
    probs = stats["cnn_probs"]
    label_cnn = stats["cnn_label"]
    conf_cnn = stats["cnn_conf"]
    counts = stats["yolo_counts"]
    used_snow = stats["yolo_used_snow_model"]

    p_clean, p_dust, p_snow = [float(p) for p in probs]

    return PredictionResponse(
        condition=label_cnn,
        condition_confidence=conf_cnn,
        p_clean=p_clean,
        p_dust=p_dust,
        p_snow=p_snow,
        dust_level=dust_level_from_prob(p_dust),
        snow_level=snow_level_from_prob(p_snow),
        yolo_counts=counts,
        yolo_used_snow_model=used_snow,
        is_solar_panel=True,
>>>>>>> c8bbe8e (Initial solar backend)
    )
