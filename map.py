import requests

# ==========================================
# 1. ВАШИ НАСТРОЙКИ
# ==========================================
YANDEX_API_KEY = "40c0ece5-dbf1-44cf-97f9-1a0e1a5f0ef7"

# Введите адреса здесь (можно с опечатками, без 'Москва')
START_ADDRESS = "тверская 1"      # Точка А
END_ADDRESS   = "парк горького"   # Точка Б
# ==========================================


def get_moscow_location(address_text):
    """
    Ищет координаты, принудительно добавляя контекст Москвы.
    """
    # Хитрость: добавляем 'Москва' к запросу, чтобы не искать в других городах
    search_query = f"Москва {address_text}"
    
    base_url = "https://geocode-maps.yandex.ru/1.x/"
    params = {
        "apikey": YANDEX_API_KEY,
        "geocode": search_query,
        "format": "json",
        "results": 1
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        # Разбор ответа
        geo_object_collection = data["response"]["GeoObjectCollection"]
        if len(geo_object_collection["featureMember"]) == 0:
            return None

        top_result = geo_object_collection["featureMember"][0]["GeoObject"]
        full_address = top_result["metaDataProperty"]["GeocoderMetaData"]["text"]
        pos = top_result["Point"]["pos"]
        lon, lat = pos.split(" ")
        
        return float(lat), float(lon), full_address

    except Exception as e:
        print(f"Ошибка геокодирования: {e}")
        return None

def get_route_osrm(start_lat, start_lon, end_lat, end_lon):
    """
    Строит маршрут по дорогам (OSRM).
    """
    base_url = "http://router.project-osrm.org/route/v1/driving/"
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base_url}{coordinates}?overview=false"

    try:
        response = requests.get(url)
        data = response.json()
        if data.get("code") == "Ok":
            route = data["routes"][0]
            return route["distance"], route["duration"]
        return None
    except:
        return None

def main():
    print("=== Расчет маршрута по Москве ===")
    print(f"📍 Исходный запрос А: '{START_ADDRESS}'")
    print(f"📍 Исходный запрос Б: '{END_ADDRESS}'")
    print("-" * 30)

    # 1. Ищем координаты с привязкой к Москве
    start_loc = get_moscow_location(START_ADDRESS)
    end_loc = get_moscow_location(END_ADDRESS)

    if not start_loc:
        print(f"❌ Не удалось найти адрес в Москве: {START_ADDRESS}")
        return
    if not end_loc:
        print(f"❌ Не удалось найти адрес в Москве: {END_ADDRESS}")
        return

    # Распаковываем данные
    lat_a, lon_a, addr_a = start_loc
    lat_b, lon_b, addr_b = end_loc

    print(f"✅ Найдено А: {addr_a}")
    print(f"✅ Найдено Б: {addr_b}")

    # 2. Считаем маршрут
    result = get_route_osrm(lat_a, lon_a, lat_b, lon_b)

    if result:
        dist_m, time_s = result
        dist_km = round(dist_m / 1000, 2)
        time_min = int(time_s // 60)

        print("\n" + "=" * 30)
        print(f"🚗 По реальным дорогам:")
        print(f"📏 Расстояние: {dist_km} км")
        print(f"⏱  Время (без пробок): ~{time_min} мин")
        print("=" * 30)
    else:
        print("\n❌ Не удалось проложить автомаршрут между этими точками.")

if __name__ == "__main__":
    if "ВАШ_КЛЮЧ" in YANDEX_API_KEY:
        print("⚠️ Пожалуйста, вставьте API ключ Яндекса в строку 6!")
    else:
        main()