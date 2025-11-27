
// Вариант расчета через API(более медленный но должен быть более точный)

// === НАСТРОЙКИ ===
const API_KEY = ''; // API Ключ Яндекс
const TRAFF_COEFF = 1.4; // Коэффициент пробок

const people = [
    "Красная площадь, 1",
    "Москва, ул. Остоженка, 10",
    "Москва, ВДНХ (главный вход)",
    "Москва, МГУ (Воробьевы горы)",
    "Москва, район Бутово, ул. Скобелевская 1",
    "1-я Парковая ул. 54",
    "Москва, 1-я парковая ул. 1",
    "Москва, Космодамианская набережная, 4/22с8"
];

const hospitals = [
    { name: "НИИ Склифосовского", address: "Москва, Большая Сухаревская площадь, 3" },
    { name: "Боткинская больница", address: "Москва, 2-й Боткинский проезд, 5" },
    { name: "Первая Градская (ГКБ №1)", address: "Москва, Ленинский проспект, 8" },
    { name: "ГКБ №15 им. Филатова", address: "Москва, ул. Вешняковская, 23" },
    { name: "ГКБ №67 им. Ворохобова", address: "Москва, ул. Саляма Адиля, 2/44" },
    {name: "Тест", address:"Москва, Котельническая набережная, 1/15кА"},
    {name: "Тест2", address:"Москва, Китайгородский проезд, 9/5с12"}
];

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

// 1. Получение координат (Яндекс Геокодер)
async function getCoords(address) {
    const moscowBbox = "37.300000,55.500000~38.000000,56.050000"; 
    const url = `https://geocode-maps.yandex.ru/1.x/?apikey=${API_KEY}&format=json&geocode=${encodeURIComponent(address)}&bbox=${moscowBbox}&rspn=1`;
    
    try {
        const res = await fetch(url);
        const data = await res.json();
        const featureMember = data.response.GeoObjectCollection.featureMember;
        
        if (!featureMember || featureMember.length === 0) return null;

        const pos = featureMember[0].GeoObject.Point.pos;
        const [lon, lat] = pos.split(' ').map(Number);
        return { lat, lon };
    } catch (e) {
        console.error("Ошибка геокодинга:", e.message);
        return null;
    }
}

// 2. Построение маршрута (OSRM)

async function getRoute(start, end) {
    const url = `http://router.project-osrm.org/route/v1/driving/${start.lon},${start.lat};${end.lon},${end.lat}?overview=false`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.code !== 'Ok') return null;
        
        const durationMin = (data.routes[0].duration / 60) * TRAFF_COEFF;
        const distanceKm = data.routes[0].distance / 1000;

        return {
            dist: distanceKm,      // Дистанция в км (число)
            time: durationMin      // Время в минутах с учетом пробок (число)
        };
    } catch (e) {
        return null;
    }
}

// Пауза
const delay = ms => new Promise(r => setTimeout(r, ms));

// === ГЛАВНАЯ ЛОГИКА ===

async function main() {
    console.log(`🏥 Загружаем координаты больниц (${hospitals.length} шт)...`);
    
    // 1. Геокодируем больницы
    const activeHospitals = [];
    for (const h of hospitals) {
        const coords = await getCoords(h.address);
        if (coords) activeHospitals.push({ ...h, coords });
    }
    console.log("✅ Больницы найдены. Начинаем расчет реальных маршрутов.\n");

    // 2. Проходим по каждому человеку
    for (let i = 0; i < people.length; i++) {
        const personAddr = people[i];
        console.log(`👤 [${i+1}/${people.length}] Пациент: "${personAddr}"`);

        // А. Ищем координаты человека
        const personCoords = await getCoords(personAddr);
        
        if (!personCoords) {
            console.log(`   ❌ Ошибка: Не удалось найти адрес человека.`);
            console.log("-".repeat(40));
            continue;
        }

        // Б. Перебираем ВСЕ больницы и строим маршруты
        let bestHospital = null;
        let bestRoute = null;
        let minTime = Infinity; // Будем искать минимальное время

        // Используем цикл for...of чтобы работал await
        for (const hospital of activeHospitals) {
            // Строим маршрут
            const route = await getRoute(personCoords, hospital.coords);
            
            // Небольшая задержка, чтобы OSRM не забанил за частые запросы
            await delay(150); 

            if (route) {
                // Сравниваем время. Если нашли быстрее - запоминаем
                if (route.time < minTime) {
                    minTime = route.time;
                    bestHospital = hospital;
                    bestRoute = route;
                }
            }
        }

        // В. Вывод результатов
        if (bestHospital && bestRoute) {
            console.log(`   🚑 Самая быстрая больница: ${bestHospital.name}`);
            console.log(`   📍 Адрес: ${bestHospital.address}`);
            console.log(`   🚗 Время в пути: ~${Math.round(bestRoute.time)} мин.`);
            console.log(`   📏 Расстояние: ${bestRoute.dist.toFixed(1)} км.`);
        } else {
            console.log("   ❌ Не удалось построить маршруты ни к одной больнице.");
        }
        
        console.log("-".repeat(40));
    }
}

// Запуск
main();