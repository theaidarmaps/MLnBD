import hashlib
import streamlit as st
import requests
import uuid

def get_title_list():
    try:
        response_ = requests.get('http://127.0.0.1:8000/all_movie_titles')
        if response_.status_code == 200:
            return response_.json()

        return []
    except requests.exceptions.RequestException:
        return []

if 'session_id' not in st.session_state:
    session_id = uuid.uuid4()
    digest = hashlib.sha1(session_id.bytes).digest()
    val = int.from_bytes(digest[:8], 'big')
    st.session_state['session_id'] = val


st.title('Рекомендательная система')

if st.button('Топ 10 фильмов'):
    response = requests.get('http://127.0.0.1:8000/top10')
    result = response.json()
    for i, movie in enumerate(result, 1):
        st.write(f"{i}. {movie}")

st.markdown('### Рекомендация по жанру')

selected_genre = st.selectbox('Выберите жанр', [
    'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama',
    'Family', 'Fantasy', 'History', 'Horror', 'Music', 'Mystery', 'Romance',
    'Science Fiction', 'Thriller', 'War', 'Western'
])
if st.button('Рекомендация по жанру'):
    response = requests.get(f'http://127.0.0.1:8000/recommend/genre?genre={selected_genre}')
    response.raise_for_status()
    result = response.json()
    for i, movie in enumerate(result, 1):
        st.write(f"{i}. {movie}")


st.markdown('### Рекомендация по контенту')

title_input = st.text_input('Введите название фильма')

if st.button('Рекомендация по контенту'):
    if title_input == '':
        st.warning('Введите название фильма')
    else:
        response = requests.get(f'http://127.0.0.1:8000/recommend/title?title={title_input}')
        response.raise_for_status()
        result = response.json()
        for i, movie in enumerate(result, 1):
            st.write(f"{i}. {movie}")

st.markdown('### Коллаборативная фильтрация')
id_input = st.text_input('Введите номер пользователя')

if st.button('Коллаборативная фильтрация'):
    if id_input == '':
        st.warning('Введите номер пользователя')
    else:
        response = requests.get(f'http://127.0.0.1:8000/recommend/collaborative?user_id={id_input}')
        response.raise_for_status()
        result = response.json()
        for i, movie in enumerate(result, 1):
            st.write(f"{i}. {movie}")

st.markdown('### Пользовательская рекомендация')

st.markdown('#### Поставить оценку')

titles_list = get_title_list()

if len(titles_list) == 0:
    st.warning('Не удалось загрузить список фильмов')

film_select = st.selectbox('Выберите фильм', titles_list)
if film_select:
    movie_id = requests.get(f'http://127.0.0.1:8000/get_movie_id?movie={film_select}')
    rating = st.number_input('Оценка (1-5)', min_value=1.0, max_value=5.0, step=1.0)
    if st.button('Сохранить оценку'):
        response = requests.post('http://127.0.0.1:8000/set_rating',
                                 params={'user_id': str(st.session_state['session_id']), 'movie_id': movie_id, 'rating': rating})
        if response.status_code == 200:
            st.success('Оценка сохранена')
        else:
            st.error(response.json()['detail'])

if st.button('Получить рекомендации'):
    response = requests.get('http://127.0.0.1:8000/recommend/personal', params={'user_id': str(st.session_state['session_id'])})
    if response.status_code == 200:
        recs = response.json()
        if recs:
            for rec in recs:
                st.write(rec)
        else:
            st.write('Нет рекомендаций')
    else:
        st.error(response.json())