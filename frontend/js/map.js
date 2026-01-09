/**
 * Управление картой и построением маршрутов
 */

let map = null;
let startMarker = null;
let routeLayer = null;
let markersLayer = null;
let currentRoute = null;

/**
 * Инициализация карты
 */
function initMap() {
    // Создаем карту с центром на Москве
    map = L.map('map').setView([55.7539, 37.6208], 11);

    // Добавляем тайлы OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18,
    }).addTo(map);

    // Слои для маршрута и маркеров
    routeLayer = L.layerGroup().addTo(map);
    markersLayer = L.layerGroup().addTo(map);

    // Обработчик клика по карте
    map.on('click', onMapClick);

    console.log('Карта инициализирована');
}

/**
 * Обработчик клика по карте
 */
function onMapClick(e) {
    const { lat, lng } = e.latlng;
    
    // Устанавливаем маркер начальной точки
    setStartPoint(lat, lng);
    
    // Обновляем координаты в форме
    document.getElementById('start-lat').value = lat.toFixed(6);
    document.getElementById('start-lon').value = lng.toFixed(6);
    
    // Получаем адрес (обратное геокодирование)
    reverseGeocode(lat, lng);
}

/**
 * Установить точку старта
 */
function setStartPoint(lat, lng) {
    // Удаляем предыдущий маркер
    if (startMarker) {
        map.removeLayer(startMarker);
    }

    // Создаем новый маркер
    const icon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    startMarker = L.marker([lat, lng], { icon: icon })
        .addTo(map)
        .bindPopup('<b>Точка старта</b>')
        .openPopup();
}

/**
 * Обратное геокодирование (получение адреса по координатам)
 */
async function reverseGeocode(lat, lng) {
    try {
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
            {
                headers: {
                    'Accept-Language': 'ru'
                }
            }
        );
        
        const data = await response.json();
        
        if (data.display_name) {
            document.getElementById('start-address').value = data.display_name;
        }
    } catch (error) {
        console.error('Ошибка геокодирования:', error);
    }
}

/**
 * Построить маршрут
 */
