import os
import logging
from dotenv import load_dotenv
import gettext
import redis
import telebot

_ = gettext.gettext

load_dotenv("vars.env")
datefmt = "%d/%m/%Y %H:%M:%S"
logging.basicConfig(filename="bot.log", format="%(asctime)s %(levelname)s %(message)s", datefmt=datefmt,
                    level=logging.DEBUG)

TELEBOT_TOKEN = os.getenv("TELEBOT_TOKEN")
bot = telebot.TeleBot(TELEBOT_TOKEN)
ADMIN_ID = (1054140400, 975772882)
DB_CONFIG = {"dbname": "postgres",
             "user": "postgres",
             "password": "swearter903",
             "host": "178.150.167.216",
             "port": 5432
             }
TABLE_NAME = "test_telegram_users"
LANG = {
    "English": "en_US",
    "Русский": "ru_RU"
}

redis_ = redis.Redis(host="127.0.0.1", 
                     port=6379,
                     password="5DD0B4430246F6B0AE98BDABB3A42ED5A630B81F05031F464F0AE9928AF31EB1")

if __name__ == "__main":
    ...
