import requests

# ==========================================
# 1. НАСТРОЙКИ
# ==========================================
YANDEX_API_KEY = "40c0ece5-dbf1-44cf-97f9-1a0e1a5f0ef7"

# Адреса (программа сама добавит 'Москва')
START_ADDRESS = "тверская 1" 
END_ADDRESS   = "парк горького"
# ==========================================

def get_moscow_location(address_text):
    """
    Ищет координаты через Яндекс Геокодер.
    """
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

def get_route_osrm_secure(start_lat, start_lon, end_lat, end_lon):
    """
    Использует HTTPS зеркало OSRM (обычно не заблокировано).
    """
    # Используем немецкий сервер OSM (он стабильнее и работает по HTTPS)
    base_url = "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
    
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base_url}{coordinates}?overview=false"

    # Притворяемся обычным браузером, чтобы нас не блокировали
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Сервер маршрутов вернул ошибку: {response.status_code}")
            return None
            
        data = response.json()
        
        if data.get("code") == "Ok":
            route = data["routes"][0]
            return route["distance"], route["duration"]
        return None
    except Exception as e:
        print(f"Ошибка соединения с сервером маршрутов: {e}")
        return None

def main():
    print("=== Расчет маршрута (Режим без прокси) ===")
    
    # 1. Геокодирование (Яндекс)
    loc_a = get_moscow_location(START_ADDRESS)
    loc_b = get_moscow_location(END_ADDRESS)

    if not loc_a or not loc_b:
        print("❌ Не удалось найти координаты одного из адресов.")
        return

    lat_a, lon_a, addr_a = loc_a
    lat_b, lon_b, addr_b = loc_b

    print(f"📍 Откуда: {addr_a}")
    print(f"📍 Куда:   {addr_b}")

    # 2. Маршрутизация (Защищенный OSRM)
    print("\n🔄 Запрос маршрута...")
    result = get_route_osrm_secure(lat_a, lon_a, lat_b, lon_b)

    if result:
        dist_m, time_s = result
        dist_km = round(dist_m / 1000, 2)
        
        # Красивый вывод времени
        time_min = int(time_s // 60)
        hours = time_min // 60
        minutes = time_min % 60
        
        time_str = f"{minutes} мин"
        if hours > 0:
            time_str = f"{hours} ч {minutes} мин"

        print("-" * 30)
        print(f"🚗 Дистанция: {dist_km} км")
        print(f"⏱  Время:     {time_str} (при свободных дорогах)")
        print("-" * 30)
    else:
        print("❌ Не удалось построить маршрут. Возможно, сервер перегружен.")

if __name__ == "__main__":
    if "ВАШ_КЛЮЧ" in YANDEX_API_KEY:
        print("⚠️ ОШИБКА: Вставьте API ключ Яндекса в код!")
    else:
        main()