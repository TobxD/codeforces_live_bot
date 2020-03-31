import json, requests, time, urllib.parse
import sys, traceback, random, hashlib, queue
import database as db
import codeforces as cf
import util
import bot
import UpdateService
import settings
import Chat
from util import logger

requestUrl = ""
testFlag = False

endTimes = queue.Queue() # 30 msg per second to telegram
for i in range(30):
	endTimes.put(-1)

#------ Main part with bot API access ------
# wrap this method to ensure timing
def requestPost(chatId, url, **kwargs):
	if testFlag:
		logger.info("telegram object that would have been sent: " + str(kwargs))
		r = {'ok':True, 'result':{'message_id':0}}
		return r
	waitTime = endTimes.get() + 1 - time.time()
	if waitTime > 0:
		time.sleep(waitTime)
	try:
		r = requests.post(url, **kwargs)
		r = r.json()
		if r['ok']:
			return r
		else:
			#only print if error not handled yet
			if not handleRequestError(chatId, r):
				logger.critical('Failed to request telegram with message: ' + str(kwargs))
			return False
	except requests.Timeout as e:
		logger.error('Timeout at telegram request with message: ' + str(kwargs))
		return False
	except Exception as e:
		logger.critical('Failed to request telegram with message: ' + str(kwargs) + '\nexception: %s', e, exc_info=True)
		return False
	finally:
		endTimes.put(time.time())

#returns if error could be handled
def handleRequestError(chatId, req):
	errMsg = req['description']
	if (errMsg == "Forbidden: bot was blocked by the user" or
		 errMsg == "Forbidden: bot was kicked from the group chat" or
		 errMsg == "Bad Request: chat not found" or
		 errMsg == "Forbidden: user is deactivated" or
		 errMsg == "Forbidden: bot can't initiate conversation with a user"):
		db.deleteUser(chatId)
		return True
	elif errMsg == "Bad Request: group chat was upgraded to a supergroup chat":
		Chat.getChat(chatId).chatId = req['parameters']['migrate_to_chat_id']
		return True
	else:
		return False

def shortenMessage(text):
	if len(text) > 4000: # Telegram doesn't allow longer messages
		cutof = text[4000:]
		text = text[:4000]
		if cutof.count("```") % 2 == 1:
			text += "```"
		text += "…"
	return text

def sendAnswerCallback(chatId, callback_query_id, text = ""):
	params = {
		'callback_query_id':callback_query_id,
		'text':text
	}
	requestPost(chatId, requestUrl + 'answerCallbackQuery', data=params, timeout=5)

def sendMessage(chatId, text, reply_markup = None):
	text = shortenMessage(text)
	if chatId == '0':
		print('message sent: ' + text + "\n -------- End Message ----------")
		return 1
	params = {
	'parse_mode':'Markdown',
	'chat_id':str(chatId),
	'text':text,
	'reply_markup': reply_markup
	}
	r = requestPost(chatId, requestUrl + 'sendMessage', data=params, timeout=5)
	if r:
		return r['result']['message_id']
	else:
		return False

def editMessageReplyMarkup(chatId, msgId, reply_markup):
	params = {
		'chat_id':str(chatId),
		'message_id': str(msgId),
		'reply_markup': reply_markup
	}
	requestPost(chatId, requestUrl + 'editMessageReplyMarkup', data=params, timeout=5)

def editMessageText(chatId, msgId, msg):
	msg = shortenMessage(msg)
	if chatId == '0':
		print(str(msgId) + ' edited to: ' + msg + "\n -------- End Message ----------")
		return
	params = {
		'parse_mode':'Markdown',
		'chat_id':str(chatId),
		'message_id':str(msgId),
		'text':msg
	}
	url = requestUrl + 'editMessageText'
	requestPost(chatId, url, data=params, timeout=5)

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
			logger.error("Timeout on Telegram polling.")
			return []
		except Exception as e:
			logger.critical("Error on Telegram polling: " + str(e))
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
				logger.debug("no text in message: " + str(update['message']))
		elif 'edited_message' in update:
			bot.handleMessage(Chat.getChat(str(update['edited_message']['chat']['id'])), update['edited_message']['text'])
		elif 'callback_query' in update:
			settings.handleCallbackQuery(update['callback_query'])
	
	def _doTask(self):
		curUpd = self._poll()
		for u in curUpd:
			self._handleUpdate(u)
