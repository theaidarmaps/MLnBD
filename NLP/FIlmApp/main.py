from fastapi import FastAPI
import pickle
from pydantic import BaseModel
import pandas as pd
import numpy as np
import string
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pymorphy3

app = FastAPI()
with open('film_model.pkl', 'rb') as file:
    model = pickle.load(file)

with open('film_vectorizer.pkl', 'rb') as file:
    vectorizer = pickle.load(file)


def remove_english_words(text):
    # Удаляет слова, состоящие только из английских букв (включая сокращения)
    return re.sub(r'\b[a-zA-Z]+\b', '', text)


def remove_punctuation(text):
    return "".join([ch if ch not in string.punctuation else ' ' for ch in text])


def remove_numbers(text):
    return ''.join([i if not i.isdigit() else ' ' for i in text])


def remove_multiple_spaces(text):
    return re.sub(r'\s+', ' ', text, flags=re.I)


def fun_prepare(text):
    return remove_english_words(remove_multiple_spaces(remove_numbers(remove_punctuation(text.lower()))))


def fun_punctuation_text(text):
    text = text.lower()
    text = ''.join([ch for ch in text if ch not in string.punctuation])
    text = ''.join([i if not i.isdigit() else '' for i in text])
    text = ''.join([i if i.isalpha() else ' ' for i in text])
    text = re.sub(r'\s+', ' ', text, flags=re.I)
    text = re.sub('[a-z]', '', text, flags=re.I)
    st = '❯\xa0'
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
    nltk.download('stopwords')
    russian_stopwords = nltk.corpus.stopwords.words('russian')
    russian_stopwords.extend(
        [['т.д.', 'т', 'д', 'это','который','с','своём','всем','наш', 'свой', 'фильм']])
    t = word_tokenize(text)
    tokens = [token for token in t if token not in russian_stopwords]
    text = " ".join(tokens)
    return text


def fun_pred_text(text):
    text = fun_prepare(text)
    text = fun_punctuation_text(text)
    text = fun_tokenize(text)
    text = fun_lemmatizing_text(text)
    text = fun_tokenize(text)
    return text


def predict_cluster(text, threshold=0.1):
    text_vectorized = vectorizer.transform([fun_pred_text(text)])
    probabilities = model.predict_proba(text_vectorized)[0]
    prediction = model.predict(text_vectorized)[0]
    mapping = {
        0: "история, год, хороший, реальный, рассказывать, стать, американский, реальный история, время, человек",
        1: "война",
        2: "история, год, стать, хороший, реальный, жизнь, рассказывать, реальный история, работать, зритель",
        3: "дело, убийство, друг, человек, расследование, местный, решать, женщина, полицейский, расследование дело",
        4: "жизнь, работа, стать, ребёнок, депрессия, отношение, деньга, семья, помогать, однако"
    }
    max_prob = max(probabilities)
    selected_clusters = [
        mapping[i] for i, prob in enumerate(probabilities)
        if max_prob - prob <= 0
    ]
    rez1 = f"{' или '.join(selected_clusters)}"
    rez2 = f"Вероятности по кластерам: {probabilities}"
    return rez1, rez2


class Item(BaseModel):
    text: str


@app.post("/predict")
def post_pred_text(item: Item):
    return {'cluster': predict_cluster(item.text)}

# uvicorn api:app --reload
# streamlit run app.py