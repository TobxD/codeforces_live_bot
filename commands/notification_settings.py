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
NOTIFY_LEVEL_DESC_SHORT = ["Disabled", "Only Scoreboard", "Scoreboard + SysTest fail", "Scb + SysTest + Upsolve", "All Notifications"]
NOTIFY_LEVEL_DESC = ["Disabled", "Only Scoreboard", "Scoreboard + System Test Fail Notf.", "Scoreboard + System Test Fail Notf. + Upsolving Notf.", "All Notifications"]
NOTIFY_SETTINGS_DESC = ["Show on Scoreboard", "Notify System Test Failed", "Upsolving Notf.", "In Contest Notifications"]

def getUserButtons(handle, notSettingsRow, page):
	return [
		[{"text": handle, "callback_data": "friend_notf:handlepress"}],
		[ {"text": '✅' if notSettingsRow[i] else '❌', "callback_data": f"friend_notf:toggle-{handle};{i};{page}"} 
			for i in range(len(notSettingsRow))]
	]

def getButtonRows(chat, page=0):
	PAGE_SIZE = 10
	friends = db.getFriends(chat.chatId) # [(handle, ...notRow)]
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
	btnManyPagesR = {"text": "(10) 👉👉",      "callback_data": "friend_notf:config-page" + str(page+10)}
	btnManyPagesL = {"text": "👈👈 (10)",      "callback_data": "friend_notf:config-page" + str(page-10)}
	if pagesCount > 1:
		if page == 0:
			buttons.append([btnNextPage])
		elif page == pagesCount-1:
			buttons.append([btnPrevPage])
		else:
			buttons.append([btnPrevPage, btnNextPage])
	# skip many pages:
	if page >= 10 or pagesCount - 1 - page >= 10:
		if not page >= 10:
			buttons.append([btnManyPagesR])
		elif not pagesCount-1 - page >= 10:
			buttons.append([btnManyPagesL])
		else:
			buttons.append([btnManyPagesL, btnManyPagesR])
	buttons.append([{"text":"👈 Back to the Notification Settings", "callback_data":"friend_notf:"}])
	title = (f"Page {page+1} / {pagesCount}\n"
		"With the buttons you change (in this order):\n• " + ('\n• '.join(NOTIFY_SETTINGS_DESC)))
	return buttons, title


def toggleFriendsSettings(chat:Chat, handleIdAndPage):
	[handle, notId, page] = handleIdAndPage.split(';')
	notId = int(notId)
	page = int(page)
	gesetzt = db.toggleFriendSettings(chat.chatId, handle, notId)
	notf = f"{NOTIFY_SETTINGS_DESC[notId]}: {'✅ enabled' if gesetzt else '❌ disabled'}"
	buttons, title = getButtonRows(chat, page)
	return notf, buttons, title


def getMenu(chat:Chat):
	friends = db.getFriends(chat.chatId) # [(handle, ...notifySettingsRow)]
	friendsTotal = len(friends)
	friendsCountWithLvl = [len([f for f in friends if f[i+1]]) for i in range(len(NOTIFY_SETTINGS_DESC))]

	def activeState(id):
		return '✅' if id <= chat.notifyLevel else '❌'
	def condBold(id):
		return '*' if id <= chat.notifyLevel else ''

	title = (f"*Change Your Friends Settings*\n"
		"\nThere are 4 different settings:\n"
		f"{condBold(1)}1. Show user in the scoreboard {condBold(1)}{activeState(1)}\n"
		f"{condBold(2)}2. Receive _System Tests failed_ notifications for user {condBold(2)}{activeState(2)}\n"
		f"{condBold(3)}3. Receive upsolving notifications for user (has solved a task after the contest) {condBold(3)}{activeState(3)}\n"
		f"{condBold(4)}4. Receive solving notifications during the contest {condBold(4)}{activeState(4)}\n"
		"\nYou can specify a global notifcation level and override it for specific users if you want.\n"
		"Currently, your settings are:\n"
		f"For *{friendsCountWithLvl[0]}* / {friendsTotal} friends: see them in the standings\n"
		f"For *{friendsCountWithLvl[1]}* / {friendsTotal} friends: receive 'system test failed' notifications\n"
		f"For *{friendsCountWithLvl[2]}* / {friendsTotal} friends: receive upsolving notifications\n"
		f"For *{friendsCountWithLvl[3]}* / {friendsTotal} friends: in contest notifications\n"
		f"\nYour *global notification level* is\n_({chat.notifyLevel}) {NOTIFY_LEVEL_DESC[chat.notifyLevel]}_\nChange it here:") # TODO bar with pointer

	buttons = [
		[{"text": f"({chat.notifyLevel}) {NOTIFY_LEVEL_DESC_SHORT[chat.notifyLevel]}", "callback_data": "friend_notf:hoverNotifyLvl"}],
		[
			{"text": "⬅️" if chat.notifyLevel -1 >= 0 else " ",                     "callback_data": "friend_notf:decNotifyLvl"},
			{"text": "➡️" if chat.notifyLevel +1 < len(NOTIFY_LEVEL_DESC) else " ", "callback_data": "friend_notf:incNotifyLvl"}
		],
		[{"text": "Reset All to Level", "callback_data": "friend_notf:reset"}],
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
	elif data == "handlepress":
		return
	elif data == "decNotifyLvl":
		if chat.notifyLevel == 0:
			return "You already disabled all friend notifications"
		else:
			db.updateToNotifyLevel(chat.chatId, chat.notifyLevel-1, chat.notifyLevel,)
			chat.notifyLevel -= 1
		buttons, title = getMenu(chat)
	elif data == "incNotifyLvl":
		if chat.notifyLevel >= len(NOTIFY_LEVEL_DESC) -1:
			return "You already enabled all friend notifications"
		else:
			db.updateToNotifyLevel(chat.chatId, chat.notifyLevel+1, chat.notifyLevel)
			chat.notifyLevel += 1
		buttons, title = getMenu(chat)
	elif data == "hoverNotifyLvl":
		return
	elif data == "reset":
		db.updateToNotifyLevel(chat.chatId, chat.notifyLevel, reset=True)
		buttons, title = getMenu(chat)
	else:
		logger.critical("no valid bahaviour option for notify settings: " + data)

	replyMarkup = settings.getReplyMarkup(buttons)
	msgId = callback['message']['message_id']
	chat.editMessageText(msgId, title, replyMarkup)
	return answerToast
