from fastapi import FastAPI
import pickle
from pydantic import BaseModel
import numpy as np
import string
import re
import nltk
from nltk.tokenize import word_tokenize
import pymorphy3

app = FastAPI()

with open('model_rf.pkl', 'rb') as f:
    model = pickle.load(f)

with open('updated_vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)



def fun_punctuation_text(text):
    text = text.lower()
    text = ''.join([ch for ch in text if ch not in string. punctuation])
    text = ''.join([i if not i.isdigit() else '' for i in text])
    text = ''.join([i if i. isalpha() else ' ' for i in text])
    text = re. sub(r'\s+', ' ', text, flags=re. I)
    text = re.sub(' [a-z] ', '', text, flags=re.I)
    st = '>\xa0'
    text = ''.join([ch if ch not in st else ' ' for ch in text])
    return text

def fun_lemmatizing_text(text):
    tokens = word_tokenize(text)
    res = list()
    for word in tokens:
        p = pymorphy3.MorphAnalyzer(lang='ru').parse(word)[0]
        res.append(p.normal_form)
    text = " ".join(res)
    return text

def fun_tokenize(text):
    russian_stopwords = nltk.corpus.stopwords.words("russian")
    russian_stopwords.extend(['и', 'в', 'во', 'не', 'что', 'как', 'а', 'он', 'она', 'они', 'это', 'то'])
    t = word_tokenize(text)
    tokens = [token for token in t if token not in russian_stopwords]
    text = " ".join(tokens)
    return text

def fun_pred_text(text):
    text = fun_punctuation_text(text)
    text = fun_lemmatizing_text(text)
    text = fun_tokenize(text)
    return text

def predict_cluster(text):
    text_vectorized = vectorizer.transform([fun_pred_text(text)])
    text_vectorized = text_vectorized[:, :model.n_features_in_]
    text_vectorized = text_vectorized[:, :model.n_features_in_]
    prediction = model.predict(text_vectorized)
    probabilities = model.predict_proba(text_vectorized)
    rez1 = f"Номер кластера: {prediction[0]}"
    rez2 = f"Вероятности: {probabilities[0]}"
    mapping = {0: 'Благоустройство', 1: 'Водоотведение', 2: 'Водоснабжение', 3: 'Кровля', 4: 'Нарушение порядка пользования общим имуществом', 5: 'Нарушение правил пользования общим имуществом', 6: 'Незаконная информационная и (или) рекламная конструкция', 7: 'Незаконная реализация товаров с торгового оборудования (прилавок, ящик, с земли)', 8: 'Повреждения или неисправность элементов уличной инфраструктуры', 9: 'Подвалы', 10: 'Санитарное состояние', 11: 'Содержание МКД', 12: 'Состояние рекламных или информационных конструкций', 13: 'Фасад', 14: 'Центральное отопление'}
    selected_cluster = mapping[prediction[0]]
    return selected_cluster, rez1, rez2


class Item(BaseModel):
    text: str

@app.post("/predict")
def post_pred_text(item: Item):
    return {'cluster': predict_cluster(item.text)}