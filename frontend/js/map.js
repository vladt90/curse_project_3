/**
 * Управление картой и построением маршрутов (Яндекс.Карты)
 */

const MOSCOW_CENTER = [55.7539, 37.6208]; // [lat, lon]

let map = null;
let startMarker = null;
let routeLine = null;
let routeMultiRoute = null;
let markers = [];
let currentRoute = null;
let currentStart = null;
let favoriteRouteIds = new Set();
let storyCache = new Map();

/**
 * Инициализация карты
 */
function initMap() {
    map = new ymaps.Map('map', {
        center: MOSCOW_CENTER,
        zoom: 11,
        controls: ['zoomControl']
    });

    // Обработчик клика по карте
    map.events.add('click', onMapClick);
}

/**
 * Обработчик клика по карте
 */
function onMapClick(e) {
    const coords = e.get('coords'); // [lat, lon]
    const lat = coords?.[0];
    const lon = coords?.[1];

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        showMessage('Не удалось определить координаты точки', 'error');
        return;
    }

    // Устанавливаем маркер начальной точки
    setStartPoint(lat, lon);
    currentStart = { lat, lng: lon };

    // Обновляем координаты в форме
    document.getElementById('start-lat').value = lat.toFixed(6);
    document.getElementById('start-lon').value = lon.toFixed(6);

    // Получаем адрес (обратное геокодирование)
    reverseGeocode(lat, lon);
}

/**
 * Установить точку старта
 */
function setStartPoint(lat, lon) {
    if (startMarker) {
        map.geoObjects.remove(startMarker);
    }

    startMarker = new ymaps.Placemark([lat, lon], {
        balloonContent: '<b>Точка старта</b>'
    }, {
        preset: 'islands#greenIcon'
    });

    map.geoObjects.add(startMarker);
}

/**
 * Обратное геокодирование (Яндекс)
 */
async function reverseGeocode(lat, lon) {
    try {
        const data = await api.request(`/geocode/reverse?lat=${lat}&lon=${lon}`);
        if (data?.address) {
            document.getElementById('start-address').value = data.address;
        }
    } catch (error) {
        console.error('Ошибка геокодирования:', error);
    }
}

/**
 * Построить маршрут
 */
