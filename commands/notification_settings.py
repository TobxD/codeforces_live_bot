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
from commands import bot, settings

# constants
NOTIFY_LEVEL_DESC = ["Hidden", "Only Scoreboard", "Scoreboard + SysTest fail", "No Contest Notf.", "All Notifications"]

def getButton(handle, showInList, notify, isNotifyBtn, page):
	if isNotifyBtn:
		text = f"{handle} notify {'✅' if notify else '❌'}"
		data = "friend_notf:toggle-notify-" + handle + ";" + str(page)
	else:
		text = f"{handle} list {'✅' if showInList else '❌'}"
		data = "friend_notf:toggle-list-" + handle + ";" + str(page)
	return {"text": text, "callback_data":data}

def getUserButtons(handle, notSettingsRow, page):
	return [
		{"text": handle, "callback_data": "friend_notf:handlepress"},
		[ {"text": '✅' if notSettingsRow[i] else '❌', "callback_data": f"toogle-{handle};{i};{page}"} 
			for i in range(len(notSettingsRow))]
	]

def getButtonRows(chat, page=0):
	PAGE_SIZE = 10
	friends = db.getFriends(chat.chatId) # [(handle, showInList, notfiy)]
	if friends == None:
		chat.sendMessage("You don't have any friends :(")
		return [], ""
	
	buttons = []
	for i in range(PAGE_SIZE*page, min(len(friends), PAGE_SIZE*(page+1))):
		handle = friends[i][0]
		notRow = friends[i][1:]
		buttons += getUserButtons(handle, notRow, page)

	pagesCount = (len(friends)+PAGE_SIZE-1) // PAGE_SIZE
	btnNextPage = {"text": "Next Page 👉",     "callback_data": "friend_notf:config-page" + str(page+1)}
	btnPrevPage = {"text": "👈 Previous Page", "callback_data": "friend_notf:config-page" + str(page-1)}
	if pagesCount > 1:
		if page == 0:
			buttons.append([btnNextPage])
		elif page == pagesCount-1:
			buttons.append([btnPrevPage])
		else:
			buttons.append([btnPrevPage, btnNextPage])
	buttons.append([{"text":"👈 Back to the Notification Settings", "callback_data":"friend_notf:"}])
	title = f"Page {page+1} / {pagesCount}" # TODO Button description
	return buttons, title


def toggleFriendsSettings(chat:Chat, handleIdAndPage, isNotify):
	[handle, notId, page] = handleIdAndPage.split(';')
	notId = int(notId)
	page = int(page)
	gesetzt = db.toggleFriendSettings(chat.chatId, handle, id)
	# TODO
	#if isNotify:
	#	notf = ("🔔" if gesetzt else "🔕") + "You will" + ("" if gesetzt else " no longer") + " receive notifications for "+ handle +"."
	#else:
	#	notf = ("✅" if gesetzt else "❌") + " You will" + ("" if gesetzt else " no longer") + " see "+ handle +" on your list."
	buttons, title = getButtonRows(chat, page)
	return "", buttons, title


def getMenu(chat:Chat):
	friends = db.getFriends(chat.chatId) # [(handle, showInList, notfiy)]
	friendsTotal = len(friends)
	friendsList, friendsNotify = len([f for f in friends if f[1]]), len([f for f in friends if f[2]])
	title = (f"*Change your friends settings*\n"
		"\nThere are 4 different settings:\n"
		"1. Show user in the scoreboard\n"
		"2. Receive _System Tests failed_ notifications for user\n"
		"3. Receive upsolving notifications for user (has solved a task after the contest)\n"
		"4. Receive solving notifications during the contest\n"
		"\nYou can specify a global notifcation level and override it for specific users if you want.\n"
		"Currently, your settings\n"
		f"For *{friendsList}* / {friendsTotal} friends: see them in the standings\n"
		f"For *{friendsList}* / {friendsTotal} friends: receive System Test failed notifications\n"
		f"For *{friendsList}* / {friendsTotal} friends: receive upsolving notifications\n"
		f"For *{friendsNotify}* / {friendsTotal} friends: contest notifications\n"
		f"\nYour *global notification level* is _{NOTIFY_LEVEL_DESC[chat.notifyLevel]}_. Change it here:") # TODO bar with pointer

	buttons = [
		[
			{"text": "⬅️" if chat.notifyLevel -1 >= 0 else " ",                     "callback_data": "friend_notf:decNotifyLvl"},
			{"text": NOTIFY_LEVEL_DESC[chat.notifyLevel],                          "callback_data": "friend_notf:hoverNotifyLvl"},
			{"text": "➡️" if chat.notifyLevel +1 < len(NOTIFY_LEVEL_DESC) else " ", "callback_data": "friend_notf:incNotifyLvl"}
		],
		[{"text": "Reset All Friends",        "callback_data": "friend_notf:reset"}],
		[{"text": "Configure Individually",   "callback_data": "friend_notf:config-page0"}],
		[{"text": "👈 Back to the Overview",  "callback_data": "settings:"}]
	]
	return buttons, title

def handleChatCallback(chat:Chat, data, callback):
	answerToast = None
	if data == "":
		buttons, title = getMenu(chat)
	elif data.startswith("config-page"):
		page = int(data[len("config-page"):])
		buttons, title = getButtonRows(chat, page)
	elif data.startswith("toggle-"):
		answerToast, buttons, title = toggleFriendsSettings(chat, data[len("toggle-"):])
	elif data == "decNotifyLvl":
		if chat.notifyLevel == 0:
			answerToast = "You already disabled all friend notifications"
		else:
			chat.notifyLevel -= 1
		buttons, title = getMenu(chat)
	elif data == "incNotifyLvl":
		if chat.notifyLevel >= len(NOTIFY_LEVEL_DESC) -1:
			answerToast = "You already enabled all friend notifications"
		else:
			chat.notifyLevel += 1
		buttons, title = getMenu(chat)
	elif data == "hoverNotifyLvl":
		buttons, title = getMenu(chat)
	elif data == "reset":
		# TODO 
		buttons, title = getMenu(chat)
	else:
		logger.critical("no valid bahaviour option for notify settings: " + data)

	replyMarkup = settings.getReplyMarkup(buttons)
	msgId = callback['message']['message_id']
	chat.editMessageText(msgId, title, replyMarkup)
	return answerToast
