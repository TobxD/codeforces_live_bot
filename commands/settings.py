from __future__ import annotations
import json
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from telegram.Chat import Chat

from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from commands import bot
from telegram import Chat as ChatFunctions
from commands import general_settings, notification_settings as notify_settings, behavior_settings, widthSelector



def handleSettings(chat:Chat, req):
	def deleteOldSettings(chat:Chat):
		if chat.settings_msgid:
			chat.deleteMessage(chat.settings_msgid)
			chat.settings_msgid = None
	def callbackSetMsgId(id):
		if id != False:
			chat.settings_msgid = id

	bot.setOpenCommandFunc(chat.chatId, None)
	deleteOldSettings(chat)
	buttons = getSettingsButtons()
	replyMarkup = getReplyMarkup(buttons)
	chat.sendMessage("What do you want to change?", replyMarkup, callbackSetMsgId)

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
	chat = ChatFunctions.getChat(str(callback['message']['chat']['id']))
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
		retMsg = funs[pref](chat, suff, callback)
		tg.requestSpooler.put(lambda : tg.sendAnswerCallback(chat.chatId, callback['id'], retMsg))

def handleSettingsCallback(chat:Chat, data, callback):
	if data != "":
		logger.critical("Invalid callback settings data: " + data)
	else:
		chat.editMessageText(callback['message']['message_id'], "What do you want to change?", getReplyMarkup(getSettingsButtons()))
