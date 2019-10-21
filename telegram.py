import json, requests, time, urllib.parse
import sys, traceback, random, hashlib
import database as db
import codeforces as cf
import util
import bot
import UpdateService
import settings
import Chat

requestUrl = ""
RESTART = 0
RESTART_WAIT = 600
#------ Main part with bot API access ------

def sendAnswerCallback(callback_query_id, text = ""):
	params = {
		'callback_query_id':callback_query_id,
		'text':text
	}
	try:
		r = requests.post(requestUrl + 'answerCallbackQuery', data=params, timeout=5)
		r = r.json()
	except Exception as e:
		util.log(traceback.format_exc())
		traceback.print_exc()

def sendMessage(chatId, text, reply_markup = None):
	if chatId == '0':
		print('message sent: ' + text + "\n -------- End Message ----------")
		return
	# dont send msg 100sec after restart
	if time.time() - RESTART < RESTART_WAIT:
		util.log("message that would have been sent to chat " + str(chatId) + ": \n" + str(text))
		return
	params = {
	'parse_mode':'Markdown',
	'chat_id':str(chatId),
	'text':text,
	'reply_markup': reply_markup
	}
	try:
		r = requests.post(requestUrl + 'sendMessage', data=params, timeout=5)
		r = r.json()
		if r['ok']:
			return r['result']['message_id']
		else:
			util.log('!!!!!Fehler beim senden der Nachricht: ' + r['description']+ " !!!!!")
			return False
	except Exception as e:
		traceback.print_exc()
		util.log(traceback.format_exc())
		return False

def editMessageReplyMarkup(chatId, msgId, reply_markup):
	params = {
		'chat_id':str(chatId),
		'message_id': str(msgId),
		'reply_markup': reply_markup
	}
	try:
		r = requests.post(requestUrl + 'editMessageReplyMarkup', data=params, timeout=5)
		r = r.json()
	except Exception as e:
		traceback.print_exc()
		util.log(traceback.format_exc())

def editMessageText(chatId, msgId, msg):
	#TODO escape msg???
	#util.log("editMessageText: " + str(chatId) + " " + str(msg))
	if chatId == '0':
		print(str(msgId) + ' edited to: ' + msg + "\n -------- End Message ----------")
		return
	if time.time() - RESTART < RESTART_WAIT:
		util.log("message that would have been sent to chat " + str(chatId) + ": \n" + str(text))
		return
	params = {
		'parse_mode':'Markdown',
		'chat_id':str(chatId),
		'message_id':str(msgId),
		'text':msg
	}
	url = requestUrl + 'editMessageText'
	try:
		r = requests.post(url, data=params, timeout=5)
		r = r.json()
		if not r['ok']:
			print("fehler beim editieren einer Nachricht:", r['description'])
	except Exception as e:
		traceback.print_exc()
		util.log(traceback.format_exc())

class TelegramUpdateService (UpdateService.UpdateService):
	def __init__(self):
		global requestUrl
		UpdateService.UpdateService.__init__(self, 1)
		self.name = "telegramService"
		requestUrl = [line.rstrip('\n') for line in open('.telegram_api_url')][0]
		self._lastUpdateID = -1

	def _poll(self):
		try:
			r = requests.get(requestUrl + 'getUpdates?offset=' + str(self._lastUpdateID + 1), timeout=5)
			r = r.json()
		except Exception as e:
			traceback.print_exc()
			util.log(traceback.format_exc(), True)
			return []
		if r['ok']:
			return r['result']
		else:
			return []

	def _handleUpdate(self, update):
		self._lastUpdateID = update['update_id']
		if 'message' in update:
			if 'text' in update['message']:
				bot.handleMessage(Chat.getChat(str(update['message']['chat']['id'])), update['message']['text'])
			else:
				util.log("no text in message: " + str(update['message']), isError=True)
		elif 'edited_message' in update:
			bot.handleMessage(Chat.getChat(str(update['edited_message']['chat']['id'])), update['edited_message']['text'])
		elif 'callback_query' in update:
			#sendAnswerCallback(update['callback_query']['id'])
			settings.handleCallbackQuery(update['callback_query'])
	
	def _doTask(self):
		curUpd = self._poll()
		for u in curUpd:
			self._handleUpdate(u)
