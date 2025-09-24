import os
import json
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import zipfile
from io import BytesIO

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('data', exist_ok=True)

# Структура данных (сокращенная версия)
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
            "accentColor": "#8a5c2d"
        }
    
    return content, portfolio

def save_data(content, portfolio):
    with open('data/content.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    
    with open('data/portfolio.json', 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/structure')
def get_structure():
    return jsonify(structure)

@app.route('/api/content', methods=['GET'])
def get_content():
    content, _ = load_data()
    return jsonify(content)

@app.route('/api/content', methods=['POST'])
def add_content():
    content, portfolio = load_data()
    
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
    save_data(content, portfolio)
    
    return jsonify({'status': 'success', 'id': new_id})

@app.route('/api/content/<int:content_id>', methods=['DELETE'])
def delete_content(content_id):
    content, portfolio = load_data()
    
    # Find and remove content item
    content = [item for item in content if item['id'] != content_id]
    
    save_data(content, portfolio)
    return jsonify({'status': 'success'})

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    _, portfolio = load_data()
    return jsonify(portfolio)

@app.route('/api/portfolio', methods=['POST'])
def update_portfolio():
    content, portfolio = load_data()
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
        'accentColor': data.get('accentColor', '#8a5c2d')
    })
    
    save_data(content, portfolio)
    return jsonify({'status': 'success'})

@app.route('/api/export', methods=['POST'])
def export_site():
    content, portfolio = load_data()
    data = request.json
    
    username = data.get('username', 'user')
    site_title = data.get('siteTitle', 'Портфолио творческих работ')
    
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
            'structure': structure
        }
        zf.writestr('data.json', json.dumps(export_data, ensure_ascii=False, indent=2))
        
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
        
        if portfolio['portrait']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], portfolio['portrait'])
            if os.path.exists(file_path):
                zf.write(file_path, f"portrait/{portfolio['portrait']}")
        
        # Add HTML templates
        zf.writestr('index.html', render_template('export_index.html', 
                                                 data=export_data, 
                                                 structure=structure))
        zf.writestr('works.html', render_template('export_works.html', 
                                                 data=export_data, 
                                                 structure=structure))
        zf.writestr('graph.html', render_template('export_graph.html', 
                                                 data=export_data, 
                                                 structure=structure))
        
        # Add CSS
        with open('static/styles.css', 'r') as f:
            zf.writestr('styles.css', f.read())
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        download_name=f'portfolio_{username}.zip',
        as_attachment=True
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)