#!/usr/bin/python3.6
# -*- coding: utf-8 -*-
import telebot
import os
import requests
import wget
import configparser
import json
from emoji import emojize
from urllib.error import HTTPError

config = configparser.ConfigParser()
config.read('config.ini')

telebot.apihelper.proxy = {'https': config.get('connection', 'proxyConnSting')}
bot = telebot.TeleBot(config.get('connection', 'teleToken'))
apiString = ':5000/api/v2.0/'
CURSTAND = ''
tab = '        '
commandTypes = {'get': '', 'getOpts': 'get=', 'getTests': 'get=', 'getFile': 'get=', 'setBin': 'set=', 'setInt': 'set='}
sequense = {'/current': '/current', '/check': '/check', '/startApp': '/startApp', '/stopApp': '/stopApp',
            '/AppStatus': '/AppStatus', '/AutoDeployStatus': '/AutoDeployStatus',
            '/setAutoDeployStatus': '/setAutoDeployStatus', '/setAutoDeployPeriod': '/setAutoDeployPeriod',
            '/update': '/update', '/containers': '/containerInfo', '/containerInfo': '/download',
            '/download': '/download', '/autoTests': '/runTest', '/runAllTests': '/runAllTests',
            '/runTest': '/getTestReport'}
binary = {'True': 'true', 'False': 'false'}


def getStands():
    stands = json.loads(config.get('api', 'stands'))
    return stands


def checkFirstLastNames(message):
    for it in json.loads(config.get('bot', 'allowNames')).items():
        if list(it) == [message.from_user.last_name, message.from_user.first_name]:
            return True
    return False


def checkUsers(message):
    if message.from_user.username in json.loads(config.get('bot', 'allowUsernames')):
        return True
    if checkFirstLastNames(message):
        return True
    else:
        return False


def wrongUser():
    photo = open('noenter.jpg', 'rb')
    return photo


@bot.message_handler(commands=['start'])
def start_message(message):
    if checkUsers(message):
        bot.send_message(message.chat.id, 'Этот бот предназначен для управления и обновления стендов ИСТО',
                         reply_markup=startKeyboard())


#    else:
#        bot.send_photo(message.chat.id, wrongUser())

@bot.message_handler(commands=['setAutoDeployPeriod'])
def setPeriod(message):
    msg_text = message.text.split(maxsplit=1)[1]
    command = '/setAutoDeployPeriod'
    bot.send_message(message.chat.id,
                     command.replace('/', '') + ':\n' + parseAnswer(
                         runCommand(
                             '{command}?{commandType}{value}'.format(command=command,
                                                                     commandType=commandTypes['setInteger'],
                                                                     value=msg_text),
                             CURSTAND)),
                     parse_mode='Markdown',
                     reply_markup=inlineKeyBoardBack())


def startKeyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    stands = telebot.types.KeyboardButton('Серверы')
    markup.add(stands)
    return markup


@bot.message_handler(content_types=['document'])
def sendTestFile(message):
    if message.document:
        fileName = message.document.file_name
        if '.feature' in fileName:
            if CURSTAND:
                # file_id = message.document.file_name
                file_id_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_id_info.file_path)
                with open(fileName, 'wb') as new_file:
                    new_file.write(downloaded_file)
                bot.send_message(message.chat.id, 'Файл получен')
                bot.send_message(message.chat.id, 'Направляю на {}'.format(CURSTAND))
                with open('./{}'.format(fileName), 'rb') as file:
                    url = 'http://{url}{apiStr}tasks/uploadTestFile'.format(url=getStands()[CURSTAND], apiStr=apiString)
                    files = {
                        'file': ('./{}'.format(fileName), file),
                    }
                    # headers = {'enctype': 'multipart/form-data'}
                    # print(url)
                    # resp = requests.post(url, headers=headers, data={"file": '@./{}'.format(fileName)})
                    resp = requests.post(url, files=files)

                    print(resp.text)
                os.remove(fileName)


            else:
                bot.send_message(message.chat.id, 'Необходимо выбрать стенд и попробовать еще раз',
                                 reply_markup=startKeyboard())
        else:
            bot.send_message(message.chat.id, 'Я принимаю только файлы с расширением \'.feature\'')


@bot.message_handler(content_types=['text'])
def talk(message):
    if checkUsers(message):
        if message.text.lower() == 'серверы':
            bot.send_message(message.chat.id, "Серверы:", reply_markup=inlineKeyboardStands(getStands()))


