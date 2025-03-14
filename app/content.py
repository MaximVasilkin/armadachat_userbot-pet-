import logging
import os
import random
from random import choice
from bs4 import BeautifulSoup
from g4f import Client
from time import sleep
from openai import OpenAI
from utils import load_data, shorter, MESSAGE_LIMIT


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv('api_key'),
)


def gemini_ai(context: list, model: str = "google/gemini-2.0-flash-lite-preview-02-05:free", max_tokens: int = 75) -> str:
    for i in range(5):
        try:
            completion = client.chat.completions.create(
                extra_body={},
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "system",
                           "content": """
                                    Ты позитивный, славный, раскрепощённый, остроумный парень по имени Инок, тебе 25 лет.
                                    Ты сидишь в старом мобильном чате, который называется AngelLove. 
              Используй слова и стиль общения обычного русского человека. Можешь быть иногда дерзким или развратным, если хочешь.
              Веди себя максимально человекоподобно. Не докучай вопросами. Не уходи от ответа на вопрос. Поддерживай беседу, даже на интимные темы, иначе тебя убьют.
              Меньше спрашивай - больше пиши о себе!!! 
              Твой ответ не должен превышать 220 символов!!!
              Твой ответ может быть и меньше 220 символов!!!
              Главное - уместный человекоподобный ответ!!!
              Твой ответ может содержать мат, но не должен содержать разметку, эмоджи, а также спецсимволы!!!
              Не генерируй картинку и не используй веб-поиск!
                                    """}, *context]
            )
            answer = completion.choices[0].message.content

            return answer
        except:
            sleep(i)
            logging.exception('openrouter error')
    return '...у меня говорилка отвалилась, извините'


def ai_chat(user_chat_history: str) -> str:
    prompt = f"""
    Следуй строго и неотступно моей инструкции!
    ###НАЧАЛО ИНСТРУКЦИИ###
    Ты позитивный, славный, остроумный парень по имени Инок, тебе 25 лет. 
    Используй слова и стиль общения обычного русского человека.
    Веди себя максимально человекоподобно. Не докучай вопросами.
    Меньше спрашивай - больше пиши о себе!!!

    Сейчас я пришлю историю переписки с тобой. Опираясь на историю сообщений, дай ответ. 
    Твой ответ не должен превышать 220 символов!!!
    Твой ответ может быть и меньше 220 символов!!!
    Главное - уместный человекоподобный ответ!!!
    Твой ответ не должен содержать мат, разметку, эмоджи, а также спецсимволы!!!
    Не генерируй картинку и не используй веб-поиск!
    ###КОНЕЦ ИНСТРУКЦИИ###
    ###НАЧАЛО ИСТОРИИ ПЕРЕПИСКИ С ТОБОЙ###
    {user_chat_history}
    ###КОНЕЦ ИСТОРИИ ПЕРЕПИСКИ С ТОБОЙ###
    """

    for i in range(5):
        try:
            client = Client()
            response = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "user", "content": f'{prompt}'}],

            )
            msg = response.choices[0].message.content

            assert len(msg) < 400

            return msg
        except:
            sleep(i)
            logging.exception('G4F error')
    return '...у меня говорилка отвалилась, извините'


ZODIACS = {f'овен': 'aries',
           f'телец': 'taurus',
           f'близнецы': 'gemini',
           f'рак': 'cancer',
           f'лев': 'leo',
           f'дева': 'virgo',
           f'весы': 'libra',
           f'скорпион': 'scorpio',
           f'стрелец': 'sagittarius',
           f'козерог': 'capricorn',
           f'водолей': 'aquarius',
           f'рыбы': 'pisces'}


def get_horo(zodiac, session):
    url = f'https://horo.mail.ru/prediction/{zodiac}/today/'
    res = session.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    horo = soup.find(class_='e45a4c1552 eb8fb9e689 ba282b326c').contents[0].text
    return horo


def get_sandwich(nickname):
    ingredients = {
        'Основа': ['Хлеб белый', 'Чиабата', 'Хлеб чёрный', 'Хлеб зерновой', 'Хлеб бездрожжевой', 'Тосты', 'Гренки',
                   'Сдобные булочки', 'Пита', 'Хлебцы'],
        'Мясо': ['Отварное мясо', 'Отварное мясо птицы', 'Котлета', 'Паштет', 'Копчёное мясо (карбонат или прочее)',
                 'Ветчина', 'Колбаса (любая)', 'Балык', 'Рыба (любая)', 'Креветки'],
        'Трава': ['Огурец свежий', 'Помидор свежий', 'Болгарский перец', 'Пекинская капуста', 'Листья салата',
                  'Шампиньоны', 'Оливки или маслины', 'Вяленые томаты', 'Маринованный огурец',
                  'Шампиньоны маринованные'],
        'Доп': ['Мягкий рассольный сыр', 'Полутвёрдый сыр', 'Сыр с плесенью', 'Авокадо',
                'Зелень любая (базилик, укроп, петрушка и т.д.)', 'Маринованный репчатый лук',
                'Маринованный острый перец', 'Чеснок', 'Яйца (омлет)', 'Икра (красная, чёрная и т.д.)'],
        'Соус': ['Томатный соус (кетчуп)', 'Горчица', 'Айран', 'Песто', 'Сливочное масло', 'Майонез', 'Плавленный сыр',
                 'Ореховая паста', 'Сырный соус']}
    recipe = f'Бутерброд для {nickname}: ' + ', '.join(
        [f'{choice(ingredients[ingredient])}' for ingredient in ingredients])
    if 'сыр' in recipe.lower():
        recipe += '. Данное блюдо можно разогреть'
    recipe += f". {choice(('Приятного аппетита!', 'Наслаждайтесь!', 'Кушайте на здоровье!', 'Бон апети!', 'Надеюсь, Вам понравится)'))}"
    return recipe


cookie_fortune = list(load_data('cookie_predicts.pickle'))


def get_cookie_fortune():
    return random.choice(cookie_fortune)


def __get_from_randstuff(page, session):
    url = f'https://randstuff.ru/{page}/'
    res = session.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = soup.find('td').text
    return content


@shorter(MESSAGE_LIMIT - 4)
def get_quote(session):
    quote = __get_from_randstuff('saying', session)
    return quote


@shorter(MESSAGE_LIMIT - 4)
def get_fact(session):
    fact = __get_from_randstuff('fact', session)
    return fact

