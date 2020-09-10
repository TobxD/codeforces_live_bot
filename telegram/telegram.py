import requests
from collections import defaultdict

from utils import database as db
from utils.util import logger
from commands import bot, settings
from services import UpdateService
from telegram import Chat
from codeforces import standings
from utils.Spooler import Spooler

requestUrl = [line.rstrip('\n') for line in open('.telegram_api_url')][0]
testFlag = False

def requestPost(chatId, url, data, timeout=30):
	errorTxt = 'chatId: ' + str(data.get('chat_id')) + ' text:\n' + str(data.get('text'))
	if testFlag:
		logger.info("telegram object that would have been sent: " + errorTxt)
		r = {'ok':True, 'result':{'message_id':1}}
		return r
	try:
		r = requests.post(url, timeout=timeout, data=data)
		r = r.json()
		if r['ok']:
			return r
		else:
			#only print if error not handled yet
			if not handleRequestError(chatId, r):
				logger.critical('Failed to request telegram. Error: ' + r.get('description', "No description available.") + '\n' + errorTxt)
			return False
	except requests.Timeout as e:
		logger.critical('Timeout at telegram request: ' + errorTxt)
		return False
	except Exception as e:
		logger.critical('Failed to request telegram: \nexception: %s\ntext: %s', e, errorTxt, exc_info=True)
		return False

requestSpooler = Spooler(19, "telegram", timeInterval=2, priorityCount=3)


#returns whether error could be handled
def handleRequestError(chatId, req):
	errMsg = req['description']
	if (errMsg == "Forbidden: bot was blocked by the user" or
		 errMsg == "Forbidden: bot was kicked from the group chat" or
		 errMsg == "Forbidden: bot was kicked from the supergroup chat" or
		 errMsg == "Bad Request: chat not found" or
		 errMsg == "Forbidden: user is deactivated" or
		 errMsg == "Forbidden: bot can't initiate conversation with a user"):
		Chat.deleteUser(chatId)
		return True
	elif errMsg == "Bad Request: group chat was upgraded to a supergroup chat":
		Chat.getChat(chatId).chatId = req['parameters']['migrate_to_chat_id']
		return True
	elif errMsg == "Bad Request: message to edit not found":
		with standings.standingsSentLock:
			standings.standingsSent[chatId] = defaultdict()
		logger.error(f"deleted standingsSent for Chat {chatId}")
		return True
	elif (errMsg == "Bad Request: message can't be deleted for everyone"
		or errMsg == "Bad Request: message to delete not found"):
		logger.error(f"Message deletion failed for Chat {chatId}")
		return True
	elif errMsg == "Bad Request: have no rights to send a message":
		logger.error(f"No rights to send message in Chat {chatId}")
		return True
	else:
		return False

def shortenMessage(text):
	if len(text) > 4000: # Telegram doesn't allow longer messages
		cutof = text[4000:]
		text = text[:4000]
		while text[-1] == '`': 			# don't split on "```"
			cutof = text[-1] + cutof
			text = text[:-1]
		if cutof.count("```") % 2 == 1:
			text += "```"
		text += "…"
	return text

def sendAnswerCallback(chatId, callback_query_id, text = ""):
	params = {
		'callback_query_id':callback_query_id,
		'text':text
	}
	requestPost(chatId, requestUrl + 'answerCallbackQuery', params)

def sendMessage(chatId, text, reply_markup = None, callback=None):
	text = shortenMessage(text)
	logger.debug("sendMessage to " + str(chatId) + ":\n" + text + "\n\n") # TODO test
	params = {
		'parse_mode':'Markdown',
		'chat_id':str(chatId),
		'text':text,
		'reply_markup': reply_markup
	}
	res = requestPost(chatId, requestUrl + 'sendMessage', params)
	if callback:
		callback(res['result']['message_id'] if res else False)

def editMessageText(chatId, msgId, msg, reply_markup=None):
	msg = shortenMessage(msg)
	logger.debug("editMessageText to " + str(chatId) + " msgId: " + str(msgId)+":\n" + msg + "\n\n") # TODO test
	params = {
		'parse_mode':'Markdown',
		'chat_id':str(chatId),
		'message_id':str(msgId),
		'text':msg,
		'reply_markup': reply_markup
	}
	url = requestUrl + 'editMessageText'
	requestPost(chatId, url, params)

def deleteMessage(chatId, msgId):
	logger.debug(f"deleting msg {msgId} for chat {chatId}")
	params = {
		'chat_id':str(chatId),
		'message_id':msgId,
	}
	url = requestUrl + 'deleteMessage'
	requestPost(chatId, url, params)

class TelegramUpdateService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 0.2, logPerf=False)
		self.name = "telegramService"
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
