import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging
import io
import requests
import pandas as pd
import oracledb
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text, inspect
from datetime import date, datetime
from typing import Optional
from requests.exceptions import RequestException, Timeout, HTTPError, ConnectionError
from tqdm import tqdm

# --- НАСТРОЙКА ЛОГИРОВАНИЯ В GUI ---
class TextHandler(logging.Handler):
    """Класс для перенаправления логов в текстовое поле Tkinter"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        # Обновление GUI должно быть в основном потоке
        self.text_widget.after(0, append)

# --- ВАШ КЛАСС DATA PROCESSOR (С ДОРАБОТКАМИ) ---
class DataProcessor:
    HOST = 'hostname'
    PORT = '1521'
    SERVICE_NAME = 'service_name'
    CONFIG = {
        "user": "login",
        "password": "password",
        "dsn": f"{HOST}:{PORT}/{SERVICE_NAME}",
    }

    DATABASE_URL = f'oracle+oracledb://{CONFIG["user"]}:{CONFIG["password"]}@{HOST}:{PORT}/?service_name={SERVICE_NAME}'
    TABLE_NAME = 'is_data_bank_temp'
    
    FILENAME_LIST = ['Сведения о страховых премиях в разрезе страховщиков',
                     "Сведения о страховых премиях (взносах) по договорам страхования, в разрезе страховщиков"]

    TABLE_COLUMNS = ["Регистрационный номер", "Полное наименование страховщика", "Всего", "ДМС выезжающих за рубеж",
                     "ДМС работодателем своих работников", "ДМС иных граждан"]
    
    TABLE_COLUMNS_WITH_DATA = ["Период отчета"] + TABLE_COLUMNS
    SAVEPATH = "." # Изменил на текущую папку для теста, замените на свой путь
    BASE_URL = 'https://cbr.ru'
    
    COLUMNS_AFTER_2021_4 = [0, 1, 151, 152, 153, 154]
    COLUMNS_BEFORE_2021_4 = [1, 2, 15]

    def __init__(self):
        # Логгер инициализируется внутри
        self.logger = logging.getLogger(__name__)

    def download_page_html(self, year: int = date.today().year, quater: int = 1):
        page_url = f'{self.BASE_URL}/finmarket/supervision/sv_insurance/stat_ssd/{year}_{quater}/'
        response = self.download_file(page_url, check_link=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        spans = soup.find_all('span')
        return spans

    def check_file_in_html(self, spans, filename):
        files = []
        for span in spans:
            if filename in span.get_text(strip=True):
                parent = span.find_parent('a')
                if parent and parent.has_attr('href'):
                    file_url = self.BASE_URL + parent['href']
                    files.append((file_url, span.get_text(strip=True)))
        return files

    def download_file(self, url: str, check_link: bool = False, timeout: int = 50):
        try:
            self.logger.debug(f"Попытка загрузки: {url}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            if check_link:
                self.logger.info(f"Ссылка найдена: {url}")
            else:
                self.logger.info(f"Файл загружен: {url}")
                return response
        except Exception as e:
            self.logger.error(f"Ошибка загрузки {url}: {e}")
            raise RuntimeError(f"Ошибка загрузки: {e}")

    def save_file(self, year: int, quarter: int, filename: str, datatosave, type: str = "xlsx", flag :bool =False):
        # Убрал жесткую привязку к пути с слэшами, лучше использовать os.path.join, но пока оставим try/except
        try:
            if flag:
                # datatosave is DataFrame
                full_name = f"{self.SAVEPATH}/{year}_{quarter}_processed.{type}"
                datatosave.to_excel(full_name, index=False)
            else:
                # datatosave is bytes
                full_name = f"{self.SAVEPATH}/{filename}{year}_{quarter}.{type}"
                with open(full_name, "wb") as file:
                    file.write(datatosave)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения файла (проверьте SAVEPATH): {e}")

    def generate_year_quarter(self, start_year, start_quarter, end_year, end_quarter):
        pair_list = []
        current_year = start_year
        current_quarter = start_quarter
        while (current_year < end_year) or (current_year == end_year and current_quarter <= end_quarter):
            pair_list.append((current_year, current_quarter))
            current_quarter += 1
            if current_quarter > 4:
                current_quarter = 1
                current_year += 1
        return pair_list

    def processing_file(self, year, quarter, data) -> list:
        target_column_idx = 0
        if year >= 2022 or (year == 2021 and quarter == 4):
            columns = self.COLUMNS_AFTER_2021_4
        else:
            columns = self.COLUMNS_BEFORE_2021_4

        df = pd.read_excel(data)
        start_index = None
        end_index = None
        for idx, val in enumerate(df.iloc[:, target_column_idx]):
            if isinstance(val, str) and "итог" in val.lower():
                start_index = idx + 1
                break

        if start_index is None:
            self.logger.error(f"Индекс 'итог' не найден {year}_{quarter}")
            return []

        for idx in range(start_index, len(df)):
            val = df.iat[idx, target_column_idx]
            if pd.to_numeric(val, errors='coerce') and not pd.isna(pd.to_numeric(val, errors='coerce')):
                continue
            else:
                end_index = idx
                break
        
        if end_index is None: end_index = len(df) # Fallback

        df_result = df.iloc[start_index: end_index, columns].copy()
        
        # Исправление для старых файлов (добавление пустых колонок)
        if year < 2022 and not (year == 2021 and quarter == 4):
            # Внимание: логика добавления колонок может зависеть от структуры старых файлов
            # Здесь я просто копирую логику из вашего кода, но с проверкой
            missing_cols = 6 - len(df_result.columns)
            if missing_cols > 0:
               for i in range(missing_cols):
                   df_result[f'temp_{i}'] = 0 
            
            # Принудительно берем только нужное количество колонок или дополняем нулями
            # Это место требует осторожности в зависимости от реальных данных
            df_result = df_result.iloc[:, :6] 
            
        df_result.columns = self.TABLE_COLUMNS

        quarter_dict = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}
        report_date = pd.to_datetime(f"{year}{quarter_dict[quarter]}")
        df_result.insert(0, "Дата", value=report_date)

        for col in df_result.columns[-4:]:
            df_result[col] = pd.to_numeric(df_result[col], errors='coerce').fillna(0).astype(float)

        # Сохранение обработанного
        self.save_file(year, quarter, '', df_result, flag=True)
        return df_result.values.tolist()

    def _drop_and_create_table(self):
        engine = create_engine(self.DATABASE_URL)
        with engine.connect() as conn:
            inspector = inspect(conn)
            if inspector.has_table(self.TABLE_NAME):
                conn.execute(text(f"DROP TABLE {self.TABLE_NAME}"))
                self.logger.info(f"Таблица {self.TABLE_NAME} удалена.")
            
            create_table_sql = f"""
                CREATE TABLE {self.TABLE_NAME} (
                    id NUMBER PRIMARY KEY,
                    reportdate DATE NOT NULL,
                    regno NUMBER NOT NULL,
                    name VARCHAR2(200) NOT NULL,
                    total NUMBER NOT NULL,
                    abroad NUMBER NOT NULL,
                    worker NUMBER NOT NULL,
                    other NUMBER NOT NULL
                )
            """
            conn.execute(text(create_table_sql))
            conn.commit()
            self.logger.info(f"Таблица {self.TABLE_NAME} создана.")

    # --- НОВЫЙ МЕТОД ДЛЯ УДАЛЕНИЯ КОНКРЕТНОГО КВАРТАЛА ---
    def delete_quarter_data(self, year, quarter):
        """Удаляет данные из БД за определенный квартал (по дате отчета)"""
        quarter_dict = {1: "31-03", 2: "30-06", 3: "30-09", 4: "31-12"}
        date_str = f"{quarter_dict[quarter]}-{year}" # Format DD-MM-YYYY matches SQL below
        
        self.logger.info(f"Удаление данных за дату: {date_str}...")
        
        try:
            connection = oracledb.connect(**self.CONFIG)
            cursor = connection.cursor()
            
            sql = f"DELETE FROM {self.TABLE_NAME} WHERE reportdate = TO_DATE(:1, 'DD-MM-YYYY')"
            cursor.execute(sql, [date_str])
            rows_deleted = cursor.rowcount
            connection.commit()
            self.logger.info(f"Удалено строк: {rows_deleted}")
            
            cursor.close()
            connection.close()
        except oracledb.DatabaseError as e:
            self.logger.error(f"Ошибка удаления квартала: {e}")

    def _get_current_row_count(self, cursor):
        try:
            cursor.execute(f"SELECT COUNT(id) FROM {self.TABLE_NAME}")
            return int(cursor.fetchone()[0])
        except:
            return 0

    def _insert_data(self, df):
        try:
            connection = oracledb.connect(**self.CONFIG)
            cursor = connection.cursor()
            
            # Проверка существования таблицы, если нет - создать (для режима Append)
            try:
                cursor.execute(f"SELECT 1 FROM {self.TABLE_NAME} WHERE ROWNUM = 1")
            except oracledb.DatabaseError:
                self.logger.info("Таблица не найдена при вставке. Создаем...")
                cursor.close()
                connection.close()
                self._drop_and_create_table()
                connection = oracledb.connect(**self.CONFIG)
                cursor = connection.cursor()

            row_count = self._get_current_row_count(cursor)
            df.insert(0, "id", value=range(row_count, row_count + df.shape[0]))
            
            insert_sql = f"""
                INSERT INTO {self.TABLE_NAME}
                (id, reportdate, regno, name, total, abroad, worker, other)
                VALUES (:1, TO_DATE(:2, 'DD-MM-RRRR'), :3 ,:4, :5, :6, :7, :8)
            """
            cursor.executemany(insert_sql, df.values.tolist())
            connection.commit()
            self.logger.info(f"Вставлено строк: {len(df)}")
        except oracledb.DatabaseError as e:
            self.logger.error(f"Ошибка Oracle: {e}")
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'connection' in locals(): connection.close()

    def load_into_df(self, lines, update: bool = False):
        df = pd.DataFrame(data=lines, columns=self.TABLE_COLUMNS_WITH_DATA)
        if update:
            self._drop_and_create_table()
        if not df.empty:
            self._insert_data(df)
        else:
            self.logger.warning("Нет данных для вставки.")

    def run_pipeline(self, start_date: str, end_date: Optional[str] = None):
        """
        Основной метод запуска. 
        Если end_date указан -> генерирует список и делает Recreate Table (update=True).
        Если end_date НЕ указан -> обрабатывает один квартал и делает Append (update=False).
        """
        files_to_download = []
        start_year, start_quarter = map(int, start_date.split("_"))
        
        if not end_date:
            files_to_download.append((start_year, start_quarter))
            is_full_rewrite = False
        else:
            end_year, end_quarter = map(int, end_date.split("_"))
            files_to_download = self.generate_year_quarter(start_year, start_quarter, end_year, end_quarter)
            is_full_rewrite = True

        self.logger.info(f"Задачи: {files_to_download}")
        
        # 1. Поиск ссылок
        prepared_files = []
        for year, quarter in files_to_download:
            filename = None
            url = None
            try:
                spans = self.download_page_html(year=year, quater=quarter)
                for file_tmpl in self.FILENAME_LIST:
                    candidates = self.check_file_in_html(spans, file_tmpl)
                    # Выбор по длине названия (эвристика из оригинала)
                    best_match = None
                    for cand_url, cand_name in candidates:
                         if len(file_tmpl) == len(cand_name):
                             best_match = (cand_url, cand_name)
                             break
                    
                    if best_match:
                        url, filename = best_match
                        break
                
                if url:
                    self.logger.info(f"Найдено: {year}_{quarter} -> {url}")
                    prepared_files.append((year, quarter, filename, url))
                else:
                    self.logger.warning(f"НЕ НАЙДЕНО: {year}_{quarter}")
            except Exception as e:
                self.logger.error(f"Ошибка поиска {year}_{quarter}: {e}")

        # 2. Скачивание и Обработка
        db_line = []
        for year, quarter, fname, url in prepared_files:
            try:
                resp = self.download_file(url)
                rows = self.processing_file(year, quarter, io.BytesIO(resp.content))
                db_line.extend(rows)
                # Сохраняем сырой файл
                # self.save_file(year, quarter, fname, resp.content) 
            except Exception as e:
                self.logger.error(f"Ошибка обработки {year}_{quarter}: {e}")

        # 3. Загрузка в БД
        self.load_into_df(db_line, update=is_full_rewrite)
        self.logger.info("Операция завершена.")

# --- GUI ПРИЛОЖЕНИЕ ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Загрузчик данных ЦБ РФ (Oracle)")
        self.root.geometry("600x650")

        self.processor = DataProcessor()
        
        # Настройка логгера
        self.setup_logging()

        # --- БЛОК 1: ВЫБОР ДАТ (Диапазон) ---
        frame_dates = tk.LabelFrame(root, text="Выбор периода", padx=10, pady=10)
        frame_dates.pack(padx=10, pady=5, fill="x")

        # Начало периода
        tk.Label(frame_dates, text="НАЧАЛО (Год/Квартал):", font=('bold')).grid(row=0, column=0, sticky="w", pady=5)
        
        years = list(range(2015, datetime.now().year + 2))
        self.start_year_cb = ttk.Combobox(frame_dates, values=years, width=6)
        self.start_year_cb.set(datetime.now().year)
        self.start_year_cb.grid(row=0, column=1, padx=5)
        
        self.start_q_cb = ttk.Combobox(frame_dates, values=[1, 2, 3, 4], width=3)
        self.start_q_cb.current(0)
        self.start_q_cb.grid(row=0, column=2, padx=5)

        # Конец периода
        tk.Label(frame_dates, text="КОНЕЦ (Год/Квартал):").grid(row=1, column=0, sticky="w", pady=5)
        tk.Label(frame_dates, text="(Нужен только для замены всего диапазона)", font=("Arial", 8, "italic"), fg="gray").grid(row=2, column=0, columnspan=3, sticky="w")
        
        self.end_year_cb = ttk.Combobox(frame_dates, values=years, width=6)
        self.end_year_cb.set(datetime.now().year)
        self.end_year_cb.grid(row=1, column=1, padx=5)
        
        self.end_q_cb = ttk.Combobox(frame_dates, values=[1, 2, 3, 4], width=3)
        self.end_q_cb.current(0)
        self.end_q_cb.grid(row=1, column=2, padx=5)

        # --- БЛОК 2: КНОПКИ ДЕЙСТВИЙ ---
        frame_actions = tk.LabelFrame(root, text="Действия с Базой Данных", padx=10, pady=10)
        frame_actions.pack(padx=10, pady=5, fill="x")

        # 1. Дополнить
        btn_append = tk.Button(frame_actions, text="Дополнить базу (Append)", 
                               command=self.run_append, bg="#d9ffd9", height=2)
        btn_append.pack(fill="x", pady=2)
        tk.Label(frame_actions, text="* Загружает только 'Начало периода'. Добавляет новые строки.").pack(anchor="w", pady=(0,5))

        # 2. Обновить конкретный квартал
        btn_update_q = tk.Button(frame_actions, text="Обновить этот квартал (Update Quarter)", 
                                 command=self.run_update_quarter, bg="#fffdd0", height=2)
        btn_update_q.pack(fill="x", pady=2)
        tk.Label(frame_actions, text="* Удаляет данные за 'Начало периода' и загружает их заново.").pack(anchor="w", pady=(0,5))

        # 3. Перезаписать всё
        btn_replace = tk.Button(frame_actions, text="ПЕРЕЗАПИСАТЬ ВСЁ (Replace All)", 
                                command=self.run_replace_all, bg="#ffd9d9", height=2)
        btn_replace.pack(fill="x", pady=2)
        tk.Label(frame_actions, text="* Удаляет таблицу целиком! Загружает диапазон от Начала до Конца.").pack(anchor="w", pady=(0,5))

        # --- БЛОК 3: ЛОГИ ---
        self.log_area = scrolledtext.ScrolledText(root, state='disabled', height=10, font=("Consolas", 9))
        self.log_area.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Перенаправляем логгер класса DataProcessor сюда
        handler = TextHandler(self.log_area)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def setup_logging(self):
        # Настройка базового логгера, чтобы он не спамил в stderr
        logging.basicConfig(level=logging.INFO)

    def get_start_str(self):
        return f"{self.start_year_cb.get()}_{self.start_q_cb.get()}"

    def get_end_str(self):
        return f"{self.end_year_cb.get()}_{self.end_q_cb.get()}"

    def run_in_thread(self, target_func):
        """Запускает функцию в отдельном потоке, чтобы GUI не зависал"""
        t = threading.Thread(target=target_func)
        t.start()

    # --- ОБРАБОТЧИКИ КНОПОК ---

    def run_append(self):
        start = self.get_start_str()
        logging.info(f"--- ЗАПУСК: Дополнить за {start} ---")
        
        def task():
            try:
                # end_date=None означает Append одного квартала
                self.processor.run_pipeline(start_date=start, end_date=None)
            except Exception as e:
                logging.error(f"Критическая ошибка: {e}")
                
        self.run_in_thread(task)

    def run_update_quarter(self):
        year = int(self.start_year_cb.get())
        quarter = int(self.start_q_cb.get())
        start = f"{year}_{quarter}"
        
        if not messagebox.askyesno("Подтверждение", f"Удалить данные за {quarter} кв. {year} г. из базы и загрузить заново?"):
            return

        logging.info(f"--- ЗАПУСК: Обновление квартала {start} ---")

        def task():
            try:
                # 1. Удаляем старые данные
                self.processor.delete_quarter_data(year, quarter)
                # 2. Загружаем новые (как append)
                self.processor.run_pipeline(start_date=start, end_date=None)
            except Exception as e:
                logging.error(f"Критическая ошибка: {e}")

        self.run_in_thread(task)

    def run_replace_all(self):
        start = self.get_start_str()
        end = self.get_end_str()
        
        if not messagebox.askyesno("ОПАСНО", f"Это удалит ВСЮ таблицу {self.processor.TABLE_NAME}!\nБудут загружены данные с {start} по {end}.\nПродолжить?"):
            return

        logging.info(f"--- ЗАПУСК: Полная перезапись {start} -> {end} ---")

        def task():
            try:
                # Передача end_date включает режим update=True (Drop table)
                self.processor.run_pipeline(start_date=start, end_date=end)
            except Exception as e:
                logging.error(f"Критическая ошибка: {e}")

        self.run_in_thread(task)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()