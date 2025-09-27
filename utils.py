import pandas as pd
import numpy as np
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st





# Функция 1
def uploading_processing_data(df:pd.DataFrame):
    '''
    Функция подгрузки исходных данных:
    вход - исходные данные (df)
    выход - преобразованные исходные данные (df)
    '''
    cols = {
        'FIELD': object
        , 'AREA': object
        , 'DEVELOPMENT_AREA': object
        , 'OBJECT_NAME': object
        , 'STRATUM': object
        , 'WELLID': 'Int64'
        , 'WELL_NAME': object
        , 'DATE_PROD': object
        , 'WORK_TIME': float
        , 'ACCUMULATION_TIME': float
        , 'WELL_CHARACTER': object
        , 'FLUID_T': float
        , 'OIL_T': float
        , 'GAS_M3': float
        , 'DOWNLOAD_WATER_M3': float
        , 'PRESSURE_STRATUM': float
        , 'PRESSURE_WELL_BOTTOM': float
        , 'WELLBOTTOM_X': float
        , 'WELLBOTTOM_Y': float
        }

    # отбор колонок из df:
    df = df[list(cols.keys())]
    print(f'df (исходный) - {df.shape}')

    # смена типов данных (дата):
    df = df.astype(cols)
    df['DATE_PROD'] = pd.to_datetime(df['DATE_PROD']).dt.date
    df['DATE_PROD'] = pd.to_datetime(df['DATE_PROD'], format='%Y-%m-%d')

    # сортировка данных:
    df.sort_values(by=['FIELD', 'AREA', 'DEVELOPMENT_AREA', 'OBJECT_NAME', 'STRATUM', 'WELLID', 'DATE_PROD'], inplace=True)

    # нумировка пластов:
    df['RESERVOIR_number'] = df.groupby(['FIELD', 'AREA', 'DEVELOPMENT_AREA', 'OBJECT_NAME', 'STRATUM']).ngroup() + 1
    df['RESERVOIR_number'] = df['RESERVOIR_number'].astype('Int64')

    # удаление дубликатов скважина на дату:
    df.drop_duplicates(subset = ['RESERVOIR_number', 'WELLID', 'DATE_PROD'], keep='first', inplace=True)
    print(f'df (после удаления после удаления дубликатов на скважину на дату) - {df.shape}')

    # фильтрация данных:
    df = df[(df['WORK_TIME'] > 0)]
    print(f"df (после удаления строк с WORK_TIME <= 0) - {df.shape}")

    df = df[(df['WELLBOTTOM_X'].notnull()) | (df['WELLBOTTOM_Y'].notnull()) ]
    print(f"df (после удаления строк с пустыми WELLBOTTOM_X ) - {df.shape}")

    df = df[~((df['WELL_CHARACTER'] == 'Нефтяная') & (df['FLUID_T'] == 0))]
    print(f"df (после удаления строк на нефтяных скважинах с нулевой FLUID_T) - {df.shape}")

    df = df[~((df['WELL_CHARACTER'] == 'Нагнетательная') & (df['DOWNLOAD_WATER_M3'] == 0))]
    print(f"df (после удаления строк на нагнетаетльных скважинах с нулевой DOWNLOAD_WATER_M3) - {df.shape}")

    # расчет фич по скважинам:
    df['WCT'] = (df['FLUID_T'] - df['OIL_T'])/df['FLUID_T']
    df['CUM_FLUID_T'] = df.groupby(['RESERVOIR_number', 'WELLID'])['FLUID_T'].cumsum()
    df['CUM_OIL_T'] = df.groupby(['RESERVOIR_number', 'WELLID'])['OIL_T'].cumsum()
    df['CUM_DOWNLOAD_WATER_M3'] = df.groupby(['RESERVOIR_number', 'WELLID'])['DOWNLOAD_WATER_M3'].cumsum()
    df['DATE_PROD_min'] = df.groupby(['RESERVOIR_number', 'WELLID'])['DATE_PROD'].transform('min')

    return df





# Функция 1.1.
def create_dataframes(init_table:pd.DataFrame):
    '''
    Функция, которая создает таблицы с нефтяными и нагнетательными скважинами:
     - на вход подается таблица ДОБЫЧИ и ЗАКАЧКИ по скважинам - data 
     - на выходе формируются таблицы - prod_df, prod_wells_df, inj_df, inj_wells_df
    '''
    drop_inj_cols = ['DOWNLOAD_WATER_M3', 'CUM_DOWNLOAD_WATER_M3']
    drop_prod_cols = ['FLUID_T', 'OIL_T', 'GAS_M3', 'WCT', 'CUM_FLUID_T', 'CUM_OIL_T']

    # создание таблиц с уникальными нефтяными скважинами, которые находятся или находились под добычей:
    prod_df = init_table[init_table['WELL_CHARACTER'] == 'Нефтяная']
    prod_df.drop(columns=drop_inj_cols, inplace=True)
    prod_wells_df = init_table[init_table['WELL_CHARACTER'] == 'Нефтяная'].drop_duplicates(subset=['WELLID'], keep='first')
    prod_wells_df.drop(columns=drop_inj_cols, inplace=True)
    print(f"Уникальных скважин, которые были под добычей - {prod_wells_df.shape[0]}\n  - строк добычи по ним - {prod_df.shape[0]}")

    # создание таблиц с уникальными нагнетательными скважинами, которые находятся или находились под закачкой:
    inj_df = init_table[init_table['WELL_CHARACTER'] == 'Нагнетательная']
    inj_df.drop(columns=drop_prod_cols, inplace=True)
    inj_wells_df = init_table[init_table['WELL_CHARACTER'] == 'Нагнетательная'].drop_duplicates(subset=['WELLID'], keep='first')
    inj_wells_df.drop(columns=drop_prod_cols, inplace=True)
    print(f"Уникальных скважин, которые были под нагнетанием - {inj_wells_df.shape[0]}\n  - строк закачки по ним - {inj_df.shape[0]}")

    # Таблица для сценария 2 расчета компенсации (сюда записывается нераспределенная закачка, когда скважин в округе нагнетательной нет)
    zak_no_prod_well_radius = pd.DataFrame(columns=['DATE_PROD', 'WELL_CHARACTER', 'WELLID', 'FIELD', 'AREA', 'STRATUM', 'DOWNLOAD_WATER_M3']) # таблица для записи значений, где нераспределяется закачка (скважин в радиусе нет)


    return prod_df, prod_wells_df, inj_df, inj_wells_df, zak_no_prod_well_radius





