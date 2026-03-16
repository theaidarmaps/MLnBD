import nltk
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tensorflow as tf
import pickle
import numpy as np
from pymorphy3 import MorphAnalyzer
from nltk.corpus import stopwords
from keras.preprocessing.sequence import pad_sequences
from datetime import datetime
from psycopg2 import connect, Error

CONN_STRING = "user='postgres' password='1245780' dbname='postgres' host='localhost' port='5432'"
morph = MorphAnalyzer()
my_stop_words = ['такой', 'это', 'всё', 'весь']
stop_words = set(stopwords.words('russian'))
stop_words.update(my_stop_words)


def preprocessing(text):
    tokens = nltk.word_tokenize(text.lower())
    words = [t.replace('ё', 'е') for t in tokens if t.isalpha()]
    lemmas = [morph.parse(w)[0].normal_form for w in words]
    filtered_lemmas = [l for l in lemmas if l not in stop_words]
    return filtered_lemmas


def save_to_database(text, predictions, is_toxic):
    try:
        connection = connect(CONN_STRING)
        with connection.cursor() as cursor:
            tone = 'positive' if not is_toxic else 'negative'
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor.execute(
                'INSERT INTO python_task.comments (comment, date, tone) VALUES (%s, %s, %s)',
                (text, current_date, tone)
            )
            connection.commit()
            print(f'Запрос: {text[:30]}... -> {tone} успешно сохранен в БД')
            connection.close()
    except Error as e:
        print(e)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)

model = tf.keras.models.load_model('multi_toxic_ru.h5')

with open('tokenizer_multi.pkl', 'rb') as f:
    tokenizer = pickle.load(f)

target_names = ['normal', 'insult', 'threat', 'obscenity']


class TextRequest(BaseModel):
    text: str


@app.post('/predict')
async def predict(request: TextRequest):
    clean_text = preprocessing(request.text)

    seq = tokenizer.texts_to_sequences([clean_text])
    padded = pad_sequences(seq, maxlen=120, padding='post')

    pred = model.predict(padded, verbose=0)[0]

    results = {target_names[i]: float(pred[i]) for i in range(len(target_names))}
    is_toxic = any(results[label] > 0.5 for label in target_names if label != 'normal')

    save_to_database(request.text, results, is_toxic)

    return {
        'text': request.text,
        'predictions': results,
        'is_toxic': is_toxic
    }


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