@bot.callback_query_handler(func=lambda call: True)
def answer(call):
    try:
        global CURSTAND
        bot.answer_callback_query(callback_query_id=call.id)

        # if not CURSTAND:
        #     bot.send_message(call.message.chat.id, 'Необходимо выбрать стенд',
        #                      reply_markup=startKeyboard())
        if 'stand' in call.data:
            # 'stand' in call.data:
            CURSTAND = call.data.split('_')[1]
            # print(CURSTAND)
            methods = getMethods(CURSTAND)
            if len(methods) > 0:
                bot.send_message(call.message.chat.id, "Доступные методы:",
                                 reply_markup=inlineKeyboardMethods(getMethods(CURSTAND)))
            else:
                bot.send_message(call.message.chat.id, "API недоступно")
        if 'help' in call.data:
            if 'test' in call.data:
                pos = call.data.split('_')[2]
                bot.send_message(call.message.chat.id,
                                 runCommand('/getTestInfo?get=' + pos, CURSTAND),
                                 # parse_mode='Markdown',
                                 reply_markup=inlineKeyBoardBack())
            pos = call.data.split('_')[1]
            for item in getMethods(CURSTAND):
                if item['id'] == pos:
                    bot.send_message(call.message.chat.id, item['title'], reply_markup=inlineKeyBoardBack())

        if 'command' in call.data:
            commandType = call.data.split('_')[1]
            command = call.data.split('_')[2]
            if commandType == 'get':
                method = command.split('?')[0]
                if method == sequense[method]:
                    answer = runCommand(command, CURSTAND)
                    parsedAnswer = parseAnswer(answer)
                    bot.send_message(call.message.chat.id,
                                     command.replace('/', '') + ':\n' + parsedAnswer,
                                     # parse_mode='Markdown',
                                     reply_markup=inlineKeyBoardBack())
                else:
                    if getMethodInfo(CURSTAND, sequense[method])['type'] == 'getFile':
                        bot.send_message(call.message.chat.id,
                                         command.replace('/', '') + ':\n' + parseAnswer(runCommand(command, CURSTAND)),
                                         reply_markup=inlineKeyboardDownload(sequense[method], command.split('?')[1])
                                         )
            if commandType == 'getTestReport':
                method = command.split('?')[0]
                message = bot.send_message(call.message.chat.id, 'Тесты выполняются...')
                answer = command.replace('/', '') + ':\n' + parseTestReport(runCommand(command, CURSTAND))
                if answer:
                    bot.delete_message(message_id=message.message_id, chat_id=call.message.chat.id)
                    bot.send_message(call.message.chat.id, answer,
                                     reply_markup=inlineKeyboardDownload(sequense[method], command.split('?')[1]))

            if commandType == 'setBin':
                bot.send_message(call.message.chat.id,
                                 "Доступные опции: {command}".format(command=command.replace('/', '')),
                                 reply_markup=inlineKeyboardOptions(command, commandType, binary))
            if commandType == 'getOpts':
                command = command.split('?')[0]
                bot.send_message(call.message.chat.id,
                                 "Доступные опции: {command}".format(command=command.replace('/', '')),
                                 reply_markup=inlineKeyboardOptions(command, commandType,
                                                                    runCommand(command, CURSTAND)))
            if commandType == 'getTests':
                command = command.split('?')[0]
                bot.send_message(call.message.chat.id,
                                 "Доступные тесты: {command}".format(command=command.replace('/', '')),
                                 reply_markup=inlineKeyboardTests(command, commandType,
                                                                  runCommand(command, CURSTAND)))
            if commandType == 'setInt':
                bot.send_message(call.message.chat.id,
                                 'Set value by keyboard:\n{command} X, where X in minutes'.format(command=command),
                                 reply_markup=inlineKeyBoardBack())
            if commandType == 'getFile':
                name = getFile(command, CURSTAND)
                print(name)
                if isinstance(name, str):
                    size = os.stat(name).st_size
                    with open(name, 'rb') as file:
                        if size > 0:
                            bot.send_document(call.message.chat.id, open(name, 'r'), reply_markup=inlineKeyBoardBack())
                        else:
                            bot.send_message(call.message.chat.id,
                                             'Файл логов пуст',
                                             reply_markup=inlineKeyBoardBack())
                    os.remove(name)
                else:
                    bot.send_message(call.message.chat.id,
                                     parseAnswer(name),
                                     reply_markup=inlineKeyBoardBack())

        if 'back' in call.data:
            bot.delete_message(message_id=call.message.message_id, chat_id=call.message.chat.id)
    except KeyError:
        bot.send_message(call.message.chat.id, 'Необходимо выбрать стенд',
                         reply_markup=startKeyboard())


def bolding(text):
    return "*" + text + "*"


def getMethods(stand):
    try:
        response = requests.get('http://' + getStands()[stand] + apiString + 'tasks', verify=False, timeout=2)
        return response.json()
    except requests.exceptions.ConnectTimeout:
        return []


def getMethodInfo(stand, method):
    response = requests.get('http://' + getStands()[stand] + apiString + 'tasks')
    for item in response.json():
        command = (item['id'][item['id'].rfind('/'):])
        if command == method:
            return item


def runCommand(command, stand):
    callString = ('http://' + getStands()[stand] + apiString + 'tasks' + command)
    response = requests.get(callString)
    if response.status_code == 200:
        return response.json()
    else:
        return {'Error': response.status_code}


def getFile(params, stand):
    callString = ('http://' + getStands()[stand] + apiString + 'tasks' + params)
    # id = params.split('=')[0]
    # fileName = id + ":" + (
    # datetime.datetime.strftime(datetime.datetime.today(), "%d%m%Y-%H%M%S")) + '.log'
    try:
        name = wget.download(callString, '')
        return name
    except HTTPError as e:
        return {'Error': e.read()}