# Функция 2
def create_prod_all_table(prod_table:pd.DataFrame):
    '''
    Функция по продлению заполнению пропусков дат в таблице доычи и продлению таблицы добычи до максимальной даты:
     - на вход подается таблица ДОБЫЧИ - prod_df
     - на выходе получается продленная таблица добычи prod_all_df
    '''
    # создание столбца база/продление:
    prod_table['база/продление'] = 'база'

    # создание переменной с максимальной датой, создание колонки по списком от мин. даты работы скважины до макс. даты с шагом месяц. Развертка этой колонки вниз:
    max_date = prod_table['DATE_PROD'].max()
    min_data_wells = prod_table.groupby(['RESERVOIR_number', 'WELLID']).agg({'DATE_PROD':min}).reset_index()
    min_data_wells['Dates_Range'] = min_data_wells['DATE_PROD'].apply(lambda x: list(pd.date_range(x, max_date, freq='MS')))
    min_data_wells = min_data_wells.explode('Dates_Range')
    min_data_wells.drop(columns='DATE_PROD', inplace=True)
    min_data_wells.rename(columns={'Dates_Range':'DATE_PROD'}, inplace=True)
    print(f'min_data_wells (таблица с продленными датами) - {min_data_wells.shape}')

    # присоединение данных из таблицы data_all_prod (копия таблицы data):
    prod_table = min_data_wells.merge(prod_table, on=['RESERVOIR_number', 'WELLID', 'DATE_PROD'], how='left')
    prod_table.sort_values(by=['RESERVOIR_number', 'WELLID', 'DATE_PROD'], inplace=True)
    print(f'data_all_prod (после матчинга с min_data_wells) - {prod_table.shape} ')
    print(f'   - присоединилось значений из data_all_prod в min_data_wells - {prod_table[prod_table["WELL_CHARACTER"].notnull()].shape}')

    # заполнение "пропущенных" значений:
    for col in ['FIELD', 'AREA', 'DEVELOPMENT_AREA', 'OBJECT_NAME', 'STRATUM',  'WELL_NAME', 'DATE_PROD_min', 'WELL_CHARACTER', 'CUM_FLUID_T', 'CUM_OIL_T', 'WELLBOTTOM_X', 'WELLBOTTOM_Y']:
        prod_table[col] = prod_table.groupby(['RESERVOIR_number', 'WELLID'])[col].fillna(method='ffill')

    for col in ['WORK_TIME', 'ACCUMULATION_TIME', 'FLUID_T', 'OIL_T', 'GAS_M3', 'WCT']:
        prod_table[col] = prod_table[col].fillna(value=0)

    prod_table['база/продление'] = prod_table['база/продление'].fillna(value='продление')
    print(f'data_all_prod (после заполнения пустых значений) - {prod_table.shape} ')

    return prod_table





# Функция 3
def search_all_neighbors(inj_df_table:pd.DataFrame, inj_wells_df_table:pd.DataFrame, prod_wells_df_table:pd.DataFrame, inj_radius:int):
    '''
    Функция по нахождению списка всех имеющихся нефтяных соседей по плоскоти по каждой нагнетательной скважины
     - на вход inj_df (для merge в конце), inj_wells_df, prod_wells_df
     - на выходе inj_df со списком нефтяных скважин по плоскости
    '''
    # global inj_radius
    inj_wells_df_table[['list_all_prod_well_radius', 'count_all_prod_well_radius']] = None

    for index, row in inj_wells_df_table.iterrows(): # ограничить количество столбцов в inj_df_table для более быстрой иттерации
        list_prod_wells_radius = []
        inj_wellid = row['WELLID']
        inj_reservoir_number = row['RESERVOIR_number']
        X = row['WELLBOTTOM_X']
        Y = row['WELLBOTTOM_Y']
        prod_wells_df_table_rn = prod_wells_df_table[prod_wells_df_table['RESERVOIR_number'] == inj_reservoir_number] # Фильтруем таблицу добычи по пласту нагнетательной скважины (чтобы бы далее искать только соседей по ним)
        for index1, row1 in prod_wells_df_table_rn.iterrows():
            prod_wellid = row1['WELLID']
            X1 = row1['WELLBOTTOM_X']
            Y1 = row1['WELLBOTTOM_Y']
            distance = math.sqrt(((X - X1)**2 + (Y - Y1)**2))
            if distance < inj_radius:
                list_prod_wells_radius.append(prod_wellid)
        inj_wells_df_table.at[index, 'list_all_prod_well_radius'] = list_prod_wells_radius
        inj_wells_df_table.at[index, 'count_all_prod_well_radius'] = len(list_prod_wells_radius)

    inj_df_table = inj_df_table.merge(inj_wells_df_table[['WELLID', 'RESERVOIR_number', 'list_all_prod_well_radius', 'count_all_prod_well_radius']], on=['WELLID', 'RESERVOIR_number'], how='left')
    print(f"Уникальных скважин, которые были по нагнетанием (после присоединения) - {inj_wells_df_table.shape[0]}\n  - строк закачки по ним - {inj_df_table.shape[0]}")
    
    return inj_df_table





