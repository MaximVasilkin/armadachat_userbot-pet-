import time
from itertools import cycle
from threading import Thread
from collections import deque, defaultdict
from urllib.parse import parse_qs, urlparse
import requests
from bs4 import BeautifulSoup
from content import get_quote, get_fact
from handlers import router
from utils import load_data, save_data, clean_text, MESSAGE_LIMIT, text_spliter
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import logging


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout')
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get('timeout')
        if timeout is None:
            kwargs['timeout'] = self.timeout
        return super().send(request, **kwargs)


class TextColor:
    blue = '2'
    black = '1'
    green = '3'
    brown = '4'


class Message:
    def __init__(self, room_id, user_id, usernick, is_private, text, date, bot):
        self.room_id = room_id
        self.user_id = user_id
        self.nickname = usernick
        self.text = text
        self.date = date
        self.is_private = is_private
        self.bot = bot

    def __eq__(self, other):
        if not isinstance(other, Message):
            return False
        return (self.room_id, self.user_id, self.is_private, self.text, self.date) == \
               (other.room_id, other.user_id, other.is_private, other.text, other.date)

    def is_new(self) -> bool:
        return (self.nickname != self.bot.login) and (self not in self.bot.db[self.room_id])

    def mark_as_read(self):
        self.bot.db[self.room_id].append(self)

    def answer(self, text, color=TextColor.blue, expression='0', private=None):
        if private is None:
            private = self.is_private
        self.bot.smart_send(self.user_id, text, color=color, private=private, expression=expression, room_id=self.room_id)

    def __str__(self):
        return f'Комната {self.room_id}: {self.nickname} {"[!]" if self.is_private else ""} {self.date} {self.text}'

    __repr__ = __str__

    def to_dict(self):
        d = {
            'room_id': self.room_id,
            'user_id': str(self.user_id),
            'usernick': self.nickname,
            'text': self.text,
            'date': self.date,
            'is_private': self.is_private
        }
        return d

    @classmethod
    def from_dict(cls, dict_, bot):
        return cls(**dict_, bot=bot)


