from bot import start_bot
from os import getenv


if __name__ == '__main__':
    base_url = getenv('base_url')
    login = getenv('login')
    password = getenv('password')
    room = int(getenv('room'))
    admins = set(map(lambda x: x.strip(' \n'), getenv('admins').split(',')))
    post_every_min = int(getenv('post_every_min'))
    context_len = int(getenv('context_len'))

    start_bot(base_url=base_url,
              login=login,
              password=password,
              room=room,
              admins=admins,
              post_every_min=post_every_min,
              context_len=context_len)
