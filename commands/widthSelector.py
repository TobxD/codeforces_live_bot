from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from telegram.Chat import Chat

from utils.Table import Table
from utils.util import logger
from commands import settings


def handleWidthChange(chat:Chat, data, callback):
	if data == '':
		pass # initial call, don't change
	elif data == '+':
		chat.width = min(12, chat.width + 1)
	elif data == '-':
		chat.width = max(4, chat.width - 1)
	else:
		logger.critical("unrecognized data at handle width: " + str(data))

	table = Table(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"], [])	
	text = ("Configure how many columns you want to display. Choose the maximum "
		"value which still displays the table correctly.\n"
		"Note: This setting is global for the chat, make sure it works on all of "
		"your devices.\n")
	text += table.formatTable(chat.width)
	
	buttons = [[
		{"text": "-", "callback_data": "width:-"},
		{"text": "+", "callback_data": "width:+"}
	]]
	chat.editMessageText(callback["message"]["message_id"], text,
		settings.getReplyMarkup(buttons))
