import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import zipfile
import re
from io import BytesIO
import sys

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5000", "http://localhost:5000"])
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('static/templates', exist_ok=True)

def get_resource_path(relative_path):
    """Получает правильный путь к ресурсам для PyInstaller"""
    try:
        # PyInstaller создает временную папку в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Обновляем пути к папкам
if getattr(sys, 'frozen', False):
    # Если приложение запущено из собранного exe
    template_folder = get_resource_path('templates')
    static_folder = get_resource_path('static')
    data_folder = get_resource_path('data')
    upload_folder = get_resource_path('static/uploads')
else:
    # Обычный режим разработки
    template_folder = 'templates'
    static_folder = 'static'
    data_folder = 'data'
    upload_folder = 'static/uploads'

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
app.config['UPLOAD_FOLDER'] = upload_folder

# Структура данных (полная версия)
structure = {
    "сферы": {
        "programming": {
            "name": "Программирование",
            "genre_type": "language",
            "topic_type": "application_domain",
            "genres": [
                {"id": "py", "name": "Python"},
                {"id": "js", "name": "JavaScript"},
                {"id": "java", "name": "Java"},
                {"id": "cpp", "name": "C++"},
                {"id": "cs", "name": "C#"},
                {"id": "php", "name": "PHP"},
                {"id": "go", "name": "Go"},
                {"id": "rust", "name": "Rust"},
                {"id": "sql", "name": "SQL"},
                {"id": "html_css", "name": "HTML/CSS"},
                {"id": "r", "name": "R"},
                {"id": "ruby", "name": "Ruby"},
                {"id": "swift", "name": "Swift"},
                {"id": "kotlin", "name": "Kotlin"},
                {"id": "other_lang", "name": "Другой язык"}
            ],
            "topics": [
                {"id": "web_back", "name": "Веб-разработка (бэкенд)"},
                {"id": "web_front", "name": "Веб-разработка (фронтенд)"},
                {"id": "mobile", "name": "Мобильная разработка"},
                {"id": "desktop", "name": "Десктоп приложения"},
                {"id": "game_dev", "name": "Разработка игр"},
                {"id": "data_science", "name": "Data Science"},
                {"id": "ml", "name": "Машинное обучение / AI"},
                {"id": "devops", "name": "DevOps / Системное администрирование"},
                {"id": "embedded", "name": "Встроенные системы"},
                {"id": "blockchain", "name": "Блокчейн"},
                {"id": "other_domain", "name": "Другая область"}
            ]
        },
        "literature": {
            "name": "Литература",
            "genre_type": "literary_genre",
            "topic_type": "theme",
            "genres": [
                {"id": "fantasy", "name": "Фэнтези"},
                {"id": "sci_fi", "name": "Научная фантастика"},
                {"id": "detective", "name": "Детектив"},
                {"id": "romance", "name": "Любовный роман"},
                {"id": "horror", "name": "Ужасы"},
                {"id": "realism", "name": "Реализм"},
                {"id": "poetry", "name": "Поэзия"},
                {"id": "drama", "name": "Драматургия"},
                {"id": "prose", "name": "Проза (малая форма)"},
                {"id": "nonfiction", "name": "Нон-фикшн"},
                {"id": "other_lit", "name": "Другой жанр"}
            ],
            "topics": [
                {"id": "love", "name": "Любовь"},
                {"id": "war", "name": "Война"},
                {"id": "death", "name": "Смерть"},
                {"id": "nature", "name": "Природа"},
                {"id": "city", "name": "Город"},
                {"id": "philosophy", "name": "Философия"},
                {"id": "politics", "name": "Политика"},
                {"id": "history", "name": "История"},
                {"id": "adventure", "name": "Приключения"},
                {"id": "psychology", "name": "Психология"},
                {"id": "other_theme", "name": "Другая тема"}
            ]
        },
        "science_pop": {
            "name": "Научпоп / Педагогика",
            "genre_type": "science",
            "topic_type": "specialization",
            "genres": [
                {"id": "physics", "name": "Физика"},
                {"id": "math", "name": "Математика"},
                {"id": "chemistry", "name": "Химия"},
                {"id": "biology", "name": "Биология"},
                {"id": "medicine", "name": "Медицина"},
                {"id": "astronomy", "name": "Астрономия"},
                {"id": "geology", "name": "Геология"},
                {"id": "psychology_sci", "name": "Психология"},
                {"id": "history_sci", "name": "История"},
                {"id": "linguistics", "name": "Лингвистика"},
                {"id": "economics", "name": "Экономика"},
                {"id": "philosophy_sci", "name": "Философия"},
                {"id": "other_sci", "name": "Другая наука"}
            ],
            "topics": [
                {"id": "quantum", "name": "Квантовая механика"},
                {"id": "thermodynamics", "name": "Термодинамика"},
                {"id": "organic_chem", "name": "Органическая химия"},
                {"id": "genetics", "name": "Генетика"},
                {"id": "neuroscience", "name": "Нейробиология"},
                {"id": "black_holes", "name": "Черные дыры"},
                {"id": "ancient_rome", "name": "Древний Рим"},
                {"id": "ww2", "name": "Вторая мировая война"},
                {"id": "cognitive", "name": "Когнитивная психология"},
                {"id": "market", "name": "Теория рынков"},
                {"id": "other_spec", "name": "Другое направление"}
            ]
        },
        "digital_art": {
            "name": "Цифровое искусство",
            "genre_type": "style",
            "topic_type": None,
            "genres": [
                {"id": "realism_d", "name": "Реализм"},
                {"id": "stylized", "name": "Стилизация"},
                {"id": "pixel", "name": "Пиксель-арт"},
                {"id": "low_poly", "name": "Лоу-поли"},
                {"id": "vector", "name": "Векторная графика"},
                {"id": "concept", "name": "Концепт-арт"},
                {"id": "photo_manip", "name": "Фотоманипуляция"},
                {"id": "3d_modeling", "name": "3D-моделирование"},
                {"id": "abstract_d", "name": "Абстракционизм"},
                {"id": "other_d_style", "name": "Другой стиль"}
            ],
            "topics": []
        },
        "traditional_art": {
            "name": "Изобразительное искусство",
            "genre_type": "style",
            "topic_type": "technique",
            "genres": [
                {"id": "realism_t", "name": "Реализм"},
                {"id": "impressionism", "name": "Импрессионизм"},
                {"id": "expressionism", "name": "Экспрессионизм"},
                {"id": "abstractionism", "name": "Абстракционизм"},
                {"id": "surrealism", "name": "Сюрреализм"},
                {"id": "cubism", "name": "Кубизм"},
                {"id": "modern", "name": "Модерн"},
                {"id": "avant_garde", "name": "Авангард"},
                {"id": "other_t_style", "name": "Другой стиль"}
            ],
            "topics": [
                {"id": "oil", "name": "Масло"},
                {"id": "acrylic", "name": "Акрил"},
                {"id": "watercolor", "name": "Акварель"},
                {"id": "pastel", "name": "Пастель"},
                {"id": "charcoal", "name": "Уголь"},
                {"id": "pencil", "name": "Карандаш"},
                {"id": "ink", "name": "Тушь"},
                {"id": "linocut", "name": "Линогравюра"},
                {"id": "mixed", "name": "Смешанная техника"},
                {"id": "other_tech", "name": "Другая техника"}
            ]
        },
        "science_research": {
            "name": "Научные работы",
            "genre_type": "science",
            "topic_type": "specialization",
            "genres": [
                {"id": "physics_r", "name": "Физика"},
                {"id": "math_r", "name": "Математика"},
                {"id": "chemistry_r", "name": "Химия"},
                {"id": "biology_r", "name": "Биология"},
                {"id": "medicine_r", "name": "Медицина"},
                {"id": "astronomy_r", "name": "Астрономия"},
                {"id": "geology_r", "name": "Геология"},
                {"id": "psychology_r", "name": "Психология"},
                {"id": "history_r", "name": "История"},
                {"id": "linguistics_r", "name": "Лингвистика"},
                {"id": "economics_r", "name": "Экономика"},
                {"id": "philosophy_r", "name": "Философия"},
                {"id": "other_sci_r", "name": "Другая наука"}
            ],
            "topics": [
                {"id": "quantum_r", "name": "Квантовая механика"},
                {"id": "thermodynamics_r", "name": "Термодинамика"},
                {"id": "organic_chem_r", "name": "Органическая химия"},
                {"id": "genetics_r", "name": "Генетика"},
                {"id": "neuroscience_r", "name": "Нейробиология"},
                {"id": "black_holes_r", "name": "Черные дыры"},
                {"id": "ancient_rome_r", "name": "Древний Рим"},
                {"id": "ww2_r", "name": "Вторая мировая война"},
                {"id": "cognitive_r", "name": "Когнитивная психология"},
                {"id": "market_r", "name": "Теория рынков"},
                {"id": "other_spec_r", "name": "Другое направление"}
            ]
        }
    }
}

