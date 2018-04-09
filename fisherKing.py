import sys
import time
import telepot
import telepot.namedtuple
import datetime
import threading
import re
import random
import sqlite3
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.namedtuple import InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent
from pprint import pprint

conn2 = sqlite3.connect('fish.sqlite', check_same_thread = False)
cur2 = conn2.cursor()

cur2.execute('''
            CREATE TABLE IF NOT EXISTS FishTable
            (id INTEGER PRIMARY KEY, username TEXT, userid TEXT UNIQUE, fishCount INTEGER)''')

cur2.execute('''
            CREATE TABLE IF NOT EXISTS FishOccurence
            (id INTEGER PRIMARY KEY, origmsg INTEGER, chatid INTEGER, msgid INTEGER, status TEXT)''')

cur2.execute('''
            CREATE TABLE IF NOT EXISTS Orders
            (id INTEGER PRIMARY KEY, orders TEXT UNIQUE)''')

cur2.execute('''
            CREATE TABLE IF NOT EXISTS Votings
            (id INTEGER PRIMARY KEY, target TEXT UNIQUE, count INTEGER, voters TEXT, message_id INTEGER, chat_id INTEGER)''')

cur2.execute('''
            CREATE TABLE IF NOT EXISTS Data
            (id INTEGER PRIMARY KEY, name TEXT UNIQUE, num INTEGER UNIQUE)''')

bot = telepot.Bot('457399966:AAH-MN0EwmzmJLC7o18QmMIDa8wIxY9kW-Q')
bot.getMe()

