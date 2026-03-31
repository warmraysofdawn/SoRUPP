import os
import json
import shutil
import hashlib
import zipfile
import re
import tempfile
import csv
import base64
import logging
from functools import wraps
from datetime import datetime
from io import BytesIO, StringIO
from hmac import compare_digest

from flask import (
    Flask, render_template, request, jsonify,
    send_file, send_from_directory, Response, abort, session
)
from flask_cors import CORS
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from github import Github, GithubException
import gitlab
import markdown


# ----------------------------------------------------------------------
# Конфигурация и настройки
# ----------------------------------------------------------------------
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24).hex())
    MASTER_PASSWORD = os.environ.get('MASTER_PASSWORD')  # Может быть None (необязательный)
    UPLOAD_FOLDER = 'static/uploads'
    BACKUP_FOLDER = 'backups'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    MAX_BACKUPS = 10
    DATA_DIR = 'data'
    STATIC_TEMPLATES = 'static/templates'
    SALT_FILE = os.path.join(DATA_DIR, 'salt.bin')


app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=["http://127.0.0.1:5000", "http://localhost:5000"])

# Создаём необходимые папки
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_DIR'], exist_ok=True)
os.makedirs(app.config['STATIC_TEMPLATES'], exist_ok=True)
os.makedirs(app.config['BACKUP_FOLDER'], exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Утилиты для шифрования (Git токен) – работают только если задан MASTER_PASSWORD
# ----------------------------------------------------------------------
def _get_salt():
    """Читает или генерирует случайную соль для PBKDF2."""
    salt_path = app.config['SALT_FILE']
    if os.path.exists(salt_path):
        with open(salt_path, 'rb') as f:
            return f.read()
    salt = os.urandom(16)
    with open(salt_path, 'wb') as f:
        f.write(salt)
    return salt


def get_cipher_from_password(password):
    """Создаёт объект Fernet на основе пароля (PBKDF2)."""
    if password is None:
        raise ValueError("MASTER_PASSWORD environment variable is not set. Git functions will not work.")
    password_bytes = password.encode('utf-8')
    salt = _get_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000
    )
    key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
    return Fernet(key)


def encrypt_token(token):
    """Шифрует токен. Требует MASTER_PASSWORD."""
    cipher = get_cipher_from_password(app.config['MASTER_PASSWORD'])
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token):
    """Расшифровывает токен. Требует MASTER_PASSWORD."""
    cipher = get_cipher_from_password(app.config['MASTER_PASSWORD'])
    return cipher.decrypt(encrypted_token.encode()).decode()


# ----------------------------------------------------------------------
# Аутентификация (простая HTTP Basic – опционально)
# ----------------------------------------------------------------------
def check_auth(username, password):
    """Проверяет логин/пароль. Если переменные не заданы – доступ разрешён."""
    valid_user = os.environ.get('AUTH_USERNAME')
    valid_pass = os.environ.get('AUTH_PASSWORD')
    if not valid_user or not valid_pass:
        # Аутентификация отключена
        return True
    return compare_digest(username, valid_user) and compare_digest(password, valid_pass)


