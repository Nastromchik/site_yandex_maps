import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import requests
import io
from datetime import datetime

class CBRLoaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Загрузчик ЦБ РФ (Без БД)")
        self.root.geometry("600x500")

        # --- ЭМУЛЯЦИЯ БАЗЫ ДАННЫХ ---
        # Здесь мы будем хранить данные пока работает программа
        self.mock_database = pd.DataFrame(columns=['Date', 'Nominal', 'Value'])

        # --- ИНТЕРФЕЙС ---

        # 1. Панель выбора периода
        frame_top = tk.LabelFrame(root, text="Период выгрузки", padx=10, pady=10)
        frame_top.pack(padx=10, pady=5, fill="x")

        tk.Label(frame_top, text="Год:").pack(side="left", padx=5)
        current_year = datetime.now().year
        # Список лет от 2000 до текущего
        self.year_cb = ttk.Combobox(frame_top, values=list(range(2000, current_year + 1)), width=6)
        self.year_cb.set(current_year)
        self.year_cb.pack(side="left", padx=5)

        tk.Label(frame_top, text="Квартал:").pack(side="left", padx=5)
        self.quarter_cb = ttk.Combobox(frame_top, values=[
            "1 кв. (Янв-Мар)", 
            "2 кв. (Апр-Июн)", 
            "3 кв. (Июл-Сен)", 
            "4 кв. (Окт-Дек)"
        ], width=15, state="readonly")
        self.quarter_cb.current(0)
        self.quarter_cb.pack(side="left", padx=5)

        # 2. Панель кнопок (Ваши требования)
        frame_actions = tk.LabelFrame(root, text="Действия", padx=10, pady=10)
        frame_actions.pack(padx=10, pady=5, fill="x")

        # Кнопка 1: Дополнить (Append)
        btn_append = tk.Button(frame_actions, text="Дополнить базу (Append)", 
                               command=self.action_append, bg="#e6f2ff")
        btn_append.pack(fill="x", pady=2)

        # Кнопка 2: Обновить конкретный квартал
        btn_update_q = tk.Button(frame_actions, text="Обновить выбранный квартал (Update Quarter)", 
                                 command=self.action_update_quarter, bg="#fffde6")
        btn_update_q.pack(fill="x", pady=2)

        # Кнопка 3: Заменить всё (Replace All)
        btn_replace = tk.Button(frame_actions, text="Заменить всё (Replace All)", 
                                command=self.action_replace_all, bg="#ffe6e6")
        btn_replace.pack(fill="x", pady=2)

        # 3. Вывод логов и текущего состояния "Базы"
        tk.Label(root, text="Текущее состояние 'Базы данных' (в памяти):").pack(padx=10, anchor="w")
        
        self.text_area = tk.Text(root, font=("Consolas", 9))
        self.text_area.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Скроллбар для текста
        scrollbar = tk.Scrollbar(self.text_area)
        scrollbar.pack(side="right", fill="y")
        self.text_area.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text_area.yview)

        self.log("Приложение запущено. База пуста.")

    def log(self, msg):
        """Вывод сообщений в текстовое поле"""
        self.text_area.insert(tk.END, f"> {msg}\n")
        self.text_area.see(tk.END)

    def show_db_state(self):
        """Показывает, что сейчас лежит в переменной mock_database"""
        count = len(self.mock_database)
        if count > 0:
            # Сортируем для красоты
            df_sorted = self.mock_database.sort_values(by='Date')
            # Показываем первые и последние 5 строк
            preview = df_sorted.to_string(index=False, max_rows=10)
            self.text_area.insert(tk.END, f"\n--- В БАЗЕ СЕЙЧАС ЗАПИСЕЙ: {count} ---\n{preview}\n-----------------------------------\n")
        else:
            self.text_area.insert(tk.END, "\n--- БАЗА ПУСТА ---\n")
        self.text_area.see(tk.END)

    def get_dates_by_quarter(self):
        """Возвращает даты (str) и объекты datetime для фильтрации"""
        year = int(self.year_cb.get())
        q_index = self.quarter_cb.current() # 0, 1, 2, 3

        # Определение месяцев квартала
        # Q1: 1-3, Q2: 4-6, Q3: 7-9, Q4: 10-12
        start_month = q_index * 3 + 1
        end_month = start_month + 2
        
        # Последний день конечного месяца
        if end_month in [1, 3, 5, 7, 8, 10, 12]:
            last_day = 31
        elif end_month == 2:
            # Простая проверка високосного года
            last_day = 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28
        else:
            last_day = 30

        # Формат для ЦБ URL: dd/mm/yyyy
        date_req1 = f"01/{start_month:02d}/{year}"
        date_req2 = f"{last_day}/{end_month:02d}/{year}"

        # Объекты datetime для фильтрации внутри pandas
        dt_start = pd.to_datetime(f"{year}-{start_month:02d}-01")
        dt_end = pd.to_datetime(f"{year}-{end_month:02d}-{last_day}")

        return date_req1, date_req2, dt_start, dt_end

    def fetch_from_cbr(self, date_from, date_to):
        """Скачивает данные и возвращает DataFrame"""
        # Код R01235 - Доллар США
        url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date_from}&date_req2={date_to}&VAL_NM_RQ=R01235"
        self.log(f"Запрос данных: {url}")
        
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            # Читаем XML
            df = pd.read_xml(io.BytesIO(response.content), xpath=".//Record")
            
            if df.empty:
                self.log("ЦБ вернул пустой список (возможно, выходные или нет данных).")
                return None
            
            # Обработка данных
            # 1. Меняем запятую на точку в курсе
            df['Value'] = df['Value'].str.replace(',', '.').astype(float)
            # 2. Преобразуем дату в формат datetime
            df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y')
            
            return df[['Date', 'Nominal', 'Value']]

        except Exception as e:
            self.log(f"ОШИБКА: {e}")
            messagebox.showerror("Ошибка", str(e))
            return None

    # --- ЛОГИКА КНОПОК ---

    def action_append(self):
        """Добавить данные, пропуская дубликаты"""
        d1, d2, _, _ = self.get_dates_by_quarter()
        new_df = self.fetch_from_cbr(d1, d2)
        
        if new_df is not None:
            # Склеиваем старую базу и новые данные
            self.mock_database = pd.concat([self.mock_database, new_df])
            # Удаляем дубликаты по дате (оставляем последние загруженные)
            self.mock_database = self.mock_database.drop_duplicates(subset=['Date'], keep='last')
            
            self.log("Данные успешно добавлены (дубликаты удалены).")
            self.show_db_state()

    def action_replace_all(self):
        """Стереть всё и записать только текущий квартал"""
        d1, d2, _, _ = self.get_dates_by_quarter()
        new_df = self.fetch_from_cbr(d1, d2)
        
        if new_df is not None:
            self.mock_database = new_df
            self.log("База полностью перезаписана новыми данными.")
            self.show_db_state()

    def action_update_quarter(self):
        """Удалить из памяти данные за этот квартал и загрузить их заново"""
        d1, d2, dt_start, dt_end = self.get_dates_by_quarter()
        
        # 1. Скачиваем свежие данные
        new_df = self.fetch_from_cbr(d1, d2)
        
        if new_df is not None:
            # 2. Удаляем из "Базы" всё, что попадает в диапазон этого квартала
            # Логика: оставляем только те строки, где дата МЕНЬШЕ начала ИЛИ БОЛЬШЕ конца
            current_df = self.mock_database
            if not current_df.empty:
                mask = (current_df['Date'] >= dt_start) & (current_df['Date'] <= dt_end)
                rows_to_delete = mask.sum()
                self.log(f"Удалено старых записей за этот квартал: {rows_to_delete}")
                
                # Оставляем "не этот квартал"
                self.mock_database = current_df[~mask]
            
            # 3. Добавляем скачанное
            self.mock_database = pd.concat([self.mock_database, new_df])
            
            self.log("Квартал обновлен.")
            self.show_db_state()

if __name__ == "__main__":
    root = tk.Tk()
    app = CBRLoaderApp(root)
    root.mainloop()