import streamlit as st
import requests

st.title('Список всех фильмов')

response = requests.get(f'http://127.0.0.1:8000/all_movies')
if response.status_code == 200:
    movies_list = response.json()['movies']
    for movie in movies_list:
        st.write(f'{movie['original_title']} ({movie.get('release_date', 'N/A')})')
else:
    st.error('Ошибка при получении данных')