from bot_config import TELEGRAM_TOKEN
import telebot  #Python implementation for the Telegram Bot API
from message_processing import db_open_connection, db_close_connection, text_processing


bot = telebot.TeleBot(TELEGRAM_TOKEN)



@bot.message_handler(content_types=["text"])
def text_answer(message):
    db_open_connection()
    ans = text_processing(message.text)
    db_close_connection()
    bot.send_message(message.chat.id, ans)


if __name__ == '__main__':
     bot.polling(none_stop=True)
