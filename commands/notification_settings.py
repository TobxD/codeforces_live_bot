import json
from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from commands import bot
from telegram import Chat

def getButtons(handle, ratingWatch, contestWatch):
	text1 = f"{handle} list {'✅' if ratingWatch else '❌'}"
	text2 = f"{handle} notify {'✅' if contestWatch else '❌'}"
	data1 = "friend_notf:" + handle + ";0"
	data2 = "friend_notf:" + handle + ";1"
	return [{"text":text1, "callback_data":data1}, {"text":text2, "callback_data":data2}]

def getButtonRows(chat):
	friends = cf.getFriendsWithDetails(chat)
	if friends == None:
		chat.sendMessage("You don't have any friends :(")
		return []
	buttons = []
	for [handle, ratingWatch, contestWatch] in friends:
		buttons.append(getButtons(handle, ratingWatch == 1, contestWatch == 1))
	buttons.append([{"text":"<< back to general settings", "callback_data":"settings:"}])
	return buttons

def sendFriendSettingsButtons(chat, callback):
	buttons = getButtonRows(chat)
	replyMarkup = getReplyMarkup(buttons)
	chat.editMessageText(callback['message']['message_id'], "Click the buttons to change the friend settings.", replyMarkup)

def updateButtons(chat, msgId):
	buttons = getButtonRows(chat)
	replyMarkup = getReplyMarkup(buttons)
	chat.editMessageText(msgId, "", replyMarkup)


#called with: funs[pref](chat, suff, callback)
def handleFriendNotSettingsCallback(chat, data, callback):
	if data == "":
		sendFriendSettingsButtons(chat, callback)
	else:
		[handle, button] = data.split(';')
		gesetzt = db.toggleFriendSettings(chat.chatId, handle, 'ratingWatch' if button == "0" else 'contestWatch')
		if button == "0":
			notf = ("✅" if gesetzt else "❌") + " You will" + ("" if gesetzt else " no longer") + " see "+ handle +" on your list."
		else:
			notf = ("🔔" if gesetzt else "🔕") + "You will" + ("" if gesetzt else " no longer") + " receive notifications for "+ handle +"."
		tg.sendAnswerCallback(chat.chatId, callback['id'], notf)
		updateButtons(chat, callback['message']['message_id'])
