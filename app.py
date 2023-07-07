import time
from openai_interact import *
import sys
import flask
from telebot import formatting
from telebot.types import Message
from telebot.util import quick_markup
from db_interaction import *
from markups import *
from bot_users import *
from typing import Optional
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace.samplers import ProbabilitySampler

app = flask.Flask(__name__)
middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(connection_string="InstrumentationKey=90aa48ca-c34e-4b3f-b633-582417b8d887"),
    sampler=ProbabilitySampler(rate=1.0)
)
THR_NAME = threading.current_thread().name


@bot.message_handler(commands=["start"])
def start(msg: Message, txt="Hello, I'm a smart bot 🤖\nMy ability is to answer user questions👤\n"
                            "What topics can I touch on? In fact, almost any, preferably not related to "
                            "politicians. Why? The fact is that I am not ideologically tied to any country. "
                            "So your opinion may differ from mine.\n"
                            "To start working with me, select the option:"):
    if msg.text == "/start":
        add_user_to_database(msg.chat.id)
    add_user_to_redis(msg.chat.id)
    _ = translate[red.hget(f"user_{msg.chat.id}", "local").decode("utf-8")].gettext
    if bot.get_chat_member(chat_id=-1001857064307, user_id=msg.chat.id).status in (
            "member", "creator", "administrator"):
        bot.send_message(chat_id=msg.chat.id,
                         text=_(txt),
                         reply_markup=markup_main_menu(msg.chat.id))
        logging.info(f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: начало работы")
    else:
        markup = quick_markup({"ChatGPTBOT_channel": {"url": "https://t.me/ChatGPTBOT_channel"}})
        bot.send_message(chat_id=msg.chat.id,
                         text=_("In order to use this bot, you need to subscribe telegram channel"),
                         reply_markup=markup)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: требуется подписка на телеграм-канал")


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)('❔ Detailed answer'))
def give_a_detailed_answer(msg: Message):
    _ = get_user_translator(msg.chat.id)
    red.hset(f"user_{msg.chat.id}", "replicas", "")
    if bot.get_chat_member(chat_id=-1001857064307, user_id=msg.chat.id).status in (
            "member", "creator", "administrator"):
        bot.send_message(chat_id=msg.chat.id,
                         text=_("Bot gives a detailed answer in this mode"),
                         reply_markup=get_main_menu_button(_))
        red.hset(f"user_{msg.chat.id}", "mode", UserMode.DETAILED_ANSWER.value)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: выбран режим 'Обширный ответ'")
    else:
        markup = quick_markup({"ChatGPTBOT_channel": {"url": "https://t.me/ChatGPTBOT_channel"}})
        bot.send_message(chat_id=msg.chat.id,
                         text=_("In order to continue using this bot, you need to subscribe telegram channel"),
                         reply_markup=markup)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: требуется подписка на телеграм-канал")


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)('💬 Dialogue'))
def start_first_dialog(msg: Message):
    _ = get_user_translator(msg.chat.id)
    if bot.get_chat_member(chat_id=-1001857064307, user_id=msg.chat.id).status in (
            "member", "creator", "administrator"):
        bot.send_message(chat_id=msg.chat.id,
                         text=_("Bot can build a dialogue with logically connected replicas in this mode"),
                         reply_markup=get_dialog_menu(_))
        red.hset(f"user_{msg.chat.id}", "mode", UserMode.DIALOG.value)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: выбран режим 'Начать диалог' ")
    else:
        markup = quick_markup({"ChatGPTBOT_channel": {"url": "https://t.me/ChatGPTBOT_channel"}})
        bot.send_message(chat_id=msg.chat.id,
                         text=_("In order to continue using this bot, you need to subscribe telegram channel"),
                         reply_markup=markup)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: требуется подписка на телеграм-канал")


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)("🗯 Feedback"))
def show_feedback_names(msg: Message):
    _ = get_user_translator(msg.chat.id)
    bot.send_message(chat_id=msg.chat.id,
                     text=_("If you have some issues with using this bot, please contact @nnisl4 и @vadmart"))
    logging.info(
        f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: просмотр контактов для обратной связи")


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)("🌏 Language"))
def change_language(msg: Message):
    _ = get_user_translator(msg.chat.id)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(*(types.KeyboardButton(text=txt)
             for txt in LANG.keys()
             if LANG[txt] != red.hget(f"user_{msg.chat.id}", "local").decode("utf-8"))
           )
    bot.send_message(chat_id=msg.chat.id, text=_("Choose language:"), reply_markup=kb)


