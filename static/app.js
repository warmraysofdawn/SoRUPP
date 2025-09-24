// Структура данных
let structure = {};
let contentItems = [];
let portfolioData = {};
let availableTemplates = [];
let galleries = [];

// Элементы DOM
const sphereSelect = document.getElementById('sphere');
const genreSelect = document.getElementById('genre');
const topicSelect = document.getElementById('topic');
const contentFileInput = document.getElementById('contentFile');
const coverFileInput = document.getElementById('coverFile');
const contentFileName = document.getElementById('contentFileName');
const coverFileName = document.getElementById('coverFileName');
const coverPreview = document.getElementById('coverPreview');
const addContentBtn = document.getElementById('addContentBtn');
const contentList = document.getElementById('contentList');
const editContentList = document.getElementById('editContentList');
const exportSiteBtn = document.getElementById('exportSiteBtn');
const exportStatus = document.getElementById('exportStatus');
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');
const portraitInput = document.getElementById('portrait');
const portraitFileName = document.getElementById('portraitFileName');
const portraitPreview = document.getElementById('portraitPreview');
const fullNameInput = document.getElementById('fullName');
const quoteInput = document.getElementById('quote');
const bioInput = document.getElementById('bio');
const savePortfolioBtn = document.getElementById('savePortfolioBtn');
const templateSelect = document.getElementById('template');
const templatePreviewImg = document.getElementById('templatePreviewImg');
const galleryImagesInput = document.getElementById('galleryImages');
const galleryImagesName = document.getElementById('galleryImagesName');
const galleryPreview = document.getElementById('galleryPreview');
const addGalleryBtn = document.getElementById('addGalleryBtn');
const galleriesList = document.getElementById('galleriesList');

// API базовый URL - используем относительный путь
const API_BASE = '/api';

// Инициализация
document.addEventListener('DOMContentLoaded', async () => {
    await loadInitialData();
    setupEventListeners();
    setupGalleryListeners();
    updateContentList();
    document.getElementById('creationDate').valueAsDate = new Date();
});

// Загрузка начальных данных
async function loadInitialData() {
    try {
        const [structureRes, contentRes, portfolioRes, galleriesRes] = await Promise.all([
            fetch(`${API_BASE}/structure`),
            fetch(`${API_BASE}/content`),
            fetch(`${API_BASE}/portfolio`),
            fetch(`${API_BASE}/galleries`)
        ]);
        
        structure = await structureRes.json();
        contentItems = await contentRes.json();
        portfolioData = await portfolioRes.json();
        galleries = await galleriesRes.json();
        
        // Заполнение данных портфолио в форму
        if (portfolioData.portrait) {
            portraitPreview.src = `/uploads/${portfolioData.portrait}`;
            portraitPreview.classList.remove('hidden');
            portraitFileName.textContent = 'Портрет загружен';
        }
        fullNameInput.value = portfolioData.fullName || '';
        quoteInput.value = portfolioData.quote || '';
        bioInput.value = portfolioData.bio || '';
        
        // Заполнение мета-тегов
        if (portfolioData.metaTags) {
            document.getElementById('metaTitle').value = portfolioData.metaTags.title || '';
            document.getElementById('metaDescription').value = portfolioData.metaTags.description || '';
            document.getElementById('metaKeywords').value = portfolioData.metaTags.keywords || '';
        }
        
        // Заполняем шаблоны
        await loadTemplates();
        
        // Обновляем список галерей
        updateGalleriesList();
        
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        showAlert('Ошибка загрузки данных', 'error');
    }
}

