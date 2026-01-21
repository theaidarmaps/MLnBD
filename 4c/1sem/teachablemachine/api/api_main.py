import io
import os

import numpy as np
from PIL import Image, ImageOps
from fastapi import FastAPI, UploadFile, File, HTTPException
from keras.models import load_model

app = FastAPI()

MODEL_PATH = '../second/keras_Model.h5'
LABELS_PATH = '../second/labels.txt'

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f'Модель не найдена: {MODEL_PATH}')
if not os.path.exists(LABELS_PATH):
    raise FileNotFoundError(f'Метки не найдены: {LABELS_PATH}')

model = load_model(MODEL_PATH, compile=False)
with open(LABELS_PATH, 'r', encoding='utf-8') as f:
    class_names = [line.strip() for line in f.readlines()]

print(f'Модель загружена: {MODEL_PATH}')
print(f'Классы: {class_names}')

@app.post('/predict')
async def predict(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='Файл должен быть изображением')

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
        image_array = np.asarray(image)
        normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
        data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
        data[0] = normalized_image_array

        prediction = model.predict(data, verbose=0)
        index = int(np.argmax(prediction))
        confidence = float(prediction[0][index])
        class_name = class_names[index]

        probs = {class_names[i]: float(prediction[0][i]) for i in range(len(class_names))}

        return {
            'class': class_name,
            'confidence': confidence,
            'all_probabilities': probs,
            'message': f'Предсказано: {class_name} ({confidence:.3f})'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Ошибка обработки: {str(e)}')