# Функция 4 
def search_all_neighbors_bydate(inj_df_table:pd.DataFrame, prod_all_df_table:pd.DataFrame):
    '''
    Функция по нахождению количества и списока нефтяных соседних скважин по каждой нагнетательной скважине на дату + расчет показателей по этим нефтяным скважинам
     - на вход inj_df (уже с предращитанными соседями), prod_all_df
     - на выходе inj_df 
    '''
    # создание пустых колонок для записи значений
    inj_df_table[['list_prod_well_radius', 'count_prod_well_radius', 'sum_production_fluid_radius', 'list_production_fluid_radius', 'sum_production_oil_radius', 'list_production_oil_radius', 'cumsum_production_fluid_radius', 'list_cum_production_fluid_radius', 'cumsum_production_oil_radius', 'list_cum_production_oil_radius']] = None

    # счетчик
    i = 0
        
    # цикл поиска и расчета
    for index, row in inj_df_table.iterrows():
        i = i + 1
        reservoir_number = row['RESERVOIR_number']
        date = row['DATE_PROD']
        list_all_prod_well_radius = row['list_all_prod_well_radius']
        prod_wells_radius_date_df = prod_all_df_table[
            (prod_all_df_table['RESERVOIR_number'] == reservoir_number) & 
            (prod_all_df_table['DATE_PROD'] == date) & 
            (prod_all_df_table['WELL_CHARACTER'] == 'Нефтяная') & 
            (prod_all_df_table['WELLID'].isin(list_all_prod_well_radius))
            ]

        inj_df_table.at[index, 'list_prod_well_radius'] = list(prod_wells_radius_date_df['WELLID'])  # Нефтяные скважины, которые уже вступили в добычу указанном радиусе
        inj_df_table.at[index, 'count_prod_well_radius'] = len(prod_wells_radius_date_df['WELLID'])  #  - их количество
        inj_df_table.at[index, 'sum_production_fluid_radius'] = prod_wells_radius_date_df['FLUID_T'].sum() #  список текущей добычи жидкости по этим нефтяным скважинам за месяц
        inj_df_table.at[index, 'list_production_fluid_radius'] = prod_wells_radius_date_df['FLUID_T'].to_list() #  сумма текущей добычи жидкости по этим нефтяным скважинам за месяц
        inj_df_table.at[index, 'sum_production_oil_radius'] = prod_wells_radius_date_df['OIL_T'].sum() #  список текущей добычи нефти по этим нефтяным скважинам за месяц
        inj_df_table.at[index, 'list_production_oil_radius'] = prod_wells_radius_date_df['OIL_T'].to_list() #  сумма текущей добычи нефти по этим нефтяным скважинам за месяц
        inj_df_table.at[index, 'cumsum_production_fluid_radius'] = prod_wells_radius_date_df['CUM_FLUID_T'].sum() #  сумма накопленной добычи жидкости по этим нефтяным скважинам на указанный месяц 
        inj_df_table.at[index, 'list_cum_production_fluid_radius'] = prod_wells_radius_date_df['CUM_FLUID_T'].to_list() #  список накопленной добычи жидкости по этим нефтяным скважинам на указанный месяц 
        inj_df_table.at[index, 'cumsum_production_oil_radius'] = cumsum_production_oil_radius = prod_wells_radius_date_df['CUM_OIL_T'].sum() #  сумма накопленной добычи нефти по этим нефтяным скважинам на указанный месяц 
        inj_df_table.at[index, 'list_cum_production_oil_radius'] = cumsum_production_oil_radius = prod_wells_radius_date_df['CUM_OIL_T'].to_list() #  список накопленной добычи нефти по этим нефтяным скважинам на указанный месяц 
        
        print(f"Количество всех нефтяных скважин в радиусе (в списке) - {len(list_all_prod_well_radius)}")
        print(f"  - работающих на дату - {prod_wells_radius_date_df.shape[0]}")
        print(f"  - итерация {i}\n")

    # смена типа данных в колонках
    for col in ['count_all_prod_well_radius', 'count_prod_well_radius']:
        inj_df_table[col] = inj_df_table[col].astype('int')

    for col in ['sum_production_fluid_radius', 'sum_production_oil_radius', 'cumsum_production_fluid_radius', 'cumsum_production_oil_radius']:
        inj_df_table[col] = inj_df_table[col].astype('float')

    # расчет текущей компенсацию в радиусе (очаге)
    inj_df_table['COMPENS_cur_radius'] = round((inj_df_table['DOWNLOAD_WATER_M3'] / inj_df_table['sum_production_fluid_radius'])*100, 1)

    # приравниваем компенсацию к нулю, там где количество скважин в радиусе равно 0, а закачка по нагнетательной скважине есть:
    inj_df_table.loc[(inj_df_table['count_prod_well_radius'] == 0), 'COMPENS_cur_radius'] = 0

    # ограничение компенсацию 3000%:
    inj_df_table.loc[inj_df_table['COMPENS_cur_radius']>3000, 'COMPENS_cur_radius'] = 3000

    return inj_df_table





