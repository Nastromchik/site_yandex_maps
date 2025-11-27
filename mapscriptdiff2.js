// === НАСТРОЙКИ ===
const API_KEY = '40c0ece5-dbf1-44cf-97f9-1a0e1a5f0ef7'; // ⚠️ ВСТАВЬТЕ СЮДА ВАШ API КЛЮЧ ЯНДЕКС
const TRAFF_COEFF = 1.4; 
const CHECK_CANDIDATES = 3; 
const REQUEST_TIMEOUT = 5000; // 5 секунд тайм-аут

// === СПИСОК ПАЦИЕНТОВ ===
const people = [
    "Москва, Красная площадь, 1",
    "Москва, ул. Остоженка, 10",
    "Москва, ВДНХ (Главный вход)",
    "Москва, МГУ (Воробьевы горы)",
    "Москва, Южное Бутово, ул. Скобелевская 1",
    "Москва, Северное Бутово, бульвар Дмитрия Донского, 1",
    "Москва, 1-я Парковая ул. 54",
    "Москва, Митино, Пятницкое шоссе, 15",
    "Москва, Алтуфьевское шоссе, 100",
    "Москва, Выхино, ул. Хлобыстова, 10",
    "Москва, Крылатские холмы, 35",
    "Москва, Марьино, Новомарьинская ул., 5",
    "Москва, Ленинградский проспект, 75",
    "Москва, Таганская площадь, 1",
    "Москва, Хамовнический вал, 20",
    "Москва, Медведково, ул. Широкая, 12",
    "Москва, Строгино, ул. Исаковского, 2",
    "Москва, Ясенево, Литовский бульвар, 7",
    "Москва, Зеленоград, корп. 100",
    "Москва, пос. Коммунарка, ул. Липовый парк, 2"
];

// === СПИСОК БОЛЬНИЦ ===
const hospitals = [
    { name: "НИИ Склифосовского", address: "Москва, Большая Сухаревская площадь, 3" },
    { name: "Боткинская больница", address: "Москва, 2-й Боткинский проезд, 5" },
    { name: "Первая Градская (ГКБ №1)", address: "Москва, Ленинский проспект, 8" },
    { name: "ГКБ №15 им. Филатова", address: "Москва, ул. Вешняковская, 23" },
    { name: "ГКБ №67 им. Ворохобова", address: "Москва, ул. Саляма Адиля, 2/44" },
    { name: "ГКБ №20 им. Ерамишанцева", address: "Москва, ул. Ленская, 15" },
    { name: "ГКБ №4 (Павловская)", address: "Москва, ул. Павловская, 25" },
    { name: "ГКБ №52", address: "Москва, ул. Пехотная, 3" },
    { name: "ГКБ №31", address: "Москва, ул. Лобачевского, 42" },
    { name: "Морозовская ДГКБ", address: "Москва, 4-й Добрынинский переулок, 1/9" },
    { name: "ДГКБ им. Филатова", address: "Москва, ул. Садовая-Кудринская, 15" },
    { name: "ДГКБ св. Владимира", address: "Москва, ул. Рубцовско-Дворцовая, 1/3" },
    { name: "ГКБ №29 им. Баумана", address: "Москва, Госпитальная площадь, 2" },
    { name: "ГКБ №36 им. Иноземцева", address: "Москва, ул. Фортунатовская, 1" },
    { name: "ГКБ №50 им. Спасокукоцкого", address: "Москва, ул. Вучетича, 21" },
    { name: "ГКБ №24", address: "Москва, ул. Писцовая, 10" },
    { name: "ММКЦ Коммунарка (ГКБ 40)", address: "Москва, ул. Сосенский Стан, 8" },
    { name: "ГКБ №12 им. Буянова", address: "Москва, ул. Бакинская, 26" },
    { name: "ГКБ им. Юдина (№7)", address: "Москва, Коломенский проезд, 4" },
    { name: "ГКБ №68 им. Демихова", address: "Москва, ул. Шкулева, 4" },
    { name: "ГКБ №13", address: "Москва, ул. Велозаводская, 1/1" },
    { name: "ГКБ №51", address: "Москва, ул. Алябьева, 7/33" },
    { name: "ГКБ №17", address: "Москва, ул. Волынская, 7" },
    { name: "ГКБ №70 им. Мухина", address: "Москва, Федеративный проспект, 17" },
    { name: "ГКБ №64 им. Виноградова", address: "Москва, ул. Вавилова, 61" },
    { name: "ИКБ №1 (Инфекционная)", address: "Москва, Волоколамское шоссе, 63" },
    { name: "ИКБ №2 (Соколинка)", address: "Москва, 8-я улица Соколиной Горы, 15" },
    { name: "НИИ Нейрохирургии Бурденко", address: "Москва, ул. 4-я Тверская-Ямская, 16" },
    { name: "ЦКБ УДП РФ", address: "Москва, ул. Маршала Тимошенко, 15" },
    { name: "ГКБ №3 им. Кончаловского", address: "Москва, Зеленоград, Каштановая аллея, 2" }
];

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