# Load data
def load_data():
    try:
        data_path = os.path.join(data_folder, 'content.json') if getattr(sys, 'frozen', False) else 'data/content.json'
        with open(data_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
    except:
        content = []
    
    # Аналогично для portfolio.json и galleries.json
    try:
        portfolio_path = os.path.join(data_folder, 'portfolio.json') if getattr(sys, 'frozen', False) else 'data/portfolio.json'
        with open(portfolio_path, 'r', encoding='utf-8') as f:
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
        # ИСПРАВЛЕНИЕ: galleries/ должно вести на относительные пути для статического сайта
        template_content = template_content.replace('src="galleries/', 'src="../galleries/')
        template_content = template_content.replace('src="portrait/', 'src="/portrait/')
        template_content = template_content.replace('href="styles.css"', 'href="/styles.css"')
        template_content = template_content.replace('src="graph.js"', 'src="/graph.js"')
        template_content = template_content.replace('src="gallery.js"', 'src="/gallery.js"')
    
    return template_content

# Новая исправленная функция для обработки путей в экспортированном сайте
def process_template_for_seo_corrected(template_content, page_folder):
    """
    Обрабатывает HTML-контент с правильными путями для экспортированного сайта
    """
    # Заменяем все ссылки на .html файлы на чистые пути
    template_content = re.sub(r'href="([^"/]+)\.html"', r'href="/\1"', template_content)
    
    # ОСОБОЕ ПРАВИЛО: заменяем ссылки на главную страницу
    template_content = re.sub(r'href="(/?index)"', r'href="/"', template_content)
    
    # Корректируем пути к ресурсам в зависимости от папки страницы
    if page_folder != 'index':
        # Для страниц в подпапках используем относительные пути
        template_content = template_content.replace('src="content/', f'src="../content/')
        template_content = template_content.replace('src="covers/', f'src="../covers/')
        template_content = template_content.replace('src="galleries/', f'src="../galleries/')
        template_content = template_content.replace('src="portrait/', f'src="../portrait/')
        template_content = template_content.replace('href="styles.css"', f'href="../styles.css"')
        template_content = template_content.replace('src="graph.js"', f'src="../graph.js"')
        template_content = template_content.replace('src="gallery.js"', f'src="../gallery.js"')
    else:
        # Для главной страницы пути остаются как есть
        template_content = template_content.replace('src="content/', 'src="content/')
        template_content = template_content.replace('src="covers/', 'src="covers/')
        template_content = template_content.replace('src="galleries/', 'src="galleries/')
        template_content = template_content.replace('src="portrait/', 'src="portrait/')
        template_content = template_content.replace('href="styles.css"', 'href="styles.css"')
        template_content = template_content.replace('src="graph.js"', 'src="graph.js"')
        template_content = template_content.replace('src="gallery.js"', 'src="gallery.js"')
    
    return template_content

import tempfile
@app.route('/api/export', methods=['POST'])
def export_site():
    content, portfolio, galleries = load_data()
    data = request.json
    
    username = data.get('username', 'user')
    site_title = data.get('siteTitle', 'Портфолио творческих работ')
    template_name = portfolio.get('template', 'default')
    
    # ЧЕТКО указываем путь для сохранения - папка Downloads пользователя
    downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
    export_base_path = os.path.join(downloads_path, 'SoRUPP_Exports')
    os.makedirs(export_base_path, exist_ok=True)
    
    # Создаем уникальное имя файла с timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f'portfolio_{username}_{timestamp}.zip'
    zip_filepath = os.path.join(export_base_path, zip_filename)
    
    # Создаем физический файл на диске
    with zipfile.ZipFile(zip_filepath, 'w') as zf:
        # Add data.json
        export_data = {
            'user': username,
            'site_title': site_title,
            'generated_at': datetime.now().isoformat(),
            'portfolio': portfolio,
            'content': content,
            'galleries': galleries,
            'structure': structure,
            'export_path': zip_filepath
        }
        zf.writestr('data.json', json.dumps(export_data, ensure_ascii=False, indent=2))
        
        # Create a separate ZIP with all works
        all_works_zip_path = os.path.join(tempfile.gettempdir(), f'all_works_{timestamp}.zip')
        with zipfile.ZipFile(all_works_zip_path, 'w') as works_zip:
            for item in content:
                if item['content_file']:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], item['content_file'])
                    if os.path.exists(file_path):
                        original_name = item['content_file'].split('_', 1)[1] if '_' in item['content_file'] else item['content_file']
                        works_zip.write(file_path, f"{item['id']}_{original_name}")
        
        # Добавляем all_works.zip в основной архив
        zf.write(all_works_zip_path, 'all_works.zip')
        # Удаляем временный файл
        os.unlink(all_works_zip_path)
        
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
        
        # Process templates for SEO-friendly URLs with CORRECTED paths
        index_html = process_template_for_seo(index_html, is_index=True)
        works_html = process_template_for_seo_corrected(works_html, 'works')
        graph_html = process_template_for_seo_corrected(graph_html, 'graph')
        downloads_html = process_template_for_seo_corrected(downloads_html, 'downloads')
        gallery_html = process_template_for_seo_corrected(gallery_html, 'gallery')
        
        # Create directory structure for human-readable URLs
        zf.writestr('index.html', index_html)
        zf.writestr('works/index.html', works_html)
        zf.writestr('graph/index.html', graph_html)
        zf.writestr('downloads/index.html', downloads_html)
        zf.writestr('gallery/index.html', gallery_html)
        
        # Add JavaScript files with CORRECTED paths for galleries
        try:
            graph_js_path = get_resource_path('static/graph.js') if getattr(sys, 'frozen', False) else 'static/graph.js'
            with open(graph_js_path, 'r', encoding='utf-8') as f:
                graph_js_content = f.read()
            zf.writestr('graph.js', graph_js_content)
        except:
            zf.writestr('graph.js', '// Graph JS file not found')
        
        try:
            gallery_js_path = get_resource_path('static/gallery.js') if getattr(sys, 'frozen', False) else 'static/gallery.js'
            with open(gallery_js_path, 'r', encoding='utf-8') as f:
                gallery_js_content = f.read()
            
            # CORRECTION: Fix paths in gallery.js for exported site
            gallery_js_content = gallery_js_content.replace("imgElement.src = `/uploads/${image}`", "imgElement.src = `../galleries/${image}`")
            gallery_js_content = gallery_js_content.replace("img.src = `/uploads/${currentImage}`", "img.src = `../galleries/${currentImage}`")
            gallery_js_content = gallery_js_content.replace("img.src = `/uploads/${images[currentIndex]}`", "img.src = `../galleries/${images[currentIndex]}`")
            gallery_js_content = gallery_js_content.replace("preloadImg.src = `/uploads/${imageSrc}`", "preloadImg.src = `../galleries/${imageSrc}`")
            
            zf.writestr('gallery.js', gallery_js_content)
        except:
            zf.writestr('gallery.js', '// Gallery JS file not found')
        
        # Add CSS from selected template
        template_path = f'static/templates/{template_name}/styles.css'
        if getattr(sys, 'frozen', False):
            template_path = get_resource_path(template_path)
        
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                zf.writestr('styles.css', f.read())
        else:
            # Fallback to default template
            default_template_path = 'static/templates/default/styles.css'
            if getattr(sys, 'frozen', False):
                default_template_path = get_resource_path(default_template_path)
            
            if os.path.exists(default_template_path):
                with open(default_template_path, 'r', encoding='utf-8') as f:
                    zf.writestr('styles.css', f.read())
            else:
                zf.writestr('styles.css', '/* Default styles not found */')
        
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
        
        # Add README file with export info
        readme_content = f'''
SoRUPP Portfolio Export
======================

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
User: {username}
Site Title: {site_title}
Template: {template_name}

Contents:
- index.html - Main portfolio page
- works/ - All works page
- graph/ - Relationship graph
- downloads/ - Downloads page  
- gallery/ - Gallery page
- content/ - Uploaded content files
- covers/ - Cover images
- galleries/ - Gallery images
- portrait/ - Portrait image

To deploy:
1. Upload all files to your web server
2. Ensure .htaccess is supported (for Apache)
3. Or use _redirects file (for Netlify)

Export path: {zip_filepath}
'''
        zf.writestr('README.txt', readme_content)
    
    # Логируем путь для отладки
    app.logger.info(f'Сайт экспортирован в: {zip_filepath}')
    
    # Возвращаем информацию о сохраненном файле
    return jsonify({
        'status': 'success',
        'message': f'Сайт успешно экспортирован в папку Downloads/SoRUPP_Exports',
        'file_path': zip_filepath,
        'file_name': zip_filename,
        'file_size': os.path.getsize(zip_filepath),
        'export_time': datetime.now().isoformat(),
        'download_url': f'/api/download-export/{zip_filename}'
    })