# Функция 5
def compens_scenario_1(prod_all_df_table:pd.DataFrame, inj_df_table:pd.DataFrame):   
    '''
    Функция по расчету компенсации по сценарию 1:
     - при расчете компенсации, делаю допущение, что закачка распространяется в очаге на нефтяные скважины, в зависимости от текущей добычи жидкости в месяце
     - например, всего закачка в очаге радиусом 700 метров 50 м3, всего добыча в этом очаге 100 м3. Исходя из этого скважина которая добыла в месяце 30 м3 получит закачки 15 м3 жидкости, а скважина, которая добыла 10 м3 получит закачки  5 м3
     - на входе prod_all_df, inj_df
     - на входе prod_all_df
    '''
    # создание пустых колонок для записи значений
    prod_all_df_table[['InjWellid_affects', 'count_InjWellid_affects', 'InjWellid_DOWNLOAD_WATER_M3', 'COMPENS_cur_percent_list_sc1', 'COMPENS_cur_percent_sc1']] = None

    # счетчик
    i = 0

    # алгоритм: иттерируем таблицу добычи prod_all_df_table построчно через irerrows(), берем дату в строке и номер скважины, фильтруем таблицу inj_df_table по дате и номеру скважины и компенсацию записываем в список и присоедяем к новой колонке компенсации в prod_all_df_table
    for index, row in prod_all_df_table.iterrows():
        i = i + 1
        wellid = row['WELLID'] # Нефтяная скважина
        reservoir_number = row['RESERVOIR_number']
        date = row['DATE_PROD']
        
        # отбор нагнетательных скважин, которые влияют на иттерируемую нефтяную
        mask = (inj_df_table['RESERVOIR_number'] == reservoir_number) & (inj_df_table['DATE_PROD'] == date) & (inj_df_table['list_prod_well_radius'].apply(lambda lst: wellid in lst if isinstance(lst, list) else False))
        
        # расчет показателей и запись значений в таблицу prod_all_df_table
        prod_all_df_table.at[index, 'InjWellid_affects'] = inj_df_table[mask]['WELLID'].to_list()
        prod_all_df_table.at[index, 'count_InjWellid_affects'] = len(inj_df_table[mask]['WELLID'].to_list())
        prod_all_df_table.at[index, 'InjWellid_DOWNLOAD_WATER_M3'] = inj_df_table[mask]['DOWNLOAD_WATER_M3'].to_list()
        prod_all_df_table.at[index, 'COMPENS_cur_percent_list_sc1'] = inj_df_table[mask]['COMPENS_cur_radius'].to_list()
        prod_all_df_table.at[index, 'COMPENS_cur_percent_sc1'] = inj_df_table[mask]['COMPENS_cur_radius'].sum()
        print()
        print(date)
        print(wellid)
        print(i)

    # cмена типов данных в колонках
    prod_all_df_table['count_InjWellid_affects'] = prod_all_df_table['count_InjWellid_affects'].astype(int)
    prod_all_df_table['COMPENS_cur_percent_sc1'] = prod_all_df_table['COMPENS_cur_percent_sc1'].astype(float)

    # расчет компенсации (текущая) и накопленная времени по 1-ому сценарияю:
    prod_all_df_table['zakachka_M3_sc1'] = prod_all_df_table['FLUID_T'] * (prod_all_df_table['COMPENS_cur_percent_sc1'] / 100)
    prod_all_df_table['cum_zakachka_M3_sc1'] = prod_all_df_table.groupby(['WELLID', 'RESERVOIR_number'])['zakachka_M3_sc1'].cumsum().round(2)
    prod_all_df_table['COMPENS_cum_percent_sc1'] = round((prod_all_df_table['cum_zakachka_M3_sc1'] / prod_all_df_table['CUM_FLUID_T']) * 100, 1)  # Компенсация накопленная на дату

    return prod_all_df_table