def handle(msg):

    content_type, chat_type, chat_id = telepot.glance(msg)

    update_users(msg)

    if content_type == 'text' and not 'forward_from' in msg:

        #check fish sum
        if re.match("Бот, (сколько у меня рыбы\?)|(посчитай мою рыбу)", msg['text'], re.I):
            count = check_balance(msg)
            tempStr = "";
            if count == 0:
                tempStr = "У тебя нет рыбы."
            elif count == 1:
                tempStr = "У тебя 1 рыба."
            else:
                tempStr = "У тебя " + str(count) + " рыбы."
            if count > 0 :
                tempStr = tempStr + "\n"
                for i in range(count) :
                    tempStr = tempStr + random.choice(["\U0001F41F"])
            bot.sendMessage(chat_id, tempStr)

        #debug
        elif msg['text'] == "Debug" and msg['from']['username'] == 'Williander':
            spawn_fish(msg)

        elif msg['text'] == "База данных" and msg['from']['username'] == 'Williander':
            bot.sendDocument(chat_id, open('fish.sqlite'))

        #choose
        elif re.match("Бот,", msg['text'], re.I) and re.search (' или ', msg['text'], re.I) and re.search ('\?', msg['text'], re.I) :
            str1 = re.findall(', (.+) или', msg['text'], re.I)[0]
            str2 = re.findall(' или (.+)\?', msg['text'], re.I)[0]
            choice = random.choice([str1, str2])
            choice = choice[0].capitalize() + choice [1:];
            if not choice.endswith(('.', '!', '?', ')', '(', ',')) :
                choice = choice + "."
            if not re.search('или или', msg['text']) :
                bot.sendMessage(chat_id, choice)
            else :
                bot.sendMessage(chat_id, "Некорректный запрос.")

        #fish market
        elif re.match("Бот,", msg['text'], re.I) and re.search (' рыбн(ой|ая|ую) бирж(и|а|е|у)', msg['text'], re.I) :
            count = 0
            cur2.execute('SELECT fishCount FROM FishTable')
            for row in cur2:
                count = count + row[0]
            cur2.execute('SELECT username, fishCount FROM FishTable WHERE fishcount > 0 ORDER bY fishCount DESC')
            tempStr = "На данный момент рыбными активами обладают:\n\n"
            for row in cur2:
                tempStr = tempStr + str(row[0]) + ":\t" + str(int(100 * round(row[1] / count, 2))) + "% акций\n"
            bot.sendMessage(chat_id, tempStr)

        #transfer fish
        elif re.match("Бот,", msg['text'], re.I) and re.search("переда(й|ть) рыбу", msg['text'], re.I):
            count = check_balance(msg)
            if count == 0 :
                bot.sendMessage(chat_id, "У тебя нет рыбы для этого.")
            else :
                try:
                    user = re.findall("рыбу ([a-zа-я0-9]+)", msg['text'], re.I)[0]
                except:
                    bot.sendMessage(chat_id, "Некорректный запрос.")
                    pass
                cur2.execute('SELECT username FROM FishTable WHERE username = ?', (user,))
                if len(cur2.fetchall()) == 0:
                    bot.sendMessage(chat_id, "Такого рыбовладельца не существует.")
                else:
                    spend_fish(msg, 1)
                    rnd = random.randint(0, 10)
                    if rnd == 6:
                        bot.sendMessage(chat_id, "Пролетающая мимо чайка грациозно выхватывает рыбу у вас из рук в момент передачи.")
                    else:
                        add_fish_by_id(username_to_id(user), 1)
                        bot.sendMessage(chat_id, "Рыба успешно передана.")

        elif re.match("Бот, гимн", msg['text'], re.I):
            bot.sendAudio(chat_id, 'CQADBQADCQADzpJpVRrBnIfTki9AAg')

        #commands
        elif re.match("/help", msg['text'], re.I):
            bot.sendAudio(chat_id, 'CQADBQADDAADXbtJVSLx2GhQr0VSAg')

        elif re.match("/roll1d20", msg['text'], re.I):
            bot.sendMessage(chat_id, "1d20: " + str(random.randrange(20) + 1))

        elif re.match("/nroll", msg['text'], re.I):
            threshold = str(random.randrange(20) + 1);
            result = str(random.randrange(20) + 1);
            bot.sendMessage(chat_id, "Порог: " + threshold);
            if threshold == "1":
                bot.sendMessage(chat_id, "Звёзды благосклонны тебе.");
            elif threshold == "20":
                result = "Критическая неудача!"
            else :
                bot.sendMessage(chat_id, "1d20: " + result);

        #probability roll
        elif re.match('Бот, оцени вероятность', msg['text'], re.I):
            bot.sendMessage(chat_id, str(random.randrange(101)) + "%")

        #evaluation roll
        elif re.match('Бот, оцени', msg['text'], re.I):
            bot.sendMessage(chat_id, str(random.randrange(11)) + "/10")

        #coin toss
        elif re.match('Бот, подбрось монетку', msg['text'], re.I):
            bot.sendMessage(chat_id, str(random.choice(['Орёл.', 'Решка.'])))

        #thanks bot
        elif re.match('Спасибо, бот', msg['text'], re.I) or re.match('Бот, спасибо', msg['text'], re.I):
            bot.sendMessage(chat_id, random.choice(["Обращайся.", "Рад помочь.", "Пожалуйста."]))

        #fish roll
        elif re.match('(/fishroll)', msg['text'], re.I):
            if check_balance(msg) > 0:
                spend_fish(msg, 1)
                bot.sendMessage(msg['chat']['id'], "Рыба начинает растворяться в воздухе. В её глазах ты видишь облегчение.")
                bot.sendMessage(msg['chat']['id'], "1d20: 20")

        #prohibit
        elif re.search('Бот, запрети .+', msg['text'], re.I):
            text = re.findall('запрети (.+)', msg['text'], re.I)[0].rstrip()
            if text.endswith('.') :
                text = text[:-1]
            cur2.execute('SELECT orders FROM Orders')
            result = False
            for row in cur2:
                if str(row[0].lower()) == text.lower():
                    result = True
            cur2.execute('SELECT orders FROM Orders WHERE orders = ?', (text,))
            if (re.search('запрети|разреши', text, re.I)):
                bot.sendMessage(chat_id, "Петрович, заебал.")
            elif (cur2.fetchone() is None and not result):
                if (check_balance(msg) > 0):
                    spend_fish(msg, 1)
                    bot.sendMessage(msg['chat']['id'], "Рыба бьёт тебя хвостом и вырывается на волю.")
                    cur2.execute('INSERT INTO Orders (orders) VALUES (?)', (text,))
                    bot.sendMessage(chat_id, "Запрещаю " + text + ".")
                    conn2.commit()
                else:
                    bot.sendMessage(msg['chat']['id'], "У тебя нет рыбы для этого.")
            else:
                bot.sendMessage(chat_id, "Такой запрет уже в силе.")

        #allow
        elif re.search('Бот, разреши .+', msg['text'], re.I):
            text = re.findall('разреши (.+)', msg['text'], re.I)[0].rstrip()
            if text.endswith('.') :
                text = text[:-1]
            cur2.execute('SELECT orders FROM Orders')
            result = False
            tempstr = ""
            for row in cur2:
                if str(row[0].lower()) == text.lower():
                    result = True
                    tempstr = row[0]
            cur2.execute('SELECT orders FROM Orders WHERE orders = ?', (text,))
            if (re.search('запрети|разреши', text, re.I)):
                bot.sendMessage(chat_id, "Петрович, заебал.")
            elif (cur2.fetchone() is not None or result):
                if (check_balance(msg) > 0):
                    spend_fish(msg, 1)
                    bot.sendMessage(msg['chat']['id'], "Рыба бьёт тебя хвостом и вырывается на волю.")
                    if (result):
                        cur2.execute('DELETE FROM Orders WHERE orders = ?', (tempstr,))
                        bot.sendMessage(chat_id, "Разрешаю " + tempstr + ".")
                    else:
                        cur2.execute('DELETE FROM Orders WHERE orders = ?', (text,))
                        bot.sendMessage(chat_id, "Разрешаю " + text + ".")
                else:
                    bot.sendMessage(msg['chat']['id'], "У тебя нет рыбы для этого.")
            else:
                bot.sendMessage(chat_id, "Такого запрета нет.")

        #disallowed
        elif re.search('Бот, ', msg['text'], re.I) and re.search("запрет(ы|ов|ам)", msg['text'], re.I):
            cur2.execute('SELECT orders FROM Orders')
            if (cur2.fetchone() is None):
                bot.sendMessage(chat_id, "На данный момент на территории Острова не действует никаких запретов.")
            else:
                cur2.execute('SELECT orders FROM Orders')
                tempStr = "На территории Острова строго запретили:\n\n"
                for row in cur2:
                    stri = str(row[0])
                    stri = stri[0].upper() + stri[1:]
                    tempStr = tempStr + stri.rstrip() + ";\n"
                tempStr = tempStr.rstrip()
                tempStr = tempStr[:-1] + "."
                bot.sendMessage(chat_id, tempStr)

        #roll dice
        elif re.match('/roll ', msg['text'], re.I) and len(re.findall('[0-9+][dд][0-9+]', msg['text'])) == 1 :
            instr = re.findall('[0-9]+[дd][0-9]+', msg['text'])[0]
            num = int(re.findall('([0-9]+)[дd]', instr)[0])
            dice = int(re.findall('[дd]([0-9]+)', instr)[0])
            if (num > 100) :
                bot.sendMessage(chat_id, "Слишком много кубиков, лень.")
            elif (num == 0 or dice == 0) :
                bot.sendMessage(chat_id, "Я тебе буквами скажу: ноль.")
            elif (dice > 100) :
                bot.sendMessage(chat_id, "Это уже шарики, а не кубики, сорян.")
            else :
                summ = 0
                for count in range(num):
                    summ = summ + random.randrange(dice) + 1
                if len(re.findall('\+[0-9]+', msg['text'])) == 1 :
                    mod = int(re.findall('\+[0-9]+', msg['text'])[0])
                    summ = summ + mod
                    bot.sendMessage(chat_id, str(num) + "d" + str(dice) + " +" + str(mod) + ": " + str(summ))
                else :
                    bot.sendMessage(chat_id, str(num) + "d" + str(dice) + ": " + str(summ))

        #generate character
        elif re.match('Бот, сгенерируй', msg['text'], re.I) :
            bot.sendMessage(chat_id, "Сила: " + str(random.randrange(10) + 1) + "\nЛовкость: " + str(random.randrange(10) + 1) + "\nИнтеллект: " + str(random.randrange(10) + 1) + "\nХаризма: " + str(random.randrange(10) + 1) + "\nТелосложение: " + str(random.randrange(10) + 1) + "\nОмерзительность: " + str(random.randrange(10) + 1))

        #tellbot
        elif msg['chat']['id'] != -1001246713784 and re.match('Бот, скажи', msg['text'], re.I) and len(re.findall('\"', msg['text'])) == 2 :
            message = re.findall(r'\"(.+)\"', msg['text'])
            if len(re.findall("\*", msg['text'])) > 0 :
                bot.sendMessage(chat_id, "Пожалуйста, не используйте звёздочки.", "Markdown")
            else :
                bot.sendMessage(-1001246713784, "*" + message[0] + "*", "Markdown")

        #default
        elif re.match('Бот,', msg['text'], re.I):
            randstring = random.choice(["CAADAgADFgAD1L_qBCuBbCv6w1PhAg", "CAADAgADGAAD1L_qBNsikKLAu_2eAg", "CAADAgADJgAD1L_qBI-iJL-j9LA5Ag", "CAADAgADLAAD1L_qBAKXEdvEO1_cAg"])
            bot.sendSticker(chat_id, randstring)

    if msg['chat']['id'] == -1001246713784:
        countTemp = 0
        cur2.execute('SELECT fishCount FROM FishTable')
        for row in cur2:
            countTemp = countTemp + row[0]
        rand = random.randint(0, 10 + 10 * countTemp)
        if rand == 0:
            time.sleep(random.randint(5,10))
            spawn_fish(msg)

    if msg['chat']['id'] == 330727801:
        pprint(msg)

