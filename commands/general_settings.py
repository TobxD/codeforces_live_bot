from __future__ import annotations
import json
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from telegram.Chat import Chat as ChatClass

from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from commands import bot
from telegram import Chat
from commands import settings

#		"setup": setup.handleSetupCallback,
#funs[pref](chat, suff, callback)
# ---- General Setup buttons ----
def handleSetupCallback(chat, data, callback):
	if data == "":
		showSetupPage(chat, data, callback)
	else:
		funs = {
			'timezone': handleChangeTimezone,
			'handle': handleSetUserHandlePrompt,
			'apikey': handleSetAuthorization,
		}
		if data not in funs:
			logger.critical("wrong setup data: " + str(data))
		else:
			return funs[data](chat)

def showSetupPage(chat, data, callback):
	buttons = [
		[{"text": "Set timezone",								"callback_data": "general:timezone"}],
		[{"text": "Set your handle",						"callback_data": "general:handle"}],
		[{"text": "Set your api key",						"callback_data": "general:apikey"}],
		[{"text": "Set displayed table width",	"callback_data": "width:"}],
		[{"text": "👈 Back to the Overview",		"callback_data": "settings:"}]
	]
	replyMarkup = settings.getReplyMarkup(buttons)
	chat.editMessageText(callback['message']['message_id'], "General settings:", replyMarkup)

# ---- Set User Handle ------
def handleSetUserHandlePrompt(chat, msg=None):
	bot.setOpenCommandFunc(chat.chatId, handleSetUserHandle)
	chat.sendNotification("Please enter your Codeforces handle:")

def handleSetUserHandle(chat:ChatClass, handle):
	handle = util.cleanString(handle)
	if util.cleanString(handle) == 'no':
		bot.sendSetupFinished(chat)
		return
	userInfos = cf.getUserInfos([handle])
	if userInfos == False or len(userInfos) == 0 or "handle" not in userInfos[0]:
		chat.sendMessage("👻 No user with this handle! Try again:")
	else:
		bot.setOpenCommandFunc(chat.chatId, None)
		chat.handle = userInfos[0]['handle']
		db.addFriends(chat.chatId, [userInfos[0]['handle']], chat.notifyLevel)
		rating = userInfos[0].get('rating', 0)
		chat.sendNotification("Welcome `" + userInfos[0]['handle'] + "`. Your current rating is " + str(rating) + " " + util.getUserSmiley(rating) + ".")
		if chat.apikey is None:
			chat.sendNotification("Do you want import your friends from Codeforces? Then, I need your Codeforces API key.")
			handleSetAuthorization(chat, "")

# ------- Add API KEY -----
def handleAddSecret(chat, secret):
	if not secret.isalnum():
		chat.sendMessage("Your API-secret is incorrect, it may only contain alphanumerical letters. Please try again:")
		return
	chat.secret = secret
	bot.setOpenCommandFunc(chat.chatId, None)
	logger.debug('new secret added for user ' + str(chat.chatId))
	chat.sendMessage("Key added. Now fetching your codeforces friends...")
	cf.updateFriends(chat)
	bot.sendSetupFinished(chat)

def handleAddKey(chat, key):
	if util.cleanString(key) == "no":
		bot.sendSetupFinished(chat)
		return
	if not key.isalnum():
		chat.sendMessage("Your API-key is incorrect, it may only contain alphanumerical letters. Please try again:")
		return
	chat.apikey = key
	bot.setOpenCommandFunc(chat.chatId, handleAddSecret)
	chat.sendMessage("Enter your secret:")

def handleSetAuthorization(chat, req=None):
	bot.setOpenCommandFunc(chat.chatId, handleAddKey)
	chat.sendNotification("Go to https://codeforces.com/settings/api and generate a key.\n"
	+ "Then text me two seperate messages - the first one containing the key and the second one containing the secret.\n"
	+ "If you do not want to add your secret now, text me _no_ and don't forget to add your secret later in the settings.")

# ------- Time zone -------------
def handleChangeTimezone(chat, text=None):
	bot.setOpenCommandFunc(chat.chatId, handleSetTimezone)
	chat.sendMessage("Setting up your time zone... Please enter the city you live in:")

def handleSetTimezone(chat:ChatClass, tzstr):
	tzstr = tzstr.lstrip().rstrip()
	tz = util.getTimeZone(tzstr)
	if not tz:
		chat.sendMessage("Name lookup failed. Please use a different city:")
	else:
		bot.setOpenCommandFunc(chat.chatId, None)
		chat.timezone = tz
		chat.sendNotification("Timezone set to '" + util.escapeMarkdown(tz) + "'")
		# if in setup after start, ask for user handle
		if chat.handle is None:
			# use notification so that the order is correct
			chat.sendNotification("Now I need *your* handle. Answer 'no' if you don't want to add your handle.")
			handleSetUserHandlePrompt(chat, "")