# Функция 6
def compens_scenario_2(prod_all_df:pd.DataFrame, inj_df:pd.DataFrame, zak_no_prod_well_radius:pd.DataFrame):  # не стал менять название  prod_all_df -> prod_all_df_table и inj_df -> inj_df_table (много вычислений)
    '''
    Функция по расчету компенсации по сценарию 2:
     - закачка от нагнетательной скважины в очаге на дату распределяется на скважины в пропорционально некомпенсированной накопленной добыче жидкости
    Алгоритм: 
        - создаем колонки в таблице добычи по нефтяной скважине 
          - ['zakachka_M3_sc2'] - сколько воды от нагнетания попадает в нефтяную скважину за месяц
          - ['necompensirovannay_dobycha_T_sc2'] - изначально равняется накопленной добычи жидкости
        - итерируем дату (с начала момента вступления первой нагнетательной скважины)
        - итерируем на нагнетательные скважины на дату
        - смотрим некомпенсированную добычу по скважинам (общую)
            - если есть нефтяные скважины с нескомпенсированной добычей по скважинам, направляем закачку только на эти скважины (прямая пропорция, чем больше нескомпенсированная добыча, тем больше туда направляем закачку)
            - если нет скважин с нескомпенсированной добычей в очаге, распределяем обратной пропорцией между скважиными у которых перекомпенсированная добыча в очаге (обратная пропорция, чем больше пеескомпенсированная добыча, тем меньше туда направляем закачку)
            - если нет скважин в радиусе просто записываем данные по добыче в таблицу zak_no_prod_well_radius
        - закачку ['zakachka_M3_sc2'] на нефтяную скважину плюсуем вниз с текуще даты и до макисмальной (вниз вставляем) - итого получается на выходе накопленная закачка на нефтяной скважине
        - закачку ['zakachka_M3_sc2'] на нефтяную скважину минусуем вниз с текуще даты и до макисмальной (вниз вставляем) на в столбец ['necompensirovannay_dobycha_T_sc2']- итого получается сколько жидкости нескомпенсировано на дату по нефтяной скважине
     Вход и выход:
     - на входе prod_all_df, inj_df, zak_no_prod_well_radius
     - на входе prod_all_df

    '''
    # формирование списка дат sorted_dates для итераций
    min_date = pd.to_datetime(inj_df['DATE_PROD'].min())  # минимальная дата закачки
    max_date = pd.to_datetime(prod_all_df['DATE_PROD'].max())  # максимальная дата добычи 'prod_all_df['DATE_PROD'].max()' или '2020-01-01'
    dates_range = pd.date_range(start=min_date, end=max_date, freq='MS')
    sorted_dates = [date.strftime('%Y-%m-%d') for date in dates_range]

    # создание новых колонок в prod_all_df
    prod_all_df['zakachka_M3_sc2'] = 0
    prod_all_df['cum_zakachka_M3_sc2'] = 0
    prod_all_df['necompensirovannay_dobycha_T_sc2'] = prod_all_df['CUM_FLUID_T']

    # итерация уникальных даты по возрастанию в таблице закачки:
    for reservoir_number in prod_all_df['RESERVOIR_number'].unique():
        print(f"НОМЕР RESERVOIR_number - {reservoir_number}")
        for date in sorted_dates:
            inj = inj_df[(inj_df['RESERVOIR_number'] == reservoir_number) & (inj_df['DATE_PROD'] == date)] # DataFrame нагнетательных скважин на определенном пласте скважин на текущую дату
            prod_all = prod_all_df[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['DATE_PROD'] == date)] # DataFrame добывающих скважин на определенном пласте на текущую дату
            print(f"\n\n\n\n\n\n\n\n\nДата - {date}")
            print(f"Нагнетательных скважин на дату - {inj.shape[0]}")
            
            # итерируем DataFrame нагнетательных скважин (то есть итерируем очаги на дату на определенном пласте):
            for index, row in inj.iterrows():
                inj_well = row['WELLID'] # нагнетательная скважина
                inj_well_domnload_water = row['DOWNLOAD_WATER_M3'] # закачка на нагнетательной скважины на дату
                list_prod_wells_radius = row['list_prod_well_radius'] # список нефтяных скважин работающих (работавших ранее) на дату, на которые влияет эта нагнетательная скважина
                prod_wells_radius_df = prod_all[prod_all['WELLID'].isin(list_prod_wells_radius)] # DataFrame добычи по этим нефтянам скважинам на дату
                print(f" - нагнетательная скважина (WELLID) - {inj_well}")
                print(f" - закачка по нагнетательной скважине (WELLID) - {inj_well_domnload_water}")
                print(f" - количество доб. скважин, на которые влияет добывающая в этот месяц - {prod_wells_radius_df.shape[0]}")
                
                
                # 1 условие - берем в таблице prod_wells_radius_df только нефтяные скважины с нераспределенной добычей (['necompensirovannay_dobycha_T_sc2'] > 0) и распределяем закачку между ними:
                prod_wells_radius_df_necompensirovannay_dobycha = prod_wells_radius_df[prod_wells_radius_df['necompensirovannay_dobycha_T_sc2'] > 0]
                print(f"  - количество доб. скважин скважин с некомпенсированной добычей - {prod_wells_radius_df_necompensirovannay_dobycha.shape[0]}")
                
                if prod_wells_radius_df_necompensirovannay_dobycha.shape[0] > 0:
                    prod_wells_necompensirovannay_dobycha = prod_wells_radius_df_necompensirovannay_dobycha['necompensirovannay_dobycha_T_sc2'].sum() # Сумма некомпенсированной добычи по этим скважинам
                    print(f"   - некомпенсированная добыча по очагу - {prod_wells_necompensirovannay_dobycha}")
                    
                    # итерируем DataFrame добывающих скважин с некомпенсированной добычей, на которые влияет эта нагнетательная (записываем значение закачки в зависимости от нераспределенной жидкости):
                    for index1, row1 in prod_wells_radius_df_necompensirovannay_dobycha.iterrows():
                        # нефтяная скважина (с некомпенсированной добычей):
                        prod_well = row1['WELLID']
                        print(f"    - добывающая скважина (WELLID) - {prod_well}")
                        
                        # нераспределенная добыча текущая по скважине:
                        prod_well_necompensirovannay_dobycha = row1['necompensirovannay_dobycha_T_sc2']
                        print(f"       - некомпенсированная добыча по скважине - {prod_well_necompensirovannay_dobycha}")
                        
                        # доля закачки от нагнетательной скважины в этот месяц, которая пойдет на нефтяную скважину (доля от DOWNLOAD_WATER_M3):
                        dolya_zakachki = round(prod_well_necompensirovannay_dobycha/prod_wells_necompensirovannay_dobycha, 10)
                        print(f"       - доля закачки - {dolya_zakachki}")
                        
                        # aбсолютное значение закачки от нагнетательной скважины в этот месяц, которая пойдет на нефтяную скважину (доля от DOWNLOAD_WATER_M3):
                        prod_well_abs_compensacia = dolya_zakachki * inj_well_domnload_water
                        print(f"       - абсолютная компенсация - {prod_well_abs_compensacia}")
                        
                        # закачка на нефтяную скважину на дату (записываем в таблицу добычи prod_all_df):
                        prod_all_df.loc[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['WELLID'] == prod_well) & (prod_all_df['DATE_PROD'] == date), ['zakachka_M3_sc2']] += prod_well_abs_compensacia
                        
                        # плюсуем это значение в колонку ['cum_zakachka_M3_sc2'] полностью вниз после иттерируемой даты:
                        prod_all_df.loc[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['WELLID'] == prod_well) & (prod_all_df['DATE_PROD'] >= date), ['cum_zakachka_M3_sc2']] += prod_well_abs_compensacia
                    
                        # вычитаем это значение из всей последующей после даты итерации нераспределенной добычи по скважине:
                        prod_all_df.loc[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['WELLID'] == prod_well) & (prod_all_df['DATE_PROD'] >= date), ['necompensirovannay_dobycha_T_sc2']] -= prod_well_abs_compensacia
                    continue
                
                
                # 2 условие - если все скважины с компенсированной добычей, то распределяем закачку между ними обратной пропорцией:
                prod_wells_radius_df_compensirovannay_dobycha = prod_wells_radius_df[prod_wells_radius_df['necompensirovannay_dobycha_T_sc2'] < 0]
                print(f"  - количество скважин с компенсированной добычей - {prod_wells_radius_df_compensirovannay_dobycha.shape[0]}")
                
                if prod_wells_radius_df_compensirovannay_dobycha.shape[0] > 0:
                    prod_wells_compensirovannay_dobycha = prod_wells_radius_df_compensirovannay_dobycha['necompensirovannay_dobycha_T_sc2'].sum() # Сумма некомпенсированной добычи по этим скважинам
                    print(f"   - компенсированная добыча по очагу - {prod_wells_compensirovannay_dobycha}")
                    
                    # рассчет по скважинами (1/некомпенсированная_добыча') и берем их сумму:
                    prod_wells_radius_df_compensirovannay_dobycha['obr'] = abs(1 / prod_wells_radius_df_compensirovannay_dobycha['necompensirovannay_dobycha_T_sc2'])
                    prod_wells_radius_df_compensirovannay_dobycha_obr_sum = prod_wells_radius_df_compensirovannay_dobycha['obr'].sum()
                    print(f"   - сумма коэффициентов обратной закачки (1/некомпенсированная_добыча') по скважинам в радиусе - {prod_wells_radius_df_compensirovannay_dobycha_obr_sum}")
                    

                    # итерируем DataFrame добывающих скважин с некомпенсированной добычей, на которые влияет эта нагнетательная (записываем значение закачки в зависимости от нераспределенной жидкости):
                    for index2, row2 in prod_wells_radius_df_compensirovannay_dobycha.iterrows():
                        # нефтяная скважина (с компенсированной добычей):
                        prod_well = row2['WELLID']
                        prod_well_compensirovannay_dobycha = row2['necompensirovannay_dobycha_T_sc2'] # распределенная добыча текущая по скважине
                        prod_well_obr_compensirovannay_dobycha = row2['obr'] # (1/распределенная добыча) - обратный коэффициент распределенной добычи
                        print(f"    - добывающая скважина (WELLID) - {prod_well}")
                        print(f"       - компенсированная добыча по скважине (значение должно быть с минусом, оно тут не участвует в расчетах) - {prod_well_compensirovannay_dobycha}")
                        print(f"       - обратный коэффициент компенсированной добычи по скважине - {prod_well_obr_compensirovannay_dobycha}")
                    
                        # доля закачки от нагнетательной скважины в этот месяц, которая пойдет на нефтяную скважину (доля от DOWNLOAD_WATER_M3) - тут обратный порядок (чем больше компенсированной добычи на скважине, тем меньше в нее пойдет жидкости от нагнетательной):
                        dolya_zakachki_obr = round(prod_well_obr_compensirovannay_dobycha / prod_wells_radius_df_compensirovannay_dobycha_obr_sum, 10)
                        print(f"       - доля закачки - {dolya_zakachki_obr}")
                        
                        # абсолютное значение закачки от нагнетательной скважины в этот месяц, которая пойдет на нефтяную скважину (доля от DOWNLOAD_WATER_M3):
                        prod_well_abs_compensacia = dolya_zakachki_obr * inj_well_domnload_water
                        print(f"       - абсолютная компенсация - {prod_well_abs_compensacia}")
                        
                        # закачка на нефтяную скважину на дату (записываем в таблицу добычи prod_all_df):
                        prod_all_df.loc[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['WELLID'] == prod_well) & (prod_all_df['DATE_PROD'] == date), ['zakachka_M3_sc2']] += prod_well_abs_compensacia
                        
                        # плюсуем это значение в колонку ['cum_zakachka_M3_sc2'] полностью вниз после иттерируемой даты:
                        prod_all_df.loc[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['WELLID'] == prod_well) & (prod_all_df['DATE_PROD'] >= date), ['cum_zakachka_M3_sc2']] += prod_well_abs_compensacia
                    
                        # вычитаем это значение из всей последующей после даты итерации нераспределенной добычи по скважине:
                        prod_all_df.loc[(prod_all_df['RESERVOIR_number'] == reservoir_number) & (prod_all_df['WELLID'] == prod_well) & (prod_all_df['DATE_PROD'] >= date), ['necompensirovannay_dobycha_T_sc2']] -= prod_well_abs_compensacia
                    continue
                
                
                # Если ничего не выполнилось (нет скважин в радиусе) - закачка не распределяется и идет сюда в таблицы (учет нераспределенной закачки по скважинам):
                new_row_data = {
                    'DATE_PROD': pd.to_datetime(date),                      # Дата (datetime)
                    'WELL_CHARACTER': row['WELL_CHARACTER'],               # Категория скважины (строка)
                    'WELLID': inj_well,                                    # Идентификатор скважины (строка)
                    'FIELD': row['FIELD'],                                 # Поле добычи (строка)
                    'AREA': row['AREA'],                                   # Район (строка)
                    'STRATUM': row['STRATUM'],                             # Стратиграфия (строка)
                    'DOWNLOAD_WATER_M3': float(inj_well_domnload_water)    # Объем воды (число с плавающей точкой)
                } # записываем данные с словарь
                new_row_df = pd.DataFrame([new_row_data]) # Конвертируем словарь в DataFrame
                zak_no_prod_well_radius = pd.concat([zak_no_prod_well_radius, new_row_df], ignore_index=True) # Объединяем старый и новый DataFrames
            
    # проверка 1: сумма накопленной закачки по всем нагнетательным скважинам (даже которые перешли из добывающих в нагнетательные):
    print(f"Cумма накопленной закачки по всем нагнетательным скважинам (даже которые перешли из добывающих в нагнетательные) - варинат 1 - {inj_df.groupby(['RESERVOIR_number', 'WELLID'])['CUM_DOWNLOAD_WATER_M3'].max().sum()}")
    print(f"Cумма накопленной закачки по всем нагнетательным скважинам (даже которые перешли из добывающих в нагнетательные) - варинат 2 - {inj_df['DOWNLOAD_WATER_M3'].sum()}")
    print(f"Cумма накопленной закачки по всем нагнетательным скважинам (даже которые перешли из добывающих в нагнетательные) - варинат 3 - {inj_df.drop_duplicates(subset=['RESERVOIR_number', 'WELLID'], keep='last')['CUM_DOWNLOAD_WATER_M3'].sum()}\n")

    # проверка 1: сумма закачки, которая попала в добывающие скважины:
    print(f"Сумма закачки, которая попала в добывающие скважины  - варинат 1 - {round(prod_all_df.groupby(['RESERVOIR_number', 'WELLID'])['cum_zakachka_M3_sc2'].max().sum(), 1)}")
    print(f"Сумма закачки, которая попала в добывающие скважины  - варинат 2 - {round(prod_all_df['zakachka_M3_sc2'].sum(), 1)}\n")

    # проверка 1: сумма закачки, которая НЕ ПОПАЛА в добывающие скважины:
    print(f"Сумма закачки, которая НЕ ПОПАЛА в добывающие скважины - {zak_no_prod_well_radius['DOWNLOAD_WATER_M3'].sum()}\n")

    # проверка 1: сумма закачки, которая ПОПАЛА и НЕ ПОПАЛА в добывающие скважины:
    print(f"Сумма закачки, которая ПОПАЛА и НЕ ПОПАЛА в добывающие скважины - {round(zak_no_prod_well_radius['DOWNLOAD_WATER_M3'].sum() + prod_all_df['zakachka_M3_sc2'].sum(), 1)}\n")

    # проверка 2: некомпенсированная добыча на скважине = накопленная добыча жидкости на скважине - закачка на скважину (если не ноль, тогда неправильно считается что-то)
    prod_all_df_LastRow = prod_all_df.drop_duplicates(subset = ['WELLID', 'RESERVOIR_number'], keep='last')
    prod_all_df_LastRow['necompensirovannay_dobycha_proverka'] = prod_all_df_LastRow['CUM_FLUID_T'] - prod_all_df_LastRow['cum_zakachka_M3_sc2']
    prod_all_df_LastRow['Разность'] = abs(round(prod_all_df_LastRow['necompensirovannay_dobycha_proverka'] - prod_all_df_LastRow['necompensirovannay_dobycha_T_sc2'], 1))
    print(f"Проверка 2 - некомпенсированная добыча на скважине = накопленная добыча жидкости на скважине - закачка на скважину (если значение больше 0, то неправильно что-то посчиталось по закачке) - {prod_all_df_LastRow[prod_all_df_LastRow['Разность'] != 0].shape[0]}\n")

    # расчет компенсации (текущая и накопленная) во времени по 2-ому сценарияю 
    prod_all_df['COMPENS_cur_percent_sc2'] = round((prod_all_df['zakachka_M3_sc2'] / prod_all_df['FLUID_T']) * 100, 1) #! тут появляется бесконечность, потому что prod_all_df['FLUID_T'] может быть равен нули при продлении таблицы добычи
    prod_all_df['COMPENS_cur_percent_sc2'] = prod_all_df['COMPENS_cur_percent_sc2'].fillna(value=0)
    prod_all_df['COMPENS_cum_percent_sc2'] = round((prod_all_df['cum_zakachka_M3_sc2'] / prod_all_df['CUM_FLUID_T']) * 100, 1)  # Компенсация накопленная на дату
    
    return prod_all_df, zak_no_prod_well_radius





