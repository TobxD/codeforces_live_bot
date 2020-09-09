import queue, time, random, re
from collections import defaultdict
import threading

from utils.util import logger
from commands import settings
from telegram import telegram as tg

chatsLock = threading.Lock()

def getChatSettingsButtons(chat):
	politeText = ("Polite 😇" if chat.polite else "Rude 😈")
	replyText = ("R" if chat.reply else "Not r") + "eceiving funny replies" + ("✅" if chat.reply else "❌")
	reminder2hText = "2h Reminder: " + ("active 🔔" if chat.reminder2h else "not active 🔕")
	reminder1dText = "1d Reminder: " + ("active 🔔" if chat.reminder1d else "not active 🔕")
	reminder3dText = "3d Reminder: " + ("active 🔔" if chat.reminder3d else "not active 🔕")

	buttons = [
		[{"text": politeText,			"callback_data": "behavior:polite"}],
		[{"text": replyText,			"callback_data": "behavior:reply"}],
		[{"text": reminder2hText,	"callback_data": "behavior:reminder2h"}],
		[{"text": reminder1dText,	"callback_data": "behavior:reminder1d"}],
		[{"text": reminder3dText,	"callback_data": "behavior:reminder3d"}],
		[{"text": "👈 Back to the Overview",	"callback_data": "settings:"}]
	]
	return buttons

def handleChatCallback(chat, data, callback):
	answerText = None
	with chatsLock:
		if data == "polite":
			chat.polite = not chat.polite
			if chat.polite:
				answerText = "👿 This is what I call weakness…"
			else:
				answerText = "😈 Welcome back to the dark side."
		elif data == "reply":
			chat.reply = not chat.reply
		elif data == "reminder2h":
			chat.reminder2h = not chat.reminder2h
		elif data == "reminder1d":
			chat.reminder1d = not chat.reminder1d
		elif data == "reminder3d":
			chat.reminder3d = not chat.reminder3d
		elif data != "":
			logger.critical("no valid bahaviour option: " + data)

		buttons = getChatSettingsButtons(chat)
	replyMarkup = settings.getReplyMarkup(buttons)
	chat.editMessageText(callback['message']['message_id'], "Change the behavior of the bot:", replyMarkup)
	return answerText
