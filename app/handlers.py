from content import ai_chat, get_sandwich, get_horo, get_cookie_fortune, ZODIACS, gemini_ai


class Router:
    def __init__(self, *filtrs):
        self.handlers = []
        self.filtrs = filtrs

    def register(self, *filtrs):
        def decorator(func):
            self.handlers.append((filtrs + self.filtrs, func))
            return func
        return decorator


router = Router()


@router.register(lambda m: any(m.text.startswith(f'!{k}') for k in ZODIACS))
def horoscope(message):
    key = tuple(filter(lambda z: message.text.startswith(f'!{z}'), ZODIACS))[0]
    zodiac = ZODIACS[key]
    return get_horo(zodiac, message.bot.session)


@router.register(lambda m: m.text.startswith('!печенье'))
def fortune_cookie(message):
    prediction = f'.my. {get_cookie_fortune()}'
    return prediction


@router.register(lambda m: m.text.startswith('!бутерброд'))
def sandwich(message):
    return get_sandwich(message.nickname)


@router.register(lambda m: m.text.startswith('!комната'),
                 lambda m: str(m.user_id) in m.bot.admins)
def change_room(message):
    result = message.text.strip('     \n.!,?-;')[-2:].lstrip('     \n.!,?-;')

    try:
        room_id = int(result)
    except ValueError:
        return 'Неверно указан номер комнаты'

    if room_id in message.bot.allowed_rooms:
        message.bot.go_to_room(room_id)
        return f'Иду в комнату {room_id}'
    else:
        return f'Не, я не пойду в комнату {room_id}. Выбери другую)'


@router.register()
def ai_talk(message):
    bot = message.bot
    context = bot.context[message.user_id]
    context.append({'role': 'user', 'content': message.text})
    about_me = bot.users.get(message.user_id, 'null')
    answer = gemini_ai(context, about_me=about_me)
    context.append({'role': 'assistant', 'content': answer})
    bot.save_context()
    trans_table = str.maketrans('аоеурх', 'aoeypx')  # обход фильтра на мат, замена латиницей
    return answer.translate(trans_table)