def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Если аутентификация отключена (переменные не заданы) — пропускаем всех
        if not os.environ.get('AUTH_USERNAME') or not os.environ.get('AUTH_PASSWORD'):
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# ----------------------------------------------------------------------
# Вспомогательные функции для работы с файлами
# ----------------------------------------------------------------------
def allowed_file(filename, file_type):
    """Проверяет расширение файла по заданному типу."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in app.config['ALLOWED_EXTENSIONS'].get(file_type, set())


def secure_filename(filename):
    """Генерирует безопасное имя файла с временной меткой."""
    ts = str(datetime.now().timestamp()).replace('.', '')
    name, ext = os.path.splitext(filename)
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '', name)[:50]
    return f"{ts}_{safe_name}{ext}"


def save_uploaded_file(file, file_type, subdir=''):
    if not file or not file.filename:
        return None, None
    # Убрана проверка allowed_file
    filename = secure_filename(file.filename)
    if subdir:
        full_dir = os.path.join(app.config['UPLOAD_FOLDER'], subdir)
        os.makedirs(full_dir, exist_ok=True)
        filepath = os.path.join(full_dir, filename)
    else:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    file_hash = compute_file_hash(filepath)
    if subdir:
        return os.path.join(subdir, filename), file_hash
    return filename, file_hash


def compute_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            sha256.update(block)
    return sha256.hexdigest()


def compute_data_hash(data_dict):
    data_str = json.dumps(data_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()


def delete_file_if_exists(relative_path):
    """Удаляет файл по относительному пути внутри UPLOAD_FOLDER (безопасно)."""
    if not relative_path:
        return
    safe_path = os.path.normpath(relative_path)
    if safe_path.startswith('..') or safe_path.startswith('/'):
        logger.warning(f"Attempted to delete unsafe path: {relative_path}")
        return
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_path)
    if os.path.exists(full_path) and os.path.isfile(full_path):
        os.remove(full_path)


# ----------------------------------------------------------------------
# Загрузка и сохранение данных (с кэшированием)
# ----------------------------------------------------------------------
_data_cache = {
    'content': None,
    'portfolio': None,
    'galleries': None,
    'content_hash': None,
    'portfolio_hash': None,
    'galleries_hash': None
}


def _load_json(filepath, default):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_data(use_cache=True):
    """Загружает данные из JSON. При use_cache=True возвращает закэшированные, если хеши совпадают."""
    global _data_cache

    content_path = os.path.join(app.config['DATA_DIR'], 'content.json')
    portfolio_path = os.path.join(app.config['DATA_DIR'], 'portfolio.json')
    galleries_path = os.path.join(app.config['DATA_DIR'], 'galleries.json')

    def load_if_changed(path, cache_key, data_key):
        try:
            with open(path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
        except (FileNotFoundError, OSError):
            file_hash = None   # файла нет – хеш не считаем

        if use_cache and _data_cache.get(cache_key) == file_hash:
            return _data_cache[data_key]

        data = _load_json(path, {} if data_key == 'portfolio' else [])
        _data_cache[cache_key] = file_hash
        _data_cache[data_key] = data
        return data

    content = load_if_changed(content_path, 'content_hash', 'content')
    portfolio = load_if_changed(portfolio_path, 'portfolio_hash', 'portfolio')
    galleries = load_if_changed(galleries_path, 'galleries_hash', 'galleries')

    # Для обратной совместимости
    for work in content:
        if 'tags' not in work:
            work['tags'] = []

    return content, portfolio, galleries


def save_data(content, portfolio, galleries):
    """Сохраняет данные и сбрасывает кэш."""
    with open(os.path.join(app.config['DATA_DIR'], 'content.json'), 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    with open(os.path.join(app.config['DATA_DIR'], 'portfolio.json'), 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    with open(os.path.join(app.config['DATA_DIR'], 'galleries.json'), 'w', encoding='utf-8') as f:
        json.dump(galleries, f, ensure_ascii=False, indent=2)

    # Инвалидируем кэш
    for key in ['content_hash', 'portfolio_hash', 'galleries_hash']:
        _data_cache[key] = None


# ----------------------------------------------------------------------
# Структура данных (полная версия)
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# Резервное копирование (backup)
# ----------------------------------------------------------------------
def get_backup_list():
    backups = []
    for filename in sorted(os.listdir(app.config['BACKUP_FOLDER']), reverse=True):
        if filename.endswith('.zip'):
            filepath = os.path.join(app.config['BACKUP_FOLDER'], filename)
            stat = os.stat(filepath)
            backups.append({
                'name': filename,
                'path': filepath,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
    return backups


def create_backup(comment=''):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'backup_{timestamp}.zip'
    backup_path = os.path.join(app.config['BACKUP_FOLDER'], backup_filename)

    content, portfolio, galleries = load_data()
    temp_dir = tempfile.mkdtemp(prefix='backup_')

    # Копируем uploads
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.copytree(app.config['UPLOAD_FOLDER'], os.path.join(temp_dir, 'uploads'))

    # Сохраняем JSON
    with open(os.path.join(temp_dir, 'content.json'), 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    with open(os.path.join(temp_dir, 'portfolio.json'), 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    with open(os.path.join(temp_dir, 'galleries.json'), 'w', encoding='utf-8') as f:
        json.dump(galleries, f, ensure_ascii=False, indent=2)
    with open(os.path.join(temp_dir, 'structure.json'), 'w', encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    # Манифест
    manifest = {
        'created': datetime.now().isoformat(),
        'comment': comment,
        'files': []
    }
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), temp_dir)
            manifest['files'].append(rel_path)
    with open(os.path.join(temp_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Создаём архив
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zf.write(file_path, arcname)

    shutil.rmtree(temp_dir)

    # Ограничиваем количество бэкапов
    backups = sorted([f for f in os.listdir(app.config['BACKUP_FOLDER']) if f.endswith('.zip')])
    while len(backups) > app.config['MAX_BACKUPS']:
        oldest = backups.pop(0)
        os.remove(os.path.join(app.config['BACKUP_FOLDER'], oldest))

    return backup_filename


def restore_from_backup(backup_filename, selected_files=None):
    backup_path = os.path.join(app.config['BACKUP_FOLDER'], backup_filename)
    if not os.path.exists(backup_path):
        raise FileNotFoundError('Бэкап не найден')

    temp_restore = tempfile.mkdtemp(prefix='restore_')
    with zipfile.ZipFile(backup_path, 'r') as zf:
        zf.extractall(temp_restore)

    if selected_files is None:
        # Полное восстановление
        uploads_src = os.path.join(temp_restore, 'uploads')
        if os.path.exists(uploads_src):
            for item in os.listdir(uploads_src):
                s = os.path.join(uploads_src, item)
                d = os.path.join(app.config['UPLOAD_FOLDER'], item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        for jf in ['content.json', 'portfolio.json', 'galleries.json', 'structure.json']:
            src = os.path.join(temp_restore, jf)
            if os.path.exists(src):
                shutil.copy2(src, app.config['DATA_DIR'])
    else:
        # Выборочное восстановление
        for rel_path in selected_files:
            src = os.path.join(temp_restore, rel_path)
            if not os.path.exists(src):
                continue
            if rel_path.startswith('uploads/'):
                dest = os.path.join(app.config['UPLOAD_FOLDER'], rel_path[8:])
            else:
                dest = os.path.join(app.config['DATA_DIR'], rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)

    shutil.rmtree(temp_restore)
    load_data(use_cache=False)  # сброс кэша
    return True


# ----------------------------------------------------------------------
# Проверка целостности
# ----------------------------------------------------------------------
def check_integrity():
    content, portfolio, galleries = load_data()
    issues = []

    for work in content:
        for fld in ['content_file', 'cover_file', 'readme_file']:
            if work.get(fld):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], work[fld])
                if os.path.exists(filepath):
                    current_hash = compute_file_hash(filepath)
                    expected = work.get(fld[:-5] + '_hash')
                    if expected and current_hash != expected:
                        issues.append({
                            'type': f'work_{fld}',
                            'id': work['id'],
                            'field': fld,
                            'expected': expected,
                            'actual': current_hash,
                            'file': work[fld]
                        })
                else:
                    issues.append({
                        'type': f'work_{fld}',
                        'id': work['id'],
                        'field': fld,
                        'error': 'file_missing',
                        'file': work[fld]
                    })

    if portfolio.get('portrait'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], portfolio['portrait'])
        if os.path.exists(filepath):
            current_hash = compute_file_hash(filepath)
            if current_hash != portfolio.get('portrait_hash'):
                issues.append({
                    'type': 'portfolio_portrait',
                    'expected': portfolio['portrait_hash'],
                    'actual': current_hash,
                    'file': portfolio['portrait']
                })
        else:
            issues.append({
                'type': 'portfolio_portrait',
                'error': 'file_missing',
                'file': portfolio['portrait']
            })

    for gallery in galleries:
        for i, img in enumerate(gallery.get('images', [])):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], img)
            if os.path.exists(filepath):
                current_hash = compute_file_hash(filepath)
                expected = gallery.get('images_hashes', [])[i] if i < len(gallery.get('images_hashes', [])) else None
                if expected and current_hash != expected:
                    issues.append({
                        'type': 'gallery_image',
                        'gallery_id': gallery['id'],
                        'image_index': i,
                        'expected': expected,
                        'actual': current_hash,
                        'file': img
                    })
            else:
                issues.append({
                    'type': 'gallery_image',
                    'gallery_id': gallery['id'],
                    'image_index': i,
                    'error': 'file_missing',
                    'file': img
                })

    return issues


# ----------------------------------------------------------------------
# Маршруты
# ----------------------------------------------------------------------

@app.route('/')
@requires_auth
def index():
    templates = get_available_templates()
    return render_template('index.html', templates=templates)


def get_available_templates():
    templates = []
    templates_dir = app.config['STATIC_TEMPLATES']
    if os.path.exists(templates_dir):
        for item in os.listdir(templates_dir):
            if os.path.isdir(os.path.join(templates_dir, item)):
                template_path = os.path.join(templates_dir, item)
                preview_path = os.path.join(template_path, 'preview.jpg')
                css_path = os.path.join(template_path, 'styles.css')
                if os.path.exists(css_path):
                    templates.append({
                        'name': item,
                        'preview': f'/static/templates/{item}/preview.jpg' if os.path.exists(preview_path) else None,
                        'hasPreview': os.path.exists(preview_path)
                    })
    return templates


@app.route('/api/templates')
@requires_auth
def get_templates():
    return jsonify(get_available_templates())


@app.route('/api/templates/<template_name>/preview')
@requires_auth
def get_template_preview(template_name):
    try:
        return send_from_directory(f'static/templates/{template_name}', 'preview.jpg')
    except FileNotFoundError:
        abort(404)


@app.route('/api/templates/<template_name>/styles')
@requires_auth
def get_template_styles(template_name):
    try:
        return send_from_directory(f'static/templates/{template_name}', 'styles.css')
    except FileNotFoundError:
        abort(404)


@app.route('/api/structure')
@requires_auth
def get_structure():
    return jsonify(structure)


@app.route('/api/content', methods=['GET'])
@requires_auth
def get_content():
    content, _, _ = load_data()
    return jsonify(content)


@app.route('/api/content', methods=['POST'])
@requires_auth
def add_content():
    content, portfolio, galleries = load_data()
    data = request.form.to_dict()
    files = request.files

    try:
        content_filename, content_hash = save_uploaded_file(files.get('contentFile'), 'contentFile')
        cover_filename, cover_hash = save_uploaded_file(files.get('coverFile'), 'coverFile')
        readme_filename, readme_hash = save_uploaded_file(files.get('readmeFile'), 'readmeFile')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    tags = [t.strip() for t in data.get('tags', '').split(',') if t.strip()]
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
        'tags': tags,
        'content_file': content_filename,
        'content_hash': content_hash,
        'cover_file': cover_filename,
        'cover_hash': cover_hash,
        'username': data.get('username', ''),
        'detailed_description': data.get('detailed_description', ''),
        'readme_file': readme_filename,
        'readme_hash': readme_hash
    }

    content.append(content_item)
    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after adding work #{new_id}")
    return jsonify({'status': 'success', 'id': new_id})


@app.route('/api/content/<int:content_id>', methods=['PUT'])
@requires_auth
def edit_content(content_id):
    content, portfolio, galleries = load_data()
    data = request.form.to_dict()
    files = request.files

    work = next((w for w in content if w['id'] == content_id), None)
    if not work:
        return jsonify({'error': 'Work not found'}), 404

    for fld, fld_hash, file_key in [
        ('content_file', 'content_hash', 'contentFile'),
        ('cover_file', 'cover_hash', 'coverFile'),
        ('readme_file', 'readme_hash', 'readmeFile')
    ]:
        if file_key in files and files[file_key].filename:
            try:
                new_name, new_hash = save_uploaded_file(files[file_key], file_key)
                if new_name:
                    delete_file_if_exists(work.get(fld))
                    work[fld] = new_name
                    work[fld_hash] = new_hash
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

    tags = [t.strip() for t in data.get('tags', '').split(',') if t.strip()]
    work['tags'] = tags

    work['title'] = data.get('title', work['title'])
    work['description'] = data.get('description', work['description'])
    work['creation_date'] = data.get('creationDate', work['creation_date'])
    work['sphere'] = data.get('sphere', work['sphere'])
    work['genre'] = data.get('genre', work['genre'])
    work['topic'] = data.get('topic', work['topic'])
    work['related'] = [int(id.strip()) for id in data.get('relatedIds', '').split(',') if id.strip()]
    work['username'] = data.get('username', work['username'])
    work['detailed_description'] = data.get('detailed_description', work.get('detailed_description', ''))

    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after editing work #{content_id}")
    return jsonify({'status': 'success'})


@app.route('/api/content/<int:content_id>', methods=['DELETE'])
@requires_auth
def delete_content(content_id):
    content, portfolio, galleries = load_data()
    work = next((w for w in content if w['id'] == content_id), None)
    if work:
        for fld in ['content_file', 'cover_file', 'readme_file']:
            delete_file_if_exists(work.get(fld))
    content = [item for item in content if item['id'] != content_id]
    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after deleting work #{content_id}")
    return jsonify({'status': 'success'})


@app.route('/api/content/batch', methods=['DELETE'])
@requires_auth
def delete_content_batch():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': 'No ids provided'}), 400
    content, portfolio, galleries = load_data()
    for work in content:
        if work['id'] in ids:
            for fld in ['content_file', 'cover_file', 'readme_file']:
                delete_file_if_exists(work.get(fld))
    content = [item for item in content if item['id'] not in ids]
    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after batch delete {ids}")
    return jsonify({'status': 'success', 'deleted': ids})


@app.route('/api/portfolio', methods=['GET'])
@requires_auth
def get_portfolio():
    _, portfolio, _ = load_data()
    return jsonify(portfolio)


@app.route('/api/portfolio', methods=['POST'])
@requires_auth
def update_portfolio():
    content, portfolio, galleries = load_data()
    data = request.form.to_dict()
    files = request.files

    if 'portrait' in files and files['portrait'].filename:
        try:
            new_portrait, new_hash = save_uploaded_file(files['portrait'], 'portrait')
            delete_file_if_exists(portfolio.get('portrait'))
            portfolio['portrait'] = new_portrait
            portfolio['portrait_hash'] = new_hash
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

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
    create_backup(comment="Auto-backup after updating portfolio")
    return jsonify({'status': 'success'})


@app.route('/api/galleries', methods=['GET'])
@requires_auth
def get_galleries():
    _, _, galleries = load_data()
    return jsonify(galleries)


@app.route('/api/galleries', methods=['POST'])
@requires_auth
def create_gallery():
    content, portfolio, galleries = load_data()
    data = request.form.to_dict()
    files = request.files.getlist('galleryImages')

    image_filenames = []
    image_hashes = []
    for file in files:
        if file.filename:
            try:
                fname, fhash = save_uploaded_file(file, 'galleryImages')
                image_filenames.append(fname)
                image_hashes.append(fhash)
            except ValueError as e:
                for img in image_filenames:
                    delete_file_if_exists(img)
                return jsonify({'error': str(e)}), 400

    new_id = max([g['id'] for g in galleries] or [0]) + 1
    gallery = {
        'id': new_id,
        'title': data.get('title', ''),
        'description': data.get('description', ''),
        'type': data.get('type', 'grid'),
        'images': image_filenames,
        'images_hashes': image_hashes,
        'created_date': datetime.now().isoformat()
    }
    galleries.append(gallery)
    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after creating gallery #{new_id}")
    return jsonify({'status': 'success', 'id': new_id})


@app.route('/api/galleries/<int:gallery_id>', methods=['PUT'])
@requires_auth
def update_gallery(gallery_id):
    content, portfolio, galleries = load_data()
    gallery = next((g for g in galleries if g['id'] == gallery_id), None)
    if not gallery:
        return jsonify({'error': 'Gallery not found'}), 404

    data = request.form.to_dict()
    files = request.files.getlist('galleryImages')
    removed = request.form.getlist('removedImages')

    for img in removed:
        if img in gallery['images']:
            idx = gallery['images'].index(img)
            delete_file_if_exists(img)
            gallery['images'].pop(idx)
            gallery['images_hashes'].pop(idx)

    for file in files:
        if file.filename:
            try:
                fname, fhash = save_uploaded_file(file, 'galleryImages')
                gallery['images'].append(fname)
                gallery['images_hashes'].append(fhash)
            except ValueError as e:
                return jsonify({'error': str(e)}), 400

    gallery['title'] = data.get('title', gallery['title'])
    gallery['description'] = data.get('description', gallery['description'])
    gallery['type'] = data.get('type', gallery['type'])

    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after updating gallery #{gallery_id}")
    return jsonify({'status': 'success'})


@app.route('/api/galleries/<int:gallery_id>', methods=['DELETE'])
@requires_auth
def delete_gallery(gallery_id):
    content, portfolio, galleries = load_data()
    gallery = next((g for g in galleries if g['id'] == gallery_id), None)
    if gallery:
        for img in gallery.get('images', []):
            delete_file_if_exists(img)
    galleries = [g for g in galleries if g['id'] != gallery_id]
    save_data(content, portfolio, galleries)
    create_backup(comment=f"Auto-backup after deleting gallery #{gallery_id}")
    return jsonify({'status': 'success'})


@app.route('/api/backups', methods=['GET'])
@requires_auth
def list_backups():
    return jsonify(get_backup_list())


@app.route('/api/backups', methods=['POST'])
@requires_auth
def create_backup_route():
    data = request.get_json() or {}
    comment = data.get('comment', '')
    try:
        filename = create_backup(comment)
        return jsonify({'filename': filename})
    except Exception as e:
        logger.exception("Backup creation failed")
        return jsonify({'error': str(e)}), 500


@app.route('/api/backups/<filename>/restore', methods=['POST'])
@requires_auth
def restore_backup_route(filename):
    data = request.get_json() or {}
    selected_files = data.get('files')
    try:
        restore_from_backup(filename, selected_files)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.exception("Restore failed")
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrity/check', methods=['GET'])
@requires_auth
def integrity_check():
    issues = check_integrity()
    return jsonify(issues)


@app.route('/api/integrity/repair', methods=['POST'])
@requires_auth
def integrity_repair():
    data = request.get_json()
    backup_filename = data.get('backup')
    files = data.get('files')
    if not backup_filename:
        return jsonify({'error': 'No backup specified'}), 400
    try:
        restore_from_backup(backup_filename, files)
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.exception("Repair failed")
        return jsonify({'error': str(e)}), 500


# ----------------------------------------------------------------------
# Git интеграция – работает только если задан MASTER_PASSWORD
# ----------------------------------------------------------------------
GIT_CONFIG_FILE = os.path.join(app.config['DATA_DIR'], 'git_config.json')


def load_git_config():
    """Загружает конфиг Git. Если MASTER_PASSWORD не задан, возвращает пустой конфиг."""
    if not app.config['MASTER_PASSWORD']:
        logger.warning("MASTER_PASSWORD not set, Git integration disabled.")
        return {}
    try:
        with open(GIT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if 'encrypted_token' in config:
                try:
                    config['token'] = decrypt_token(config['encrypted_token'])
                except Exception as e:
                    logger.warning(f"Failed to decrypt Git token: {e}")
                    config['token'] = None
            return config
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_git_config(provider, repo, token):
    """Сохраняет конфиг Git. Требует MASTER_PASSWORD."""
    if not app.config['MASTER_PASSWORD']:
        raise ValueError("MASTER_PASSWORD not set, cannot save Git configuration.")
    config = {
        'provider': provider,
        'repo': repo,
        'encrypted_token': encrypt_token(token)
    }
    with open(GIT_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def git_required(f):
    """Декоратор для маршрутов Git, проверяет наличие MASTER_PASSWORD."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not app.config['MASTER_PASSWORD']:
            return jsonify({'error': 'Git integration is disabled because MASTER_PASSWORD is not set'}), 503
        return f(*args, **kwargs)
    return decorated


