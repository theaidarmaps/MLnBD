from fastapi import FastAPI
import pickle
from pydantic import BaseModel
import string
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import  sklearn
import pymorphy3


app = FastAPI()

with open('model_rf.pkl', 'rb') as file:
    model = pickle.load(file)
with open('updated_vectorizer.pkl', 'rb') as file:
    vectorizer = pickle.load(file)


def fun_punctuation_text(text):
    text = text.lower()
    text = ''.join([ch for ch in text if ch not in string.punctuation])
    text = ''.join([i if not i.isdigit() else '' for i in text])
    text = ''.join([i if i.isalpha() else ' ' for i in text])
    text = re.sub(r'\s+', ' ', text, flags=re.I)
    text = re.sub('[a-z]', '', text, flags=re.I)
    st = '❯\xa0'
    text = ''.join([ch if ch not in st else '' for ch in text])
    return text


def fun_lemmatizing_text(text):
    tokens = word_tokenize (text)
    res = list()
    for word in tokens:
        p = pymorphy3. MorphAnalyzer(lang='ru').parse(word) [0]
        res.append(p.normal_form)
    text = ' '.join(res)
    return text


def fun_tokenize (text):
    # nltk.download('stopwords')
    russian_stopwords = stopwords.words('russian')
    russian_stopwords.extend(['т.д.', 'т', 'д', 'это', 'который', 'свой', 'своём', 'всем', 'всё', 'её', 'оба', 'ещё'])
    t = word_tokenize (text)
    tokens=[token for token in t if token not in russian_stopwords]
    text = ' '.join(tokens)
    return text


def fun_pred_text(text):
    text = fun_punctuation_text(text)
    text = fun_lemmatizing_text(text)
    text = fun_tokenize (text)
    return text


def predict_cluster(text, threshold=0.1):
    text_vectorized = vectorizer.transform([fun_pred_text(text)])
    probabilities = model.predict_proba(text_vectorized)[0]
    prediction = model.predict(text_vectorized)[0]
    max_prob = max(probabilities)
    selected_clusters = [
        f'{i}' for i, prob in enumerate(probabilities)
        if max_prob - prob <= 0
    ]
    rez1 = f"{' или '.join(selected_clusters)}"
    rez2 = f"Вероятности по кластерам: {probabilities}"
    return rez1, rez2


# Модель для входных данных
class Item(BaseModel):
    text: str


# метод для подключения к интерфейсу
@app.post("/predict")
def post_pred_text(item: Item):
    return {'cluster': predict_cluster (item.text)}

#uvicorn main:app --reload