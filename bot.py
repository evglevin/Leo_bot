from bot_config import TELEGRAM_TOKEN
import telebot  #Python implementation for the Telegram Bot API
from message_processing import db_open_connection, db_close_connection, text_processing
import requests
from speechKit import speech_to_text, SpeechException


bot = telebot.TeleBot(TELEGRAM_TOKEN)


@bot.message_handler(content_types=["text"])
def text_answer(message):
    ans = db_open_connection(message.text)
    bot.send_message(message.chat.id, ans)

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    file_info = bot.get_file(message.voice.file_id)
    file = requests.get(
        'https://api.telegram.org/file/bot{0}/{1}'.format(TELEGRAM_TOKEN, file_info.file_path))

    try:
        # appeal to our new module
        text = speech_to_text(bytes=file.content)
        bot.send_message(message.chat.id, text)
        text = db_open_connection(text)
        bot.send_message(message.chat.id, text)
    except SpeechException:
        # Handling the case where the detection failed
        bot.send_message(message.chat.id, 'Я тебя не понимаю')

if __name__ == '__main__':
     bot.polling(none_stop=True)
