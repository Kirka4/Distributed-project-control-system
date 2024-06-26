from flask import Flask, request
from flask_socketio import SocketIO, send, emit
import pyodbc
import datetime
import pandas as pd
from tabulate import tabulate
import threading
import queue

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Настройки базы данных
db_name = 'Tracker'
db_user = r'WIN-AQOQMJEPJNJ\User'  # Имя пользователя Windows
db_host = 'localhost'
db_port = '1433'  # порт по умолчанию для SQL Server    

# Функция для проверки существования события в базе данных
def event_exists(event_title, event_password):
    try:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={db_host},{db_port};'
            f'DATABASE={db_name};'
            f'UID={db_user};'
            f'Trusted_Connection=yes;'  # Используем Windows Authentication
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        # Запрос для проверки по двум столбцам: Title и Password
        cursor.execute("SELECT * FROM Events WHERE Title COLLATE Latin1_General_CS_AS = ? AND Password COLLATE Latin1_General_CS_AS = ?", 
        (event_title, event_password))
        event = cursor.fetchone()
        conn.close()
        return event is not None    
    except pyodbc.Error as e:
        print(f"The error '{e}' occurred")
        return False

# Функция для получения всех строк из базы данных
def get_all_rows(event_title):
    try:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={db_host},{db_port};'
            f'DATABASE={db_name};'
            f'UID={db_user};'
            f'Trusted_Connection=yes;'  # Используем Windows Authentication
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        # Используем квадратные скобки для идентификаторов с пробелами
        query = f"SELECT * FROM [{event_title}]"
        cursor.execute(query)
        rows = cursor.fetchall()
        # Преобразуем результаты в список словарей
        column_names = [column[0] for column in cursor.description]
        result_list = []
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                if isinstance(value, datetime.date):
                    # Преобразуем объект date в строку
                    value = value.strftime('%Y-%m-%d')
                row_dict[column_names[i]] = value
            result_list.append(row_dict)
        conn.close()
        return result_list
    except pyodbc.Error as e:
        print(f"The error '{e}' occurred")
        return []
    
# Функция для создания новой таблицы
def create_table(event_title, event_password):
    try:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={db_host},{db_port};'
            f'DATABASE={db_name};'
            f'UID={db_user};'
            f'Trusted_Connection=yes;'  # Используем Windows Authentication
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Создаем таблицу с названием event_title, если она не существует
        query = f"""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name COLLATE Latin1_General_CS_AS = '{event_title}')
        CREATE TABLE [{event_title}] (
            Task VARCHAR(255) NOT NULL,
            Date DATE NOT NULL,
            Status VARCHAR(50) NOT NULL
        )
        """
        cursor.execute(query)
        
        # Добавляем в таблицу Events строку с названием события и паролем
        query = f"""
        INSERT INTO Events (Title, Password)
        VALUES (?, ?)
        """
        cursor.execute(query, (event_title, event_password))
        
        conn.commit()
        conn.close()
        return True
    except pyodbc.Error as e:
        print(f"The error '{e}' occurred")
        return False
    
# Функция для добавления новой строки в таблицу
def add_new_row(event_title, task, status):
    try:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={db_host},{db_port};'
            f'DATABASE={db_name};'
            f'UID={db_user};'
            f'Trusted_Connection=yes;'  # Используем Windows Authentication
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        # Получаем текущую дату
        current_date = datetime.date.today()
        # Формируем запрос на добавление новой строки
        query = f"INSERT INTO [{event_title}] (Task, Date, Status) VALUES (?, ?, ?)"
        cursor.execute(query, (task, current_date, status))
        conn.commit()
        conn.close()
        return True
    except pyodbc.Error as e:
        print(f"The error '{e}' occurred")
        return False

# Функция для обновления строки в таблице
def update_row(event_title, task, status):
    try:
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={db_host},{db_port};'
            f'DATABASE={db_name};'
            f'UID={db_user};'
            f'Trusted_Connection=yes;'  # Используем Windows Authentication
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Формируем запрос на обновление строки
        cursor.execute(f"UPDATE [{event_title}] SET Status = ? WHERE Task = ?", (status, task))
        conn.commit()
        conn.close()
        return True
    except pyodbc.Error as e:
        print(f"The error '{e}' occurred")
        return False
    
# Очередь для хранения запросов клиентов
request_queue = queue.Queue()

# функция для получения адреса клиента
@socketio.on('connect')
def handle_connect():
    client_ip = request.remote_addr
    client_port = request.environ.get('REMOTE_PORT')
    print(f"Client connected: {client_ip}:{client_port} (sid: {request.sid})")

# Функция для обработки запросов клиента
@socketio.on('message')
def handle_message(data):
    print(f"Received message: {data}")
    # Помещаем запрос в очередь
    request_queue.put(data)

# Функция для обработки запросов из очереди
def process_requests():
    while True:
        try:
            data = request_queue.get()
            # Разделяем данные на команду и параметры
            command_parts = data.split(',', 1)
            command_parts = [','.join(part for part in subpart.split(',') if part != 'None') for subpart in command_parts]
            command = command_parts[0]
            params = command_parts[1].split(',') if len(command_parts) > 1 else []

            if command == 'create_table':
                event_title, event_password = params
                if create_table(event_title, event_password):
                    response = "Table created successfully"
                else:
                    response = "Error: Failed to create table"
                emit('response', response)

            elif command == 'add_new_row':
                event_title, task, status = params
                if add_new_row(event_title, task, status):
                    response = get_table_response(event_title)
                else:
                    response = "Error: Failed to add new row"
                emit('response', response)

            elif command == 'update_row':
                event_title, task, status = params
                if update_row(event_title, task, status):
                    response = get_table_response(event_title)
                else:
                    response = "Error: Failed to update row"
                emit('response', response)

            else:
                event_title, event_password = params
                if event_exists(event_title, event_password):
                    response = get_table_response(event_title)
                else:
                    response = "Error: Event does not exist or password is incorrect"
                emit('response', response)

        except ValueError:
            response = "Error: Invalid data format. Expected 'command,param1,param2,...'"
            emit('response', response)

def get_table_response(event_title):
    data = get_all_rows(event_title)
    df = pd.DataFrame(data)
    table_str = tabulate(df, headers='keys', tablefmt='psql')
    return table_str


if __name__ == "__main__":  
    # Запускаем поток для обработки запросов из очереди
    threading.Thread(target=process_requests, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)