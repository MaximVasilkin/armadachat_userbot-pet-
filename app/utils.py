import pickle
import re
from string import punctuation


MESSAGE_LIMIT = 230


def load_data(file_path):
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f'no file {file_path}')
        return


def save_data(file_path, data):
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)


def clean_text(text):
    checked = [symbol_ if any([symbol_.isalnum(),
                               symbol_.isspace(),
                               symbol_ in punctuation]) else ' ' for symbol_ in text]
    checked_text = ''.join(checked)
    return checked_text


def __get_title(title, place_holder=''):
    title_start = '('
    title_end = ')'
    it = 'стр.'
    sep = '/'
    title = f'{title_start}{title}{it} {place_holder}{sep}{place_holder}{title_end}'
    return title


def __append_sentence(title, place_holder, sentence, list_of_sentences):
    sentence = f'{__get_title(title, place_holder)}{sentence}'
    list_of_sentences.append(sentence)


def text_spliter(text, limit, title='', separators=';:,.', delimiter='...'):
    text = f' {text}'
    delimiter = f' {delimiter}'
    if title:
        title = f'{title}: '

    max_len_of_pages_counter = len(str(int(len(text) / limit))) + 1
    num_counters = 2
    len_title = len(__get_title(title)) + (max_len_of_pages_counter * num_counters)
    len_delimiter = len(delimiter)
    len_add_info = len_delimiter + len_title

    list_of_tokens = re.findall(f'[^{separators}]+[{separators}]*', text)
    sentence = ''
    sentences = []

    place_holder = '^' * max_len_of_pages_counter

    for index, token in enumerate(list_of_tokens):
        len_token = len(token)
        len_sentence = len(sentence)
        if index == len(list_of_tokens) - 1 and len_title + len_sentence + len_token <= limit:
            pass
        elif len_token > limit - len_add_info - len_sentence:
            sentence += delimiter
            __append_sentence(title, place_holder, sentence, sentences)
            sentence = ''
        sentence += token
    __append_sentence(title, place_holder, sentence, sentences)

    for index, sentence in enumerate(sentences):
        sentences[index] = sentence.replace(place_holder, str(index + 1), 1).replace(place_holder, str(len(sentences)))

    return sentences


def shorter(max_len):
    def decorator(func):
        def wrapper(*args, **kwargs):
            data = func(*args, **kwargs)
            while len(data) > max_len:
                data = func(*args, **kwargs)
            return data
        return wrapper
    return decorator

