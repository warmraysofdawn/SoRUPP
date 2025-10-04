import os
import json
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import zipfile
import re
from io import BytesIO

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5000", "http://localhost:5000"])
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('static/templates', exist_ok=True)

# Структура данных (полная версия)
structure = {
    "сферы": {
        "programming": {
            "name": "Программирование",
            "genre_type": "language",
            "topic_type": "application_domain",
            "genres": [
                {
                    "id": "py", 
                    "name": "Python",
                    "topics": [
                        "Веб-бэкенд", "Наука о данных", "Машинное обучение", "DevOps",
                        "Автоматизация", "ИИ", "Компьютерное зрение", "NLP"
                    ]
                },
                {
                    "id": "js", 
                    "name": "JavaScript",
                    "topics": [
                        "Веб-фронтенд", "Веб-бэкенд", "Мобильные приложения", "Десктоп",
                        "Игры", "Анимации", "PWA", "Кросс-платформенные приложения"
                    ]
                },
                {
                    "id": "java", 
                    "name": "Java",
                    "topics": [
                        "Веб-бэкенд", "Мобильные приложения", "Корпоративные системы", "Большие данные",
                        "Микросервисы", "Облачные вычисления", "Финансовые технологии"
                    ]
                },
                {
                    "id": "cpp", 
                    "name": "C++",
                    "topics": [
                        "Разработка игр", "Встроенные системы", "Десктоп", "Высокопроизводительные вычисления",
                        "Графические приложения", "Системное программирование", "Робототехника"
                    ]
                },
                {
                    "id": "cs", 
                    "name": "C#",
                    "topics": [
                        "Разработка игр", "Десктоп", "Веб-бэкенд", "Мобильные приложения",
                        "VR/AR", "Корпоративные приложения", "Интернет вещей"
                    ]
                },
                {
                    "id": "php", 
                    "name": "PHP",
                    "topics": [
                        "Веб-бэкенд", "CMS", "Электронная коммерция",
                        "Фреймворки", "API", "Кэширование", "Безопасность"
                    ]
                },
                {
                    "id": "go", 
                    "name": "Go",
                    "topics": [
                        "Веб-бэкенд", "DevOps", "Микросервисы", "Сетевые приложения",
                        "Клауд-нативные приложения", "CLI-утилиты", "Высоконагруженные системы"
                    ]
                },
                {
                    "id": "rust", 
                    "name": "Rust",
                    "topics": [
                        "Системное программирование", "Веб-бэкенд", "Встроенные системы", "Блокчейн",
                        "Сетевые сервисы", "Криптография", "Веб-ассембли"
                    ]
                },
                {
                    "id": "sql", 
                    "name": "SQL",
                    "topics": [
                        "Базы данных", "Анализ данных", "Бизнес-аналитика",
                        "Оптимизация запросов", "Хранилища данных", "ETL", "Отчетность"
                    ]
                },
                {
                    "id": "html_css", 
                    "name": "HTML/CSS",
                    "topics": [
                        "Веб-фронтенд", "UI/UX", "Адаптивный дизайн",
                        "Препроцессоры", "Анимации", "Доступность", "Кросс-браузерность"
                    ]
                },
                {
                    "id": "r", 
                    "name": "R",
                    "topics": [
                        "Наука о данных", "Статистика", "Биостатистика", "Исследования",
                        "Визуализация данных", "Эконометрика", "Генетический анализ"
                    ]
                },
                {
                    "id": "ruby", 
                    "name": "Ruby",
                    "topics": [
                        "Веб-бэкенд", "Автоматизация", "Прототипирование",
                        "Скрипты", "Тестирование", "Веб-скрейпинг"
                    ]
                },
                {
                    "id": "swift", 
                    "name": "Swift",
                    "topics": [
                        "Мобильные приложения", "Десктоп", "Экосистема Apple",
                        "UI-разработка", "ARKit", "WatchOS", "Безопасность"
                    ]
                },
                {
                    "id": "kotlin", 
                    "name": "Kotlin",
                    "topics": [
                        "Мобильные приложения", "Веб-бэкенд", "Разработка под Android",
                        "Кросс-платформенная разработка", "Нативные приложения", "Coroutines"
                    ]
                },
                {
                    "id": "other_lang", 
                    "name": "Другой язык",
                    "topics": [
                        "Другая предметная область",
                        "Специализированные вычисления", "Образовательные проекты"
                    ]
                }
            ]
        },
        "literature": {
            "name": "Литература",
            "genre_type": "literary_genre",
            "topic_type": "theme",
            "genres": [
                {
                    "id": "fantasy", 
                    "name": "Фэнтези",
                    "topics": [
                        "Приключения", "Магия", "Мифология", "Добро и зло",
                        "Эпические битвы", "Мировоззрение", "Квесты", "Древние пророчества"
                    ]
                },
                {
                    "id": "sci_fi", 
                    "name": "Научная фантастика",
                    "topics": [
                        "Будущее", "Технологии", "Космос", "Антиутопия",
                        "ИИ и роботы", "Альтернативная история", "Киберпанк", "Трансгуманизм"
                    ]
                },
                {
                    "id": "detective", 
                    "name": "Детектив",
                    "topics": [
                        "Преступление", "Загадка", "Расследование", "Правосудие",
                        "Психологический триллер", "Криминал", "Судебная система", "Шпионаж"
                    ]
                },
                {
                    "id": "romance", 
                    "name": "Любовный роман",
                    "topics": [
                        "Любовь", "Отношения", "Семья", "Эмоции",
                        "Драма отношений", "Свадьба", "Измены", "Романтические путешествия"
                    ]
                },
                {
                    "id": "horror", 
                    "name": "Ужасы",
                    "topics": [
                        "Страх", "Смерть", "Сверхъестественное", "Психологический ужас",
                        "Паранормальное", "Выживание", "Демоны", "Проклятия"
                    ]
                },
                {
                    "id": "realism", 
                    "name": "Реализм",
                    "topics": [
                        "Общество", "Повседневная жизнь", "Социальные проблемы", "Психология",
                        "Нравственные дилеммы", "Классовые различия", "Семейные ценности"
                    ]
                },
                {
                    "id": "poetry", 
                    "name": "Поэзия",
                    "topics": [
                        "Эмоции", "Природа", "Любовь", "Философия",
                        "Духовность", "Гражданская лирика", "Имажизм", "Символизм"
                    ]
                },
                {
                    "id": "drama", 
                    "name": "Драматургия",
                    "topics": [
                        "Конфликт", "Отношения", "Общество", "Трагедия",
                        "Моральный выбор", "Судьба", "Власть", "Предательство"
                    ]
                },
                {
                    "id": "prose", 
                    "name": "Проза (малая форма)",
                    "topics": [
                        "Повседневная жизнь", "Исследование персонажей", "Моменты", "Наблюдения",
                        "Миниатюры", "Зарисовки", "Эссеистика"
                    ]
                },
                {
                    "id": "nonfiction", 
                    "name": "Нон-фикшн",
                    "topics": [
                        "История", "Биография", "Наука", "Политика",
                        "Путешествия", "Мемуары", "Исследования", "Популярная психология"
                    ]
                },
                {
                    "id": "other_lit", 
                    "name": "Другой жанр",
                    "topics": [
                        "Другая тема",
                        "Экспериментальная литература", "Постмодернизм"
                    ]
                }
            ]
        },
        "science_pop": {
            "name": "Научпоп / Педагогика",
            "genre_type": "science",
            "topic_type": "specialization",
            "genres": [
                {
                    "id": "physics", 
                    "name": "Физика",
                    "topics": [
                        "Квантовая физика", "Термодинамика", "Теория относительности", "Космология",
                        "Астрофизика", "Физика частиц", "Нанотехнологии", "Энергетика"
                    ]
                },
                {
                    "id": "math", 
                    "name": "Математика",
                    "topics": [
                        "Алгебра", "Геометрия", "Математический анализ", "Теория чисел",
                        "Дискретная математика", "Теория вероятностей", "Математическое моделирование"
                    ]
                },
                {
                    "id": "chemistry", 
                    "name": "Химия",
                    "topics": [
                        "Органическая химия", "Биохимия", "Материаловедение", "Химические реакции",
                        "Неорганическая химия", "Химия полимеров", "Экологическая химия"
                    ]
                },
                {
                    "id": "biology", 
                    "name": "Биология",
                    "topics": [
                        "Генетика", "Эволюция", "Экология", "Микробиология",
                        "Биотехнологии", "Биоразнообразие", "Физиология", "Вирусология"
                    ]
                },
                {
                    "id": "medicine", 
                    "name": "Медицина",
                    "topics": [
                        "Анатомия", "Фармакология", "Заболевания", "Общественное здоровье",
                        "Диагностика", "Хирургия", "Педиатрия", "Геронтология"
                    ]
                },
                {
                    "id": "astronomy", 
                    "name": "Астрономия",
                    "topics": [
                        "Черные дыры", "Планеты", "Звезды", "Космология",
                        "Галактики", "Темная материя", "Экзопланеты", "Космические исследования"
                    ]
                },
                {
                    "id": "geology", 
                    "name": "Геология",
                    "topics": [
                        "Минералы", "Тектоника", "Окаменелости", "Природные ресурсы",
                        "Вулканы", "Землетрясения", "Палеонтология", "Геохимия"
                    ]
                },
                {
                    "id": "psychology_sci", 
                    "name": "Психология",
                    "topics": [
                        "Когнитивная психология", "Психология развития", "Клиническая психология", "Социальная психология",
                        "Нейропсихология", "Поведенческая психология", "Психотерапия"
                    ]
                },
                {
                    "id": "history_sci", 
                    "name": "История",
                    "topics": [
                        "Древний Рим", "Вторая мировая война", "Средневековье", "Ренессанс",
                        "Древняя Греция", "История России", "Эпоха Просвещения", "Холодная война"
                    ]
                },
                {
                    "id": "linguistics", 
                    "name": "Лингвистика",
                    "topics": [
                        "Фонетика", "Синтаксис", "Семантика", "Приобретение языка",
                        "Социолингвистика", "Психолингвистика", "Компьютерная лингвистика"
                    ]
                },
                {
                    "id": "economics", 
                    "name": "Экономика",
                    "topics": [
                        "Рынки", "Макроэкономика", "Микроэкономика", "Финансы",
                        "Международная экономика", "Экономический рост", "Биржевая торговля"
                    ]
                },
                {
                    "id": "philosophy_sci", 
                    "name": "Философия",
                    "topics": [
                        "Этика", "Эпистемология", "Метафизика", "Логика",
                        "Философия сознания", "Политическая философия", "Философия науки"
                    ]
                },
                {
                    "id": "other_sci", 
                    "name": "Другая наука",
                    "topics": [
                        "Другая специализация",
                        "Антропология", "Археология", "Культурология"
                    ]
                }
            ]
        },
        "digital_art": {
            "name": "Цифровое искусство",
            "genre_type": "style",
            "topic_type": "technique",
            "genres": [
                {
                    "id": "realism_d", 
                    "name": "Реализм",
                    "topics": ["Портреты", "Пейзажи", "Натюрморты", "Гиперреализм"]
                },
                {
                    "id": "stylized", 
                    "name": "Стилизация",
                    "topics": ["Персонажи", "Окружение", "Арт-дирекшн", "Брендинг"]
                },
                {
                    "id": "pixel", 
                    "name": "Пиксель-арт",
                    "topics": ["Ретро-игры", "Анимации", "Тайлсеты", "Спрайты"]
                },
                {
                    "id": "low_poly", 
                    "name": "Лоу-поли",
                    "topics": ["Стилизованные модели", "Оптимизация", "Мобильная графика", "Архитектура"]
                },
                {
                    "id": "vector", 
                    "name": "Векторная графика",
                    "topics": ["Логотипы", "Иллюстрации", "Инфографика", "Шрифты"]
                },
                {
                    "id": "concept", 
                    "name": "Концепт-арт",
                    "topics": ["Персонажи", "Окружение", "Транспорт", "Существа"]
                },
                {
                    "id": "photo_manip", 
                    "name": "Фотоманипуляция",
                    "topics": ["Коллажи", "Сюрреализм", "Рекламные изображения", "Фэнтези"]
                },
                {
                    "id": "3d_modeling", 
                    "name": "3D-моделирование",
                    "topics": ["Персонажи", "Архитектура", "Продуктовый дизайн", "Визуализация"]
                },
                {
                    "id": "abstract_d", 
                    "name": "Абстракционизм",
                    "topics": ["Геометрические формы", "Текстуры", "Эксперименты", "Цифровые инсталляции"]
                },
                {
                    "id": "other_d_style", 
                    "name": "Другой стиль",
                    "topics": ["Экспериментальные техники", "Смешанные медиа", "Генеративное искусство"]
                }
            ]
        },
        "traditional_art": {
            "name": "Изобразительное искусство",
            "genre_type": "style",
            "topic_type": "technique",
            "genres": [
                {
                    "id": "realism_t", 
                    "name": "Реализм",
                    "topics": ["Масло", "Акрил", "Акварель", "Карандаш", "Гравюра", "Пастель"]
                },
                {
                    "id": "impressionism", 
                    "name": "Импрессионизм",
                    "topics": ["Масло", "Пастель", "Акварель", "Темпера", "Гуашь"]
                },
                {
                    "id": "expressionism", 
                    "name": "Экспрессионизм",
                    "topics": ["Масло", "Акрил", "Смешанные техники", "Литография", "Гравюра"]
                },
                {
                    "id": "abstractionism", 
                    "name": "Абстракционизм",
                    "topics": ["Акрил", "Смешанные техники", "Масло", "Коллаж", "Эмаль"]
                },
                {
                    "id": "surrealism", 
                    "name": "Сюрреализм",
                    "topics": ["Масло", "Акрил", "Смешанные техники", "Фреска", "Ассамбляж"]
                },
                {
                    "id": "cubism", 
                    "name": "Кубизм",
                    "topics": ["Масло", "Акрил", "Уголь", "Коллаж", "Гуашь"]
                },
                {
                    "id": "modern", 
                    "name": "Модерн",
                    "topics": ["Масло", "Акварель", "Тушь", "Витраж", "Мозаика"]
                },
                {
                    "id": "avant_garde", 
                    "name": "Авангард",
                    "topics": ["Смешанные техники", "Масло", "Акрил", "Инсталляция", "Реди-мейд"]
                },
                {
                    "id": "other_t_style", 
                    "name": "Другой стиль",
                    "topics": ["Другая техника", "Экспериментальные материалы", "Нативная живопись"]
                }
            ]
        },
        "science_research": {
            "name": "Научные работы",
            "genre_type": "science",
            "topic_type": "specialization",
            "genres": [
                {
                    "id": "physics_r", 
                    "name": "Физика",
                    "topics": [
                        "Квантовая физика", "Термодинамика", "Оптика", "Физика частиц",
                        "Физика конденсированного состояния", "Ядерная физика", "Плазма"
                    ]
                },
                {
                    "id": "math_r", 
                    "name": "Математика",
                    "topics": [
                        "Алгебра", "Топология", "Статистика", "Прикладная математика",
                        "Дифференциальные уравнения", "Теория графов", "Численные методы"
                    ]
                },
                {
                    "id": "chemistry_r", 
                    "name": "Химия",
                    "topics": [
                        "Органическая химия", "Физическая химия", "Аналитическая химия", "Полимеры",
                        "Химия поверхности", "Электрохимия", "Кристаллография"
                    ]
                },
                {
                    "id": "biology_r", 
                    "name": "Биология",
                    "topics": [
                        "Генетика", "Нейронауки", "Молекулярная биология", "Экология",
                        "Биоинформатика", "Структурная биология", "Эволюционная биология"
                    ]
                },
                {
                    "id": "medicine_r", 
                    "name": "Медицина",
                    "topics": [
                        "Иммунология", "Генетика", "Нейронауки", "Эпидемиология",
                        "Кардиология", "Онкология", "Геномика"
                    ]
                },
                {
                    "id": "astronomy_r", 
                    "name": "Астрономия",
                    "topics": [
                        "Черные дыры", "Экзопланеты", "Космология", "Эволюция звезд",
                        "Радиоастрономия", "Космическая динамика", "Астробиология"
                    ]
                },
                {
                    "id": "geology_r", 
                    "name": "Геология",
                    "topics": [
                        "Минералогия", "Геофизика", "Палеонтология", "Гидрология",
                        "Сейсмология", "Вулканология", "Геохимия"
                    ]
                },
                {
                    "id": "psychology_r", 
                    "name": "Психология",
                    "topics": [
                        "Когнитивная психология", "Клиническая психология", "Нейропсихология", "Социальная психология",
                        "Психометрия", "Психолингвистика", "Кросс-культурные исследования"
                    ]
                },
                {
                    "id": "history_r", 
                    "name": "История",
                    "topics": [
                        "Древний Рим", "Вторая мировая война", "Средневековая история", "Современная история",
                        "Экономическая история", "История искусств", "Устная история"
                    ]
                },
                {
                    "id": "linguistics_r", 
                    "name": "Лингвистика",
                    "topics": [
                        "Социолингвистика", "Компьютерная лингвистика", "Историческая лингвистика", "Фонология",
                        "Корпусная лингвистика", "Диалектология", "Прагматика"
                    ]
                },
                {
                    "id": "economics_r", 
                    "name": "Экономика",
                    "topics": [
                        "Рынки", "Эконометрика", "Экономика развития", "Экономика труда",
                        "Поведенческая экономика", "Международная экономика", "Государственная политика"
                    ]
                },
                {
                    "id": "philosophy_r", 
                    "name": "Философия",
                    "topics": [
                        "Этика", "Философия науки", "Метафизика", "Эстетика",
                        "Философия языка", "Политическая философия", "Логика"
                    ]
                },
                {
                    "id": "other_sci_r", 
                    "name": "Другая наука",
                    "topics": [
                        "Другая специализация",
                        "Междисциплинарные исследования", "Науковедение"
                    ]
                }
            ]
        }
    }
}
# Load data
def load_data():
    try:
        with open('data/content.json', 'r', encoding='utf-8') as f:
            content = json.load(f)
    except:
        content = []
    
    try:
        with open('data/portfolio.json', 'r', encoding='utf-8') as f:
            portfolio = json.load(f)
    except:
        portfolio = {
            "portrait": None,
            "fullName": "",
            "quote": "",
            "bio": "",
            "accentColor": "#8a5c2d",
            "template": "default",
            "metaTags": {
                "title": "",
                "description": "",
                "keywords": ""
            }
        }
    
    try:
        with open('data/galleries.json', 'r', encoding='utf-8') as f:
            galleries = json.load(f)
    except:
        galleries = []
    
    return content, portfolio, galleries