// Загрузка доступных шаблонов
async function loadTemplates() {
    try {
        const response = await fetch(`${API_BASE}/templates`);
        availableTemplates = await response.json();
        
        // Заполняем выпадающий список шаблонов
        templateSelect.innerHTML = '';
        
        availableTemplates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.name;
            option.textContent = template.name.charAt(0).toUpperCase() + template.name.slice(1);
            templateSelect.appendChild(option);
        });
        
        // Устанавливаем выбранный шаблон
        if (portfolioData.template) {
            templateSelect.value = portfolioData.template;
            updateTemplatePreview(portfolioData.template);
        }
        
    } catch (error) {
        console.error('Ошибка загрузки шаблонов:', error);
        showAlert('Ошибка загрузки шаблонов', 'error');
    }
}

// Обновление превью шаблона
function updateTemplatePreview(templateName) {
    const template = availableTemplates.find(t => t.name === templateName);
    
    if (template && template.hasPreview && templatePreviewImg) {
        templatePreviewImg.src = `${API_BASE}/templates/${templateName}/preview?t=${Date.now()}`;
        templatePreviewImg.classList.remove('hidden');
    } else if (templatePreviewImg) {
        templatePreviewImg.classList.add('hidden');
    }
}

// Настройка обработчиков событий
function setupEventListeners() {
    if (sphereSelect) sphereSelect.addEventListener('change', updateGenres);
    if (sphereSelect) sphereSelect.addEventListener('change', updateTopics);
    if (contentFileInput) contentFileInput.addEventListener('change', updateFileName);
    if (coverFileInput) coverFileInput.addEventListener('change', updateCoverFile);
    if (addContentBtn) addContentBtn.addEventListener('click', addContent);
    if (exportSiteBtn) exportSiteBtn.addEventListener('click', exportSite);
    if (portraitInput) portraitInput.addEventListener('change', updatePortrait);
    if (savePortfolioBtn) savePortfolioBtn.addEventListener('click', savePortfolioData);
    if (templateSelect) templateSelect.addEventListener('change', function() {
        updateTemplatePreview(this.value);
    });
    
    // Обработчики для табов
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.getAttribute('data-tab');
            
            // Активируем выбранную вкладку
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(tc => tc.classList.remove('active'));
            
            tab.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
            
            // Если активирована вкладка управления, обновляем список
            if (tabId === 'manage') {
                updateEditContentList();
            }
            // Если активирована вкладка галерей, обновляем список галерей
            if (tabId === 'galleries') {
                updateGalleriesList();
            }
        });
    });
}

// Настройка обработчиков для галерей
function setupGalleryListeners() {
    if (galleryImagesInput && galleryImagesName) {
        galleryImagesInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                galleryImagesName.textContent = `Выбрано ${this.files.length} изображений`;
                
                // Показываем превью
                if (galleryPreview) {
                    galleryPreview.innerHTML = '';
                    for (let i = 0; i < Math.min(this.files.length, 5); i++) {
                        const file = this.files[i];
                        if (file.type.startsWith('image/')) {
                            const reader = new FileReader();
                            reader.onload = function(e) {
                                const img = document.createElement('img');
                                img.src = e.target.result;
                                img.style.width = '100px';
                                img.style.height = '100px';
                                img.style.objectFit = 'cover';
                                img.style.margin = '5px';
                                img.style.borderRadius = '4px';
                                galleryPreview.appendChild(img);
                            };
                            reader.readAsDataURL(file);
                        }
                    }
                }
            } else {
                galleryImagesName.textContent = 'Изображения не выбраны';
                if (galleryPreview) galleryPreview.innerHTML = '';
            }
        });
    }
    
    if (addGalleryBtn) {
        addGalleryBtn.addEventListener('click', createGallery);
    }
}

