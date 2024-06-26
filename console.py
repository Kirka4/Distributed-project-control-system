from flask_socketio import SocketIO
import argparse
import shlex
import time
import socketio

# Инициализация SocketIO для клиента
client_socketio = socketio.Client()

# Функции клиента
# Подключение к серверу
@client_socketio.on('connect')
def test_connect():
    print('Client connected')

@client_socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

# Обработчик для получения ответа от сервера
@client_socketio.on('response')
def handle_response(response):
    print("Received table from server:")
    print(response)
    client_socketio.disconnect()
        
# Получение таблицы с сервера
def get_table_from_server(event_title, event_password, host, port):
    client_socketio.connect(f'http://{host}:{port}')
    request_data = f'get_table,{event_title},{event_password}'
    client_socketio.emit('message', request_data, namespace='/')
    print(f"Request sent to {host}:{port}")

# Отправка команды на сервер 
def send_command_to_server(command, event_title, task=None, status=None, port=5000):
    global host
    client_socketio.connect(f'http://{host}:{port}')
    data = {
        'command': command,
        'event_title': event_title,
        'task': task,
        'status': status
    }
    client_socketio.emit('send_command', data, namespace='/')
    print(f"Command sent to {host}:{port}")
    client_socketio.disconnect()

# Функция для обработки команды "create_table"
def handle_create_table(args):
    send_command_to_server('create_table', args.event_title, args.event_password, host=args.host, port=args.port)
    send_command_to_server('add_new_row', args.event_title, args.task, args.status, args.host, args.port)
        
# Функция для обработки команды "get-table"
def handle_get_table(args):
    get_table_from_server(args.event_title, args.event_password, args.host, args.port)

# Функция для обработки команды "send-command"
def handle_send_command(args):
    send_command_to_server(args.command, args.event_title, args.task, args.status, args.host, args.port)

# Основная функция для обработки аргументов командной строки
def main():
    # Создаем парсер аргументов
    parser = argparse.ArgumentParser(
        description='',
        formatter_class=argparse.RawTextHelpFormatter
        )
    subparsers = parser.add_subparsers(dest='command')

    # Парсер для команды "create-table"
    parser_create_table = subparsers.add_parser('create-table', help='Создать таблицу на сервере')
    parser_create_table.add_argument('event_title', help='Название события')
    parser_create_table.add_argument('event_password', help='Пароль события')
    parser_create_table.add_argument('task', help='Задача')
    parser_create_table.add_argument('status', help='Статус')
    parser_create_table.add_argument('--host', default=host, help='Адрес сервера')
    parser_create_table.add_argument('--port', type=int, default=5000, help='Порт сервера')
    parser_create_table.set_defaults(func=handle_create_table)

    # Парсер для команды "get-table"
    parser_get_table = subparsers.add_parser('get-table', help='Получить таблицу с сервера')
    parser_get_table.add_argument('event_title', help='Название события')
    parser_get_table.add_argument('event_password', help='Пароль события')
    parser_get_table.add_argument('--host', default=host, help='Адрес сервера')
    parser_get_table.add_argument('--port', type=int, default=5000, help='Порт сервера')
    parser_get_table.set_defaults(func=handle_get_table)

    # Парсер для команды "send-command"
    parser_send_command = subparsers.add_parser('send-command', help='Отправить команду на сервер')
    parser_send_command.add_argument('command', help='Команда для отправки')
    parser_send_command.add_argument('event_title', help='Название события')
    parser_send_command.add_argument('task', help='Задача')
    parser_send_command.add_argument('status', help='Статус')
    parser_send_command.add_argument('--host', default=host, help='Адрес сервера')
    parser_send_command.add_argument('--port', type=int, default=5000, help='Порт сервера')
    parser_send_command.set_defaults(func=handle_send_command)

    # Выводим информацию о программе и ее использовании
    print("Консоль для работы с сервером.")
    print("usage: console.exe [-h] {create-table,get-table,send-command} ...")
    print()
    print("positional arguments:")
    print("{create-table,get-table,send-command}")
    print("create-table        Создать таблицу на сервере")
    print("'Чтобы создать таблицу, необходимо кроме ее названия")
    print("и пароля написать название задачи и ее статус,") 
    print("они будут записаны в первую строчку созданной таблицы'")
    print("get-table           Получить таблицу с сервера")
    print("send-command        Отправить команду на сервер")
    print("options:")
    print("-h, --help            show this help message and exit")

    #  Запуск бесконечного цикла для ожидания ввода команд
    while True:
        try:
            command_line = input("Введите команду (или 'exit' для выхода): ")
            if command_line.strip().lower() == 'exit':
                break
            # Разделяем ввод пользователя на аргументы с использованием shlex.split
            args = parser.parse_args(shlex.split(command_line))
            if hasattr(args, 'func'):
                args.func(args)
        except SystemExit:
            # Обработка исключения SystemExit при вводе неправильной команды
            pass
        except argparse.ArgumentError as e:
            # Выводим справку для той команды, которая вызвала ошибку
            print(e)
            if args.command == 'create-table':
                parser_create_table.print_help()
            elif args.command == 'get-table':
                parser_get_table.print_help()
            elif args.command == 'send-command':
                parser_send_command.print_help()
        except Exception as e:
            print(f"Произошла ошибка: {e}")

if __name__ == '__main__':
    host = '192.168.0.100'  # Замените на фактический IP-адрес сервера
    port = 5000  # Порт, на котором сервер слушает
    main()