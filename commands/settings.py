import json
from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from commands import bot
from telegram import Chat
from commands import general_settings, notification_settings as notify_settings, behavior_settings, widthSelector

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
		[{"text": "General Settings",							"callback_data": "general:"}],
		[{"text": "Behavior Settings",						"callback_data": "behavior:"}],
		[{"text": "Friend Notification Settings",	"callback_data": "friend_notf:"}],
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
		"general": general_settings.handleSetupCallback,
		"behavior": behavior_settings.handleChatCallback,
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
		logger.critical("Invalid callback settings data: " + data)
	else:
		chat.editMessageText(callback['message']['message_id'], "What do you want to change?", getReplyMarkup(getSettingsButtons()))
