document.addEventListener('DOMContentLoaded', function() {
    // Загрузка данных из встроенного JSON
    const graphData = window.graphData || {};
    
    if (!graphData.content || graphData.content.length === 0) {
        document.getElementById('graph-container').innerHTML = 
            '<p style="text-align: center; padding: 50px;">Нет данных для отображения графа.</p>';
        return;
    }
    
    // Инициализация графа
    initGraph(graphData);
});

function initGraph(data) {
    const container = document.getElementById('graph-container');
    
    // Создаем элементы для графа
    const elements = [];
    const works = data.content;
    const structure = data.structure;
    
    // Добавляем работы как узлы
    works.forEach(work => {
        // Получаем названия сферы, жанра и темы из структуры
        const sphereName = structure.сферы[work.sphere]?.name || work.sphere;
        let genreName = work.genre;
        let topicName = work.topic || '';
        
        // Находим названия жанра и темы в структуре
        if (structure.сферы[work.sphere]?.genres) {
            const genreObj = structure.сферы[work.sphere].genres.find(g => g.id === work.genre);
            if (genreObj) genreName = genreObj.name;
        }
        
        if (work.topic && structure.сферы[work.sphere]?.topics) {
            const topicObj = structure.сферы[work.sphere].topics.find(t => t.id === work.topic);
            if (topicObj) topicName = topicObj.name;
        }
        
        elements.push({
            data: {
                id: work.id.toString(),
                label: work.title,
                type: 'work',
                sphere: work.sphere,
                sphereName: sphereName,
                genre: work.genre,
                genreName: genreName,
                topic: work.topic || '',
                topicName: topicName,
                description: work.description,
                creationDate: work.creation_date,
                cover: work.cover_file ? `covers/${work.cover_file}` : null
            }
        });
    });
    
    // Добавляем связи между работами
    works.forEach(work => {
        if (work.related && work.related.length > 0) {
            work.related.forEach(relatedId => {
                // Проверяем, существует ли связанная работа
                const relatedWork = works.find(w => w.id === relatedId);
                if (relatedWork) {
                    elements.push({
                        data: {
                            source: work.id.toString(),
                            target: relatedId.toString(),
                            label: 'связано'
                        }
                    });
                }
            });
        }
    });
    
    // Создаем граф с помощью Cytoscape
    const cy = cytoscape({
        container: container,
        elements: elements,
        style: [
            {
                selector: 'node[type="work"]',
                style: {
                    'background-color': function(ele) {
                        // Цвет в зависимости от сферы
                        const sphere = ele.data('sphere');
                        const colors = {
                            'programming': '#3498db',
                            'literature': '#e74c3c',
                            'science_pop': '#2ecc71',
                            'digital_art': '#9b59b6',
                            'traditional_art': '#e67e22',
                            'science_research': '#1abc9c'
                        };
                        return colors[sphere] || '#95a5a6';
                    },
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': '#fff',
                    'text-outline-color': '#000',
                    'text-outline-width': 2,
                    'width': 80,
                    'height': 40,
                    'font-size': '12px'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#ccc',
                    'target-arrow-color': '#ccc',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'text-rotation': 'autorotate',
                    'font-size': '10px'
                }
            },
            {
                selector: ':selected',
                style: {
                    'border-width': 3,
                    'border-color': '#fff'
                }
            }
        ],
        layout: {
            name: 'cose',
            idealEdgeLength: 100,
            nodeOverlap: 20,
            refresh: 20,
            fit: true,
            padding: 30,
            randomize: false,
            componentSpacing: 100,
            nodeRepulsion: 400000,
            edgeElasticity: 100,
            nestingFactor: 5,
            gravity: 80,
            numIter: 1000,
            initialTemp: 200,
            coolingFactor: 0.95,
            minTemp: 1.0
        }
    });
    
    // Добавляем информацию при наведении на узлы
    cy.on('mouseover', 'node', function(event) {
        const node = event.target;
        const nodeData = node.data();
        
        // Создаем всплывающую подсказку
        let tooltip = document.getElementById('graph-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'graph-tooltip';
            tooltip.style.cssText = `
                position: absolute;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                max-width: 300px;
                z-index: 1000;
                pointer-events: none;
            `;
            document.body.appendChild(tooltip);
        }
        
        // Заполняем подсказку информацией
        tooltip.innerHTML = `
            <strong>${nodeData.label}</strong><br>
            <span>Сфера: ${nodeData.sphereName}</span><br>
            <span>Жанр: ${nodeData.genreName}</span><br>
            ${nodeData.topicName ? `<span>Тема: ${nodeData.topicName}</span><br>` : ''}
            <span>Дата: ${nodeData.creationDate}</span>
        `;
        
        // Позиционируем подсказку рядом с курсором
        tooltip.style.display = 'block';
    });
    
    cy.on('mouseout', 'node', function() {
        const tooltip = document.getElementById('graph-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    });
    
    cy.on('mousemove', function(event) {
        const tooltip = document.getElementById('graph-tooltip');
        if (tooltip) {
            tooltip.style.left = (event.originalEvent.pageX + 10) + 'px';
            tooltip.style.top = (event.originalEvent.pageY + 10) + 'px';
        }
    });
    
    // Добавляем возможность выделения и просмотра деталей
    cy.on('tap', 'node', function(event) {
        const node = event.target;
        const nodeData = node.data();
        
        // Показываем детальную информацию о работе
        showWorkDetails(nodeData);
    });
    
    // Добавляем легенду
    addLegend(cy, structure);
    
    // Добавляем элементы управления
    addControls(cy);
}

function showWorkDetails(workData) {
    // Создаем модальное окно для показа деталей работы
    let modal = document.getElementById('work-details-modal');
    
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'work-details-modal';
        modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--bg-secondary);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        `;
        
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: var(--text-primary);
        `;
        closeBtn.onclick = function() {
            modal.style.display = 'none';
        };
        
        modal.appendChild(closeBtn);
        document.body.appendChild(modal);
    }
    
    // Заполняем модальное окно информацией о работе
    modal.innerHTML = `
        <button style="position: absolute; top: 10px; right: 10px; background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text-primary);">×</button>
        <h2>${workData.label}</h2>
        ${workData.cover ? `<img src="${workData.cover}" alt="${workData.label}" style="max-width: 100%; margin-bottom: 15px; border-radius: 4px;">` : ''}
        <p><strong>Сфера:</strong> ${workData.sphereName}</p>
        <p><strong>Жанр:</strong> ${workData.genreName}</p>
        ${workData.topicName ? `<p><strong>Тема:</strong> ${workData.topicName}</p>` : ''}
        <p><strong>Дата создания:</strong> ${workData.creationDate}</p>
        ${workData.description ? `<p><strong>Описание:</strong> ${workData.description}</p>` : ''}
    `;
    
    // Добавляем обработчик закрытия
    modal.querySelector('button').onclick = function() {
        modal.style.display = 'none';
    };
    
    modal.style.display = 'block';
}

function addLegend(cy, structure) {
    // Создаем легенду для графа
    const legend = document.createElement('div');
    legend.id = 'graph-legend';
    legend.style.cssText = `
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(45, 45, 45, 0.9);
        padding: 10px;
        border-radius: 5px;
        font-size: 12px;
        max-width: 200px;
        z-index: 100;
    `;
    
    let legendHTML = '<strong>Легенда:</strong><br>';
    
    // Цвета для сфер
    const colors = {
        'programming': '#3498db',
        'literature': '#e74c3c',
        'science_pop': '#2ecc71',
        'digital_art': '#9b59b6',
        'traditional_art': '#e67e22',
        'science_research': '#1abc9c'
    };
    
    // Добавляем элементы легенды для каждой сферы
    Object.keys(structure.сферы).forEach(sphereId => {
        const sphere = structure.сферы[sphereId];
        const color = colors[sphereId] || '#95a5a6';
        
        legendHTML += `
            <div style="display: flex; align-items: center; margin: 5px 0;">
                <div style="width: 15px; height: 15px; background: ${color}; margin-right: 5px; border-radius: 3px;"></div>
                <span>${sphere.name}</span>
            </div>
        `;
    });
    
    legend.innerHTML = legendHTML;
    cy.container().appendChild(legend);
}

function addControls(cy) {
    // Создаем элементы управления графом
    const controls = document.createElement('div');
    controls.id = 'graph-controls';
    controls.style.cssText = `
        position: absolute;
        bottom: 10px;
        left: 10px;
        display: flex;
        gap: 5px;
        z-index: 100;
    `;
    
    // Кнопка сброса представления
    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Сброс';
    resetBtn.className = 'btn';
    resetBtn.onclick = function() {
        cy.fit();
    };
    
    // Кнопка увеличения
    const zoomInBtn = document.createElement('button');
    zoomInBtn.textContent = '+';
    zoomInBtn.className = 'btn';
    zoomInBtn.onclick = function() {
        cy.zoom(cy.zoom() * 1.2);
    };
    
    // Кнопка уменьшения
    const zoomOutBtn = document.createElement('button');
    zoomOutBtn.textContent = '-';
    zoomOutBtn.className = 'btn';
    zoomOutBtn.onclick = function() {
        cy.zoom(cy.zoom() * 0.8);
    };
    
    controls.appendChild(resetBtn);
    controls.appendChild(zoomInBtn);
    controls.appendChild(zoomOutBtn);
    cy.container().appendChild(controls);
}