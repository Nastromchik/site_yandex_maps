const https = require('https');

// === НАСТРОЙКИ ===
// Ваш ключ Яндекс (он работает через HTTPS, его корп. сеть обычно пропускает)
const YANDEX_KEY = '40c0ece5-dbf1-44cf-97f9-1a0e1a5f0ef7'; 
const TRAFF_COEFF = 1.4; 
const CHECK_CANDIDATES = 3; 

const people = [
    "Москва, Красная площадь, 1",
    "Москва, ул. Остоженка, 10",
    "Москва, ВДНХ",
    "Москва, МГУ",
    "Москва, Бутово, Скобелевская 1",
    "Москва, Зеленоград, корп 100",
    "Москва, 1-я Парковая ул. 54"
];

const hospitals = [
    { name: "НИИ Склифосовского", address: "Москва, Большая Сухаревская площадь, 3" },
    { name: "Боткинская больница", address: "Москва, 2-й Боткинский проезд, 5" },
    { name: "Первая Градская (ГКБ №1)", address: "Москва, Ленинский проспект, 8" },
    { name: "ГКБ №15 им. Филатова", address: "Москва, ул. Вешняковская, 23" },
    { name: "ГКБ №67 им. Ворохобова", address: "Москва, ул. Саляма Адиля, 2" },
    { name: "ГКБ №52", address: "Москва, ул. Пехотная, 3" },
    { name: "ГКБ №31", address: "Москва, ул. Лобачевского, 42" },
    { name: "ММКЦ Коммунарка", address: "Москва, ул. Сосенский Стан, 8" },
    { name: "ГКБ Зеленоград", address: "Москва, Зеленоград, Каштановая аллея, 2" }
];

// === СЕТЕВАЯ ФУНКЦИЯ (Вместо Axios/Fetch) ===
// Умеет работать без установки библиотек и обходит SSL-ошибки
function nativeRequest(url) {
    return new Promise((resolve, reject) => {
        // Опции для обхода корпоративных прокси с подменой сертификатов
        const options = {
            headers: { 'User-Agent': 'Mozilla/5.0' },
            rejectUnauthorized: false // <--- ЭТО ВАЖНО! Игнорирует ошибки сертификатов
        };

        https.get(url, options, (res) => {
            let data = '';

            // Получаем данные кусками
            res.on('data', (chunk) => { data += chunk; });

            // Когда все пришло
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(data));
                    } catch (e) {
                        reject(new Error("Ошибка парсинга JSON"));
                    }
                } else {
                    reject(new Error(`HTTP статус: ${res.statusCode}`));
                }
            });

        }).on('error', (err) => {
            reject(err);
        });
    });
}

const delay = ms => new Promise(r => setTimeout(r, ms));

// === ЛОГИКА ===

// 1. Геокодер Яндекс (Самый надежный в РФ)
async function getCoords(address) {
    const url = `https://geocode-maps.yandex.ru/1.x/?apikey=${YANDEX_KEY}&format=json&geocode=${encodeURIComponent(address)}&results=1`;
    
    try {
        const data = await nativeRequest(url);
        const featureMember = data.response.GeoObjectCollection.featureMember;
        
        if (featureMember && featureMember.length > 0) {
            const pos = featureMember[0].GeoObject.Point.pos;
            const [lon, lat] = pos.split(' ').map(Number);
            return { lat, lon };
        }
        return null;
    } catch (e) {
        console.error(`   ⚠️ Ошибка геокодера: ${e.message}`);
        return null;
    }
}

// 2. Маршруты OSRM (Через HTTPS)
async function getRoute(start, end) {
    // Используем HTTPS версию OSRM
    const url = `https://router.project-osrm.org/route/v1/driving/${start.lon},${start.lat};${end.lon},${end.lat}?overview=false`;
    
    try {
        const data = await nativeRequest(url);
        if (data.code === 'Ok') {
            return {
                dist: data.routes[0].distance / 1000,
                time: (data.routes[0].duration / 60) * TRAFF_COEFF
            };
        }
        return null;
    } catch (e) {
        // Если OSRM недоступен, вернем null, программа продолжит работу
        return null;
    }
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

// === MAIN ===
async function main() {
    console.log(`🛡️ Запуск в режиме Native HTTPS (обход прокси)...`);
    
    const activeHospitals = [];
    console.log(`🏥 Загрузка координат больниц...`);
    
    for (const h of hospitals) {
        const coords = await getCoords(h.address);
        if (coords) activeHospitals.push({ ...h, coords });
        // Пауза не нужна для Яндекса, он быстрый
    }
    console.log(`✅ Готово. Найдено больниц: ${activeHospitals.length}\n`);

    for (let i = 0; i < people.length; i++) {
        const personAddr = people[i];
        console.log(`👤 Пациент: "${personAddr}"`);

        const personCoords = await getCoords(personAddr);
        if (!personCoords) {
            console.log("   ❌ Адрес не найден");
            console.log("-".repeat(30));
            continue;
        }

        // 1. Сортировка по прямой
        const candidates = activeHospitals.map(h => ({
             ...h, tempDist: getDirectDist(personCoords, h.coords) 
        })).sort((a, b) => a.tempDist - b.tempDist);

        // 2. Топ-3 реальных маршрута
        const checkList = candidates.slice(0, CHECK_CANDIDATES);
        let best = null;
        let minTime = Infinity;

        for (const h of checkList) {
            const route = await getRoute(personCoords, h.coords);
            await delay(200); // Пауза для OSRM (чтобы не забанил)

            if (route && route.time < minTime) {
                minTime = route.time;
                best = { ...h, route };
            }
        }

        if (best) {
            console.log(`   🚑 Ехать в: ${best.name}`);
            console.log(`   ⏱️ Время: ~${Math.round(best.route.time)} мин (${best.route.dist.toFixed(1)} км)`);
        } else {
            console.log("   ⚠️ Маршрут по дорогам не построен (OSRM занят), но ближайшая по карте:");
            console.log(`   📍 ${checkList[0].name} (~${(checkList[0].tempDist/1000).toFixed(1)} км по прямой)`);
        }
        console.log("-".repeat(40));
    }
}

main();