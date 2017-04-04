import xml.etree.ElementTree as XmlElementTree
import httplib2
import uuid
from bot_config import YANDEX_API_KEY
import subprocess
import tempfile
import os
import urllib.request
import urllib.parse
import urllib


def read_chunks(chunk_size, bytes):
    """
    
    Transfer audio recordings in parts
    
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

def speech_to_text(filename=None, bytes=None, request_id=uuid.uuid4().hex, topic='notes', lang='ru-RU', key=YANDEX_API_KEY):
    # If the file is transferred
    if filename:
        with open(filename, 'br') as file:
            bytes = file.read()
    if not bytes:
        raise Exception('Neither file name nor bytes provided.')

    # Conversion to the desired format
    bytes = convert_to_pcm16b16000r(in_bytes=bytes)

    # The forming of the body of the request to Yandex API
    url = YANDEX_ASR_PATH + '?uuid=%s&key=%s&topic=%s&lang=%s' % (
        request_id,
        key,
        topic,
        lang
    )

    # Reading bytes block
    chunks = read_chunks(CHUNK_SIZE, bytes)

    # Establishing a connection and query
    connection = httplib2.HTTPConnectionWithTimeout(YANDEX_ASR_HOST)

    connection.connect()
    connection.putrequest('POST', url)
    connection.putheader('Transfer-Encoding', 'chunked')
    connection.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000')
    connection.endheaders()

    # Sending bytes by blocks
    for chunk in chunks:
        connection.send(('%s\r\n' % hex(len(chunk))[2:]).encode())
        connection.send(chunk)
        connection.send('\r\n'.encode())

    connection.send('0\r\n\r\n'.encode())
    response = connection.getresponse()

    # Processing server response
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
                # Creating custom exceptions for handling business logic
                raise SpeechException('No text found.\n\nResponse:\n%s' % (response_text))
        else:
            raise SpeechException('No text found.\n\nResponse:\n%s' % (response_text))
    else:
        raise SpeechException('Unknown error.\nCode: %s\n\n%s' % (response.code, response.read()))


# Creating own exception
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
        # The request to the command line to access the FFmpeg
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
    key = YANDEX_API_KEY
    url = 'https://tts.voicetech.yandex.net/generate?' \
          'text={text}&' \
          'format={audio_format}&' \
          'lang=ru-RU&' \
          'speaker={speaker}&' \
          'key={key}&'

    text = urllib.parse.quote(text)
    url = url.format(text=text, audio_format=audio_format, speaker=speaker, key=key)
    file = urllib.request.urlopen(url)
    return file
