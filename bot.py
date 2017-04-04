import telebot  # Python implementation for the Telegram Bot API
import requests
from bot_config import TELEGRAM_TOKEN
from message_processing import db_connection
from speechKit import speech_to_text, SpeechException, text_to_speech


bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(content_types=["text"])
def text_answer(message):
    if '/' not in message.text:
        ans = db_connection(message.chat.id, message.text, True)
        if ans != -1:
            bot.send_message(message.chat.id, ans)
        else:
            bot.send_message(message.chat.id, 'Empty message!')

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    file_info = bot.get_file(message.voice.file_id)
    file = requests.get(
        'https://api.telegram.org/file/bot{0}/{1}'.format(TELEGRAM_TOKEN, file_info.file_path))

    try:
        # appeal to our new module
        text = speech_to_text(bytes=file.content)
        ans = db_connection(message.chat.id, text, False)
        file = text_to_speech(ans, 'wav', 'ermil')
        data = file.read()
        bot.send_voice(message.chat.id, data)
        bot.send_message(message.chat.id, text=ans)
    except SpeechException:
        # Handling the case where the detection failed
        bot.send_message(message.chat.id, text='Я вас не понимаю')

if __name__ == '__main__':
     bot.polling(none_stop=True)
