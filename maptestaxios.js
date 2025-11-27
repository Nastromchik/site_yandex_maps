const axios = require('axios');

// === ВСТАВЬТЕ СЮДА ВАШ КЛЮЧ GRAPH_HOPPER ===
// Получить бесплатно тут: https://graphhopper.com/dashboard/#/api-keys
const API_KEY = 'ВСТАВЬТЕ_ВАШ_КЛЮЧ_СЮДА'; 

const CHECK_CANDIDATES = 3; // Проверяем 3 ближайших больницы

const people = [
    "Москва, Красная площадь, 1",
    "Москва, ул. Остоженка, 10",
    "Москва, ВДНХ",
    "Москва, МГУ",
    "Москва, Бутово, Скобелевская 1",
    "Москва, 1-я Парковая ул. 54",
    "Москва, Митино, Пятницкое шоссе, 15",
    "Москва, Зеленоград, корп. 100",
    "Москва, Коммунарка, Липовый парк 2"
];

const hospitals = [
    { name: "НИИ Склифосовского", address: "Москва, Большая Сухаревская площадь, 3" },
    { name: "Боткинская больница", address: "Москва, 2-й Боткинский проезд, 5" },
    { name: "Первая Градская (ГКБ №1)", address: "Москва, Ленинский проспект, 8" },
    { name: "ГКБ №15 им. Филатова", address: "Москва, ул. Вешняковская, 23" },
    { name: "ГКБ №67 им. Ворохобова", address: "Москва, ул. Саляма Адиля, 2" },
    { name: "ГКБ №4 (Павловская)", address: "Москва, ул. Павловская, 25" },
    { name: "ГКБ №52", address: "Москва, ул. Пехотная, 3" },
    { name: "ГКБ №31", address: "Москва, ул. Лобачевского, 42" },
    { name: "ММКЦ Коммунарка", address: "Москва, ул. Сосенский Стан, 8" },
    { name: "ГКБ №3 Зеленоград", address: "Москва, Зеленоград, Каштановая аллея, 2" }
];

// === ФУНКЦИИ ===
const delay = ms => new Promise(r => setTimeout(r, ms));

// 1. Геокодер GraphHopper
async function getCoords(address) {
    // Если ключ не вставили
    if (API_KEY.includes('ВСТАВЬТЕ')) {
        console.error("⛔ ОШИБКА: Вы забыли вставить API ключ в начале скрипта!");
        process.exit(1);
    }

    try {
        const url = `https://graphhopper.com/api/1/geocode`;
        const res = await axios.get(url, {
            params: {
                q: address,
                locale: 'ru',
                limit: 1,
                key: API_KEY
            }
        });

        if (res.data.hits && res.data.hits.length > 0) {
            const point = res.data.hits[0].point;
            return { lat: point.lat, lon: point.lng };
        }
        return null;
    } catch (e) {
        console.error(`   ⚠️ Ошибка поиска "${address}": ${e.response ? e.response.status : e.message}`);
        return null;
    }
}

// 2. Маршрутизатор GraphHopper
async function getRoute(start, end) {
    try {
        const url = `https://graphhopper.com/api/1/route`;
        const res = await axios.get(url, {
            params: {
                point: [`${start.lat},${start.lon}`, `${end.lat},${end.lon}`],
                profile: 'car',
                locale: 'ru',
                calc_points: false, // Не возвращать геометрию (экономим трафик)
                key: API_KEY
            }
        });

        const path = res.data.paths[0];
        return {
            dist: path.distance / 1000, // метры -> км
            time: path.time / 60000     // миллисекунды -> минуты
        };
    } catch (e) {
        // console.error(`⚠️ Ошибка маршрута: ${e.message}`);
        return null;
    }
}

// Расстояние по прямой (для сортировки)
function getDirectDist(c1, c2) {
    const R = 6371e3; 
    const toRad = x => x * Math.PI / 180;
    const dLat = toRad(c2.lat - c1.lat);
    const dLon = toRad(c2.lon - c1.lon);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(toRad(c1.lat)) * Math.cos(toRad(c2.lat)) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

// === ГЛАВНАЯ ЛОГИКА ===

async function main() {
    console.log(`🚀 Запуск через GraphHopper API (Стабильно)...`);
    
    const activeHospitals = [];
    console.log(`🏥 Геокодируем базу больниц (${hospitals.length} шт)...`);
    
    for (const h of hospitals) {
        const coords = await getCoords(h.address);
        if (coords) activeHospitals.push({ ...h, coords });
        // Лимиты GraphHopper мягкие, но пауза 50мс не помешает
        await delay(50);
    }
    console.log(`✅ База готова: ${activeHospitals.length} больниц.\n`);

    for (let i = 0; i < people.length; i++) {
        const personAddr = people[i];
        console.log(`👤 [${i+1}/${people.length}] Пациент: "${personAddr}"`);

        const personCoords = await getCoords(personAddr);
        if (!personCoords) {
            console.log("   ❌ Адрес не найден");
            console.log("-".repeat(30));
            continue;
        }

        // 1. Быстрая сортировка по прямой
        const candidates = activeHospitals.map(h => ({
             ...h, tempDist: getDirectDist(personCoords, h.coords) 
        })).sort((a, b) => a.tempDist - b.tempDist);

        // 2. Проверка маршрутов для ТОП-3
        const checkList = candidates.slice(0, CHECK_CANDIDATES);
        let best = null;
        let minTime = Infinity;

        for (const h of checkList) {
            const route = await getRoute(personCoords, h.coords);
            await delay(100); 

            if (route && route.time < minTime) {
                minTime = route.time;
                best = { ...h, route };
            }
        }

        if (best) {
            console.log(`   🚑 Ехать в: ${best.name}`);
            console.log(`   📍 Адрес: ${best.address}`);
            console.log(`   ⏱️ Время: ~${Math.round(best.route.time)} мин (${best.route.dist.toFixed(1)} км)`);
        } else {
            console.log("   ⚠️ Маршруты не найдены");
        }
        console.log("-".repeat(40));
    }
}

main();