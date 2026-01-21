import streamlit as st
import os


os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''


pg = st.navigation([st.Page('pages/main_page.py',title='Главная'),
                    st.Page('pages/help_page.py', title='Справка'),
                    st.Page('pages/all_movies_page.py', title='Список всех фильмов')])
pg.run()

#streamlit run web_app.py
