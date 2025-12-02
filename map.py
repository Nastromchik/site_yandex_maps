import requests
import sqlite3
import time
import os

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
YANDEX_API_KEY = "40c0ece5-dbf1-44cf-97f9-1a0e1a5f0ef7"
SQLITE_DB_NAME = "routing_results.db"

# ==========================================
# 2. ГЕНЕРАТОР ДАННЫХ (ВМЕСТО ORACLE)
# ==========================================
def get_mock_data():
    """
    Возвращает список адресов для обработки.
    Эмулирует ответ от базы данных.
    Формат: (ID заявки, ID больницы, Адрес больницы, Адрес пациента)
    """
    print("📋 Загрузка тестового списка адресов...")
    return [
        (1001, 5, "Москва, Тверская 1", "Москва, Парк Горького"),
        (1002, 5, "Москва, Тверская 1", "Москва, ВДНХ"),
        (1003, 8, "Москва, Ленинский проспект 8", "Москва, Арбат 10"),
        (1004, 8, "Москва, Ленинский проспект 8", "Химки, Ленинградская 1"),
        (1005, 3, "Москва, Большая Пироговская 2", "Мытищи, Мира 10")
    ]

# ==========================================
# 3. ЛОГИКА (ГЕОКОДЕР + МАРШРУТЫ)
# ==========================================

def get_moscow_location(address_text):
    """Превращает адрес в координаты (Lat, Lon) через Яндекс."""
    if not address_text:
        return None
        
    search_query = address_text if "москва" in address_text.lower() else f"Москва {address_text}"
    base_url = "https://geocode-maps.yandex.ru/1.x/"
    
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": search_query,
        "format": "json",
        "results": 1
    }

    try:
        response = requests.get(base_url, params=params, timeout=5)
        data = response.json()
        
        geo_object = data["response"]["GeoObjectCollection"]["featureMember"]
        if not geo_object:
            return None

        pos = geo_object[0]["GeoObject"]["Point"]["pos"]
        lon, lat = pos.split(" ")
        return float(lat), float(lon)

    except Exception as e:
        print(f"⚠️ Ошибка геокодирования: {e}")
        return None

def get_route_osrm(start_lat, start_lon, end_lat, end_lon):
    """Считает маршрут через открытый сервис OSRM."""
    base_url = "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base_url}{coordinates}?overview=false"
    
    headers = {"User-Agent": "Mozilla/5.0 Python Script"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if data.get("code") == "Ok":
            route = data["routes"][0]
            # distance (метры) -> км, duration (сек) -> мин
            return round(route["distance"] / 1000, 2), round(route["duration"] / 60, 1)
        return None
    except Exception:
        return None

# ==========================================
# 4. БАЗА ДАННЫХ (SQLITE)
# ==========================================

def init_db():
    """Создает файл базы данных, если его нет."""
    conn = sqlite3.connect(SQLITE_DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            hospital_id INTEGER,
            hospital_address TEXT,
            patient_address TEXT,
            distance_km REAL,
            duration_min REAL,
            status TEXT,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(data):
    """Сохраняет одну строку в БД."""
    conn = sqlite3.connect(SQLITE_DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO route_calculations 
        (record_id, hospital_id, hospital_address, patient_address, distance_km, duration_min, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

# ==========================================
# 5. ЗАПУСК
# ==========================================

def main():
    print("=== 🚀 Запуск локального расчета маршрутов ===")
    
    # 1. Создаем БД
    init_db()
    
    # 2. Получаем список задач (теперь берется из функции get_mock_data, а не Oracle)
    tasks = get_mock_data()
    
    print(f"\nНайдено задач для обработки: {len(tasks)}\n")

    for i, item in enumerate(tasks):
        rec_id, hosp_id, addr_from, addr_to = item
        
        print(f"[{i+1}/{len(tasks)}] ID {rec_id}: {addr_from} -> {addr_to}")
        
        dist = 0.0
        time_m = 0.0
        status = "OK"
        
        # Шаг 1: Координаты
        loc_a = get_moscow_location(addr_from)
        loc_b = get_moscow_location(addr_to)
        
        if loc_a and loc_b:
            # Шаг 2: Маршрут
            res = get_route_osrm(loc_a[0], loc_a[1], loc_b[0], loc_b[1])
            if res:
                dist, time_m = res
                print(f"   ✅ Дистанция: {dist} км, Время: {time_m} мин")
            else:
                status = "ERROR_ROUTE"
                print("   ❌ Не удалось построить маршрут")
        else:
            status = "ERROR_GEOCODE"
            print("   ❌ Не найдены координаты адресов")
            
        # Шаг 3: Сохранение
        save_to_db((rec_id, hosp_id, addr_from, addr_to, dist, time_m, status))
        
        # Пауза (чтобы не забанили)
        time.sleep(0.5)

    print("\n" + "="*40)
    print("🎉 Готово!")
    print(f"📂 Результат сохранен в файл: {os.path.abspath(SQLITE_DB_NAME)}")
    print("Вы можете открыть этот файл с помощью 'DB Browser for SQLite' или прочитать через Python.")

if __name__ == "__main__":
    main()