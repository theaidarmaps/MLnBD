import streamlit as st
import requests
from PIL import Image

st.title('Распознаватель напитков')

uploaded_file = st.file_uploader(
    'Выберите изображение',
    type=['jpg', 'jpeg']
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='Загружено', use_container_width=True)

    with st.spinner('Предсказываем...'):
        files = {
            'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
        }

        response = requests.post(
            'http://127.0.0.1:8000/predict',
            files=files
        )

    if response.status_code == 200:
        result = response.json()
        st.success(f"**Класс**: {result.get('class')}")
        st.info(f"**Уверенность**: {result.get('confidence'):.2%}")
    else:
        st.error(f'Ошибка {response.status_code}: {response.text}')