# Новая исправленная функция для обработки путей в экспортированном сайте
def process_template_for_seo_corrected(template_content, page_folder):
    """
    Обрабатывает HTML-контент с правильными путями для экспортированного сайта
    """
    # Заменяем все ссылки на .html файлы на чистые пути
    template_content = re.sub(r'href="([^"/]+)\.html"', r'href="/\1"', template_content)
    
    # ОСОБОЕ ПРАВИЛО: заменяем ссылки на главную страницу
    template_content = re.sub(r'href="(/?index)"', r'href="/"', template_content)
    
    # Корректируем пути к ресурсам в зависимости от папки страницы
    if page_folder != 'index':
        # Для страниц в подпапках используем относительные пути
        template_content = template_content.replace('src="content/', f'src="../content/')
        template_content = template_content.replace('src="covers/', f'src="../covers/')
        template_content = template_content.replace('src="galleries/', f'src="../galleries/')
        template_content = template_content.replace('src="portrait/', f'src="../portrait/')
        template_content = template_content.replace('href="styles.css"', f'href="../styles.css"')
        template_content = template_content.replace('src="graph.js"', f'src="../graph.js"')
        template_content = template_content.replace('src="gallery.js"', f'src="../gallery.js"')
    else:
        # Для главной страницы пути остаются как есть
        template_content = template_content.replace('src="content/', 'src="content/')
        template_content = template_content.replace('src="covers/', 'src="covers/')
        template_content = template_content.replace('src="galleries/', 'src="galleries/')
        template_content = template_content.replace('src="portrait/', 'src="portrait/')
        template_content = template_content.replace('href="styles.css"', 'href="styles.css"')
        template_content = template_content.replace('src="graph.js"', 'src="graph.js"')
        template_content = template_content.replace('src="gallery.js"', 'src="gallery.js"')
    
    return template_content

# Старая функция (оставляем для совместимости)
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
        # ИСПРАВЛЕНИЕ: galleries/ должно вести на правильные пути
        template_content = template_content.replace('src="galleries/', 'src="/galleries/')
        template_content = template_content.replace('src="portrait/', 'src="/portrait/')
        template_content = template_content.replace('href="styles.css"', 'href="/styles.css"')
        template_content = template_content.replace('src="graph.js"', 'src="/graph.js"')
        template_content = template_content.replace('src="gallery.js"', 'src="/gallery.js"')
    
    return template_content


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