@app.route('/api/git/settings', methods=['POST'])
@requires_auth
@git_required
def git_save_settings():
    data = request.json
    provider = data.get('provider')
    token = data.get('token')
    repo = data.get('repo')
    if not all([provider, token, repo]):
        return jsonify({'error': 'Missing fields'}), 400
    try:
        save_git_config(provider, repo, token)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/git/test', methods=['POST'])
@requires_auth
@git_required
def git_test():
    data = request.json
    provider = data.get('provider')
    token = data.get('token')
    repo = data.get('repo')
    try:
        if provider == 'github':
            g = Github(token)
            g.get_user().login
            g.get_repo(repo)
        elif provider == 'gitlab':
            gl = gitlab.Gitlab(private_token=token)
            gl.auth()
            gl.projects.get(repo)
        else:
            return jsonify({'error': 'Unsupported provider'}), 400
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/git/commits', methods=['GET'])
@requires_auth
@git_required
def git_commits():
    config = load_git_config()
    if not config or not config.get('token'):
        return jsonify({'error': 'Git not configured'}), 400
    provider = config['provider']
    token = config['token']
    repo_name = config['repo']
    try:
        if provider == 'github':
            g = Github(token)
            repo = g.get_repo(repo_name)
            commits = repo.get_commits()
            result = [{
                'sha': c.sha,
                'message': c.commit.message,
                'author': c.commit.author.name,
                'date': c.commit.author.date.isoformat()
            } for c in commits[:50]]
        elif provider == 'gitlab':
            gl = gitlab.Gitlab(private_token=token)
            project = gl.projects.get(repo_name)
            commits = project.commits.list()
            result = [{
                'sha': c.id,
                'message': c.message,
                'author': c.author_name,
                'date': c.committed_date
            } for c in commits[:50]]
        else:
            return jsonify({'error': 'Unsupported provider'}), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/git/commits/<sha>/files', methods=['GET'])
