import re
import sqlite3
from collections import Counter
from string import punctuation
from math import sqrt
from bot_config import PHRASES_DATABASE_NAME


connection = None
cursor = None


def db_open_connection(text):
    """ Initialize the connection to the database
    and create the tables needed by the program
    """

    # initialize the connection to the database
    global connection
    global cursor
    try:
        connection = sqlite3.connect(PHRASES_DATABASE_NAME)
        cursor = connection.cursor()
        text = text_processing(text)
        db_close_connection()
        return text
    except:
        pass

    # create the tables needed by the program
    try:
        # create the table containing the words
        cursor.execute('''
            CREATE TABLE words (
                word TEXT UNIQUE
            )
        ''')
        # create the table containing the sentences
        cursor.execute('''
            CREATE TABLE sentences (
                sentence TEXT UNIQUE,
                used INT NOT NULL DEFAULT 0
            )''')
        # create association between weighted words and the next sentence
        cursor.execute('''
            CREATE TABLE associations (
                word_id INT NOT NULL,
                sentence_id INT NOT NULL,
                weight REAL NOT NULL)
        ''')
    except:
        pass


def get_id(entityName, text):
    global connection
    global cursor
    """ Retrieve an entity's unique ID from the database, given its associated text.
    If the row is not already present, it is inserted.
    The entity can either be a sentence or a word.
    """
    tableName = entityName + 's'
    columnName = entityName
    cursor.execute('SELECT rowid FROM ' + tableName + ' WHERE ' + columnName + ' = ?', (text,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute('INSERT INTO ' + tableName + ' (' + columnName + ') VALUES (?)', (text,))
        return cursor.lastrowid


def get_words(text):
    """ Retrieve the words present in a given string of text.
    The return value is a list of tuples where the first member is a lowercase word,
    and the second member the number of time it is present in the text.
    """
    wordsRegexpString = '(?:\w+|[' + re.escape(punctuation) + ']+)'
    wordsRegexp = re.compile(wordsRegexpString)
    wordsList = wordsRegexp.findall(text.lower())
    return Counter(wordsList).items()


def text_processing(text):
    global connection
    global cursor
    B = 'Hello'
    # Handles incoming user request and returns a response
    H = text.strip()
    if H == '':
        return -1
    # store the association between the bot's message words and the user's response
    words = get_words(B)
    words_length = sum([n * len(word) for word, n in words])
    sentence_id = get_id('sentence', H)
    for word, n in words:
        word_id = get_id('word', word)
        weight = sqrt(n / float(words_length))
        cursor.execute('INSERT INTO associations VALUES (?, ?, ?)', (word_id, sentence_id, weight))
    connection.commit()
    # retrieve the most likely answer from the database
    cursor.execute('CREATE TEMPORARY TABLE results(sentence_id INT, sentence TEXT, weight REAL)')
    words = get_words(H)
    words_length = sum([n * len(word) for word, n in words])
    for word, n in words:
        weight = sqrt(n / float(words_length))
        cursor.execute(
            'INSERT INTO results SELECT associations.sentence_id, sentences.sentence, ?*associations.weight/(4+sentences.used) FROM words INNER JOIN associations ON associations.word_id=words.rowid INNER JOIN sentences ON sentences.rowid=associations.sentence_id WHERE words.word=?',
            (weight, word,))
    # if matches were found, give the best one
    cursor.execute(
        'SELECT sentence_id, sentence, SUM(weight) AS sum_weight FROM results GROUP BY sentence_id ORDER BY sum_weight DESC LIMIT 1')
    row = cursor.fetchone()
    cursor.execute('DROP TABLE results')
    # otherwise, just randomly pick one of the least used sentences
    if row is None:
        cursor.execute(
            'SELECT rowid, sentence FROM sentences WHERE used = (SELECT MIN(used) FROM sentences) ORDER BY RANDOM() LIMIT 1')
        row = cursor.fetchone()
    # tell the database the sentence has been used once more, and prepare the sentence
    B = row[1]
    cursor.execute('UPDATE sentences SET used=used+1 WHERE rowid=?', (row[0],))
    return B


def db_close_connection():
    global connection
    connection.close()
