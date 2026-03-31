#!/usr/bin/env python3
"""
Скрипт для автоматической обработки шаблонов и создания человекочитаемых URL
"""

import os
import re
import argparse
from pathlib import Path

def process_template_file(file_path, is_index=False):
    """
    Обрабатывает HTML-файл для создания человекочитаемых URL
    """
    print(f"Обработка файла: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем все ссылки на .html файлы на чистые пути
    content = re.sub(r'href="([^"]+)\.html"', r'href="\1"', content)
    
    # Для не-главных страниц добавляем корректные пути к ресурсам
    if not is_index:
        content = content.replace('src="content/', 'src="../content/')
        content = content.replace('src="covers/', 'src="../covers/')
        content = content.replace('src="galleries/', 'src="../galleries/')
        content = content.replace('src="portrait/', 'src="../portrait/')
        content = content.replace('href="styles.css"', 'href="../styles.css"')
        content = content.replace('src="graph.js"', 'src="../graph.js"')
        content = content.replace('src="gallery.js"', 'src="../gallery.js"')
    
    # Сохраняем обработанный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Файл обработан: {file_path}")

def create_directory_structure(base_dir):
    """
    Создает структуру папок для человекочитаемых URL
    """
    directories = ['works', 'graph', 'downloads', 'gallery']
    
    for directory in directories:
        dir_path = os.path.join(base_dir, directory)
        os.makedirs(dir_path, exist_ok=True)
        print(f"Создана директория: {dir_path}")

def process_exported_site(export_dir):
    """
    Обрабатывает экспортированный сайт для создания человекочитаемых URL
    """
    print(f"Обработка экспортированного сайта в: {export_dir}")
    
    # Создаем структуру папок
    create_directory_structure(export_dir)
    
    # Обрабатываем главную страницу
    index_path = os.path.join(export_dir, 'index.html')
    if os.path.exists(index_path):
        process_template_file(index_path, is_index=True)
    
    # Обрабатываем остальные страницы и перемещаем их в папки
    pages = {
        'works.html': 'works/index.html',
        'graph.html': 'graph/index.html',
        'downloads.html': 'downloads/index.html',
        'gallery.html': 'gallery/index.html'
    }
    
    for old_name, new_name in pages.items():
        old_path = os.path.join(export_dir, old_name)
        new_path = os.path.join(export_dir, new_name)
        
        if os.path.exists(old_path):
            # Обрабатываем файл
            process_template_file(old_path, is_index=False)
            
            # Перемещаем файл в нужную папку
            os.rename(old_path, new_path)
            print(f"Перемещен файл: {old_path} -> {new_path}")
    
    # Создаем файлы для поддержки чистых URL на разных хостингах
    create_support_files(export_dir)
    
    print("Обработка завершена!")

def create_support_files(export_dir):
    """
    Создает файлы поддержки для разных хостингов
    """
    # .htaccess для Apache
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
    
    with open(os.path.join(export_dir, '.htaccess'), 'w', encoding='utf-8') as f:
        f.write(htaccess_content)
    
    # _redirects для Netlify
    redirects_content = '''
/index.html    /    200
/works/index.html    /works    200
/graph/index.html    /graph    200
/downloads/index.html    /downloads    200
/gallery/index.html    /gallery    200
'''
    
    with open(os.path.join(export_dir, '_redirects'), 'w', encoding='utf-8') as f:
        f.write(redirects_content)
    
    print("Созданы файлы поддержки для Apache и Netlify")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Обработка HTML-шаблонов для создания человекочитаемых URL")
    parser.add_argument("directory", help="Директория с экспортированным сайтом")
    
    args = parser.parse_args()
    
    if os.path.exists(args.directory):
        process_exported_site(args.directory)
    else:
        print(f"Ошибка: директория {args.directory} не существует")