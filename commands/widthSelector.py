from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from telegram.Chat import Chat

from utils.Table import Table
from utils.util import logger
from commands import settings
from telegram import telegram as tg


def handleWidthChange(chat:Chat, data, callback):
	def getMsg(width):
		table = Table(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"], [])	
		text = ("Configure how many columns you want to display. Choose the maximum "
			"value which still displays the table correctly.\n"
			"Note: This setting is global for the chat, make sure it works on all of "
			"your devices.\n")
		text += table.formatTable(chat.width)
		buttons = [
			[{"text": "-", "callback_data": "width:-"}, {"text": "+", "callback_data": "width:+"}],
			[{"text":"👈 Back to General Settings", "callback_data":"general:"}],
		]
		return text, buttons

	warningText = None
	if data == '':
		pass # initial call, don't change
	elif data == '+':
		if chat.width == 12:
			warningText = "❗️You reached the maximum table width❗️"
		else:
			chat.width = chat.width + 1
	elif data == '-':
		if chat.width == 4:
			warningText = "❗️You reached the minimum table width❗️"
		else:
			chat.width = chat.width - 1
	else:
		logger.critical("unrecognized data at handle width: " + str(data))

	if warningText:
		tg.sendAnswerCallback(chat.chatId, callback['id'], warningText)
	else:
		text, buttons = getMsg(chat.width)
		chat.editMessageText(callback["message"]["message_id"], text,
			settings.getReplyMarkup(buttons))
