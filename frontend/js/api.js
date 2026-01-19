/**
 * API клиент для взаимодействия с backend
 */

const API_BASE_URL = 'http://127.0.0.1:8000/api';

class APIClient {
    constructor() {
        this.token = localStorage.getItem('auth_token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
    }

    /**
     * Установить токен авторизации
     */
    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    }

    /**
     * Установить данные пользователя
     */
    setUser(user) {
        this.user = user;
        localStorage.setItem('user', JSON.stringify(user));
    }

    /**
     * Выход из системы
     */
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    }

    /**
     * Проверка авторизации
     */
    isAuthenticated() {
        return !!this.token;
    }

    /**
     * Получить заголовки для запроса
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    /**
     * Базовый метод для выполнения запросов
     */
    async request(url, options = {}) {
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(),
                ...options.headers,
            },
        };

        try {
            const response = await fetch(`${API_BASE_URL}${url}`, config);
            
            // Если 401 - выйти из системы
            if (response.status === 401) {
                this.logout();
                throw new Error('Необходима авторизация');
            }
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || data.error || 'Ошибка запроса');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * Регистрация пользователя
     */
    async register(username, email, password, fullName = null) {
        const data = await this.request('/register', {
            method: 'POST',
            body: JSON.stringify({
                username,
                email,
                password,
                full_name: fullName,
            }),
        });
        
        this.setToken(data.access_token);
        this.setUser(data.user);
        
        return data;
    }

    /**
     * Вход пользователя
     */
    async login(username, password) {
        const data = await this.request('/login', {
            method: 'POST',
            body: JSON.stringify({
                username,
                password,
            }),
        });
        
        this.setToken(data.access_token);
        this.setUser(data.user);
        
        return data;
    }

    /**
     * Получить объекты культурного наследия
     */
    async getObjects(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await this.request(`/objects?${queryString}`);
    }

    /**
     * Получить объект по ID
     */
    async getObject(id) {
        return await this.request(`/objects/${id}`);
    }

    /**
     * Рассказ об объекте (ИИ-экскурсовод)
     */
    async getObjectStory(id) {
        return await this.request(`/objects/${id}/story`);
    }

    /**
     * Получить список районов
     */
    async getDistricts() {
        return await this.request('/districts');
    }

    /**
     * Получить типы объектов
     */
    async getObjectTypes() {
        return await this.request('/object-types');
    }

    /**
     * Построить маршрут
     */
    async buildRoute(startLocation, objectsCount, startAddress = null) {
        return await this.request('/route', {
            method: 'POST',
            body: JSON.stringify({
                start_location: startLocation,
                objects_count: objectsCount,
                start_address: startAddress,
            }),
        });
    }

    /**
     * Получить историю маршрутов
     */
    async getRoutes() {
        return await this.request('/routes');
    }

    /**
     * Получить маршрут по ID
     */
    async getRoute(id) {
        return await this.request(`/routes/${id}`);
    }

    /**
     * Установить избранный статус маршрута
     */
    async setRouteFavorite(id, isFavorite) {
        return await this.request(`/routes/${id}/favorite?is_favorite=${isFavorite}`, {
            method: 'PATCH',
        });
    }

    /**
     * Получить текущего пользователя
     */
    async getCurrentUser() {
        return await this.request('/me');
    }
}

// Экспорт экземпляра
const api = new APIClient();

