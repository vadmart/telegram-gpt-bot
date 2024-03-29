from typing import Tuple, Any

import psycopg2
from psycopg2 import IntegrityError
import threading
from datetime import datetime
from config import *
from typing import Union, Callable
from translate import translate


def get_all_user_ids() -> tuple[int]:
    with psycopg2.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT user_id FROM {TABLE_NAME}")
        return tuple(map(lambda tup: tup[0], cursor.fetchall()))


def get_all_user_ids_and_languages():
    """
    Returns list of tuples of all user ids and languages from the database
    """
    with psycopg2.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT user_id, locale FROM {TABLE_NAME}")
        return cursor.fetchall()


def get_all_api_keys() -> tuple[str]:
    with psycopg2.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT OPENAI_API_KEY FROM TELEGRAM_USERS_KEYS")
        return tuple(map(lambda tup: tup[0], cursor.fetchall()))


def add_user_to_database(chat_id) -> None:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                            INSERT INTO {TABLE_NAME}
                            VALUES (%s, %s, %s)""", (chat_id, "en_US", 0))
            conn.commit()
    except IntegrityError:
        pass


def delete_user_from_database(chat_id) -> None:
    with psycopg2.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
                        DELETE FROM test_telegram_users
                        WHERE user_id = %s
                        """, (chat_id,))
        conn.commit()


def get_user_local_from_db(chat_id: int) -> str:
    with psycopg2.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""SELECT locale
                           FROM {TABLE_NAME}
                           WHERE user_id = {chat_id}""")
        return cursor.fetchone()[0]


def get_user_translator(chat_id: int) -> Callable[[str], str]:
    try:
        return translate[redis_.hget(f"user_{chat_id}", "local").decode("utf-8")].gettext
    except AttributeError:
        # если юзера нет в Редисе
        with psycopg2.connect(**DB_CONFIG) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""SELECT locale
                               FROM {TABLE_NAME}
                               WHERE user_id = {chat_id}""")
            try:
                _ = translate[cursor.fetchone()[0]].gettext
                add_user_to_redis(chat_id)
                return _
            except (KeyError, TypeError):
                # если нет ни в Редисе, ни в постгресе
                return translate["en_US"].gettext


def change_locale_in_db(user_id, lng):
    thr_name = threading.current_thread().name
    if lng not in LANG.values():
        raise ValueError(f"Locale must be selected from given: {LANG.keys()}")
    with psycopg2.connect(**DB_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute("""UPDATE test_telegram_users
                          SET locale = %s
                          WHERE user_id = %s""", (lng, user_id))
        conn.commit()
        logging.info(f"{thr_name} : {user_id}: локаль изменена на {lng}")


def add_user_to_redis(user_id):
    redis_.hset(f"user_{user_id}", "replicas", "")
    redis_.hset(f"user_{user_id}", "has_active_request", 0)
    try:
        redis_.hset(f"user_{user_id}", "local", get_user_local_from_db(user_id))
    except (IndexError, KeyError):
        redis_.hset(f"user_{user_id}", "local", "en_US")

if __name__ == "__main__":
    ...