@requires_auth
@git_required
def git_commit_files(sha):
    config = load_git_config()
    if not config or not config.get('token'):
        return jsonify({'error': 'Git not configured'}), 400
    provider = config['provider']
    token = config['token']
    repo_name = config['repo']
    try:
        if provider == 'github':
            g = Github(token)
            repo = g.get_repo(repo_name)
            commit = repo.get_commit(sha)
            files = [f.filename for f in commit.files]
        elif provider == 'gitlab':
            gl = gitlab.Gitlab(private_token=token)
            project = gl.projects.get(repo_name)
            commit = project.commits.get(sha)
            files = [diff['new_path'] for diff in commit.diffs.list()]
        else:
            return jsonify({'error': 'Unsupported provider'}), 400
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/git/push', methods=['POST'])
@requires_auth
@git_required
def git_push():
    config = load_git_config()
    if not config or not config.get('token'):
        return jsonify({'error': 'Git not configured'}), 400

    data = request.json or {}
    commit_message = data.get('message', 'Auto-backup from portfolio')

    provider = config['provider']
    token = config['token']
    repo_name = config['repo']

    try:
        temp_dir = tempfile.mkdtemp(prefix='git_push_')
        content, portfolio, galleries = load_data()

        with open(os.path.join(temp_dir, 'content.json'), 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        with open(os.path.join(temp_dir, 'portfolio.json'), 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        with open(os.path.join(temp_dir, 'galleries.json'), 'w', encoding='utf-8') as f:
            json.dump(galleries, f, ensure_ascii=False, indent=2)
        with open(os.path.join(temp_dir, 'structure.json'), 'w', encoding='utf-8') as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.copytree(app.config['UPLOAD_FOLDER'],
                            os.path.join(temp_dir, 'uploads'),
                            dirs_exist_ok=True)

        if provider == 'github':
            from github import InputGitTreeElement

            g = Github(token)
            repo = g.get_repo(repo_name)

            try:
                branch = repo.get_branch(repo.default_branch)
                base_sha = branch.commit.sha
            except GithubException:
                base_sha = None

            elements = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    with open(file_path, 'rb') as f:
                        content_bytes = f.read()
                    blob = repo.create_git_blob(content_bytes, "base64")
                    elements.append(InputGitTreeElement(
                        path=rel_path, mode='100644', type='blob', sha=blob.sha
                    ))

            tree = repo.create_git_tree(elements)
            commit = repo.create_git_commit(commit_message, tree, [repo.get_git_commit(base_sha)] if base_sha else [])
            ref = repo.get_git_ref(f"heads/{repo.default_branch}")
            ref.edit(sha=commit.sha)

        elif provider == 'gitlab':
            gl = gitlab.Gitlab(private_token=token)
            project = gl.projects.get(repo_name)

            branch_name = project.default_branch
            actions = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    actions.append({
                        'action': 'update',
                        'file_path': rel_path,
                        'content': base64.b64encode(content).decode('utf-8'),
                        'encoding': 'base64'
                    })

            commit_data = {
                'branch': branch_name,
                'commit_message': commit_message,
                'actions': actions
            }
            project.commits.create(commit_data)
        else:
            return jsonify({'error': 'Unsupported provider'}), 400

        shutil.rmtree(temp_dir)
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.exception("Git push failed")
        return jsonify({'error': str(e)}), 400


@app.route('/api/git/pull', methods=['POST'])
@requires_auth
@git_required
def git_pull():
    config = load_git_config()
    if not config or not config.get('token'):
        return jsonify({'error': 'Git not configured'}), 400

    provider = config['provider']
    token = config['token']
    repo_name = config['repo']

    try:
        if provider == 'github':
            g = Github(token)
            repo = g.get_repo(repo_name)
            branch = repo.default_branch
            temp_dir = tempfile.mkdtemp(prefix='git_pull_')

            def download_contents(path):
                items = repo.get_contents(path, ref=branch)
                for item in items:
                    if item.type == 'dir':
                        download_contents(item.path)
                    else:
                        file_data = base64.b64decode(item.content)
                        local_path = os.path.join(temp_dir, item.path)
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        with open(local_path, 'wb') as f:
                            f.write(file_data)
            download_contents("")

        elif provider == 'gitlab':
            gl = gitlab.Gitlab(private_token=token)
            project = gl.projects.get(repo_name)
            branch = project.default_branch
            temp_dir = tempfile.mkdtemp(prefix='git_pull_')
            items = project.repository_tree(ref=branch, all=True)
            for item in items:
                if item['type'] == 'blob':
                    file_content = project.files.get(file_path=item['path'], ref=branch)
                    local_path = os.path.join(temp_dir, item['path'])
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, 'wb') as f:
                        f.write(base64.b64decode(file_content.content))
        else:
            return jsonify({'error': 'Unsupported provider'}), 400

        for jf in ['content.json', 'portfolio.json', 'galleries.json', 'structure.json']:
            src = os.path.join(temp_dir, jf)
            if os.path.exists(src):
                shutil.copy2(src, app.config['DATA_DIR'])

        uploads_src = os.path.join(temp_dir, 'uploads')
        if os.path.exists(uploads_src):
            for item in os.listdir(uploads_src):
                s = os.path.join(uploads_src, item)
                d = os.path.join(app.config['UPLOAD_FOLDER'], item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

        shutil.rmtree(temp_dir)
        load_data(use_cache=False)
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.exception("Git pull failed")
        return jsonify({'error': str(e)}), 400


@app.route('/api/git/restore', methods=['POST'])
@requires_auth
@git_required
def git_restore():
    data = request.json
    sha = data.get('sha')
    files = data.get('files')
    config = load_git_config()
    if not config or not config.get('token'):
        return jsonify({'error': 'Git not configured'}), 400

    provider = config['provider']
    token = config['token']
    repo_name = config['repo']

    try:
        if provider == 'github':
            g = Github(token)
            repo = g.get_repo(repo_name)
            for file_path in files:
                try:
                    contents = repo.get_contents(file_path, ref=sha)
                    file_data = base64.b64decode(contents.content)
                    if file_path.startswith('uploads/'):
                        local_file = os.path.join(app.config['UPLOAD_FOLDER'], file_path[8:])
                    elif file_path.endswith('.json'):
                        local_file = os.path.join(app.config['DATA_DIR'], os.path.basename(file_path))
                    else:
                        continue
                    os.makedirs(os.path.dirname(local_file), exist_ok=True)
                    with open(local_file, 'wb') as f:
                        f.write(file_data)
                except Exception as e:
                    logger.warning(f"Error restoring {file_path}: {e}")

        elif provider == 'gitlab':
            gl = gitlab.Gitlab(private_token=token)
            project = gl.projects.get(repo_name)
            for file_path in files:
                try:
                    f = project.files.get(file_path=file_path, ref=sha)
                    file_data = base64.b64decode(f.content)
                    if file_path.startswith('uploads/'):
                        local_file = os.path.join(app.config['UPLOAD_FOLDER'], file_path[8:])
                    elif file_path.endswith('.json'):
                        local_file = os.path.join(app.config['DATA_DIR'], os.path.basename(file_path))
                    else:
                        continue
                    os.makedirs(os.path.dirname(local_file), exist_ok=True)
                    with open(local_file, 'wb') as f_out:
                        f_out.write(file_data)
                except Exception as e:
                    logger.warning(f"Error restoring {file_path}: {e}")
        else:
            return jsonify({'error': 'Unsupported provider'}), 400

        load_data(use_cache=False)
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ----------------------------------------------------------------------
# Экспорт сайта
# ----------------------------------------------------------------------
@app.route('/api/export', methods=['POST'])
@requires_auth
def export_site():
    content, portfolio, galleries = load_data()
    data = request.json

    username = data.get('username', 'user')
    site_title = data.get('siteTitle', 'Портфолио творческих работ')
    template_name = portfolio.get('template', 'default')

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
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

        for work in content:
            work_copy = work.copy()
            readme_html = ''
            if work.get('readme_file'):
                readme_path = os.path.join(app.config['UPLOAD_FOLDER'], work['readme_file'])
                if os.path.exists(readme_path):
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        readme_content = f.read()
                    readme_html = markdown.markdown(readme_content)
            elif work.get('detailed_description'):
                readme_html = markdown.markdown(work['detailed_description'])
            work_copy['readme_html'] = readme_html

            related_works = []
            for rel_id in work.get('related', []):
                rel_work = next((w for w in content if w['id'] == rel_id), None)
                if rel_work:
                    related_works.append(rel_work)
            work_copy['related_works'] = related_works

            work_html = render_template('export_work.html', data=export_data, work=work_copy, structure=structure)
            work_html = process_template_for_seo(work_html)
            zf.writestr(f'works/{work["id"]}.html', work_html)

        all_works_zip = BytesIO()
        with zipfile.ZipFile(all_works_zip, 'w') as works_zip:
            for item in content:
                if item.get('content_file'):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], item['content_file'])
                    if os.path.exists(file_path):
                        original_name = item['content_file'].split('_', 1)[1] if '_' in item['content_file'] else item['content_file']
                        works_zip.write(file_path, f"{item['id']}_{original_name}")
        all_works_zip.seek(0)
        zf.writestr('all_works.zip', all_works_zip.getvalue())

        index_html = render_template('export_index.html', data=export_data, structure=structure)
        works_html = render_template('export_works.html', data=export_data, structure=structure)
        graph_html = render_template('export_graph.html', data=export_data, structure=structure)
        downloads_html = render_template('export_downloads.html', data=export_data, structure=structure)
        gallery_html = render_template('export_gallery.html', data=export_data, structure=structure)

        index_html = process_template_for_seo(index_html, is_index=True)
        works_html = process_template_for_seo(works_html)
        graph_html = process_template_for_seo(graph_html)
        downloads_html = process_template_for_seo(downloads_html)
        gallery_html = process_template_for_seo(gallery_html)

        zf.writestr('index.html', index_html)
        zf.writestr('works/index.html', works_html)
        zf.writestr('graph/index.html', graph_html)
        zf.writestr('downloads/index.html', downloads_html)
        zf.writestr('gallery/index.html', gallery_html)

        if os.path.exists('static/graph.js'):
            with open('static/graph.js', 'r', encoding='utf-8') as f:
                zf.writestr('graph.js', f.read())
        else:
            zf.writestr('graph.js', '// graph.js placeholder')

        if os.path.exists('static/gallery.js'):
            with open('static/gallery.js', 'r', encoding='utf-8') as f:
                zf.writestr('gallery.js', f.read())
        else:
            zf.writestr('gallery.js', '// gallery.js placeholder')

        template_path = f'static/templates/{template_name}/styles.css'
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                zf.writestr('styles.css', f.read())
        else:
            with open('static/templates/default/styles.css', 'r', encoding='utf-8') as f:
                zf.writestr('styles.css', f.read())

        zf.writestr('.htaccess', '''RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_FILENAME}\.html -f
RewriteRule ^(.*)$ $1.html [L]
RewriteCond %{THE_REQUEST} /([^.]+)\.html [NC]
RewriteRule ^ /%1 [NC,L,R]''')
        zf.writestr('_redirects', '''/index.html    /    200
/works/index.html    /works    200
/graph/index.html    /graph    200
/downloads/index.html    /downloads    200
/gallery/index.html    /gallery    200''')

        for item in content:
            if item.get('content_file'):
                src = os.path.join(app.config['UPLOAD_FOLDER'], item['content_file'])
                if os.path.exists(src):
                    zf.write(src, f"content/{item['content_file']}")
            if item.get('cover_file'):
                src = os.path.join(app.config['UPLOAD_FOLDER'], item['cover_file'])
                if os.path.exists(src):
                    zf.write(src, f"covers/{item['cover_file']}")
            if item.get('readme_file'):
                src = os.path.join(app.config['UPLOAD_FOLDER'], item['readme_file'])
                if os.path.exists(src):
                    zf.write(src, f"readmes/{item['readme_file']}")

        for gallery in galleries:
            for image in gallery['images']:
                src = os.path.join(app.config['UPLOAD_FOLDER'], image)
                if os.path.exists(src):
                    zf.write(src, f"galleries/{image}")

        if portfolio.get('portrait'):
            src = os.path.join(app.config['UPLOAD_FOLDER'], portfolio['portrait'])
            if os.path.exists(src):
                zf.write(src, f"portrait/{portfolio['portrait']}")

    memory_file.seek(0)

    try:
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        export_base_path = os.path.join(downloads_path, 'SoRUPP_Exports')
        os.makedirs(export_base_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f'portfolio_{username}_{timestamp}.zip'
        zip_filepath = os.path.join(export_base_path, zip_filename)
        with open(zip_filepath, 'wb') as f:
            f.write(memory_file.getvalue())
        logger.info(f"ZIP file also saved to: {zip_filepath}")
    except Exception as e:
        logger.warning(f"Error saving to Downloads: {e}")

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name=f'portfolio_{username}.zip',
        as_attachment=True,
        mimetype='application/zip'
    )