def update_users(msg):
    cur2.execute('SELECT username FROM FishTable WHERE userid = ?', (msg['from']['id'], ))
    try:
        username = cur2.fetchone()[0]
        if (msg['from']['username'] != username):
            cur2.execute('UPDATE FishTable SET username = ? WHERE userid = ?', (username, msg['from']['id']))
    except:
        cur2.execute('INSERT INTO FishTable (username, userid, fishCount) VALUES (?, ?, ?)', (msg['from']['username'], msg['from']['id'], 0))
        conn2.commit()

def check_balance(msg):
    cur2.execute('SELECT fishCount FROM FishTable WHERE userid = ?', (msg['from']['id'], ))
    return cur2.fetchone()[0]

def spend_fish(msg, amount):
    cur2.execute('SELECT fishCount FROM FishTable WHERE userid = ?', (msg['from']['id'], ))
    count = cur2.fetchone()[0]
    if (count - amount >= 0) :
        cur2.execute('UPDATE FishTable SET fishCount = ? WHERE userid = ?', (count - amount, msg['from']['id']))
    else :
        bot.sendMessage(msg['chat']['id'], "Ошибочная операция.")
    conn2.commit()

def spawn_fish(msg):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
           [InlineKeyboardButton(text='Словить!', callback_data= "fish_" + str(msg['message_id']))],
       ])
    newmsg = bot.sendMessage(msg['chat']['id'], "Рыба прыгает из воды, лови скорее!", reply_markup = keyboard)
    cur2.execute('INSERT INTO FishOccurence (origmsg, chatid, msgid, status) VALUES (?, ?, ?, ?)', (msg['message_id'], newmsg['chat']['id'], newmsg['message_id'], "Free"))
    conn2.commit()