// Обновление жанров
function updateGenres() {
    const sphereId = sphereSelect.value;
    genreSelect.innerHTML = '';
    
    if (!sphereId) {
        genreSelect.disabled = true;
        genreSelect.innerHTML = '<option value="">-- Сначала выберите сферу --</option>';
        return;
    }
    
    const sphere = structure.сферы[sphereId];
    if (sphere && sphere.genres) {
        genreSelect.disabled = false;
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '-- Выберите жанр --';
        genreSelect.appendChild(defaultOption);
        
        sphere.genres.forEach(genre => {
            const option = document.createElement('option');
            option.value = genre.id;
            option.textContent = genre.name;
            genreSelect.appendChild(option);
        });
        
        // Автоматическое определение языка программирования
        if (sphereId === 'programming' && contentFileInput.files.length > 0) {
            const fileName = contentFileInput.files[0].name.toLowerCase();
            const extension = fileName.split('.').pop();
            
            const extensionMap = {
                'py': 'py', 'js': 'js', 'java': 'java', 'cpp': 'cpp', 
                'cs': 'cs', 'php': 'php', 'go': 'go', 'rs': 'rust',
                'sql': 'sql', 'html': 'html_css', 'css': 'html_css',
                'r': 'r', 'rb': 'ruby', 'swift': 'swift', 'kt': 'kotlin'
            };
            
            if (extensionMap[extension]) {
                genreSelect.value = extensionMap[extension];
            }
        }
    }
}

// Обновление тем
function updateTopics() {
    const sphereId = sphereSelect.value;
    topicSelect.innerHTML = '';
    
    if (!sphereId) {
        topicSelect.disabled = true;
        topicSelect.innerHTML = '<option value="">-- Сначала выберите сферу --</option>';
        return;
    }
    
    const sphere = structure.сферы[sphereId];
    if (sphere && sphere.topics && sphere.topics.length > 0) {
        topicSelect.disabled = false;
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '-- Выберите тему --';
        topicSelect.appendChild(defaultOption);
        
        sphere.topics.forEach(topic => {
            const option = document.createElement('option');
            option.value = topic.id;
            option.textContent = topic.name;
            topicSelect.appendChild(option);
        });
    } else {
        topicSelect.disabled = true;
        topicSelect.innerHTML = '<option value="">-- Для этой сферы нет тем --</option>';
    }
}

// Обновление имени файла
function updateFileName() {
    if (contentFileInput.files.length > 0) {
        contentFileName.textContent = contentFileInput.files[0].name;
        
        // Автоматическое определение языка программирования
        if (sphereSelect.value === 'programming') {
            updateGenres();
        }
    } else {
        contentFileName.textContent = 'Файл не выбран';
    }
}

// Обновление обложки
function updateCoverFile() {
    if (coverFileInput.files.length > 0) {
        coverFileName.textContent = coverFileInput.files[0].name;
        
        // Показать превью обложки
        const file = coverFileInput.files[0];
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                coverPreview.src = e.target.result;
                coverPreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    } else {
        coverFileName.textContent = 'Изображение не выбрано';
        coverPreview.classList.add('hidden');
    }
}

