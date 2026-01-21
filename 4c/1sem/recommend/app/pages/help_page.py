import streamlit as st

st.title('Команды')

st.markdown('''
            - **Топ 10 фильмов**: Выводит топ-10 фильмов по взвешенной оценке.
            - **Рекомендация по жанру**: Выберите жанр из комбо-бокса (параметр: genre). Доступные жанры: Action, Adventure, Animation, Comedy, Crime, Documentary, Drama, Family, Fantasy, History, Horror, Music, Mystery, Romance, Science Fiction, Thriller, War, Western.
            - **Рекомендация по контенту**: Введите название фильма (параметр: title). Рекомендации на основе контента (TF-IDF и NearestNeighbors).
            - **Коллаборативная фильтрация**: Введите номер пользователя (параметр: user_id).
            ''')