def username_to_id(username):
    cur2.execute('SELECT userid FROM FishTable WHERE username = ?', (username, ))
    return cur2.fetchone()[0]

def add_fish(msg, amount):
    cur2.execute('SELECT fishCount FROM FishTable WHERE userid = ?', (msg['from']['id'], ))
    count = cur2.fetchone()[0]
    cur2.execute('UPDATE FishTable SET fishCount = ? WHERE userid = ?', (count + amount, msg['from']['id']))
    conn2.commit()

def add_fish_by_id(userid, amount):
    cur2.execute('SELECT fishCount FROM FishTable WHERE userid = ?', (userid, ))
    count = cur2.fetchone()[0]
    cur2.execute('UPDATE FishTable SET fishCount = ? WHERE userid = ?', (count + amount, userid))
    conn2.commit()

def on_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')

    if re.match('fish_', query_data, re.I):
        msgnum = re.findall('fish_(.+)', query_data)[0]
        cur2.execute('SELECT status, chatid, msgid FROM FishOccurence WHERE origmsg = ?', (msgnum, ))
        msg_data = cur2.fetchone()
        if re.match("Free", msg_data[0]):
            cur2.execute('UPDATE FishOccurence SET status = ? WHERE origmsg = ?', ("Caught", msgnum))
            conn2.commit()
            bot.answerCallbackQuery(query_id, text='Рыбка твоя!')
            add_fish_by_id(from_id, 1)
            bot.editMessageText((msg_data[1], msg_data[2]), "Рыба поймана.")

MessageLoop(bot, {'chat' : handle, 'callback_query' : on_callback_query} ).run_as_thread()

print("Listening...")

while 1:
    time.sleep(10)
