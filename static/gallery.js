// Функция для инициализации галерей
function initGalleries() {
    const galleryData = window.galleryData || [];
    
    if (galleryData.length === 0) {
        const mainElement = document.querySelector('main');
        if (mainElement) {
            mainElement.innerHTML += '<p>Галереи еще не созданы.</p>';
        }
        return;
    }
    
    // Инициализация каждой галереи на странице
    galleryData.forEach(gallery => {
        const galleryElement = document.getElementById(`gallery-${gallery.id}`);
        if (galleryElement) {
            renderGallery(gallery, galleryElement);
        }
    });
}

// Функция для отображения галереи
function renderGallery(gallery, container) {
    container.innerHTML = '';
    
    // Заголовок галереи
    const title = document.createElement('h3');
    title.textContent = gallery.title;
    container.appendChild(title);
    
    // Описание галереи
    if (gallery.description) {
        const description = document.createElement('p');
        description.textContent = gallery.description;
        container.appendChild(description);
    }
    
    // Контейнер для изображений
    const imagesContainer = document.createElement('div');
    imagesContainer.className = `gallery-images gallery-${gallery.type}`;
    
    // Настройка стилей в зависимости от типа галереи
    switch(gallery.type) {
        case 'grid':
            imagesContainer.style.display = 'grid';
            imagesContainer.style.gridTemplateColumns = 'repeat(auto-fill, minmax(200px, 1fr))';
            imagesContainer.style.gap = '10px';
            break;
        case 'slider':
            imagesContainer.style.display = 'flex';
            imagesContainer.style.overflowX = 'auto';
            imagesContainer.style.gap = '10px';
            imagesContainer.style.padding = '10px 0';
            break;
        case 'masonry':
            imagesContainer.style.columnCount = '3';
            imagesContainer.style.columnGap = '10px';
            break;
        default:
            imagesContainer.style.display = 'grid';
            imagesContainer.style.gridTemplateColumns = 'repeat(auto-fill, minmax(200px, 1fr))';
            imagesContainer.style.gap = '10px';
    }
    
    // Добавление изображений
    gallery.images.forEach(image => {
        const imgElement = document.createElement('img');
        imgElement.src = `/uploads/${image}`;
        imgElement.alt = gallery.title;
        imgElement.style.width = '100%';
        imgElement.style.height = 'auto';
        imgElement.style.borderRadius = '4px';
        imgElement.style.cursor = 'pointer';
        
        // Обработчик клика для увеличения изображения
        imgElement.addEventListener('click', () => {
            openLightbox(gallery.images, image);
        });
        
        imagesContainer.appendChild(imgElement);
    });
    
    container.appendChild(imagesContainer);
}

// Функция для открытия лайтбокса с изображением
function openLightbox(images, currentImage) {
    // Создание лайтбокса
    const lightbox = document.createElement('div');
    lightbox.id = 'lightbox';
    lightbox.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        cursor: pointer;
    `;
    
    // Создание контейнера для изображения
    const imgContainer = document.createElement('div');
    imgContainer.style.cssText = `
        max-width: 90%;
        max-height: 90%;
        position: relative;
    `;
    
    // Создание изображения
    const img = document.createElement('img');
    img.src = `/uploads/${currentImage}`;
    img.style.cssText = `
        max-width: 100%;
        max-height: 100%;
        border-radius: 4px;
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
    `;
    
    // Кнопка закрытия
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.cssText = `
        position: absolute;
        top: -40px;
        right: -40px;
        background: none;
        border: none;
        color: white;
        font-size: 40px;
        cursor: pointer;
        z-index: 1001;
    `;
    closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        document.body.removeChild(lightbox);
    });
    
    // Навигация между изображениями
    if (images.length > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.textContent = '‹';
        prevBtn.style.cssText = `
            position: absolute;
            top: 50%;
            left: -50px;
            transform: translateY(-50%);
            background: rgba(0, 0, 0, 0.5);
            border: none;
            color: white;
            font-size: 30px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 1001;
        `;
        
        const nextBtn = document.createElement('button');
        nextBtn.textContent = '›';
        nextBtn.style.cssText = `
            position: absolute;
            top: 50%;
            right: -50px;
            transform: translateY(-50%);
            background: rgba(0, 0, 0, 0.5);
            border: none;
            color: white;
            font-size: 30px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            cursor: pointer;
            z-index: 1001;
        `;
        
        let currentIndex = images.indexOf(currentImage);
        
        prevBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            img.src = `/uploads/${images[currentIndex]}`;
        });
        
        nextBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            currentIndex = (currentIndex + 1) % images.length;
            img.src = `/uploads/${images[currentIndex]}`;
        });
        
        imgContainer.appendChild(prevBtn);
        imgContainer.appendChild(nextBtn);
        
        // Добавляем навигацию с помощью клавиатуры
        const handleKeydown = (e) => {
            if (e.key === 'ArrowLeft') {
                currentIndex = (currentIndex - 1 + images.length) % images.length;
                img.src = `/uploads/${images[currentIndex]}`;
            } else if (e.key === 'ArrowRight') {
                currentIndex = (currentIndex + 1) % images.length;
                img.src = `/uploads/${images[currentIndex]}`;
            } else if (e.key === 'Escape') {
                document.body.removeChild(lightbox);
                document.removeEventListener('keydown', handleKeydown);
            }
        };
        
        document.addEventListener('keydown', handleKeydown);
        
        // Сохраняем обработчик для последующего удаления
        lightbox._keydownHandler = handleKeydown;
    }
    
    imgContainer.appendChild(img);
    imgContainer.appendChild(closeBtn);
    lightbox.appendChild(imgContainer);
    
    // Закрытие по клику на фон
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            document.body.removeChild(lightbox);
            if (lightbox._keydownHandler) {
                document.removeEventListener('keydown', lightbox._keydownHandler);
            }
        }
    });
    
    document.body.appendChild(lightbox);
    
    // Предзагрузка изображений для плавной навигации
    if (images.length > 1) {
        images.forEach(imageSrc => {
            const preloadImg = new Image();
            preloadImg.src = `/uploads/${imageSrc}`;
        });
    }
}

// Инициализация галерей при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initGalleries();
});