function generateYandexUrl(address) {
    const moscowBbox = "36.800000,55.100000~38.200000,56.400000";
    // Генерируем ссылку, которую использует fetch
    return `https://geocode-maps.yandex.ru/1.x/?apikey=${API_KEY}&format=json&geocode=${encodeURIComponent(address)}&bbox=${moscowBbox}&rspn=1`;
}

async function fetchWithTimeout(url, options = {}) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
}

async function getCoords(address, url) {
    try {
        // url передаем снаружи, чтобы он был точно такой же, как в ссылке для пользователя
        const res = await fetchWithTimeout(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        const featureMember = data.response.GeoObjectCollection.featureMember;
        
        if (!featureMember || featureMember.length === 0) return null;
        
        const [lon, lat] = featureMember[0].GeoObject.Point.pos.split(' ').map(Number);
        return { lat, lon };
    } catch (e) {
        return null; // Ошибки обрабатываем выше
    }
}

async function getRoute(start, end) {
    const url = `https://router.project-osrm.org/route/v1/driving/${start.lon},${start.lat};${end.lon},${end.lat}?overview=false`;
    try {
        const res = await fetchWithTimeout(url);
        const data = await res.json();
        if (data.code !== 'Ok') return null;
        return {
            dist: data.routes[0].distance / 1000,
            time: (data.routes[0].duration / 60) * TRAFF_COEFF
        };
    } catch (e) { return null; }
}

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

function getYandexMapLink(from, to) {
    return `https://yandex.ru/maps/?rtext=${from.lat},${from.lon}~${to.lat},${to.lon}&rtt=auto`;
}

const delay = ms => new Promise(r => setTimeout(r, ms));

// === ЗАПУСК ===

async function main() {
    if (!API_KEY) {
        console.error("⛔ ОШИБКА: Нет API_KEY!"); 
        return;
    }

    console.log(`🏥 1. Геокодирование больниц...`);
    const activeHospitals = [];
    for (const h of hospitals) {
        const url = generateYandexUrl(h.address);
        const coords = await getCoords(h.address, url);
        if (coords) activeHospitals.push({ ...h, coords });
        await delay(50);
    }
    console.log(`✅ Больниц найдено: ${activeHospitals.length}\n`);

    for (let i = 0; i < people.length; i++) {
        const personAddr = people[i];
        console.log(`👤 [${i+1}/${people.length}] Пациент: "${personAddr}"`);

        // Генерируем URL здесь, чтобы показать его пользователю
        const jsonUrl = generateYandexUrl(personAddr);
        const personCoords = await getCoords(personAddr, jsonUrl);

        if (!personCoords) { 
            console.log("   ❌ Ошибка: Адрес не найден"); 
            console.log(`   🐛 JSON (Debug): ${jsonUrl}`); // Ссылка на JSON при ошибке
            console.log("-".repeat(40));
            continue; 
        }

        const candidates = activeHospitals.map(h => ({ ...h, tempDist: getDirectDist(personCoords, h.coords) }));
        candidates.sort((a, b) => a.tempDist - b.tempDist);
        const checkList = candidates.slice(0, CHECK_CANDIDATES);
        
        let bestHospital = null;
        let minTime = Infinity;
        let finalDistance = 0;

        for (const hospital of checkList) {
            const route = await getRoute(personCoords, hospital.coords);
            await delay(100);
            if (route && route.time < minTime) {
                minTime = route.time;
                bestHospital = hospital;
                finalDistance = route.dist;
            }
        }

        if (bestHospital) {
            console.log(`   🚑 Ехать в: ${bestHospital.name}`);
            console.log(`   ⏱️ Время: ~${Math.round(minTime)} мин`);
            console.log(`   🔗 Карта маршрута: ${getYandexMapLink(personCoords, bestHospital.coords)}`);
            // Ссылка на JSON для успешного поиска (на случай если координаты странные)
            console.log(`   🐛 JSON (Debug): ${jsonUrl}`); 
        } else {
            console.log("   ❌ Маршрут не построен");
        }
        console.log("-".repeat(40));
    }
}

main();