async function buildRoute() {
    const lat = parseFloat(document.getElementById('start-lat').value);
    const lng = parseFloat(document.getElementById('start-lon').value);
    const objectsCount = parseInt(document.getElementById('objects-count').value);
    const startAddress = document.getElementById('start-address').value;

    // Валидация
    if (!lat || !lng) {
        showMessage('Пожалуйста, выберите точку старта на карте', 'error');
        return;
    }

    if (objectsCount < 2 || objectsCount > 20) {
        showMessage('Количество объектов должно быть от 2 до 20', 'error');
        return;
    }

    // Показываем загрузку
    showLoading(true);
    clearRoute();

    try {
        // Отправляем запрос на построение маршрута
        const route = await api.buildRoute(
            { latitude: lat, longitude: lng },
            objectsCount,
            startAddress
        );

        currentRoute = route;
        displayRoute(route);
        showMessage('Маршрут успешно построен!', 'success');
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Отобразить маршрут на карте
 */
function displayRoute(route) {
    // Очищаем предыдущий маршрут
    clearRoute();

    const objects = route.objects;
    const startLat = route.start_location.latitude;
    const startLon = route.start_location.longitude;

    // Массив координат для линии маршрута
    const routeCoords = [[startLat, startLon]];

    // Добавляем маркеры объектов
    objects.forEach((item, index) => {
        const obj = item.object;
        const coords = [obj.latitude, obj.longitude];
        routeCoords.push(coords);

        // Создаем маркер
        const marker = L.marker(coords)
            .addTo(markersLayer)
            .bindPopup(`
                <div style="min-width: 200px;">
                    <b>${index + 1}. ${obj.name}</b><br>
                    <small>${obj.address}</small><br>
                    ${obj.object_type ? `<span style="color: #3498db;">${obj.object_type}</span><br>` : ''}
                    ${item.distance_from_previous ? `<span style="color: #e74c3c;">📍 ${formatDistance(item.distance_from_previous)}</span>` : ''}
                </div>
            `);

        // Обработчик клика на маркер
        marker.on('click', () => {
            highlightObject(index);
        });
    });

    // Рисуем линию маршрута
    const polyline = L.polyline(routeCoords, {
        color: '#3498db',
        weight: 3,
        opacity: 0.7,
        dashArray: '10, 5'
    }).addTo(routeLayer);

    // Центрируем карту на маршруте
    map.fitBounds(polyline.getBounds(), { padding: [50, 50] });

    // Отображаем информацию о маршруте
    displayRouteInfo(route);
}

/**
 * Отобразить информацию о маршруте
 */
function displayRouteInfo(route) {
    const resultsDiv = document.getElementById('route-results');
    
    const html = `
        <div class="route-info">
            <div class="info-item">
                <div class="label">Объектов</div>
                <div class="value">${route.objects_count}</div>
            </div>
            <div class="info-item">
                <div class="label">Общее расстояние</div>
                <div class="value">${formatDistance(route.total_distance)}</div>
            </div>
            <div class="info-item">
                <div class="label">Дата построения</div>
                <div class="value">${new Date(route.created_at).toLocaleString('ru-RU')}</div>
            </div>
        </div>

        <h3 style="margin-bottom: 1rem;">Маршрут</h3>
        <div class="objects-list">
            ${route.objects.map((item, index) => renderObjectCard(item, index)).join('')}
        </div>
    `;

    resultsDiv.innerHTML = html;
    resultsDiv.classList.remove('hidden');
}

/**
 * Отрисовка карточки объекта
 */
function renderObjectCard(item, index) {
    const obj = item.object;
    
    return `
        <div class="object-card" data-index="${index}" onclick="focusOnObject(${index})">
            <div class="object-card-header">
                <div class="object-number">${index + 1}</div>
                <div class="object-info">
                    <div class="object-name">${obj.name}</div>
                    <div class="object-address">📍 ${obj.address}</div>
                    ${obj.district ? `<div class="object-address">🏘️ ${obj.district}</div>` : ''}
                    ${obj.object_type ? `<span class="object-type">${obj.object_type}</span>` : ''}
                    ${item.distance_from_previous ? `<div class="object-distance">📏 ${formatDistance(item.distance_from_previous)} от предыдущей точки</div>` : ''}
                    ${obj.description ? `<div style="margin-top: 0.5rem; color: #666; font-size: 0.9rem;">${obj.description}</div>` : ''}
                </div>
            </div>
        </div>
    `;
}

/**
 * Фокус на объекте
 */
function focusOnObject(index) {
    if (!currentRoute) return;
    
    const obj = currentRoute.objects[index].object;
    map.setView([obj.latitude, obj.longitude], 16);
    highlightObject(index);
}

/**
 * Подсветить объект
 */
function highlightObject(index) {
    // Убираем подсветку со всех карточек
    document.querySelectorAll('.object-card').forEach(card => {
        card.style.borderColor = '#ddd';
    });
    
    // Подсвечиваем выбранную
    const card = document.querySelector(`[data-index="${index}"]`);
    if (card) {
        card.style.borderColor = '#3498db';
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

/**
 * Очистить маршрут
 */
function clearRoute() {
    if (routeLayer) {
        routeLayer.clearLayers();
    }
    if (markersLayer) {
        markersLayer.clearLayers();
    }
    
    document.getElementById('route-results').classList.add('hidden');
    currentRoute = null;
}

/**
 * Форматирование расстояния
 */
function formatDistance(meters) {
    if (meters < 1000) {
        return `${Math.round(meters)} м`;
    } else {
        return `${(meters / 1000).toFixed(2)} км`;
    }
}

/**
 * Показать сообщение
 */
function showMessage(text, type = 'info') {
    const messageDiv = document.getElementById('message');
    messageDiv.className = `message message-${type}`;
    messageDiv.textContent = text;
    messageDiv.classList.remove('hidden');
    
    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

/**
 * Показать/скрыть загрузку
 */
function showLoading(show) {
    const btn = document.getElementById('build-route-btn');
    btn.disabled = show;
    btn.textContent = show ? 'Построение маршрута...' : 'Построить маршрут';
}

/**
 * Инициализация страницы
 */
document.addEventListener('DOMContentLoaded', () => {
    // Проверка авторизации
    if (!api.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Инициализация карты
    initMap();

    // Обработчик формы
    document.getElementById('build-route-btn').addEventListener('click', buildRoute);

    // Отображение пользователя
    if (api.user) {
        document.getElementById('user-name').textContent = api.user.username;
    }

    // Обработчик выхода
    document.getElementById('logout-btn').addEventListener('click', () => {
        api.logout();
    });
});

