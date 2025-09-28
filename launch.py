import webview
import threading
import time
from app import app  # Импортируем твое Flask-приложение

def start_flask():
    """Запускаем Flask-сервер в отдельном потоке"""
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Запускаем Flask в фоновом потоке
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()
    
    # Ждем немного для старта сервера
    time.sleep(1)
    
    # Создаем и открываем окно приложения
    window = webview.create_window(
        'SoRUPP // СРКЦН',  # Заголовок окна
        'http://127.0.0.1:5000/',    # URL твоего Flask-приложения
        width=1200, height=800       # Размеры окна
    )
    
    webview.start()  # Запускаем главный цикл приложения