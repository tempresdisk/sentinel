import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
BASE_HOMEWORK_URL = ('https://praktikum.yandex.ru/api/'
                     'user_api/homework_statuses/')
ERROR_COUNT_THRESHOLD = 10
PAUSE_TIME = 1200
CHECK_MARK = '\N{white heavy check mark}'
ADJ_MARK = '\N{black question mark ornament}'
VIEW_MARK = '\N{eyes}'


handlers = [
    logging.FileHandler(
        filename="./program.log",
        mode='w',
        encoding='utf-8'
    )
]
logging.basicConfig(
    level=logging.DEBUG,
    handlers=handlers,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def parse_homework_status(homework):
    """
    expecting 0 exceptions in current version of get_homework_statuses
    and main
    """
    homework_name = homework['homework_name']
    if homework['status'] == 'rejected':
        verdict = ADJ_MARK + 'К сожалению в работе нашлись ошибки.'
    elif homework['status'] == 'reviewing':
        verdict = VIEW_MARK + ' Начало ревью.'
    else:
        verdict = (CHECK_MARK + ' Ревьюеру всё понравилось, можно '
                   'приступать к следующему уроку.')
    return f'Обновлён статус работы "{homework_name}"!\n\n{verdict}'


def get_homework_statuses(current_timestamp):
    headers = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    params = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(BASE_HOMEWORK_URL, headers=headers,
                                         params=params)
        return homework_statuses.json()
    except requests.RequestException as e:
        raise e  # logged in main()


def send_message(message: str, bot_client):
    try:
        return bot_client.send_message(chat_id=CHAT_ID, text=message)
    except telegram.error.TelegramError as e:
        raise e  # logged in main()


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    error_count = 0

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                status = new_homework.get('homeworks')[0]
                send_message(parse_homework_status(status), bot)
                logging.info('message has been sent to chat')
                error_count = 0  # counter restart
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            time.sleep(PAUSE_TIME)

        except (requests.RequestException, telegram.error.TelegramError) as e:
            if error_count < ERROR_COUNT_THRESHOLD:
                error = f'Бот столкнулся с ошибкой: {e}'
                logging.error(e, exc_info=True)
                try:
                    send_message(error, bot)
                except telegram.error.TelegramError as e:
                    logging.error(e, exc_info=True)
                error_count += 1
                time.sleep(5)
            else:
                pause_message = (
                    f'bot has been paused for {int(PAUSE_TIME/60)} min after '
                    f'{ERROR_COUNT_THRESHOLD} unsuccessfull tries'
                )
                try:
                    send_message(pause_message, bot)
                except telegram.error.TelegramError as e:
                    logging.error(e, exc_info=True)
                error_count = 0  # counter restart
                time.sleep(PAUSE_TIME)


if __name__ == '__main__':
    main()
