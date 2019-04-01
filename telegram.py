import json, requests, time, urllib.parse
import sys, traceback, random, hashlib
import database as db
import codeforces as cf
import util
import bot

requestUrl = ''
lastUpdateID = -1

#------ Main part with bot API access ------

def readRequestUrl():
  global requestUrl
  requestUrl = [line.rstrip('\n') for line in open('.telegram_api_url')][0]

def poll():
  try:
    r = requests.get(requestUrl + 'getUpdates?offset=' + str(lastUpdateID+1))
    r = r.json()
  except Exception as e:
    traceback.print_exc()
    return []
  if r['ok']:
    return r['result']
  else:
    return []

def sendAnswerCallback(callback_query_id, text = ""):
  params = {
    'callback_query_id':callback_query_id,
    'text':text
  }
  try:
    r = requests.post(requestUrl + 'answerCallbackQuery', data=params)
    r = r.json()
  except Exception as e:
    traceback.print_exc()

def sendMessage(chatId, text, reply_markup = None):
  params = {
  'parse_mode':'Markdown',
  'chat_id':str(chatId),
  'text':text,
  'reply_markup': reply_markup
  }
  try:
    r = requests.post(requestUrl + 'sendMessage', data=params)
    r = r.json()
    if r['ok']:
      return r['result']['message_id']
    else:
      log('fehler beim senden der Nachricht: ' + r['description'])
      return False
  except Exception as e:
    traceback.print_exc()
    return False

def editMessageReplyMarkup(chatId, msgId, reply_markup):
  params = {
    'chat_id':str(chatId),
    'message_id': str(msgId),
    'reply_markup': reply_markup
  }
  try:
    r = requests.post(requestUrl + 'editMessageReplyMarkup', data=params)
    r = r.json()
  except Exception as e:
    traceback.print_exc()

def editMessageText(chatId, msgId, msg):
  #TODO escape msg???
  #util.log("editMessageText: " + str(chatId) + " " + str(msg))
  params = {
    'parse_mode':'Markdown',
    'chat_id':str(chatId),
    'message_id':str(msgId),
    'text':msg
  }
  url = requestUrl + 'editMessageText'
  try:
    r = requests.post(url, data=params)
    r = r.json()
    if not r['ok']:
      print("fehler beim editieren einer Nachricht:", r['description'])
  except Exception as e:
    traceback.print_exc()

def startPolling():
  curUpd = poll()
  for u in curUpd:
    handleUpdate(u)

def handleUpdate(update):
  global lastUpdateID
  lastUpdateID = update['update_id']
  if 'message' in update:
    bot.handleMessage(update['message']['chat']['id'], update['message']['text'])
  elif 'edited_message' in update:
    bot.handleMessage(update['edited_message']['chat']['id'], update['edited_message']['text'])
  elif 'callback_query' in update:
    #sendAnswerCallback(update['callback_query']['id'])
    bot.handleCallbackQuery(update['callback_query'])