def save_data(content, portfolio, galleries):
    with open('data/content.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    
    with open('data/portfolio.json', 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    
    with open('data/galleries.json', 'w', encoding='utf-8') as f:
        json.dump(galleries, f, ensure_ascii=False, indent=2)

# Get available templates
def get_available_templates():
    templates = []
    templates_dir = 'static/templates'
    
    if os.path.exists(templates_dir):
        for item in os.listdir(templates_dir):
            if os.path.isdir(os.path.join(templates_dir, item)):
                template_path = os.path.join(templates_dir, item)
                preview_path = os.path.join(template_path, 'preview.jpg')
                css_path = os.path.join(template_path, 'styles.css')
                
                if os.path.exists(css_path):
                    template = {
                        'name': item,
                        'preview': f'/static/templates/{item}/preview.jpg' if os.path.exists(preview_path) else None,
                        'hasPreview': os.path.exists(preview_path)
                    }
                    templates.append(template)
    
    return templates

@app.route('/')
def index():
    templates = get_available_templates()
    return render_template('index.html', templates=templates)

@app.route('/api/templates')
def get_templates():
    templates = get_available_templates()
    return jsonify(templates)

@app.route('/api/templates/<template_name>/preview')
def get_template_preview(template_name):
    try:
        return send_from_directory(f'static/templates/{template_name}', 'preview.jpg')
    except:
        return jsonify({"error": "Preview not found"}), 404

@app.route('/api/templates/<template_name>/styles')
def get_template_styles(template_name):
    try:
        return send_from_directory(f'static/templates/{template_name}', 'styles.css')
    except:
        return jsonify({"error": "Template not found"}), 404

@app.route('/api/structure')
def get_structure():
    return jsonify(structure)

@app.route('/api/content', methods=['GET'])
def get_content():
    content, portfolio, galleries = load_data()
    return jsonify(content)

@app.route('/api/content', methods=['POST'])
def add_content():
    content, portfolio, galleries = load_data()
    
    # Get form data
    data = request.form.to_dict()
    files = request.files
    
    # Handle file uploads
    content_filename = None
    cover_filename = None
    
    if 'contentFile' in files:
        file = files['contentFile']
        if file.filename != '':
            content_filename = f"{datetime.now().timestamp()}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], content_filename))
    
    if 'coverFile' in files:
        file = files['coverFile']
        if file.filename != '':
            cover_filename = f"{datetime.now().timestamp()}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))
    
    # Create new content item
    new_id = max([item['id'] for item in content] or [0]) + 1
    
    content_item = {
        'id': new_id,
        'title': data.get('title', ''),
        'description': data.get('description', ''),
        'creation_date': data.get('creationDate', ''),
        'upload_date': datetime.now().isoformat(),
        'sphere': data.get('sphere', ''),
        'genre': data.get('genre', ''),
        'topic': data.get('topic', ''),
        'related': [int(id.strip()) for id in data.get('relatedIds', '').split(',') if id.strip()],
        'content_file': content_filename,
        'cover_file': cover_filename,
        'username': data.get('username', '')
    }
    
    content.append(content_item)
    save_data(content, portfolio, galleries)
    
    return jsonify({'status': 'success', 'id': new_id})

@app.route('/api/content/<int:content_id>', methods=['DELETE'])
def delete_content(content_id):
    content, portfolio, galleries = load_data()
    
    # Find and remove content item
    content = [item for item in content if item['id'] != content_id]
    
    save_data(content, portfolio, galleries)
    return jsonify({'status': 'success'})

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    _, portfolio, _ = load_data()
    return jsonify(portfolio)

@app.route('/api/portfolio', methods=['POST'])
def update_portfolio():
    content, portfolio, galleries = load_data()
    data = request.form.to_dict()
    files = request.files
    
    # Handle portrait upload
    if 'portrait' in files:
        file = files['portrait']
        if file.filename != '':
            portrait_filename = f"portrait_{datetime.now().timestamp()}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], portrait_filename))
            portfolio['portrait'] = portrait_filename
    
    # Update portfolio data
    portfolio.update({
        'fullName': data.get('fullName', ''),
        'quote': data.get('quote', ''),
        'bio': data.get('bio', ''),
        'accentColor': data.get('accentColor', '#8a5c2d'),
        'template': data.get('template', 'default'),
        'metaTags': {
            'title': data.get('metaTitle', ''),
            'description': data.get('metaDescription', ''),
            'keywords': data.get('metaKeywords', '')
        }
    })
    
    save_data(content, portfolio, galleries)
    return jsonify({'status': 'success'})

@app.route('/api/galleries', methods=['GET'])
def get_galleries():
    _, _, galleries = load_data()
    return jsonify(galleries)

@app.route('/api/galleries', methods=['POST'])
def create_gallery():
    content, portfolio, galleries = load_data()
    data = request.form.to_dict()
    files = request.files.getlist('galleryImages')
    
    # Handle gallery images upload
    image_filenames = []
    for file in files:
        if file.filename != '':
            filename = f"gallery_{datetime.now().timestamp()}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filenames.append(filename)
    
    # Create new gallery
    new_id = max([gallery['id'] for gallery in galleries] or [0]) + 1
    
    gallery = {
        'id': new_id,
        'title': data.get('title', ''),
        'description': data.get('description', ''),
        'type': data.get('type', 'grid'),
        'images': image_filenames,
        'created_date': datetime.now().isoformat()
    }
    
    galleries.append(gallery)
    save_data(content, portfolio, galleries)
    
    return jsonify({'status': 'success', 'id': new_id})

@app.route('/api/galleries/<int:gallery_id>', methods=['DELETE'])
def delete_gallery(gallery_id):
    content, portfolio, galleries = load_data()
    
    # Find and remove gallery
    galleries = [gallery for gallery in galleries if gallery['id'] != gallery_id]
    
    save_data(content, portfolio, galleries)
    return jsonify({'status': 'success'})

def process_template_for_seo(template_content, is_index=False):
    """
    Обрабатывает HTML-контент для создания человекочитаемых URL
    """
    # Заменяем все ссылки на .html файлы на чистые пути
    template_content = re.sub(r'href="([^"/]+)\.html"', r'href="/\1"', template_content)
    
    # ОСОБОЕ ПРАВИЛО: заменяем ссылки на главную страницу
    template_content = re.sub(r'href="(/?index)"', r'href="/"', template_content)
    
    # Для не-главных страниц добавляем корректные пути к ресурсам
    if not is_index:
        template_content = template_content.replace('src="content/', 'src="/content/')
        template_content = template_content.replace('src="covers/', 'src="/covers/')
        template_content = template_content.replace('src="galleries/', 'src="/galleries/')
        template_content = template_content.replace('src="portrait/', 'src="/portrait/')
        template_content = template_content.replace('href="styles.css"', 'href="/styles.css"')
        template_content = template_content.replace('src="graph.js"', 'src="/graph.js"')
        template_content = template_content.replace('src="gallery.js"', 'src="/gallery.js"')
    
    return template_content

# Обновленная функция экспорта с сохранением в Downloads
@app.route('/api/export', methods=['POST'])
def export_site():
    content, portfolio, galleries = load_data()
    data = request.json
    
    username = data.get('username', 'user')
    site_title = data.get('siteTitle', 'Портфолио творческих работ')
    template_name = portfolio.get('template', 'default')
    
    # Create in-memory ZIP file
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        # Add data.json
        export_data = {
            'user': username,
            'site_title': site_title,
            'generated_at': datetime.now().isoformat(),
            'portfolio': portfolio,
            'content': content,
            'galleries': galleries,
            'structure': structure
        }
        zf.writestr('data.json', json.dumps(export_data, ensure_ascii=False, indent=2))
        
        # Create a separate ZIP with all works
        all_works_zip = BytesIO()
        with zipfile.ZipFile(all_works_zip, 'w') as works_zip:
            for item in content:
                if item['content_file']:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], item['content_file'])
                    if os.path.exists(file_path):
                        # Use original filename but add ID to avoid conflicts
                        original_name = item['content_file'].split('_', 1)[1] if '_' in item['content_file'] else item['content_file']
                        works_zip.write(file_path, f"{item['id']}_{original_name}")
        
        all_works_zip.seek(0)
        zf.writestr('all_works.zip', all_works_zip.getvalue())
        
        # Add uploaded files
        for item in content:
            if item['content_file']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], item['content_file'])
                if os.path.exists(file_path):
                    zf.write(file_path, f"content/{item['content_file']}")
            
            if item['cover_file']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], item['cover_file'])
                if os.path.exists(file_path):
                    zf.write(file_path, f"covers/{item['cover_file']}")
        
        # Add gallery images
        for gallery in galleries:
            for image in gallery['images']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], image)
                if os.path.exists(file_path):
                    zf.write(file_path, f"galleries/{image}")
        
        if portfolio.get('portrait'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], portfolio['portrait'])
            if os.path.exists(file_path):
                zf.write(file_path, f"portrait/{portfolio['portrait']}")
        
        # Add HTML templates with proper data and SEO-friendly URLs
        index_html = render_template('export_index.html', 
                                   data=export_data, 
                                   structure=structure)
        works_html = render_template('export_works.html', 
                                   data=export_data, 
                                   structure=structure)
        graph_html = render_template('export_graph.html', 
                                   data=export_data, 
                                   structure=structure)
        downloads_html = render_template('export_downloads.html', 
                                      data=export_data, 
                                      structure=structure)
        gallery_html = render_template('export_gallery.html', 
                                     data=export_data, 
                                     structure=structure)
        
        # Process templates for SEO-friendly URLs
        index_html = process_template_for_seo(index_html, is_index=True)
        works_html = process_template_for_seo(works_html)
        graph_html = process_template_for_seo(graph_html)
        downloads_html = process_template_for_seo(downloads_html)
        gallery_html = process_template_for_seo(gallery_html)
        
        # Create directory structure for human-readable URLs
        zf.writestr('index.html', index_html)
        zf.writestr('works/index.html', works_html)
        zf.writestr('graph/index.html', graph_html)
        zf.writestr('downloads/index.html', downloads_html)
        zf.writestr('gallery/index.html', gallery_html)
        
        # Add JavaScript files
        with open('static/graph.js', 'r', encoding='utf-8') as f:
            zf.writestr('graph.js', f.read())
        
        with open('static/gallery.js', 'r', encoding='utf-8') as f:
            zf.writestr('gallery.js', f.read())
        
        # Add CSS from selected template
        template_path = f'static/templates/{template_name}/styles.css'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                zf.writestr('styles.css', f.read())
        else:
            # Fallback to default template
            with open('static/templates/default/styles.css', 'r', encoding='utf-8') as f:
                zf.writestr('styles.css', f.read())
        
        # Add .htaccess for Apache servers
        htaccess_content = '''
RewriteEngine On

# Remove .html extension
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME}\.html -f
RewriteRule ^(.*)$ $1.html [L]

# Redirect .html URLs to clean URLs
RewriteCond %{THE_REQUEST} /([^.]+)\.html [NC]
RewriteRule ^ /%1 [NC,L,R]
'''
        zf.writestr('.htaccess', htaccess_content)
        
        # Add _redirects for Netlify
        redirects_content = '''
/index.html    /    200
/works/index.html    /works    200
/graph/index.html    /graph    200
/downloads/index.html    /downloads    200
/gallery/index.html    /gallery    200
'''
        zf.writestr('_redirects', redirects_content)
    
    memory_file.seek(0)
    
    # Дополнительно сохраняем файл в папку Downloads
    try:
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        export_base_path = os.path.join(downloads_path, 'SoRUPP_Exports')
        os.makedirs(export_base_path, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'portfolio_{username}_{timestamp}.zip'
        zip_filepath = os.path.join(export_base_path, zip_filename)
        
        with open(zip_filepath, 'wb') as f:
            f.write(memory_file.getvalue())
            
        print(f"ZIP file also saved to: {zip_filepath}")
    except Exception as e:
        print(f"Error saving to Downloads: {e}")
    
    # Возвращаем файл для скачивания
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        download_name=f'portfolio_{username}.zip',
        as_attachment=True,
        mimetype='application/zip'
    )

# Эндпоинт для скачивания уже сохраненного файла
@app.route('/api/download-export/<filename>')
def download_export(filename):
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    export_base_path = os.path.join(downloads_path, 'SoRUPP_Exports')
    
    try:
        return send_from_directory(
            export_base_path, 
            filename, 
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404

# Эндпоинт для получения списка экспортированных файлов
@app.route('/api/exported-files', methods=['GET'])
def get_exported_files():
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    export_base_path = os.path.join(downloads_path, 'SoRUPP_Exports')
    
    if not os.path.exists(export_base_path):
        return jsonify([])
    
    files = []
    for filename in os.listdir(export_base_path):
        if filename.endswith('.zip'):
            filepath = os.path.join(export_base_path, filename)
            stat = os.stat(filepath)
            files.append({
                'name': filename,
                'path': filepath,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
    
    # Сортируем по дате создания (новые сверху)
    files.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(files)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')

@app.route('/api/process-seo', methods=['POST'])
def process_seo():
    try:
        # Запускаем обработчик SEO
        import subprocess
        result = subprocess.run(['python', 'seo_url_processor.py', 'export_directory'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'message': 'SEO-оптимизация выполнена'})
        else:
            return jsonify({'status': 'error', 'message': result.stderr}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)