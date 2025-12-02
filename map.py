import requests
from geopy.geocoders import Nominatim
import time
import urllib3

# Отключаем надоедливые предупреждения о небезопасном соединении (из-за verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. НАСТРОЙКИ ПРОКСИ (ЗАПОЛНИТЕ ЭТО!)
# ==========================================
# Если прокси без пароля: "http://адрес:порт"
# Если с паролем: "http://логин:пароль@адрес:порт"

# Пример: "http://10.10.0.1:8080"
MY_PROXY = ""  

# Если оставите кавычки пустыми (""), скрипт попробует найти прокси системы сам.
# ==========================================

START_ADDRESS = "тверская 6"
END_ADDRESS   = "парк горького"

def get_proxies():
    if not MY_PROXY:
        return None
    return {
        "http": MY_PROXY,
        "https": MY_PROXY
    }

def get_coords_osm(address_text):
    # geopy сложно настроить через словарь прокси напрямую, 
    # поэтому используем requests + Nominatim API вручную
    
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{address_text}, Москва, Россия",
        "format": "json",
        "limit": 1
    }
    
    headers = {
        "User-Agent": "MoscowWorkScript/1.0" 
    }

    try:
        # verify=False ОЧЕНЬ ВАЖЕН для рабочих сетей
        response = requests.get(
            base_url, 
            params=params, 
            headers=headers, 
            proxies=get_proxies(), 
            verify=False,
            timeout=10
        )
        
        data = response.json()
        if data:
            item = data[0]
            return float(item["lat"]), float(item["lon"]), item["display_name"]
        else:
            return None
    except Exception as e:
        print(f"Ошибка поиска адреса: {e}")
        return None

def get_route_osrm(start_lat, start_lon, end_lat, end_lon):
    base_url = "https://routing.openstreetmap.de/routed-car/route/v1/driving/"
    coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base_url}{coordinates}?overview=false"
    
    try:
        response = requests.get(
            url, 
            proxies=get_proxies(), 
            verify=False, # Игнорируем ошибки сертификатов корпоративной сети
            timeout=10
        )
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        if data.get("code") == "Ok":
            return data["routes"][0]["distance"], data["routes"][0]["duration"]
        return None
    except Exception as e:
        print(f"Ошибка маршрута: {e}")
        return None

def main():
    print("=== Поиск маршрута (Корпоративный режим) ===")
    
    if MY_PROXY:
        print(f"⚙️ Используем прокси: {MY_PROXY}")
    else:
        print("⚙️ Пробуем системные настройки (без явного прокси)...")

    # 1. Поиск координат
    loc_a = get_coords_osm(START_ADDRESS)
    time.sleep(1) # Вежливость
    loc_b = get_coords_osm(END_ADDRESS)

    if not loc_a or not loc_b:
        print("❌ Не удалось найти адреса. Проверьте настройки прокси.")
        return

    print(f"✅ Точка А: {loc_a[2]}")
    print(f"✅ Точка Б: {loc_b[2]}")

    # 2. Маршрут
    result = get_route_osrm(loc_a[0], loc_a[1], loc_b[0], loc_b[1])

    if result:
        dist_km = round(result[0] / 1000, 2)
        time_min = int(result[1] // 60)
        print("="*30)
        print(f"🛣  Расстояние: {dist_km} км")
        print(f"⏱  Время: ~{time_min} мин")
        print("="*30)
    else:
        print("❌ Ошибка построения маршрута.")

if __name__ == "__main__":
    main()