// Обновление портрета
function updatePortrait() {
    if (portraitInput.files.length > 0) {
        portraitFileName.textContent = portraitInput.files[0].name;
        
        // Показать превью портрета
        const file = portraitInput.files[0];
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function(e) {
                portraitPreview.src = e.target.result;
                portraitPreview.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    } else {
        portraitFileName.textContent = 'Изображение не выбрано';
        portraitPreview.classList.add('hidden');
    }
}

// Добавление контента
async function addContent() {
    if (!validateForm()) {
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('username', document.getElementById('username').value);
        formData.append('sphere', sphereSelect.value);
        formData.append('genre', genreSelect.value);
        formData.append('topic', topicSelect.value || '');
        formData.append('title', document.getElementById('title').value);
        formData.append('description', document.getElementById('description').value);
        formData.append('creationDate', document.getElementById('creationDate').value);
        formData.append('relatedIds', document.getElementById('relatedIds').value);
        
        if (contentFileInput.files[0]) {
            formData.append('contentFile', contentFileInput.files[0]);
        }
        
        if (coverFileInput.files[0]) {
            formData.append('coverFile', coverFileInput.files[0]);
        }
        
        const response = await fetch(`${API_BASE}/content`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            showAlert('Работа успешно добавлена!', 'success');
            
            // Перезагружаем данные
            await loadInitialData();
            updateContentList();
            resetForm();
        } else {
            throw new Error('Ошибка при добавлении работы');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка при добавлении работы', 'error');
    }
}

// Сохранение данных портфолио
async function savePortfolioData() {
    try {
        const formData = new FormData();
        formData.append('fullName', fullNameInput.value);
        formData.append('quote', quoteInput.value);
        formData.append('bio', bioInput.value);
        formData.append('template', templateSelect.value);
        formData.append('metaTitle', document.getElementById('metaTitle').value);
        formData.append('metaDescription', document.getElementById('metaDescription').value);
        formData.append('metaKeywords', document.getElementById('metaKeywords').value);
        
        if (portraitInput.files[0]) {
            formData.append('portrait', portraitInput.files[0]);
        }
        
        const response = await fetch(`${API_BASE}/portfolio`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showAlert('Данные портфолио сохранены!', 'success');
            
            // Перезагружаем данные
            await loadInitialData();
        } else {
            throw new Error('Ошибка при сохранении портфолио');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка при сохранении портфолио', 'error');
    }
}

// Экспорт сайта
async function exportSite() {
    const username = document.getElementById('exportUsername').value || 'user';
    const siteTitle = document.getElementById('siteTitle').value || 'Портфолио творческих работ';
    
    if (contentItems.length === 0) {
        showAlert('Нет данных для экспорта', 'error');
        return;
    }
    
    try {
        if (exportStatus) exportStatus.innerHTML = '<p>Начало генерации сайта...</p>';
        
        const response = await fetch(`${API_BASE}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                siteTitle: siteTitle
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `portfolio_${username}.zip`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            if (exportStatus) exportStatus.innerHTML = '<p class="alert alert-success">Сайт-портфолио успешно сгенерирован и скачан!</p>';
        } else {
            throw new Error('Ошибка при экспорте сайта');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка при экспорте сайта', 'error');
        if (exportStatus) exportStatus.innerHTML = '<p class="alert alert-error">Ошибка при экспорте сайта</p>';
    }
}

// Удаление контента
async function deleteContent(id) {
    if (confirm('Вы уверены, что хотите удалить эту работу?')) {
        try {
            const response = await fetch(`${API_BASE}/content/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showAlert('Работа удалена', 'success');
                
                // Перезагружаем данные
                await loadInitialData();
                updateContentList();
                updateEditContentList();
            } else {
                throw new Error('Ошибка при удалении работы');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showAlert('Ошибка при удалении работы', 'error');
        }
    }
}

// Создание галереи
async function createGallery() {
    const title = document.getElementById('galleryTitle').value;
    const description = document.getElementById('galleryDescription').value;
    const type = document.getElementById('galleryType').value;
    
    if (!title || !galleryImagesInput || galleryImagesInput.files.length === 0) {
        showAlert('Заполните название галереи и выберите изображения', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('title', title);
        formData.append('description', description);
        formData.append('type', type);
        
        for (let i = 0; i < galleryImagesInput.files.length; i++) {
            formData.append('galleryImages', galleryImagesInput.files[i]);
        }
        
        const response = await fetch(`${API_BASE}/galleries`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            showAlert('Галерея успешно создана!', 'success');
            
            // Перезагружаем данные
            await loadInitialData();
            
            // Очищаем форму
            document.getElementById('galleryTitle').value = '';
            document.getElementById('galleryDescription').value = '';
            document.getElementById('galleryType').value = 'grid';
            galleryImagesInput.value = '';
            if (galleryImagesName) galleryImagesName.textContent = 'Изображения не выбраны';
            if (galleryPreview) galleryPreview.innerHTML = '';
        } else {
            throw new Error('Ошибка при создании галереи');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка при создании галереи', 'error');
    }
}

// Удаление галереи
async function deleteGallery(id) {
    if (confirm('Вы уверены, что хотите удалить эту галерею?')) {
        try {
            const response = await fetch(`${API_BASE}/galleries/${id}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                showAlert('Галерея удалена', 'success');
                
                // Перезагружаем данные
                await loadInitialData();
            } else {
                throw new Error('Ошибка при удалении галереи');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showAlert('Ошибка при удалении галереи', 'error');
        }
    }
}

// Валидация формы
function validateForm() {
    const username = document.getElementById('username').value;
    const sphere = sphereSelect.value;
    const genre = genreSelect.value;
    const title = document.getElementById('title').value;
    const creationDate = document.getElementById('creationDate').value;
    const contentFile = contentFileInput.files[0];
    
    if (!username) {
        showAlert('Введите имя пользователя', 'error');
        return false;
    }
    
    if (!sphere) {
        showAlert('Выберите сферу творчества', 'error');
        return false;
    }
    
    if (!genre) {
        showAlert('Выберите жанр/направление', 'error');
        return false;
    }
    
    if (!title) {
        showAlert('Введите название работы', 'error');
        return false;
    }
    
    if (!creationDate) {
        showAlert('Укажите дату создания работы', 'error');
        return false;
    }
    
    if (!contentFile) {
        showAlert('Загрузите файл контента', 'error');
        return false;
    }
    
    return true;
}

// Показать уведомление
function showAlert(message, type) {
    // Удаляем существующие уведомления
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());
    
    // Создаем новое уведомление
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    // Добавляем в начало контейнера
    const container = document.querySelector('.container');
    if (container) {
        container.prepend(alert);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
}

// Обновление списка контента
function updateContentList() {
    if (!contentList) return;
    
    if (contentItems.length === 0) {
        contentList.innerHTML = '<p>Работы еще не добавлены.</p>';
        return;
    }
    
    contentList.innerHTML = '';
    
    contentItems.forEach(item => {
        const sphere = structure.сферы[item.sphere];
        const sphereName = sphere ? sphere.name : item.sphere;
        let genreName = item.genre;
        
        if (sphere && sphere.genres) {
            const genreObj = sphere.genres.find(g => g.id === item.genre);
            genreName = genreObj ? genreObj.name : item.genre;
        }
        
        const contentItemElement = document.createElement('div');
        contentItemElement.className = 'content-item';
        contentItemElement.innerHTML = `
            <h3>${item.title} (ID: ${item.id})</h3>
            <p><strong>Сфера:</strong> ${sphereName}</p>
            <p><strong>Жанр:</strong> ${genreName}</p>
            <p><strong>Дата создания:</strong> ${item.creation_date}</p>
        `;
        
        contentList.appendChild(contentItemElement);
    });
}

// Обновление списка редактирования
function updateEditContentList() {
    if (!editContentList) return;
    
    if (contentItems.length === 0) {
        editContentList.innerHTML = '<p>Работы еще не добавлены.</p>';
        return;
    }
    
    editContentList.innerHTML = '';
    
    contentItems.forEach(item => {
        const sphere = structure.сферы[item.sphere];
        const sphereName = sphere ? sphere.name : item.sphere;
        let genreName = item.genre;
        
        if (sphere && sphere.genres) {
            const genreObj = sphere.genres.find(g => g.id === item.genre);
            genreName = genreObj ? genreObj.name : item.genre;
        }
        
        const contentItemElement = document.createElement('div');
        contentItemElement.className = 'content-item';
        contentItemElement.innerHTML = `
            <h3>${item.title} (ID: ${item.id})</h3>
            <p><strong>Сфера:</strong> ${sphereName}</p>
            <p><strong>Жанр:</strong> ${genreName}</p>
            <p><strong>Дата создания:</strong> ${item.creation_date}</p>
            <button class="btn btn-danger" onclick="deleteContent(${item.id})">Удалить</button>
        `;
        
        editContentList.appendChild(contentItemElement);
    });
}

// Обновление списка галерей
function updateGalleriesList() {
    if (!galleriesList) return;
    
    if (galleries.length === 0) {
        galleriesList.innerHTML = '<p>Галереи еще не созданы.</p>';
        return;
    }
    
    galleriesList.innerHTML = '';
    
    galleries.forEach(gallery => {
        const galleryElement = document.createElement('div');
        galleryElement.className = 'gallery-item';
        
        // Создаем превью изображений
        let previewHtml = '';
        if (gallery.images && gallery.images.length > 0) {
            previewHtml = `
                <div class="gallery-previews" style="display: flex; flex-wrap: wrap; gap: 5px; margin: 10px 0;">
            `;
            
            // Показываем до 3 изображений для превью
            gallery.images.slice(0, 3).forEach(image => {
                previewHtml += `
                    <img src="/uploads/${image}" alt="Preview" style="width: 60px; height: 60px; object-fit: cover; border-radius: 4px;">
                `;  // ← ИСПРАВЛЕНО: /uploads/ вместо galleries/
            });
            
            if (gallery.images.length > 3) {
                previewHtml += `<div style="width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; background: #f0f0f0; border-radius: 4px;">+${gallery.images.length - 3}</div>`;
            }
            
            previewHtml += '</div>';
        }
        
        galleryElement.innerHTML = `
            <h3>${gallery.title} (ID: ${gallery.id})</h3>
            <p>${gallery.description || ''}</p>
            <p><small>Тип: ${gallery.type}, Изображений: ${gallery.images.length}</small></p>
            ${previewHtml}
            <button class="btn btn-danger" onclick="deleteGallery(${gallery.id})">Удалить галерею</button>
        `;
        
        galleriesList.appendChild(galleryElement);
    });
}

// Сброс формы
function resetForm() {
    document.getElementById('title').value = '';
    document.getElementById('description').value = '';
    document.getElementById('creationDate').value = '';
    document.getElementById('relatedIds').value = '';
    
    if (contentFileInput) contentFileInput.value = '';
    if (coverFileInput) coverFileInput.value = '';
    if (contentFileName) contentFileName.textContent = 'Файл не выбран';
    if (coverFileName) coverFileName.textContent = 'Изображение не выбрано';
    if (coverPreview) coverPreview.classList.add('hidden');
}

// Делаем функции доступными глобально
window.deleteContent = deleteContent;
window.deleteGallery = deleteGallery;

/* Генерация частиц */
function createParticles() {
    const particlesContainer = document.querySelector('.particles');
    if (!particlesContainer) return;
    
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        
        // Случайные начальные позиции и задержки анимации
        const size = Math.random() * 3 + 1;
        const posX = Math.random() * 100;
        const delay = Math.random() * 15;
        
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.left = `${posX}%`;
        particle.style.animationDelay = `${delay}s`;
        
        // Случайный цвет частицы
        const colors = [
            'var(--neon-pink)',
            'var(--neon-blue)',
            'var(--neon-purple)',
            'var(--neon-green)'
        ];
        const randomColor = colors[Math.floor(Math.random() * colors.length)];
        particle.style.backgroundColor = randomColor;
        
        particlesContainer.appendChild(particle);
    }
}

// Обработчик для кнопки SEO-оптимизации
document.getElementById('processSeoBtn').addEventListener('click', async function() {
    try {
        const response = await fetch('/api/process-seo', {
            method: 'POST'
        });
        
        if (response.ok) {
            showAlert('SEO-оптимизация URL выполнена успешно!', 'success');
        } else {
            throw new Error('Ошибка при SEO-оптимизации');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        showAlert('Ошибка при SEO-оптимизации URL', 'error');
    }
});



// Инициализация частиц при загрузке страницы
document.addEventListener('DOMContentLoaded', createParticles);