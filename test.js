const url = "https://geocode-maps.yandex.ru/1.x/?apikey=40c0ece5-dbf1-44cf-97f9-1a0e1a5f0ef7&format=json&geocode=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D0%9C%D0%93%D0%A3%20(%D0%92%D0%BE%D1%80%D0%BE%D0%B1%D1%8C%D0%B5%D0%B2%D1%8B%20%D0%B3%D0%BE%D1%80%D1%8B)&bbox=36.800000,55.100000~38.200000,56.400000&rspn=1";

async function main() {
    try {
        console.log("📡 Запрос к API...");
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        const data = await response.json();

        // Извлекаем pos из структуры:
        // response -> GeoObjectCollection -> featureMember[0] -> GeoObject -> Point -> pos
        const [lat,lon] = data?.response?.GeoObjectCollection?.featureMember?.[0]?.GeoObject?.Point?.pos.split(' ').map(Number);

        if ([lat,lon]) {
            console.log("\n✅ Найдено значение POS:");
            //console.log(pos);
            console.log(lat,lon);
        } else {
            console.log("\n❌ Значение POS не найдено в ответе.");
        }

    } catch (error) {
        console.error("\n⛔ Произошла ошибка:", error.message);
    }
}

main();