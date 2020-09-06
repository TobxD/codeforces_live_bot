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

def getButton(handle, showInList, notify, isNotifyBtn, page):
	if isNotifyBtn:
		text = f"{handle} notify {'✅' if notify else '❌'}"
		data = "friend_notf:toggle-notify-" + handle + ";" + str(page)
	else:
		text = f"{handle} list {'✅' if showInList else '❌'}"
		data = "friend_notf:toggle-list-" + handle + ";" + str(page)
	return {"text": text, "callback_data":data}

def getButtonRows(chat, isNotify, page=0):
	PAGE_SIZE = 40
	friends = db.getFriends(chat.chatId) # [(handle, showInList, notfiy)]
	if friends == None:
		chat.sendMessage("You don't have any friends :(")
		return [], ""
	if len(friends) % 2 == 1:
		friends.append(["", 0, 0])
	buttons = []
	for i in range(PAGE_SIZE*page, min(len(friends), PAGE_SIZE*(page+1)), 2):
		[handle0, showInList0, notify0] = friends[i+0]
		[handle1, showInList1, notify1] = friends[i+1]
		if handle1 == "":
			buttons.append([getButton(handle0, showInList0 == 1, notify0 == 1, isNotify, page)])
		else:
			buttons.append([
				getButton(handle0, showInList0 == 1, notify0 == 1, isNotify, page),
				getButton(handle1, showInList1 == 1, notify1 == 1, isNotify, page)
			])
	pagesCount = (len(friends)+PAGE_SIZE-1) // PAGE_SIZE
	cb_action = "friend_notf:" + ("notify-page" if isNotify else "list-page")
	btnNextPage = {"text": "Next Page 👉", "callback_data": cb_action + str(page+1)}
	btnPrevPage = {"text": "👈 Previous Page", "callback_data": cb_action + str(page-1)}
	if pagesCount > 1:
		if page == 0:
			buttons.append([btnNextPage])
		elif page == pagesCount-1:
			buttons.append([btnPrevPage])
		else:
			buttons.append([btnPrevPage, btnNextPage])
	buttons.append([{"text":"👈 Back to the Notification Settings", "callback_data":"friend_notf:"}])
	title = f"Page {page+1} / {pagesCount}"
	return buttons, title


def toggleFriendsSettings(chat:Chat, handleAndPage, isNotify):
	[handle, page] = handleAndPage.split(';')
	page = int(page)
	gesetzt = db.toggleFriendSettings(chat.chatId, handle, 'notify' if isNotify else 'showInList')
	if isNotify:
		notf = ("🔔" if gesetzt else "🔕") + "You will" + ("" if gesetzt else " no longer") + " receive notifications for "+ handle +"."
	else:
		notf = ("✅" if gesetzt else "❌") + " You will" + ("" if gesetzt else " no longer") + " see "+ handle +" on your list."
	buttons, title = getButtonRows(chat, isNotify, page)
	return notf, buttons, title

def toggleAllFriendsSettings(chat:Chat, isNotify):
	isEnabled = chat.new_friends_notify if isNotify else chat.new_friends_list
	db.toggleAllFriendSettings(chat.chatId, isEnabled, 'notify' if isNotify else 'showInList')
	if isNotify:
		if isEnabled:
			notf = "🔔 You will receive notifications for all you friends."
		else:
			notf = "🔕 You will no longer receive notifications for any friends."
	else:
		if isEnabled:
			notf = "✅ You will see all your friends on your scoreboard."
		else:
			notf = "❌ You will no longer see any friends on your scoreboard."
	return notf

def getMenu(chat:Chat):
	friends = db.getFriends(chat.chatId) # [(handle, showInList, notfiy)]
	friendsTotal = len(friends)
	friendsList, friendsNotify = len([f for f in friends if f[1]]), len([f for f in friends if f[2]])
	title = (f"*Change your friends settings*\nCurrently, you see *{friendsList}* / {friendsTotal} friends in the standings\n"
						f"and get notified for *{friendsNotify}* / {friendsTotal} friends.")
	showAllText = ("Hide" if chat.new_friends_list else "Show") + " All Friends on Scoreboard"
	notifyAllText = ("Mute" if chat.new_friends_notify else "Notify for") + " All Friends"

	buttons = [
		[{"text": showAllText,													"callback_data": "friend_notf:show-all"}],
		[{"text": "Configure Listed Friends Manually",	"callback_data": "friend_notf:list-page0"}],
		[{"text": notifyAllText,												"callback_data": "friend_notf:notify-all"}],
		[{"text": "Configure Notifications Manually",		"callback_data": "friend_notf:notify-page0"}],
		[{"text": "👈 Back to the Overview",						"callback_data": "settings:"}]
	]
	return buttons, title

def handleChatCallback(chat:Chat, data, callback):
	answerToast = None
	if data == "":
		buttons, title = getMenu(chat)
	elif data.startswith("list-page"):
		page = int(data[len("list-page"):])
		buttons, title = getButtonRows(chat, False, page)
	elif data.startswith("notify-page"):
		page = int(data[len("notify-page"):])
		buttons, title = getButtonRows(chat, True, page)
	elif data.startswith("toggle-list-"):
		answerToast, buttons, title = toggleFriendsSettings(chat, data[len("toggle-list-"):], False)
	elif data.startswith("toggle-notify-"):
		answerToast, buttons, title = toggleFriendsSettings(chat, data[len("toggle-notify-"):], True)
	elif data == "show-all":
		chat.new_friends_list = not chat.new_friends_list
		answerToast = toggleAllFriendsSettings(chat, False)
		buttons, title = getMenu(chat)
	elif data == "notify-all":
		chat.new_friends_notify = not chat.new_friends_notify
		answerToast = toggleAllFriendsSettings(chat, True)
		buttons, title = getMenu(chat)
	else:
		logger.critical("no valid bahaviour option for notify settings: " + data)

	replyMarkup = settings.getReplyMarkup(buttons)
	msgId = callback['message']['message_id']
	chat.editMessageText(msgId, title, replyMarkup)
	return answerToast
