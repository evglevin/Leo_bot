import xml.etree.ElementTree as XmlElementTree
import httplib2
import uuid
from bot_config import YANDEX_API_KEY

import subprocess
import tempfile
import os

import aiohttp
import urllib.request
import urllib.parse
import urllib


def read_chunks(chunk_size, bytes):
    """Transfer audio recordings in parts
    """
    while True:
        chunk = bytes[:chunk_size]
        bytes = bytes[chunk_size:]

        yield chunk

        if not bytes:
            break


YANDEX_ASR_HOST = 'asr.yandex.net'
YANDEX_ASR_PATH = '/asr_xml'
CHUNK_SIZE = 1024 ** 2

def speech_to_text(filename=None, bytes=None, request_id=uuid.uuid4().hex, topic='notes', lang='ru-RU',
                   key=YANDEX_API_KEY):
    # Если передан файл
    if filename:
        with open(filename, 'br') as file:
            bytes = file.read()
    if not bytes:
        raise Exception('Neither file name nor bytes provided.')

    # Конвертирование в нужный формат
    bytes = convert_to_pcm16b16000r(in_bytes=bytes)

    # Формирование тела запроса к Yandex API
    url = YANDEX_ASR_PATH + '?uuid=%s&key=%s&topic=%s&lang=%s' % (
        request_id,
        key,
        topic,
        lang
    )

    # Считывание блока байтов
    chunks = read_chunks(CHUNK_SIZE, bytes)

    # Установление соединения и формирование запроса
    connection = httplib2.HTTPConnectionWithTimeout(YANDEX_ASR_HOST)

    connection.connect()
    connection.putrequest('POST', url)
    connection.putheader('Transfer-Encoding', 'chunked')
    connection.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000')
    connection.endheaders()

    # Отправка байтов блоками
    for chunk in chunks:
        connection.send(('%s\r\n' % hex(len(chunk))[2:]).encode())
        connection.send(chunk)
        connection.send('\r\n'.encode())

    connection.send('0\r\n\r\n'.encode())
    response = connection.getresponse()

    # Обработка ответа сервера
    if response.code == 200:
        response_text = response.read()
        xml = XmlElementTree.fromstring(response_text)

        if int(xml.attrib['success']) == 1:
            max_confidence = - float("inf")
            text = ''

            for child in xml:
                if float(child.attrib['confidence']) > max_confidence:
                    text = child.text
                    max_confidence = float(child.attrib['confidence'])

            if max_confidence != - float("inf"):
                return text
            else:
                # Создавать собственные исключения для обработки бизнес-логики - правило хорошего тона
                raise SpeechException('No text found.\n\nResponse:\n%s' % (response_text))
        else:
            raise SpeechException('No text found.\n\nResponse:\n%s' % (response_text))
    else:
        raise SpeechException('Unknown error.\nCode: %s\n\n%s' % (response.code, response.read()))


# Создание своего исключения
class SpeechException(Exception):
    pass

def convert_to_pcm16b16000r(in_filename=None, in_bytes=None):
    with tempfile.TemporaryFile() as temp_out_file:
        temp_in_file = None
        if in_bytes:
            temp_in_file = tempfile.NamedTemporaryFile(delete=False)
            temp_in_file.write(in_bytes)
            in_filename = temp_in_file.name
            temp_in_file.close()
        if not in_filename:
            raise Exception('Neither input file name nor input bytes is specified.')
        # Запрос в командную строку для обращения к FFmpeg
        command = ['ffmpeg',
                   '-i', in_filename,
                   '-f', 's16le',
                   '-acodec', 'pcm_s16le',
                   '-ar', '16000', '-']

        proc = subprocess.Popen(command, stdout=temp_out_file, stderr=subprocess.DEVNULL)
        proc.wait()

        if temp_in_file:
            os.remove(in_filename)

        temp_out_file.seek(0)
        return temp_out_file.read()




def text_to_speech(text, audio_format, speaker):
    """
    text=<текст для генерации> - "гот%2bов"
    format=<формат аудио файла> - "mp3", "wav"
    lang=<язык> - "ru‑RU"
    speaker=<голос> - female: jane, omazh; male: zahar, ermil
    key=<API‑ключ>

    [emotion=<окраска голоса>] - neutral(нейтральный), evil (злой), mixed (переменная окраска)
    [drunk=<окраска голоса>] - true, false
    [ill=<окраска голоса>] - true, false
    [robot=<окраска голоса>] - true, false
    """
    key = YANDEX_API_KEY
    url = 'https://tts.voicetech.yandex.net/generate?' \
          'text={text}&' \
          'format={audio_format}&' \
          'lang=ru-RU&' \
          'speaker={speaker}&' \
          'key={key}&'

    text = urllib.parse.quote(text)

    url = url.format(
        text=text,
        audio_format=audio_format,
        speaker=speaker,
        key=key
    )

    #if a:
        #url += urllib.parse.urlencode(a)

    #urllib.request.urlretrieve(url, file)
    file = urllib.request.urlopen(url)
    return file
