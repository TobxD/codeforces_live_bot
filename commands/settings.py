import json
from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from commands import bot
from telegram import Chat
from commands import setup, notification_settings as notify_settings, chat_settings, widthSelector

def handleSettings(chat, req):
	bot.setOpenCommandFunc(chat.chatId, None)
	buttons = getSettingsButtons()
	replyMarkup = getReplyMarkup(buttons)
	chat.sendMessage("What do you want to change?", replyMarkup)

def getReplyMarkup(inlineKeyboard):
	replyMarkup = {"inline_keyboard": inlineKeyboard}
	jsonReply = json.dumps(replyMarkup)
	return jsonReply

def getSettingsButtons():
	buttons = [
		[{"text": "Setup",																	"callback_data": "setup:"}],
		[{"text": "Chat Settings",													"callback_data": "chat:"}],
		[{"text": "Friend Notification settings",						"callback_data": "friend_notf:"}],
	]
	return buttons

def handleCallbackQuery(callback):
	chat = Chat.getChat(str(callback['message']['chat']['id']))
	data = callback['data']

	if not ":" in data:
		logger.critical("Invalid callback data: " + data)
		return

	pref, suff = data.split(":", 1)
	funs = {
		"settings": handleSettingsCallback,
		"setup": setup.handleSetupCallback,
		"chat": chat_settings.handleChatCallback,
		"friend_notf": notify_settings.handleFriendNotSettingsCallback,
		"width": widthSelector.handleWidthChange,
	}
	if pref not in funs:
		logger.critical("Invalid callback prefix: "+ pref + ", data: "+ suff)
	else:
		funs[pref](chat, suff, callback)
		tg.sendAnswerCallback(chat.chatId, callback['id'])

def handleSettingsCallback(chat, data, callback):
	if data != "":
		logger.critical("Invalid callback prefix: "+ pref + ", data: "+ data)
	else:
		chat.editMessageText(callback['message']['message_id'], "What do you want to change?", getReplyMarkup(getSettingsButtons()))
