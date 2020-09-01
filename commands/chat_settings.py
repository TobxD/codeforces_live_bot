import queue, time, random, re
from collections import defaultdict
import threading

from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from services import AnalyseStandingsService, UpcomingService, SummarizingService
from codeforces import standings, upcoming
from commands import settings
from telegram import Chat

chatsLock = threading.Lock()

def getChatSettingsButtons(chat):
	politeText = ("Polite 😇" if chat.polite else "Rude 😈")
	replyText = ("R" if chat.reply else "Not r") + "eceiving funny replies" + ("✅" if chat.reply else "❌")
	reminder2hText = "Reminder 2h before contest " + ("active 🔔" if chat.reminder2h else " not active 🔕")
	reminder1dText = "Reminder 1d before contest " + ("active 🔔" if chat.reminder1d else " not active 🔕")
	reminder3dText = "Reminder 3d before contest " + ("active 🔔" if chat.reminder3d else " not active 🔕")

	buttons = [
		[{"text": politeText,		"callback_data": "chat:polite"}],
		[{"text": replyText,		"callback_data": "chat:reply"}],
		[{"text": reminder2hText,		"callback_data": "chat:reminder2h"}],
		[{"text": reminder1dText,	"callback_data": "chat:reminder1d"}],
		[{"text": reminder3dText,	"callback_data": "chat:reminder3d"}],
		[{"text": "👈 back to settings overview",	"callback_data": "settings:"}]
	]
	return buttons

def handleChatCallback(chat, data, callback):
	with chatsLock:
		if data == "polite":
			chat.polite = not chat.polite
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