class Bot:
    def __init__(self, base_url, login, password, allowed_rooms, router, session, admins, context_len=30):
        self.router = router
        self.base_url = 'https://' + base_url.strip('/. ')
        self.session = session
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                        'Accept-Language': 'ru-RU,ru;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br, zstd',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                                  'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Priority': 'u=0, i',
                        'Sec-Ch-Ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'sec-ch-ua-platform': '"Windows"',
                        'sec-fetch-dest': 'document',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-site': 'none',
                        'sec-fetch-user': '?1',
                        'upgrade-insecure-requests': '1',
                        }

        self.context_len = context_len
        self.login = login
        self.password = password
        self.allowed_rooms = allowed_rooms
        self.db = self.load_db()
        self.context = self.load_context()
        self.current_room_id = self.load_last_room() or allowed_rooms[0]
        self.last_message = self.load_last_message()
        self.admins = set(map(str, admins))

    def load_db(self):
        db = load_data('./dump/db.pickle')
        default_dict = defaultdict(lambda: deque(maxlen=30))
        if db:
            for k, v in db.items():
                default_dict[k].extend(map(lambda d: Message.from_dict(d, self), v))
        else:
            for room_id in self.allowed_rooms:
                _ = default_dict[room_id]
        return default_dict

    def save_db(self):
        db = {k: list(map(lambda x: x.to_dict(), v)) for k, v in self.db.items()}
        return save_data('./dump/db.pickle', db)

    def load_context(self):
        context = load_data('./dump/context.pickle')
        default_dict = defaultdict(lambda: deque(maxlen=self.context_len))
        if context:
            for k, v in context.items():
                default_dict[k].extend(v)
        return default_dict

    def save_context(self):
        d = {k: list(v) for k, v in self.context.items()}
        return save_data('./dump/context.pickle', d)

    def load_last_message(self):
        try:
            with open('./dump/last_msg', 'r', encoding='UTF-8') as f:
                return f.read()
        except FileNotFoundError:
            return ''

    def save_last_message(self):
        with open('./dump/last_msg', 'w', encoding='UTF-8') as f:
            return f.write(self.last_message)

    def save_last_room(self):
        with open('./dump/last_room', 'w', encoding='UTF-8') as f:
            return f.write(str(self.current_room_id))

    def load_last_room(self):
        try:
            with open('./dump/last_room', 'r', encoding='UTF-8') as f:
                return int(f.read())
        except FileNotFoundError:
            return

    def log_in(self):
        self.session.headers.update(self.headers)
        data = {'us': self.login,
                'ps': self.password,
                'submit': 'Войти'}
        res = self.session.post(f'{self.base_url}/go.php', data=data, headers={'Content-Length': '60'})
        assert 'Вход в ЧАТ' in res.text, 'Ошибка входа'

    # def log_out(self):
    #     res = self.session.get(f'{self.base_url}/exit.php')
    #     print(res.text)

    def _get_messages(self, room_id):
        params = {'rm': room_id,
                  'mod': 'filtr_lmsg'}
        res = self.session.get(f'{self.base_url}/chat.php', params=params)
        soup = BeautifulSoup(res.text, features='html.parser')
        main_screen = soup.find(class_='body')
        posts = main_screen.find_all(class_='left')
        posts.reverse()
        return posts

    def get_messages(self, room_id=None) -> list[Message, ...]:
        room_id = room_id or self.current_room_id
        messages_ = self._get_messages(room_id)
        messages = []

        for message in messages_:
            message_content = message.contents
            message_length = len(message_content)

            text = message_content[-1].text.strip().lower()
            to_me = (message_length in (4, 5)) and message_content[-2].text == self.login and text[0] == ','

            if to_me:
                author = message.find('a')
                author_link = author.attrs['href']
                time = str(message_content[-3])[1:-2]

                usernick = author.text
                user_id = parse_qs(urlparse(author_link).query)['nk'][0]
                text = text[2:]
                is_private = message_length == 5 and str(message_content[1]) == '<b>[P!]</b>'
                messages.append(Message(room_id, user_id, usernick, is_private, text, time, self))

        return messages

    def get_new_messages(self, room_id=None):
        room_id = room_id or self.current_room_id
        return filter(lambda x: x.is_new(), self.get_messages(room_id))

    def go_to_room(self, room):
        self.current_room_id = room
        self.save_last_room()

    @staticmethod
    def split_unique(max_len=MESSAGE_LIMIT, delay=3):
        def decorator(func):
            def wrapper(*args, **kwargs):
                args = list(args)
                self = args[0]
                text = args[2]
                text = clean_text(text)
                text = self.to_unique(text)
                args[2] = text
                if len(text) > MESSAGE_LIMIT:
                    list_of_messages = text_spliter(text, max_len)
                    for answer in list_of_messages:
                        args[2] = answer
                        time.sleep(delay)
                        func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
                self.last_message = text
                return
            return wrapper
        return decorator

    def send(self, user_id, text, color=TextColor.blue, private=False, expression='0', room_id=None):
        params = {'rm': room_id or self.current_room_id}

        if private:
            res = self.session.get(f'{self.base_url}/inside.php', params=params | {'nk': user_id})

            form = BeautifulSoup(res.text, 'html.parser').find('form')
            if form is None:  # ignored
                return

            post_url = form.attrs['action']
            ref = post_url.split('=')[-1]
            params['ref'] = ref

        data = {'towhom': user_id,
                'msg': text,
                'prvt': str(int(private)),
                'nastr': expression,
                'color': color,
                'submit': 'Сказать'}

        self.session.post(f'{self.base_url}/chat.php', params=params, data=data)

    def say(self, room_id, text, color=TextColor.green):
        params = {'rm': room_id, 'skaz': '0'}
        data = {'msg': text, 'color': color, 'submit': 'Сказать'}
        self.session.post(f'{self.base_url}/chat.php', params=params, data=data)

    def say_here(self, text, color=TextColor.green):
        return self.say(self.current_room_id, text, color)

    def to_unique(self, text):
        if text == self.last_message:
            text += '.'
        return text

    smart_send = split_unique()(send)
    smart_say = split_unique()(say)

    def _mind_posting(self, latency_min=30):
        for value in cycle(range(2)):
            try:
                time.sleep(latency_min * 60)
                post = f'...{get_quote(self.session) if value else get_fact(self.session)}'
                self.smart_say(self.current_room_id, post, TextColor.green)
                self.save_last_message()
            except:
                logging.exception('error in mindposting')

    def mind_posting(self, latency_min=30):
        thr = Thread(target=self._mind_posting, args=(latency_min,))
        thr.start()

    def polling(self):
        while True:
            time.sleep(1)
            try:
                new_messages = self.get_new_messages()

                for message in new_messages:
                    time.sleep(2)
                    for filtrs, func in self.router.handlers:
                        if not filtrs or all([f(message) for f in filtrs]):

                            try:
                                answer = func(message)
                            except:
                                answer = 'Простите, возникла ошибка (что-то поломалось)'
                                logging.exception('Handler error')

                            message.answer(answer)
                            self.save_last_message()
                            break

                    message.mark_as_read()
                    self.save_db()
            except:
                logging.exception('Polling error')


def start_bot(base_url, login, password, room, admins, post_every_min=30, context_len=30):
    import platform

    if platform.system() == 'Windows':
        from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
        set_event_loop_policy(WindowsSelectorEventLoopPolicy())

    logging.basicConfig(filename='./dump/errors',
                        level=logging.ERROR,
                        format='============================\n[%(asctime)s] [%(levelname)s] => %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    with requests.Session() as session:
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=list(range(400, 550)),
            allowed_methods={'POST', 'GET'},
        )
        timeout_adapter = TimeoutHTTPAdapter(timeout=60)
        session.mount('http://', timeout_adapter)
        session.mount('https://', timeout_adapter)
        session.mount('https://', HTTPAdapter(max_retries=retries))
        session.mount('http://', HTTPAdapter(max_retries=retries))

        bot = Bot(base_url,
                  login,
                  password,
                  (2, 3, 4, 6, 16, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22),
                  session=session,
                  router=router,
                  admins=admins,
                  context_len=context_len)
        bot.log_in()
        bot.go_to_room(room)
        bot.mind_posting(post_every_min)
        bot.polling()


