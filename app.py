import pandas as pd
import numpy as np
import streamlit as st
import math
import warnings
import io            # import io, re, unicodedata, requests, sys
from io import BytesIO
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import uploading_processing_data, create_dataframes, create_prod_all_table, search_all_neighbors, search_all_neighbors_bydate, compens_scenario_1, compens_scenario_2, graph_param1 # Импорт функций из файла .py    

def main():
    st.set_page_config(
        page_title = 'Расчет поскважинной компенсации',
        page_icon = '💧',
        layout='wide',
        initial_sidebar_state = 'auto',
        menu_items={
            'About': "# This is a header. This is an *extremely* cool app!"
            }
        )

    # 1. ФУНКЦИИ СОЗДАНИЯ КНОПКИ ВЫГРУЗКИ РЕЗУЛЬТАТОВ
    # - функция чтения данных примеров загрузки для моделей:
    @st.cache_data
    def read_examples():
        example_excel = pd.read_excel('data/upload_example/data_example.xlsx', skiprows=[1]).drop(columns='Unnamed: 0')
        return example_excel

    # - функция перекодировки эксель:
    def save_df_to_excel(df, ind=False):
        output = BytesIO()
        df.to_excel(output, index=ind, engine='openpyxl')
        output.seek(0)
        return output

    # - функция кнопок выгрузки примеров загрузки для моделей
    def upload_examples(excel_file): 
        st.write('**Скачать пример таблицы для подачи расчетов алгоритмов:**')
        col1, col2, col3, col4, col5, col6, col7, col8, col9,  = st.columns(9)
        button_excel = col1.download_button(
            label="Скачать таблицу в .xlsx",
            data=save_df_to_excel(excel_file),
            file_name='example_excel.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        )
        if button_excel:
            st.success("Таблица примера успешно сохранена в загрузки")


    # 2. ФУНКЦИЯ СОЗДАНИЯ КНОПОК ВЫГРУЗКИ РЕЗУЛЬТАТОВ РАСЧЕТА
    def upload_results(prod_all_df_table, inj_df_table): 
        st.write('**Скачать результаты расчета:**')
        col1, col2, col3, col4, col5, col6, col7, col8, col9,  = st.columns(9)
        button_excel_prod = col1.download_button(
            label="Таблица по нефтяным скважинам",
            data=save_df_to_excel(prod_all_df_table),
            file_name='prod_all_df.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        )
        button_excel_inj = col2.download_button(
            label="Таблица по нагнетательным скважинам",
            data=save_df_to_excel(inj_df_table),
            file_name='inj_df.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        )
        if button_excel_prod or button_excel_inj:
            st.success("Результат успешно сохранен в загрузках")

    # 3. ОСНОВНАЯ ФУНКЦИЯ ОБРАБОТКИ ДАННЫХ (ВЫНЕСЕНА ОТДЕЛЬНО)
    @st.cache_data(show_spinner="Идет расчет, немного подождите...")
    def process_full_data(uploaded_file, inj_radius):
        if '.xls' in uploaded_file.name or '.xlsx' in uploaded_file.name: 
            data = pd.read_excel(uploaded_file) #.drop(columns='Unnamed: 0')
        else:
            st.error('Неправильный формат данных, подгрузите данные в формате .xls, .xlsx')
            return None, None
        
        # ''' ВЫЗОВ ФУНКЦИЙ РАСЧЕТА ДАННЫХ '''
        # Вызов функции 1 - uploading_processing_data:
        data = uploading_processing_data(data)
        # Вызов функции 1.1 create_dataframes():
        tables_create_dataframes = create_dataframes(data)
        prod_df = tables_create_dataframes[0]
        prod_wells_df = tables_create_dataframes[1]
        inj_df = tables_create_dataframes[2]
        inj_wells_df = tables_create_dataframes[3]
        zak_no_prod_well_radius = tables_create_dataframes[4]
        if prod_df is not None:
            st.markdown("**Загруженные данные**")
            st.dataframe(data.head(10))
            st.write(f"Строк загруженных данных (после первичной обработки) - {data.shape}")
            st.markdown("**Таблица добычи по нефтяным скважинам**")
            st.dataframe(prod_df.head(10))
            st.write(f"Строк в сформированной таблице добычи нефтяным скважинам - {prod_df.shape}")
        # Вызов функции 2 - create_prod_all_table():
        prod_all_df = create_prod_all_table(prod_df)
        # Вызов функции 3 - search_all_neighbors():
        inj_df = search_all_neighbors(inj_df, inj_wells_df, prod_wells_df, inj_radius)
        # Вызов функции 4 - search_all_neighbors_bydate():
        inj_df = search_all_neighbors_bydate(inj_df, prod_all_df)
        # Вызов функции 5 - compens_scenario_1():
        prod_all_df = compens_scenario_1(prod_all_df, inj_df)
        # Вызов функции 6 - compens_scenario_2():
        result_compens_scenario_2 = compens_scenario_2(prod_all_df, inj_df, zak_no_prod_well_radius)
        prod_all_df = result_compens_scenario_2[0]
        zak_no_prod_well_radius = result_compens_scenario_2[1]
        return prod_all_df, inj_df, zak_no_prod_well_radius
    




    #   -----------------------------------------------------------------------------------------------------------
    # '''ИНТЕРФЕЙС ПРОГРАММЫ'''
    st.markdown(f'''
    ### 💧 Расчет поскважинной компенсации отбора жидкости закачкой по нефтяным добывающим скважинам
    ---
    **🎯 Цель:**  
    Расчет поскважинной компенсации отбора жидкости закачкой по нефтяным скважинам по историческим данным МЭР  

    **📋 Алгоритм использования сервиса:**  
    1. **Скачать пример шаблона** исходных данных  
    2. **Сформировать собственные данные** под формат исходных  
    3. **Подгрузить Ваши данные** в окно подгрузки  
    4. **Подождать несколько минут** для расчета данных:  
        **📊 Расчет компенсации по сценарию 1** - закачка с нагнетательных скважин распространяется в очаге с выбранным радиусом на нефтяные добывающие скважины, в зависимости от текущей добычи жидкости в месяце  
        > 💡 **Пример:** всего закачка в очаге радиусом 700 метров 50 м³, всего добыча в этом очаге 100 м³. Исходя из этого скважина которая добыла в месяце 30 м³ получит закачки 15 м³ жидкости, а скважина, которая добыла 10 м³ получит закачки 5 м³  
        
        **📊 Расчет компенсации по сценарию 2** - закачка от нагнетательной скважины в очаге на дату распределяется на скважины пропорционально некомпенсированной накопленной добыче жидкости  
        > 💡 **Принцип:** прямо пропорционально, когда недокомпенсация по очагу с выбранным радиусом и обратно пропорционально, когда перекомпенсация
    5. **Проанализировать поскважинные графики** добычи и влияемой закачки на добывающую скважину по добывающим скважинам  
    6. **Скачать результат** для анализа в табличном виде
    ''')

    # Вызов ФУНКЦИИ 2 (кнопка с выгрузкой примера подгрузки данных) 
    example_excel = read_examples()
    upload_examples(example_excel)

    # Выбор радиуса влияния нагнетательных скважин:
    st.markdown("**Выбор радиуса влияния нагнетательных скважин**")
    st.session_state.inj_radius = st.slider(
        "Радиус влияния нагнетательных скважин (метры)",
        min_value=50,
        max_value=1500,
        value=700,  # значение по умолчанию
        step=50,
        help="Радиус в метрах, в пределах которого нагнетательные скважины влияют на добывающие"
    )
    st.write(f"Выбранный радиус - {st.session_state.inj_radius}")

    # Подгрузка пользовательских данных:
    uploaded_file = st.file_uploader(
        label='**Загрузите данные для расчета**', 
        accept_multiple_files=False
        ) 
    
    if uploaded_file is not None:
        # Вызов ФУНКЦИИ 1 (основная обработка данных)
        prod_all_df, inj_df, zak_no_prod_well_radius = process_full_data(uploaded_file, st.session_state.inj_radius)
        if prod_all_df is not None:
            # Вывод показателей, правильности распределения закачки: (они есть в конце функции 6)
            st.markdown(f"""
            **ПРОВЕРКА РАСЧЕТА КОМПЕНСАЦИИ ПО СЦЕНАРИЮ 2**  
            Cумма закачки по всем нагнетательным скважинам (даже которые перешли из добывающих в нагнетательные) - {inj_df.drop_duplicates(subset=['RESERVOIR_number', 'WELLID'], keep='last')['CUM_DOWNLOAD_WATER_M3'].sum()}  
            Сумма закачки, которая ПОПАЛА в добывающие скважины - {round(prod_all_df['zakachka_M3_sc2'].sum(), 1)}  
            Сумма закачки, которая НЕ ПОПАЛА в добывающие скважины - {zak_no_prod_well_radius['DOWNLOAD_WATER_M3'].sum()}  
            Сумма закачки, которая ПОПАЛА и НЕ ПОПАЛА в добывающие скважины - {round(zak_no_prod_well_radius['DOWNLOAD_WATER_M3'].sum() + prod_all_df['zakachka_M3_sc2'].sum(), 1)}  
            """)
            st.success("Расчет завершен! Теперь вы можете выбирать скважины для анализа.")

            # Вызов ФУНКЦИИ 2 (кнопки с выгрузкой prod_all_df, inj_df):
            upload_results(prod_all_df, inj_df)
            
            # selectbox с номером скважины (для графика и данных)
            wellid = st.selectbox("Выберите скважину для анализа", prod_all_df['WELLID'].unique())

            # Вывод показатели на последнюю дату по скважине в st.markdown()
            prod_all_df_wellid = prod_all_df[(prod_all_df['WELLID'] == wellid)]
            st.markdown(f"""
            **Последняя фактическая дата добычи скважины:** {prod_all_df_wellid[(prod_all_df_wellid['база/продление'] == 'база')]['DATE_PROD'].max()}  
            **Расчет показателей на дату:** {prod_all_df_wellid['DATE_PROD'].iloc[-1]}  
            **Накопленная добыча жидкости, м3:** {prod_all_df_wellid['CUM_FLUID_T'].iloc[-1]}  
            **Накопленная добыча нефти, м3:** {prod_all_df_wellid['CUM_OIL_T'].iloc[-1]}  
            **Обводненность, д.е.:** {round(prod_all_df_wellid['WCT'].iloc[-1], 3)}  
            **Компенсация по сценарию 1, %:** {prod_all_df_wellid['COMPENS_cum_percent_sc1'].iloc[-1]}  
            **Компенсация по сценарию 2, %:** {prod_all_df_wellid['COMPENS_cum_percent_sc2'].iloc[-1]}  
            """)

            # Вызов функции 7 - graph_param1():
            if not prod_all_df_wellid.empty:
                graph_param1(prod_all_df_wellid)
            else:
                st.warning("Нет данных для выбранной скважины")

    else:
        st.info("Загрузите файл в формате .xls, .xlsx")
    

if __name__ == '__main__':
    main()