# Функция 6
def graph_param1(df):
    '''
    Функция по отображению графиков по скважинам
     - вход prod_all_df
     - выход графики
    '''
    # Создаем фигуру с двумя графиком:
    fig = make_subplots(rows=3, cols=1, subplot_titles=["Дебиты и закачка", "Накопленная добыча и закачка", "Компенсация и коэффициент продуктивнсоти"], specs=[
        [{}], 
        [{"secondary_y": True}], 
        [{"secondary_y": True}]])
    
    legend_groups = ['top_left', 'middle_right', 'bottom']
    
    # 1.1. Линейный график 'Q_FLUID_T':
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['FLUID_T'],
        mode='lines',  # Изменено с 'lines' на 'markers' для точечного графика
        marker=dict(
            color='red',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Добыча жидкости, м3',
        legendgroup=legend_groups[0],
        showlegend=True
    ), row=1, col=1)
    
    # 1.2. Линейный график 'Закачка, м/сут' по сценарию 1:
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['zakachka_M3_sc1'],
        mode='lines', 
        marker=dict(
            color='blue',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Закачка, м3 (сценарий 1)',
        legendgroup=legend_groups[0],
        showlegend=True
    ), row=1, col=1)
    
    # 1.3. Линейный график 'Закачка, м/сут' по сценарию 2:
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['zakachka_M3_sc2'],
        mode='lines', 
        marker=dict(
            color='lightblue',
            size=8, 
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Закачка, м3 (сценарий 2)', 
        legendgroup=legend_groups[0],
        showlegend=True
    ), row=1, col=1)
    
    # # 1.4. Точечный график для ГТМ_ввод (лежит на оси X):
    # df.loc[df['ГТМ_ввод'].notnull(), 'ГТМ_ввод_отображение'] = 0
    # fig.add_trace(go.Scatter(
    #     x=df['DATE_PROD'], 
    #     y=df['ГТМ_ввод_отображение'],
    #     mode='markers',  # Изменено с 'lines' на 'markers' для точечного графика
    #     marker=dict(
    #         color='blue',
    #         size=15,  
    #         symbol='diamond', # Увеличил размер точек для лучшей видимости
    #         line=dict(width=1, color='DarkSlateGrey')
    #     ),
    #     hovertemplate='%{x}<br>%{y:.2f}',
    #     name='ГТМ при работе скважины',
    #     legendgroup=legend_groups[0],
    #     showlegend=False
    # ), row=1, col=1)
    
    # # 1.5. Точечный график для ГТМ_работа (лежит на оси X):
    # df.loc[df['ГТМ_работа'].notnull(), 'ГТМ_работа_отображение'] = 0
    # fig.add_trace(go.Scatter(
    #     x=df['DATE_PROD'], 
    #     y=df['ГТМ_работа_отображение'],
    #     mode='markers',  # Изменено с 'lines' на 'markers' для точечного графика
    #     marker=dict(
    #         color='red',
    #         size=15,  
    #         symbol='diamond', # Увеличил размер точек для лучшей видимости
    #         line=dict(width=1, color='DarkSlateGrey')
    #     ),
    #     hovertemplate='%{x}<br>%{y:.2f}',
    #     name='ГТМ при работе скважины',
    #     legendgroup=legend_groups[0],
    #     showlegend=False
    # ), row=1, col=1)
    
    # -------------------------------------------------------------------
    
    # 2.1. Линейный график 'Накопленная добыча жидкости м3':
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['CUM_FLUID_T'],
        mode='lines',  
        marker=dict(
            color='red',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Накопленная добыча жидкости м3',
        legendgroup=legend_groups[1],
        showlegend=True
    ), secondary_y=False, row=2, col=1)
    
    # 2.2. Линейный график 'Накопленная закачка, м3 - сценарий 1':
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['cum_zakachka_M3_sc1'],
        mode='lines',  
        marker=dict(
            color='blue',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Накопленная закачка, м3 - сценарий 1', 
        legendgroup=legend_groups[1],
        showlegend=True
    ), secondary_y=False, row=2, col=1)
    
    # 2.3. Линейный график 'Накопленная закачка, м3 - сценарий 2':
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['cum_zakachka_M3_sc2'],
        mode='lines',  
        marker=dict(
            color='lightblue',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Накопленная закачка, м3 - сценарий 2',
        legendgroup=legend_groups[1],
        showlegend=True
    ), secondary_y=False, row=2, col=1)
    
    
    # 2.4. Линейный график 'Обводненность, д.е.':
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['WCT'],
        mode='lines',
        line=dict(color='grey', width=2, dash='dash'),   # "dot", "dashdot", "longdash", "solid" 
        marker=dict(
            color='grey',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Обводненность, д.е.',
        legendgroup=legend_groups[1],
        showlegend=True
    ), secondary_y=True, row=2, col=1)
    # -------------------------------------------------------------------    
    
    # 3 Рпл, компенсация (сценарий 1 и сценарий 2) и коэффициент продуктивности
    # 3.1. Линейный график 'Компенсация, %' сценарий1:
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['COMPENS_cum_percent_sc1'],
        mode='lines',  
        marker=dict(
            color='blue',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Компенсация, % (сценарий 1)', 
        legendgroup=legend_groups[2],
        showlegend=True,
    ), secondary_y=False, row=3, col=1)
    
    # 3.2. Линейный график 'Компенсация, %' сценарий2:
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['COMPENS_cum_percent_sc2'],
        mode='lines',
        marker=dict(
            color='lightblue',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Компенсация, % (сценарий 2)',
        legendgroup=legend_groups[2], 
        showlegend=True,
    ),  secondary_y=False, row=3, col=1)
    
    # 3.3. Точечный график 'Пластовое давление, атм':
    fig.add_trace(go.Scatter(
        x=df['DATE_PROD'], 
        y=df['PRESSURE_STRATUM'],
        mode='markers',
        marker=dict(
            color='red',
            size=8,  
            line=dict(width=1, color='DarkSlateGrey')
        ),
        hovertemplate='%{x}<br>%{y:.2f}',
        name='Пластовое давление, атм', 
        legendgroup=legend_groups[2],
        showlegend=True,
    ), secondary_y=False, row=3, col=1)
    
    # # 3.4. Точечный график 'Коэффициент продуктивности, м3/(сут*МПа)':
    # fig.add_trace(go.Scatter(
    #     x=df['DATE_PROD'], 
    #     y=df['coef_prod'],
    #     mode='markers',
    #     marker=dict(
    #         color='green',
    #         size=8,  
    #         line=dict(width=1, color='DarkSlateGrey')
    #     ),
    #     hovertemplate='%{x}<br>%{y:.2f}',
    #     name='Коэффициент продуктивноcти, м3/(сут*МПа)',
    #     legendgroup=legend_groups[2], 
    #     showlegend=True,
    # ), secondary_y=True, row=3, col=1)
    # -------------------------------------------------------------------
    
    # Настройка layout
    fig.update_layout(
        title_text=f"Скважина {df['WELLID'].unique()[0]}",  # Добавил [0] чтобы получить конкретное значение
        width=1400, 
        height=1000,
        hovermode='x unified',  # Показывать подсказки для всех графиков по оси X
        showlegend=True,        # Глобальная установка легенды
        # legend={'orientation':'h'}
    )
    
    # -------------------------------------------------------------------
    # Настройка оси X
    fig.update_xaxes(
        title_text="Дата", 
        range=[df['DATE_PROD'].min() - pd.DateOffset(months=2), 
            df['DATE_PROD'].max() + pd.DateOffset(months=2)], 
        row=1, col=1
    )

    fig.update_xaxes(
        title_text="Дата", 
        range=[df['DATE_PROD'].min() - pd.DateOffset(months=2), 
            df['DATE_PROD'].max() + pd.DateOffset(months=2)], 
        row=2, col=1
    )
    
    fig.update_xaxes(
        title_text="Дата", 
        range=[df['DATE_PROD'].min() - pd.DateOffset(months=2), 
            df['DATE_PROD'].max() + pd.DateOffset(months=2)], 
        row=3, col=1
    )
    
    # -------------------------------------------------------------------
    # Настройка оси Y
    fig.update_yaxes(
        title_text="Добыча жидкости, закачка м3", 
        # range=[0, df['coef_prod'].max() + df['coef_prod'].max() * 0.2], 
        row=1, col=1
    )
    
    
    fig.update_yaxes(
        title_text="Накопленные показатели, м3", 
        # range=[0, df['Q_FLUID_T'].max() + df['Q_FLUID_T'].max() * 0.2], 
        row=2, col=1,
        secondary_y=False
    )
    
    fig.update_yaxes(
        title_text="Обводненность, д.е.", 
        range=[0, 1], 
        row=2, col=1,
        secondary_y=True
    )
        
    fig.update_yaxes(
        title_text="Компенсацйия и Pпл", 
        # range=[0, df['Q_FLUID_T'].max() + df['Q_FLUID_T'].max() * 0.2], 
        row=3, col=1,
        secondary_y=False
    )
    
    fig.update_yaxes(
        title_text="Коэффициент продуктивности", 
        # range=[0, df['Q_FLUID_T'].max() + df['Q_FLUID_T'].max() * 0.2], 
        row=3, col=1,
        secondary_y=True
    )

    # -------------------------------------------------------------------
    # Отдельные области для легенд
    annotations = []
    for i, group in enumerate(legend_groups):
        if i == 0:
            pos_x, pos_y = 1.05, 0.95  # Левый верхний угол первой легенды
        elif i == 1:
            pos_x, pos_y = 1.05, 0.5    # Центр второй легенды
        else:
            pos_x, pos_y = 1.05, 0.1   # Нижний левый угол третьей легенды
        
        annotations.append(dict(text='', xref='paper', yref='paper', x=pos_x, y=pos_y, showarrow=False))
    
    fig.update_layout(annotations=annotations)
    
    # Показать график (было в notebook python fig.show())
    st.plotly_chart(fig, use_container_width=True)