def findDescr(id, file):
    for item in file:
        if id == item['id']:
            return file['title']


def parseAnswer(file):
    retString = ''
    for item in file:
        value = file[item]
        retString += str(item + ': ' + str(value) + '\n')
    return retString


def parseTestReport(file):
    retString = ''
    for dct in file:
        if isinstance(dct, dict):
            for item in dct:
                if not item == "Scenarios":
                    retString = retString + str(item + ': ' + dct[item])
                if item == "Scenarios":
                    for key, value in dict(dct[item]).items():
                        retString = retString + '\n' + str(tab + key + ': ' + value)
        retString = retString.replace('passed', '\U00002705').replace('failed', '\U0000274C')
        return retString


def inlineKeyboardStands(dct):
    inlineKeys = telebot.types.InlineKeyboardMarkup()
    for stand, adr in dct.items():
        status = checkAPIStatus(adr)
        inlineKeys.add(
            telebot.types.InlineKeyboardButton(text=stand,
                                               callback_data='stand_{}'.format(stand))
            , telebot.types.InlineKeyboardButton(text=status, callback_data='stand_{}'.format(stand))
        )
    return inlineKeys


def checkAPIStatus(address):
    callString = 'http://' + address + apiString
    try:
        response = requests.get(callString, verify=False, timeout=2)
        return "\U0001F7E2"
        # return 'Online'
    except requests.exceptions.ConnectTimeout:
        return "\U0001F534"
        # return 'Offline'


def inlineKeyboardMethods(dct):
    inlineKeys = telebot.types.InlineKeyboardMarkup()
    for item in dct:
        if item['showTask']:
            command = (item['id'][item['id'].rfind('/'):])
            commandType = (item['type'])
            inlineKeys.add(
                telebot.types.InlineKeyboardButton(text=command,
                                                   callback_data='command_{commandType}_{command}'.format(
                                                       commandType=commandType,
                                                       command=command)),
                telebot.types.InlineKeyboardButton(text='help',
                                                   callback_data=str('help_{}'.format(item['id']))))
    inlineKeys.add(telebot.types.InlineKeyboardButton(text='<- Back', callback_data='back'))
    return inlineKeys


def inlineKeyboardOptions(command, commandType, options):
    callMethod = commandTypes[commandType]
    inlineKeys = telebot.types.InlineKeyboardMarkup()
    if len(command.split('?')) > 1:
        command = command.split('?')[0]
        command = sequense[command]
    else:
        command = sequense[command]
    commandType = getMethodInfo(CURSTAND, command)['type']
    for option in options.keys():
        callString = 'command_{commandType}_{command}?{callMethod}{option}'.format(
            commandType=commandType,
            callMethod=callMethod,
            command=command,
            option=options[option])
        inlineKeys.add(
            telebot.types.InlineKeyboardButton(text=option,
                                               callback_data=callString))
    inlineKeys.add(telebot.types.InlineKeyboardButton(text='<- Back', callback_data='back'))
    return inlineKeys


def inlineKeyboardTests(command, commandType, options):
    inlineKeys = telebot.types.InlineKeyboardMarkup()
    # inlineKeys.add(
    #     telebot.types.InlineKeyboardButton(text='Запустить все тесты',
    #                                        callback_data='command_getTestReport_/runAllTests'))
    if len(command.split('?')) > 1:
        command = command.split('?')[0]
        command = sequense[command]
    else:
        command = sequense[command]
    callMethod = commandTypes[commandType]
    commandType = getMethodInfo(CURSTAND, command)['type']
    for test, description in options.items():
        callString = 'command_{commandType}_{command}?{callMethod}{option}'.format(
            commandType=commandType,
            callMethod=callMethod,
            command=command,
            option=test)

        inlineKeys.add(telebot.types.InlineKeyboardButton(text=test, callback_data=callString),
                       telebot.types.InlineKeyboardButton(text='help',
                                                          callback_data=str(
                                                              'help_test_{test}'.format(test=test))))
    inlineKeys.add(telebot.types.InlineKeyboardButton(text='<- Back', callback_data='back'))
    return inlineKeys


def inlineKeyboardDownload(method, parameter):
    inlineKeys = telebot.types.InlineKeyboardMarkup()
    callString = str('command_getFile_' + method + '?' + parameter)
    inlineKeys.add(telebot.types.InlineKeyboardButton(text=method, callback_data=callString),
                   telebot.types.InlineKeyboardButton(text='help',
                                                      callback_data=str('help_/api/v2.0/tasks{}'.format(method))))
    inlineKeys.add(telebot.types.InlineKeyboardButton(text='<- Back', callback_data='back'))
    return inlineKeys


def inlineKeyBoardBack():
    inlineKeys = telebot.types.InlineKeyboardMarkup()
    inlineKeys.add(telebot.types.InlineKeyboardButton(text='<- Back', callback_data='back'))
    return inlineKeys


if __name__ == '__main__':
    bot.polling(none_stop=True)

# bot.polling()