async function buildRoute() {
    let lat = parseFloat(document.getElementById('start-lat').value);
    let lon = parseFloat(document.getElementById('start-lon').value);
    const objectsCount = parseInt(document.getElementById('objects-count').value);
    const startAddress = document.getElementById('start-address').value;

    // Валидация
    if ((!Number.isFinite(lat) || !Number.isFinite(lon)) && currentStart) {
        lat = currentStart.lat;
        lon = currentStart.lng;
    }

    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        showMessage('Пожалуйста, выберите точку старта на карте', 'error');
        return;
    }

    if (objectsCount < 2 || objectsCount > 20) {
        showMessage('Количество объектов должно быть от 2 до 20', 'error');
        return;
    }

    // Показываем загрузку
    showLoading(true);
    currentRoute = null;
    clearRoute();

    try {
        // Отправляем запрос на построение маршрута
        const route = await api.buildRoute(
            { latitude: lat, longitude: lon },
            objectsCount,
            startAddress
        );

        currentRoute = route;
        await displayRoute(route);
        await loadRouteHistory();
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
async function displayRoute(route) {
    // Очищаем предыдущий маршрут
    clearRoute();

    const objects = [...route.objects].sort((a, b) => {
        if (Number.isFinite(a.sequence_number) && Number.isFinite(b.sequence_number)) {
            return a.sequence_number - b.sequence_number;
        }
        return 0;
    });
    const startLat = route.start_location.latitude;
    const startLon = route.start_location.longitude;

    // Массив координат для линии маршрута [lat, lon]
    const routeCoords = [[startLat, startLon]];

    // Добавляем маркеры объектов
    objects.forEach((item, index) => {
        const obj = item.object;
        const coords = [obj.latitude, obj.longitude];
        routeCoords.push(coords);

        const marker = new ymaps.Placemark(coords, {
            balloonContent: `
                <div style="min-width: 200px;">
                    <b>${index + 1}. ${obj.name}</b><br>
                    <small>${obj.address}</small><br>
                    ${obj.object_type ? `<span style="color: #3498db;">${obj.object_type}</span><br>` : ''}
                    ${item.distance_from_previous ? `<span style="color: #e74c3c;">• ${formatDistance(item.distance_from_previous)}</span>` : ''}
                </div>
            `
        }, {
            preset: 'islands#blueIcon'
        });

        marker.events.add('click', () => {
            highlightObject(index);
        });

        map.geoObjects.add(marker);
        markers.push(marker);
    });

    drawStraightRoute(routeCoords);

    // Отображаем информацию о маршруте
    displayRouteInfo(route);
}

/**
 * Отобразить информацию о маршруте
 */
function displayRouteInfo(route) {
    const resultsDiv = document.getElementById('route-results');
    const routeId = route.route_id;
    const isFavorite = routeId ? favoriteRouteIds.has(routeId) : false;
    // Кнопка в боковой панели была удалена — обновлять нечего.

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
        <div style="margin: 0.75rem 0;">
            <button id="toggle-favorite-btn" class="btn btn-primary">
                ${isFavorite ? 'Убрать из избранного' : 'Добавить в избранное'}
            </button>
        </div>

        <h3 style="margin-bottom: 1rem;">Маршрут</h3>
        <div class="objects-list">
            ${route.objects.map((item, index) => renderObjectCard(item, index)).join('')}
        </div>
    `;

    resultsDiv.innerHTML = html;
    resultsDiv.classList.remove('hidden');

    // Клики по карточкам объектов (вместо inline onclick, чтобы работало надежно)
    resultsDiv.querySelectorAll('.object-card').forEach(card => {
        card.addEventListener('click', () => {
            const idx = Number(card.getAttribute('data-index'));
            if (Number.isFinite(idx)) {
                focusOnObject(idx);
            }
        });
    });

    const favoriteButton = document.getElementById('toggle-favorite-btn');
    if (favoriteButton && routeId) {
        favoriteButton.addEventListener('click', async () => {
            try {
                const nextValue = !favoriteRouteIds.has(routeId);
                await api.setRouteFavorite(routeId, nextValue);
                await loadRouteHistory();
                favoriteButton.textContent = nextValue ? 'Убрать из избранного' : 'Добавить в избранное';
                showMessage(nextValue ? 'Маршрут добавлен в избранное' : 'Маршрут удален из избранного', 'success');
            } catch (error) {
                showMessage(error.message, 'error');
            }
        });
    }
}

/**
 * Отрисовка карточки объекта
 */
function renderObjectCard(item, index) {
    const obj = item.object;

    const iconPin = `
        <svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z"/>
        </svg>
    `;

    const iconDistrict = `
        <svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path fill="currentColor" d="M12 3l9 7v11a1 1 0 0 1-1 1h-5v-7H10v7H5a1 1 0 0 1-1-1V10l8-7Zm0 2.6L6 10v10h2v-7a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v7h2V10l-6-4.4Z"/>
        </svg>
    `;

    return `
        <div class="object-card" data-index="${index}">
            <div class="object-card-header">
                <div class="object-number">${index + 1}</div>
                <div class="object-info">
                    <div class="object-name">${obj.name}</div>
                    <div class="object-address"><span class="ui-icon-wrap">${iconPin}</span>${obj.address}</div>
                    ${obj.district ? `<div class="object-address"><span class="ui-icon-wrap">${iconDistrict}</span>${obj.district}</div>` : ''}
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
    map.setCenter([obj.latitude, obj.longitude], 16);
    highlightObject(index);
    openAiStoryModal(obj);
}

async function openAiStoryModal(obj) {
    if (!obj?.id) return;

    const modal = document.getElementById('ai-modal');
    const backdrop = document.getElementById('ai-modal-backdrop');
    const closeBtn = document.getElementById('ai-modal-close');
    const title = document.getElementById('ai-modal-title');
    const body = document.getElementById('ai-modal-body');
    if (!modal || !backdrop || !closeBtn || !title || !body) return;

    title.textContent = obj.name || 'Объект';
    body.textContent = 'Готовлю рассказ…';
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');

    const close = () => {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
    };

    backdrop.onclick = close;
    closeBtn.onclick = close;

    if (storyCache.has(obj.id)) {
        body.textContent = storyCache.get(obj.id);
        return;
    }

    try {
        const data = await api.getObjectStory(obj.id);
        const story = data?.story || 'Не удалось получить рассказ.';
        storyCache.set(obj.id, story);
        body.textContent = story;
    } catch (error) {
        body.textContent = error.message || 'Не удалось получить рассказ.';
    }
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
    if (routeLine) {
        map.geoObjects.remove(routeLine);
        routeLine = null;
    }
    markers.forEach(marker => map.geoObjects.remove(marker));
    markers = [];

    document.getElementById('route-results').classList.add('hidden');
}

function drawStraightRoute(routeCoords) {
    routeLine = new ymaps.Polyline(routeCoords, {}, {
        strokeColor: '#3498db',
        strokeWidth: 3,
        strokeOpacity: 0.7,
        strokeStyle: 'shortdash'
    });
    map.geoObjects.add(routeLine);
    const bounds = routeLine.geometry.getBounds();
    if (bounds) {
        map.setBounds(bounds, { checkZoomRange: true, zoomMargin: 50 });
    }
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
function onPageReady() {
    // Проверка авторизации
    if (!api.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Инициализация карты
    ymaps.ready(initMap);

    // История маршрутов
    loadRouteHistory();

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
}

// map.js может быть подгружен динамически после ymaps, когда DOMContentLoaded уже сработал
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', onPageReady);
} else {
    onPageReady();
}

// Делегирование кликов по карточкам объектов (надежнее, чем навешивать после рендера)
document.addEventListener('click', (event) => {
    const card = event.target?.closest?.('.object-card');
    if (!card) return;
    const idx = Number(card.getAttribute('data-index'));
    if (Number.isFinite(idx)) {
        focusOnObject(idx);
    }
});

/**
 * Загрузить историю маршрутов пользователя
 */
async function loadRouteHistory() {
    const list = document.getElementById('routes-list');
    if (!list) return;

    try {
        const data = await api.getRoutes();
        renderRouteHistory(data?.routes || []);
    } catch (error) {
        console.error('Ошибка загрузки истории маршрутов:', error);
        list.innerHTML = '<div style="color:#666;">Не удалось загрузить историю</div>';
    }
}

/**
 * Отрисовать историю маршрутов
 */
function renderRouteHistory(routes) {
    const list = document.getElementById('routes-list');
    if (!list) return;

    favoriteRouteIds = new Set(routes.filter(route => route.is_favorite).map(route => route.id));
    const favorites = routes.filter(route => route.is_favorite);

    if (!favorites.length) {
        list.innerHTML = '<div style="color:#666;">Избранных маршрутов пока нет</div>';
        return;
    }

    const html = favorites.map(route => `
        <div class="route-history-item" data-route-id="${route.id}">
            <div style="display:flex; align-items:center; justify-content:space-between;">
                <strong>Маршрут #${route.id}</strong>
                <button class="route-fav-btn" title="Убрать из избранного">★</button>
            </div>
            <div style="font-size: 0.9rem; color: #666;">
                ${route.start_address || 'Адрес не указан'}
            </div>
            <div style="font-size: 0.85rem; color: #888;">
                Объектов: ${route.objects_count} · ${formatDistance(route.total_distance)}
            </div>
            <div style="font-size: 0.85rem; color: #888;">
                ${new Date(route.created_at).toLocaleString('ru-RU')}
            </div>
        </div>
    `).join('');

    list.innerHTML = html;

    list.querySelectorAll('.route-history-item').forEach(item => {
        item.addEventListener('click', async (event) => {
            if (event.target?.classList?.contains('route-fav-btn')) {
                return;
            }
            const routeId = item.getAttribute('data-route-id');
            await openSavedRoute(routeId);
        });
    });

    list.querySelectorAll('.route-fav-btn').forEach(button => {
        button.addEventListener('click', async (event) => {
            event.stopPropagation();
            const routeId = event.target.closest('.route-history-item')?.getAttribute('data-route-id');
            if (!routeId) return;
            try {
                await api.setRouteFavorite(routeId, false);
                await loadRouteHistory();
                showMessage('Маршрут удален из избранного', 'success');
            } catch (error) {
                showMessage(error.message, 'error');
            }
        });
    });
}

/**
 * Открыть сохраненный маршрут
 */
async function openSavedRoute(routeId) {
    if (!routeId) return;
    showLoading(true);
    currentRoute = null;
    clearRoute();

    try {
        const route = await api.getRoute(routeId);
        currentRoute = route;
        await displayRoute(route);
        showMessage('Маршрут загружен', 'success');
    } catch (error) {
        showMessage(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// updateAddFavoriteButton удален (кнопка в боковой панели убрана)