@bot.message_handler(func=lambda msg: msg.text in LANG.keys())
def choose_lang_for_user(msg: Message):
    change_locale_in_db(msg.chat.id, LANG[msg.text])
    red.hset(f"user_{msg.chat.id}", "local", LANG[msg.text])
    _ = get_user_translator(msg.chat.id)
    try:
        bot.send_message(chat_id=msg.chat.id,
                         text=_("Chosen language: {lng}").format(lng=msg.text),
                         reply_markup=markup_main_menu(msg.chat.id))
    except ValueError as e:
        bot.send_message(msg.chat.id, text=e)


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)("📝 Solving tasks"))
def solve_task(msg: Message):
    _ = get_user_translator(msg.chat.id)
    red.hset(f"user_{msg.chat.id}", "mode", UserMode.SOLVING_TASKS.value)
    bot.send_message(chat_id=msg.chat.id,
                     text=_("In this mode bot can answer a question by choosing correct variant(-s)"),
                     reply_markup=get_tasks_menu(_))


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)("🖼 Image generation"))
def image_generation(msg: Message):
    _ = get_user_translator(msg.chat.id)
    red.hset(f"user_{msg.chat.id}", "mode", UserMode.IMAGE_GENERATION.value)
    bot.send_message(chat_id=msg.chat.id,
                     text=_(
                         "In this mode bot can generate an image by using your description. Choose the image resolution:"),
                     reply_markup=get_image_mode_menu(_))
    bot.register_next_step_handler(message=msg, callback=set_user_resolution)


def set_user_resolution(msg: Message) -> None:
    _ = get_user_translator(msg.chat.id)
    if msg.text not in ("512x512", "1024x1024", _("☰ Main menu"), "/start"):
        bot.send_message(chat_id=msg.chat.id,
                         text=_("Choose the correct option!"))
        bot.register_next_step_handler(message=msg, callback=set_user_resolution)
        return
    elif msg.text == _("☰ Main menu"):
        start(msg, _("Our beautiful dialogue is over🙂\nChoose the option:"))
        return
    elif msg.text == "/start":
        start(msg)
        return
    red.hset(f"user_{msg.chat.id}", "image_resolution", msg.text)
    bot.send_message(chat_id=msg.chat.id,
                     text=_("Now provide me a text and i'll generate you an image 🙂"),
                     reply_markup=get_main_menu_button(_))