@app.route('/api/download-export/<filename>')
@requires_auth
def download_export(filename):
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    export_base_path = os.path.join(downloads_path, 'SoRUPP_Exports')
    try:
        return send_from_directory(export_base_path, filename, as_attachment=True, download_name=filename)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


@app.route('/api/exported-files', methods=['GET'])
@requires_auth
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
    files.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(files)


@app.route('/api/export/data', methods=['POST'])
@requires_auth
def export_data():
    data = request.json
    format = data.get('format', 'json')
    fields = data.get('fields')
    content, _, _ = load_data()
    if fields:
        export_content = [{f: item.get(f) for f in fields if f in item} for item in content]
    else:
        export_content = content

    if format == 'json':
        return jsonify(export_content)
    elif format == 'csv':
        si = StringIO()
        if export_content:
            headers = export_content[0].keys()
            writer = csv.DictWriter(si, fieldnames=headers)
            writer.writeheader()
            writer.writerows(export_content)
        output = si.getvalue()
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=export.csv'}
        )
    else:
        return jsonify({'error': 'Unsupported format'}), 400


def process_template_for_seo(template_content, is_index=False):
    template_content = re.sub(r'href="([^"/]+)\.html"', r'href="/\1"', template_content)
    template_content = re.sub(r'href="(/?index)"', r'href="/"', template_content)
    if not is_index:
        template_content = template_content.replace('src="content/', 'src="/content/')
        template_content = template_content.replace('src="covers/', 'src="/covers/')
        template_content = template_content.replace('src="galleries/', 'src="/galleries/')
        template_content = template_content.replace('src="portrait/', 'src="/portrait/')
        template_content = template_content.replace('href="styles.css"', 'href="/styles.css"')
        template_content = template_content.replace('src="graph.js"', 'src="/graph.js"')
        template_content = template_content.replace('src="gallery.js"', 'src="/gallery.js"')
    return template_content


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    safe_path = os.path.normpath(filename)
    if safe_path.startswith('..') or safe_path.startswith('/'):
        abort(404)
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_path)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')


# ----------------------------------------------------------------------
# Запуск
# ----------------------------------------------------------------------
if __name__ == '__main__':
    if not app.config['MASTER_PASSWORD']:
        logger.warning("MASTER_PASSWORD not set. Git integration will be unavailable.")

    issues = check_integrity()
    if issues:
        logger.warning("Найдены проблемы целостности при запуске:")
        for issue in issues:
            logger.warning(issue)
    else:
        logger.info("Целостность данных в порядке.")

    if not os.environ.get('AUTH_USERNAME') or not os.environ.get('AUTH_PASSWORD'):
        logger.warning("AUTH_USERNAME/AUTH_PASSWORD не заданы, аутентификация отключена (только для разработки)")

    app.run(debug=True, host='0.0.0.0', port=5000)