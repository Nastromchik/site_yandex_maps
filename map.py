import requests
from geopy.geocoders import Nominatim
import time

# ==========================================
# 1. ВВОД АДРЕСОВ (Можно писать с маленькой буквы)
# ==========================================
START_ADDRESS = "тверская 6"       # Точка А
END_ADDRESS   = "парк горького"    # Точка Б
# ==========================================

def get_coords_osm(address_text):
    """
    Ищет координаты через бесплатный Nominatim (OpenStreetMap).
    """
    # Создаем геокодер. ВАЖНО: user_agent должен быть уникальным, иначе заблокируют.
    geolocator = Nominatim(user_agent="moscow_simple_router_v2")
    
    # Уточняем, что ищем в Москве, Россия
    query = f"{address_text}, Москва, Россия"
    
    try:
        # language='ru' помогает получать адреса на русском
        location = geolocator.geocode(query, language='ru')
        
        if location:
            return location.latitude, location.longitude, location.address
        else:
            return None
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return None

def get_route_osrm(start_lat, start_lon, end_lat, end_lon):
    """
    Строит маршрут через защищенный немецкий сервер OSRM (HTTPS).
    """
    base_url = "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base_url}{coordinates}?overview=false"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data.get("code") == "Ok":
            route = data["routes"][0]
            return route["distance"], route["duration"]
        return None
    except Exception as e:
        print(f"Ошибка маршрутизации: {e}")
        return None

def main():
    print("=== Поиск маршрута (Без Яндекса / OpenStreetMap) ===")
    print(f"Запрос А: {START_ADDRESS}")
    print(f"Запрос Б: {END_ADDRESS}")
    print("-" * 40)

    # 1. Ищем координаты
    # Nominatim требует паузу между запросами (правила вежливости OSM), ждем 1 сек
    loc_a = get_coords_osm(START_ADDRESS)
    time.sleep(1.1) 
    loc_b = get_coords_osm(END_ADDRESS)

    if not loc_a:
        print(f"❌ Не удалось найти адрес: '{START_ADDRESS}'")
        print("💡 Совет: В бесплатной версии пишите адрес точнее (например, с пробелом: 'Тверская 1')")
        return
    if not loc_b:
        print(f"❌ Не удалось найти адрес: '{END_ADDRESS}'")
        return

    lat_a, lon_a, addr_a = loc_a
    lat_b, lon_b, addr_b = loc_b

    # Очищаем адрес для красивого вывода (убираем страну и индекс)
    short_addr_a = addr_a.split(", Москва")[0]
    short_addr_b = addr_b.split(", Москва")[0]

    print(f"✅ Найдено А: {short_addr_a}...")
    print(f"✅ Найдено Б: {short_addr_b}...")

    # 2. Считаем маршрут
    result = get_route_osrm(lat_a, lon_a, lat_b, lon_b)

    if result:
        dist_m, time_s = result
        dist_km = round(dist_m / 1000, 2)
        
        # Перевод времени
        time_min = int(time_s // 60)
        hours = time_min // 60
        minutes = time_min % 60
        
        time_str = f"{minutes} мин"
        if hours > 0:
            time_str = f"{hours} ч {minutes} мин"

        print("\n" + "=" * 30)
        print(f"🛣  Расстояние: {dist_km} км")
        print(f"⏱  Время:      ~{time_str}")
        print("=" * 30)
    else:
        print("❌ Не удалось построить маршрут.")

if __name__ == "__main__":
    main()