@bot.message_handler(func=lambda msg: msg.text == get_user_translator(msg.chat.id)("❌ Disable a bot"))
def disable_bot_menu(msg: Message):
    _ = get_user_translator(msg.chat.id)
    markup = quick_markup({_("1 minute"): {"callback_data": "1 minute"},
                           _("5 minutes"): {"callback_data": "5 minutes"},
                           _("10 minutes"): {"callback_data": "10 minutes"},
                           _("20 minutes"): {"callback_data": "20 minutes"}})
    bot.send_message(chat_id=msg.chat.id,
                     text=_("For how long do you want to disable the bot?"),
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def bot_disabler(call):
    all_users = get_all_user_ids_and_languages()
    logging.warning(f"{THR_NAME} : Отправка пользователям информации о ПРЕДСТОЯЩЕМ отключении бота")
    for user_id, loc in all_users:
        _ = translate[loc].gettext
        try:
            bot.send_message(chat_id=user_id,
                             text=_("Bot will be disabled in {data} for further impovements").format(
                                 data=_(call.data)),
                             disable_notification=True)
        except telebot.apihelper.ApiTelegramException:
            pass
    minutes_amount = float(call.data.split()[0])
    logging.warning(f"{THR_NAME} : Отключение бота через {minutes_amount} минут")
    time.sleep(minutes_amount * 60)
    logging.warning(f"{THR_NAME} : Отправка пользователям информации об отключении бота")
    all_users = get_all_user_ids_and_languages()
    for user_id, loc in all_users:
        _ = translate[loc].gettext
        try:
            bot.send_message(chat_id=user_id,
                             text=_("Bot has been disabled for further improvements").format(
                                 data=_(call.data)),
                             disable_notification=True)
        except telebot.apihelper.ApiTelegramException:
            pass
    bot.stop_bot()
    logging.warning(f"{THR_NAME} : Бот отключен")
    time.sleep(10)
    sys.exit()


@bot.message_handler(
    func=lambda msg: msg.text == get_user_translator(msg.chat.id)("📜 Instruction"))
def get_instruction(msg: Message):
    _ = get_user_translator(msg.chat.id)
    bot.send_message(chat_id=msg.chat.id,
                     text=_("""
                     Bot instruction:
     💬 Dialogue - the bot gives a non-detailed answer (although it is enough in most cases), but remembers replicas and, therefore, understands the context. For example, you can ask "What is a cell?", and if  you write to the bot "Do you like it?" after the answer, it will give an information about the cell.
     ❔ Detailed answer - the bot does not remember replicas, that is, it will not understand the context of the conversation. However, the maximum possible answer can be 2 times more than in the "Dialogue" mode. Useful if you are not going to develop the topic, but want to get a detailed answer."""))
    logging.info(f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: просмотр инструкции")


@bot.message_handler(
    func=lambda msg: msg.text == get_user_translator(msg.chat.id)("New dialogue"))
def start_new_dialog(msg: Message):
    _ = get_user_translator(msg.chat.id)
    if bot.get_chat_member(chat_id=-1001857064307, user_id=msg.chat.id).status in (
            "member", "creator", "administrator"):
        red.hset(f"user_{msg.chat.id}", "replicas", "")
        bot.send_message(chat_id=msg.chat.id, text=_("Start a new dialogue!"))
        logging.info(f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: начало нового диалога")
    else:
        markup = quick_markup({"ChatGPTBOT_channel": {"url": "https://t.me/ChatGPTBOT_channel"}})
        bot.send_message(chat_id=msg.chat.id,
                         text=_("In order to continue using this bot, you need to subscribe telegram channel"),
                         reply_markup=markup)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: требуется подписка на телеграм-канал")


@bot.message_handler(
    func=lambda msg: msg.text == get_user_translator(msg.chat.id)("☰ Main menu"))
def end_dialog(msg: Message):
    _ = get_user_translator(msg.chat.id)
    try:
        start(msg, _("Our beautiful dialogue is over🙂\nChoose the option:"))
        logging.info(f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: завершение диалога")
    except KeyError:
        pass


@bot.message_handler(content_types=["text"])
def handle_requests(msg: Message):
    _ = get_user_translator(msg.chat.id)
    try:
        if not int(red.hget(f"user_{msg.chat.id}", "has_active_request")):
            if red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.DIALOG.value:
                bot.send_message(chat_id=msg.chat.id,
                                 text=formatting.hitalic(_("The request was sent, wait for an answer...😉")),
                                 parse_mode="HTML")
                send_request(msg)
            elif red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.DETAILED_ANSWER.value:
                bot.send_message(chat_id=msg.chat.id,
                                 text=formatting.hitalic(_("The request was sent, wait for an answer...😉")),
                                 parse_mode="HTML")
                send_request(msg)
            elif red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.SOLVING_TASKS.value:
                msg.text += '\n' + "Choose either one answer, if there are no more, and then write: " + \
                            f"""{_('"Correct answer - *insert the correct variant here*"')}, and if there are more """ + \
                            f"""correct variants - answer {_('"Correct answers - *insert correct variants here*"')}. If """ + \
                            f"""there is no correct variant from listed above, answer """ + \
                            _('"There is no correct variant from listed above. The correct answer is *insert correct answer here*"')
                bot.send_message(chat_id=msg.chat.id,
                                 text=formatting.hitalic(_("The request was sent, wait for an answer...😉")),
                                 parse_mode="HTML")
                send_request(msg)
            elif red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.IMAGE_GENERATION.value:
                bot.send_message(chat_id=msg.chat.id,
                                 text=formatting.hitalic(_("The request was sent, wait for an answer...😉")),
                                 parse_mode="HTML")
                send_request(msg)
        else:
            bot.send_message(chat_id=msg.chat.id,
                             text=formatting.hitalic(_("Your answer is processing.\nPlease, wait…")),
                             parse_mode="HTML")
    except (AttributeError, TypeError):
        bot.send_message(chat_id=msg.chat.id, text=_("Choose the mode from the main menu!"))
        logging.error(f"{THR_NAME} : Пользователь id = {msg.chat.id} не найден!")


def send_request(msg: Message) -> Optional[Message]:
    _ = get_user_translator(msg.chat.id)
    logging.info(f"{THR_NAME} : старт работы")
    red.hset(f"user_{msg.chat.id}", "has_active_request", 1)
    all_api_keys = {k.decode("utf-8"): int(v) for k, v in red.hgetall("openai_keys-reqs_amount").items()}
    best_api_key = min(all_api_keys.keys(), key=lambda k: all_api_keys[k])
    all_api_keys[best_api_key] += 1
    red.hset("openai_keys-reqs_amount", best_api_key, all_api_keys[best_api_key])
    try:
        if red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.DIALOG.value:
            bot.send_chat_action(msg.chat.id, "typing")
            replica = red.hget(f"user_{msg.chat.id}", "replicas").decode("utf-8") + msg.text + "\n"
            answer = CompletionAI(api_key=best_api_key,
                                  txt=replica,
                                  max_tokens=1600).get_answer()
            current_user_mode = red.hget(f"user_{msg.chat.id}", "mode")  # получаем текущий выбранный режим юзера
            if current_user_mode:  # если тип не равен None, то
                if current_user_mode.decode("utf-8") == UserMode.DIALOG.value:
                    # если после получения ответа пользователь не изменил режим
                    replica += answer + "\n"
                    red.hset(f"user_{msg.chat.id}", "replicas", replica)
                    return bot.send_message(msg.chat.id, answer,
                                            reply_markup=get_dialog_menu(_))
        elif red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.DETAILED_ANSWER.value:
            # режим обширный ответ
            bot.send_chat_action(msg.chat.id, "typing")
            answer = CompletionAI(api_key=best_api_key, txt=msg.text, max_tokens=3200).get_answer()
            current_user_mode = red.hget(f"user_{msg.chat.id}", "mode")  # получаем текущий выбранный режим юзера
            if current_user_mode:  # если тип не равен None, то
                if current_user_mode.decode("utf-8") == UserMode.DETAILED_ANSWER.value:
                    return bot.send_message(msg.chat.id, answer, reply_markup=get_main_menu_button(_))
        elif red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.SOLVING_TASKS.value:
            bot.send_chat_action(msg.chat.id, "typing")
            answer = CompletionAI(api_key=best_api_key,
                                  txt=msg.text,
                                  max_tokens=500).get_answer()
            current_user_mode = red.hget(f"user_{msg.chat.id}", "mode")  # получаем текущий выбранный режим юзера
            if current_user_mode:  # если тип не равен None, то
                if current_user_mode.decode("utf-8") == UserMode.SOLVING_TASKS.value:
                    # если после получения ответа пользователь не изменил режим
                    return bot.send_message(msg.chat.id, answer)
        elif red.hget(f"user_{msg.chat.id}", "mode").decode("utf-8") == UserMode.IMAGE_GENERATION.value:
            bot.send_chat_action(msg.chat.id, "upload_photo")
            image = ImageDALLEAI(api_key=best_api_key,
                                 txt=msg.text,
                                 size=red.hget(f"user_{msg.chat.id}", "image_resolution").decode("utf-8"))
            current_user_mode = red.hget(f"user_{msg.chat.id}", "mode")
            if current_user_mode:
                if current_user_mode.decode("utf-8") == UserMode.IMAGE_GENERATION.value:
                    bot.send_photo(chat_id=msg.chat.id,
                                   photo=image.img_url)
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: получение ответа")
    except (OpenAIServerErrorException,
            KeyError,
            telebot.apihelper.ApiTelegramException):
        bot.send_message(chat_id=msg.chat.id,
                         text=_("Something went wrong. Send me a message again or change the text"))
        logging.info(
            f"{THR_NAME} : {msg.from_user.first_name} {msg.from_user.last_name}: бот ответил пустым сообщением либо ошибкой")
    except ExcessTokensException as e:
        bot.send_message(chat_id=msg.chat.id,
                         text=_(str(e)))
    except AttributeError:
        bot.send_message(chat_id=msg.chat.id, text=_("Choose the mode from the main menu!"))
        logging.error(f"{THR_NAME} : Пользователь id = {msg.chat.id} не найден!")
    finally:
        all_api_keys[best_api_key] -= 1
        red.hset("openai_keys-reqs_amount", best_api_key, all_api_keys[best_api_key])
        red.hset(f"user_{msg.chat.id}", "has_active_request", 0)
    logging.info(f"{THR_NAME} : конец работы")


def init_api_keys():
    for key_name in get_all_api_keys():
        # добавление АПИ-ключа в Redis
        red.hset("openai_keys-reqs_amount", key_name, 0)


def init_users():
    for user_id, language in get_all_user_ids_and_languages():
        red.hset(f"user_{user_id}", "replicas", "")
        red.hset(f"user_{user_id}", "local", language)
        red.hset(f"user_{user_id}", "has_active_request", 0)


def launch():
    for id_ in get_all_user_ids():
        try:
            _ = get_user_translator(id_)
            bot.send_message(chat_id=id_,
                             text=_("Bot has been launched and is ready to use🙂"),
                             reply_markup=create_launch_menu(_))
        except telebot.apihelper.ApiTelegramException:
            pass


@app.route(f"/{TELEBOT_TOKEN}", methods=["POST"])
def server():
    json_string = flask.request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    logging.info(str(update))
    return "!", 200


@app.route("/", methods=["GET"])
def echo():
    return "!", 200


clear_redis()
init_api_keys()
init_users()
