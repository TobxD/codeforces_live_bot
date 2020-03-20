import json, requests, time, urllib.parse
import sys, traceback, random, hashlib, queue
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

endTimes = queue.Queue() # 30 msg per second to telegram
for i in range(30):
	endTimes.put(-1)

#------ Main part with bot API access ------
# wrap this method to ensure timing
def requestPost(url, **kwargs):
	waitTime = endTimes.get() + 1 - time.time()
	if waitTime > 0:
		time.sleep(waitTime)
	try:
		return requests.post(url, **kwargs)
	except Exception as e:
		raise e
	finally:
		endTimes.put(time.time())


def sendAnswerCallback(callback_query_id, text = ""):
	params = {
		'callback_query_id':callback_query_id,
		'text':text
	}
	try:
		r = requestPost(requestUrl + 'answerCallbackQuery', data=params, timeout=5)
		r = r.json()
	except Exception as e:
		util.log(traceback.format_exc(), isError=True)
		traceback.print_exc()

def shortenMessage(text):
	if len(text) > 4000: # Telegram doesn't allow longer messages
		cutof = text[4000:]
		text = text[:4000]
		if cutof.count("```") % 2 == 1:
			text += "```"
		text += "…"
	return text

def sendMessage(chatId, text, reply_markup = None):
	text = shortenMessage(text)
	if chatId == '0':
		print('message sent: ' + text + "\n -------- End Message ----------")
		return
	# dont send msg RESTART_WAIT seconds after restart
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
		r = requestPost(requestUrl + 'sendMessage', data=params, timeout=5)
		r = r.json()
		if r['ok']:
			return r['result']['message_id']
		else:
			#only print if error not handled yet
			if not handleSendError(r['description'], chatId):
				util.log('Fehler beim senden der Nachricht: ( ' + str(text) + ' ) an chatId ' + str(chatId) + ': ' + r['description'], isError=True)
			return False
	except requests.Timeout as e:
		util.log('Timeout beim senden der Nachricht: ( ' + str(text) + ' ) an chatId ' + str(chatId), isError=True)
		return False
	except Exception as e:
		util.log('Fehler beim senden der Nachricht: ( ' + str(text) + ' ) an chatId ' + str(chatId) + '\noccurred at: ' + traceback.format_exc(), isError=True)
		return False

#returns if error could be handled
def handleSendError(errMsg, chatId):
	if (errMsg == "Forbidden: bot was blocked by the user" or
		 errMsg == "Forbidden: bot was kicked from the group chat" or
		 errMsg == "Bad Request: chat not found" or
		 errMsg == "Forbidden: user is deactivated" or
		 errMsg == "Forbidden: bot can't initiate conversation with a user"):
		db.deleteUser(chatId)
		return True
	else:
		return False

def editMessageReplyMarkup(chatId, msgId, reply_markup):
	params = {
		'chat_id':str(chatId),
		'message_id': str(msgId),
		'reply_markup': reply_markup
	}
	try:
		r = requestPost(requestUrl + 'editMessageReplyMarkup', data=params, timeout=5)
		r = r.json()
		if not r['ok']:
			print("Failed to edit reply markup: ", r['description'])
	except Exception as e:
		traceback.print_exc()
		util.log(traceback.format_exc(), isError=True)

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
		r = requestPost(url, data=params, timeout=5)
		r = r.json()
		if not r['ok']:
			print("fehler beim editieren einer Nachricht:", r['description'])
	except requests.exceptions.Timeout as errt:
		util.log("Timeout on edit message text (" + str(msg) + ") to chatId: " + str(chatId), isError=True)
	except Exception as e:
		traceback.print_exc()
		util.log(traceback.format_exc(), isError=True)

class TelegramUpdateService (UpdateService.UpdateService):
	def __init__(self):
		global requestUrl
		UpdateService.UpdateService.__init__(self, 1)
		self.name = "telegramService"
		requestUrl = [line.rstrip('\n') for line in open('.telegram_api_url')][0]
		self._lastUpdateID = -1

	def _poll(self):
		try:
			t = 10
			r = requests.get(requestUrl + 'getUpdates?offset=' + str(self._lastUpdateID + 1) + ';timeout=' + str(t), timeout=2*t)
			r = r.json()
		except requests.exceptions.Timeout as errt:
			util.log("Timeout on Telegram polling.", isError=True)
			return []
		except Exception as e:
			util.log("Error on Telegram polling: " + str(e), True)
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
				util.log("no text in message: " + str(update['message']))
		elif 'edited_message' in update:
			bot.handleMessage(Chat.getChat(str(update['edited_message']['chat']['id'])), update['edited_message']['text'])
		elif 'callback_query' in update:
			#sendAnswerCallback(update['callback_query']['id'])
			settings.handleCallbackQuery(update['callback_query'])
	
	def _doTask(self):
		curUpd = self._poll()
		for u in curUpd:
			self._handleUpdate(u)
