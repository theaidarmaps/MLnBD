from fastapi import FastAPI
import pickle
from pydantic import BaseModel
import numpy as np
from sklearn.preprocessing import LabelEncoder
from typing import Optional

app = FastAPI()
TRY_TO_RUB_EXCHANGE_RATE = 3.0

with open('rf_model.pkl', 'rb') as f:
    bag_reg = pickle.load(f)

with open('label_encoders.pkl', 'rb') as f:
    all_encoders = pickle.load(f)

    encoders = {
        'type': all_encoders.get('type'),
        'sub_type': all_encoders.get('sub_type'),
        'listing_type': all_encoders.get('listing_type'),
        'building_age': all_encoders.get('building_age'),
        'floor_no': all_encoders.get('floor_no'),
        'heating_type': all_encoders.get('heating_type'),
        'city': all_encoders.get('city'),
        'district': all_encoders.get('district'),
        'neighborhood': all_encoders.get('neighborhood')
    }

def convert_to_rubles(try_amount: float) -> float:
    return try_amount * TRY_TO_RUB_EXCHANGE_RATE


def create_interaction_features(size: float, room_count: int, total_floor_count: int) -> dict:
    # 1. Площадь на комнату (важный признак!)
    if room_count > 0:
        size_per_room = size / room_count
    else:
        size_per_room = size

    # 2. Этажность в процентах (если указан этаж)
    floor_percentage = 0
    # Здесь нужно будет доработать, когда будем знать формат floor_no

    # 3. Логарифм площади (часто помогает моделям)
    log_size = np.log(size + 1)  # +1, чтобы избежать логарифма от 0

    return {
        'size_per_room': size_per_room,
        'log_size': log_size
    }


def encode_text_to_number(field_name: str, text_value: str):
    try:
        if field_name in encoders and encoders[field_name] is not None:
            encoder = encoders[field_name]

            if text_value in encoder.classes_:
                return float(encoder.transform([text_value])[0])
            else:
                if len(encoder.classes_) > 0:
                    return float(encoder.transform([encoder.classes_[0]])[0])
                return 0.0

        # Пробуем преобразовать в число
        try:
            return float(text_value)
        except:
            return 0.0

    except:
        return 0.0


class RegInput(BaseModel):
    type: str
    sub_type: str
    listing_type: str
    tom: float
    building_age: str
    total_floor_count: int
    floor_no: str
    room_count: int
    size: float
    heating_type: str
    city: str
    district: str
    neighborhood: str

    # Дополнительные (опциональные)
    price_per_m2: Optional[float] = None
    age_size_interact: Optional[float] = None


def convert_to_categories(df):
    categorical_cols = ['sub_type', 'heating_type', 'city', 'district', 'neighborhood']
    label_encoders = {}
    for col in categorical_cols:
        df[col] = df[col].replace('', np.nan).fillna('Unknown')
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le

@app.post('/predict')
def predict(features: RegInput):
    interaction_features = create_interaction_features(
        features.size,
        features.room_count,
        features.total_floor_count
    )

    # Вычисляем price_per_m2, если не предоставлен
    if features.price_per_m2 is None or features.price_per_m2 == 0:
        # Ориентировочная цена за м² для разных городов
        base_price_per_m2 = {
            'İstanbul': 50000,  # Более дорогой город
            'Ankara': 35000,
            'İzmir': 40000,
            'Bursa': 30000
        }

        price_per_m2_val = base_price_per_m2.get(features.city, 30000)
        # Корректируем на размер (обычно цена за м² падает с ростом площади)
        if features.size > 100:
            price_per_m2_val *= 0.9
        elif features.size < 50:
            price_per_m2_val *= 1.2
    else:
        price_per_m2_val = features.price_per_m2

    # Вычисляем age_size_interact, если не предоставлен
    if features.age_size_interact is None:
        # Взаимодействие возраста и площади: старые большие квартиры дешевле
        age_mapping = {'0-5': 1.2, '5-10': 1.1, '10-20': 1.0, '20-30': 0.9, '30+': 0.8}
        age_multiplier = age_mapping.get(features.building_age, 1.0)
        age_size_interact_val = features.size * age_multiplier
    else:
        age_size_interact_val = features.age_size_interact

    input_data = np.array([[
        # Основные признаки (1-13)
        encode_text_to_number('type', features.type),
        encode_text_to_number('sub_type', features.sub_type),
        encode_text_to_number('listing_type', features.listing_type),
        float(features.tom),
        encode_text_to_number('building_age', features.building_age),
        float(features.total_floor_count),
        encode_text_to_number('floor_no', features.floor_no),
        float(features.room_count),
        float(features.size),
        encode_text_to_number('heating_type', features.heating_type),
        encode_text_to_number('city', features.city),
        encode_text_to_number('district', features.district),
        encode_text_to_number('neighborhood', features.neighborhood),

        # Базовые вычисляемые признаки (14-15)
        float(price_per_m2_val),
        float(age_size_interact_val),

        # Дополнительные улучшенные признаки (16-17)
        float(interaction_features['size_per_room']),
        float(interaction_features['log_size'])
    ]])

    # Проверяем количество признаков
    if input_data.shape[1] < 15:
        return {'error': f'Недостаточно признаков: {input_data.shape[1]}'}

    # Используем только первые 15 признаков (как ожидает модель)
    if input_data.shape[1] > 15:
        input_data = input_data[:, :15]

    predicted_price_try = bag_reg.predict(input_data)[0]

    # Конвертируем в рубли
    predicted_price_rub = convert_to_rubles(predicted_price_try)

    # Делаем предсказание более чувствительным к изменению параметров

    # Базовый разброс зависит от города и типа
    city_multiplier = 1.0
    if features.city == "İstanbul":
        city_multiplier = 1.5  # Больше неопределенности в Стамбуле

    # Увеличиваем влияние площади на разброс
    size_impact = min(features.size / 100, 2.0)  # До 2x разброса

    base_std_dev = predicted_price_try * 0.10  # 10% базовый разброс
    adjusted_std_dev = base_std_dev * city_multiplier * size_impact

    # Конвертируем разброс в рубли
    confidence_interval_rub = convert_to_rubles(adjusted_std_dev)

    # Уверенность обратно пропорциональна разбросу
    confidence = max(0, 100 - (adjusted_std_dev / predicted_price_try * 100 * 1.5))

    return {
        # Цены в рублях
        'price_prediction_rub': round(predicted_price_rub, 2),
        'price_prediction_try': round(predicted_price_try, 2),
        'confidence_interval_rub': round(confidence_interval_rub, 2),
        'confidence_percentage': round(confidence, 2),

        # Дополнительная информация
        'currency': 'RUB',  # Основная валюта - рубли
        'exchange_rate': TRY_TO_RUB_EXCHANGE_RATE,
        'original_currency': 'TRY',

        # Вычисленные параметры
        'calculated_price_per_m2': round(price_per_m2_val, 2),
        'size_per_room': round(interaction_features['size_per_room'], 2),

        'features_used': input_data.shape[1]
    }