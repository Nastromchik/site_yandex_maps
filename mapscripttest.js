// === НАСТРОЙКИ ===
const API_KEY = ''; // API Ключ Яндекс (для поиска координат)

// 1. Список людей (начальные точки)
const people = [
    "Москва, Красная площадь, 1",
    "Москва, ул. Остоженка, 10",
    "Москва, ВДНХ (главный вход)",
    "Москва, МГУ (Воробьевы горы)",
    "Москва, район Бутово, ул. Скобелевская 1",
    "Москва, 9-я Парковая ул. 68"
];

// 2. Список больниц (целевые точки)
const hospitals = [
    { name: "НИИ Склифосовского", address: "Москва, Большая Сухаревская площадь, 3" },
    { name: "Боткинская больница", address: "Москва, 2-й Боткинский проезд, 5" },
    { name: "Первая Градская (ГКБ №1)", address: "Москва, Ленинский проспект, 8" },
    { name: "ГКБ №15 им. Филатова", address: "Москва, ул. Вешняковская, 23" },
    { name: "ГКБ №67 им. Ворохобова", address: "Москва, ул. Саляма Адиля, 2/44" }
];

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

// Получение координат (Яндекс Геокодер)
async function getCoords(address) {
    const url = `https://geocode-maps.yandex.ru/1.x/?apikey=${API_KEY}&format=json&geocode=${encodeURIComponent(address)}`;
    try {
        const res = await fetch(url);
        const data = await res.json();
        // Парсим ответ: "lon lat" -> { lat, lon }
        const pos = data.response.GeoObjectCollection.featureMember[0]?.GeoObject?.Point?.pos;
        if (!pos) return null;
        const [lon, lat] = pos.split(' ').map(Number);
        return { lat, lon };
    } catch (e) {
        return null;
    }
}

// Построение маршрута (OSRM - бесплатный сервис маршрутизации)
async function getRoute(start, end) {
    // OSRM требует порядок: lon,lat
    const url = `http://router.project-osrm.org/route/v1/driving/${start.lon},${start.lat};${end.lon},${end.lat}?overview=false`;
    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.code !== 'Ok') return null;
        return {
            dist: (data.routes[0].distance / 1000).toFixed(1), // км
            time: Math.round(data.routes[0].duration / 60)      // минуты
        };
    } catch (e) {
        return null;
    }
}

// Расчет расстояния по прямой (формула Хаверсина)
function getDirectDist(c1, c2) {
    const R = 6371e3; // Радиус Земли
    const toRad = x => x * Math.PI / 180;
    const dLat = toRad(c2.lat - c1.lat);
    const dLon = toRad(c2.lon - c1.lon);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(toRad(c1.lat)) * Math.cos(toRad(c2.lat)) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// Пауза (чтобы не спамить запросами)
const delay = ms => new Promise(r => setTimeout(r, ms));

// === ГЛАВНАЯ ЛОГИКА ===

async function main() {
    console.log(`🏥 Загружаем координаты больниц (${hospitals.length} шт)...`);
    
    // 1. Сначала геокодируем все больницы (один раз!)
    const activeHospitals = [];
    for (const h of hospitals) {
        const coords = await getCoords(h.address);
        if (coords) activeHospitals.push({ ...h, coords });
    }
    console.log("✅ Больницы найдены. Начинаем расчет для людей.\n");

    // 2. Проходим по каждому человеку
    for (let i = 0; i < people.length; i++) {
        const personAddr = people[i];
        console.log(`👤 [${i+1}/${people.length}] Обработка: "${personAddr}"`);

        // А. Ищем координаты человека
        const personCoords = await getCoords(personAddr);
        
        if (!personCoords) {
            console.log(`   ❌ Ошибка: Не удалось найти адрес человека.`);
            console.log("-".repeat(40));
            continue;
        }

        // Б. Ищем геометрически ближайшую больницу
        let bestHospital = null;
        let minDirectDist = Infinity;

        activeHospitals.forEach(h => {
            const dist = getDirectDist(personCoords, h.coords);
            if (dist < minDirectDist) {
                minDirectDist = dist;
                bestHospital = h;
            }
        });

        // В. Строим реальный маршрут
        if (bestHospital) {
            // Ждем чуть-чуть, чтобы API не забанил за частые запросы
            await delay(300); 
            const route = await getRoute(personCoords, bestHospital.coords);

            console.log(`   🚑 Едем в: ${bestHospital.name}`);
            console.log(`   📍 Адрес больницы: ${bestHospital.address}`);
            if (route) {
                console.log(`   🚗 Маршрут: ${route.dist} км, ~${route.time} мин.`);
            } else {
                console.log(`   ⚠️ Маршрут по дорогам не построен (ошибка OSRM), но это ближайшая точка.`);
            }
        } else {
            console.log("   ❌ Не найдено ни одной больницы.");
        }
        
        console.log("-".repeat(40));
    }
}

// Запуск
main();