import streamlit as st
import requests
import os

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

st.title('Предсказание цены')

tab1, tab2 = st.tabs(['Предсказание', 'Руководство'])

with tab1:
    city = st.selectbox('Город', ['İstanbul', 'Ankara', 'İzmir', 'Bursa'])
    district = st.text_input('Район', 'Kadıköy')
    neighborhood = st.text_input('Микрорайон', 'Moda')
    type_ = st.selectbox('Тип', ['Konut', 'İş Yeri', 'Arsa'])
    sub_type = st.selectbox('Подтип', ['Daire', 'Villa', 'Müstakil', 'Residence'])
    building_age = st.selectbox('Возраст', ['0-5', '5-10', '10-20', '20-30', '30+'])
    total_floor_count = st.slider('Этажей в доме', 1, 50, 5)
    floor_no = st.selectbox('Этаж', ['1', '2', '3', '4', '5', 'Giriş Kat', 'Çatı Katı'])
    room_count = st.select_slider('Комнат', options=[1, 2, 3, 4, 5, 6], value=2)
    size = st.slider('Площадь (м²)', 30, 200, 65, 5)
    heating_type = st.selectbox('Отопление', [
        'Kalorifer (Doğalgaz)', 'Kombi (Doğalgaz)', 'Merkezi Sistem', 'Yok'
    ])

    st.markdown("""
                ### Дополнительные параметры
                """)
    listing_type = st.selectbox('Тип сделки', ['Satılık', 'Kiralık'])
    tom = st.slider('Дней на рынке', 0, 365, 30)

    if st.button('Предсказать'):
        input_data = {
            'type': type_,
            'sub_type': sub_type,
            'listing_type': listing_type,
            'tom': float(tom),
            'building_age': building_age,
            'total_floor_count': total_floor_count,
            'floor_no': floor_no,
            'room_count': room_count,
            'size': float(size),
            'heating_type': heating_type,
            'city': city,
            'district': district,
            'neighborhood': neighborhood
        }
        url = "http://127.0.0.1:8000/predict"
        response = requests.post(url, json=input_data)
        result = response.json()

        if 'error' in result:
            st.error(f"Ошибка: {result['error']}")
        else:
            # Основная цена в рублях
            price_rub = result['price_prediction_rub']

            st.success(f"""
                                ## Предсказанная стоимость:
                                # **{price_rub:,.0f} RUB**
                                """)



    with tab2:
        tab2.subheader("Руководство пользователя")

        st.markdown(f"""
                    ### ⚠️ Для работы программы требуется запущенный API
                    """)

        st.markdown("""
        ### **Заполните параметры слева и нажмите кнопку "Рассчитать"**

        Модель учитывает:
        - Местоположение (город, район)
        - Характеристики объекта
        - Рыночные условия
        """)