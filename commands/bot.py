from __future__ import annotations
import queue, time, random, re
from collections import defaultdict
import threading
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from telegram.Chat import Chat as ChatClass

from utils import database as db
from telegram import telegram as tg
from codeforces import codeforces as cf
from utils import util
from utils.util import logger
from services import AnalyseStandingsService, UpcomingService, SummarizingService
from codeforces import standings, upcoming
from commands import settings
from commands import general_settings
from telegram import Chat

# chatId -> function
openCommandFunc = {}
# Change emoji after serveral invalid commands in last 5h
invalidComTimes = defaultdict(lambda : queue.Queue())
invalidComTimesLock = threading.Lock()

def invalidCommandCount(chatId):   # how often was 'invalid command' used in last 5h
	with invalidComTimesLock:
		invalidComTimes[chatId].put(time.time())
		while invalidComTimes[chatId].queue[0] < time.time() - 5*60*60:
			invalidComTimes[chatId].get()
		return invalidComTimes[chatId].qsize() - 1

def setOpenCommandFunc(chatId, func):
	global openCommandFunc
	if func is None:
		if chatId in openCommandFunc:
			del openCommandFunc[chatId]
	else:
		openCommandFunc[chatId] = func


#------------------------- Rating request --------------------------------------
def ratingsOfUsers(userNameArr):
	if len(userNameArr) == 0:
		return ("You have no friends 😭\n"
				"Please add your API key in the settings to add codeforces friends automatically or add friends manually with `/add_friend`.")
	userInfos = cf.getUserInfos(userNameArr)
	if userInfos is False or len(userInfos) == 0:
		return "Unknown user in this list"
	res = "```\n"
	maxNameLen = max([len(user['handle']) for user in userInfos])
	userInfos = sorted(userInfos, key= lambda k: k.get('rating', 0), reverse=True)
	for user in userInfos:
		rating = user.get('rating', 0)
		res += util.getUserSmiley(rating) + " " + user['handle'].ljust(maxNameLen) + ': ' + str(rating) + '\n'
	res += "```"
	return res

def handleRatingRequestCont(chat, handleStr):
	handleStr = util.cleanString(handleStr)
	handles = handleStr.split(',')
	handles = [util.cleanString(h) for h in handles]
	chat.sendMessage(ratingsOfUsers(handles))
	setOpenCommandFunc(chat.chatId, None)

def handleRatingRequest(chat, req):
	setOpenCommandFunc(chat.chatId, handleRatingRequestCont)
	chat.sendMessage("Codeforces handle(s), comma seperated:")

def handleFriendRatingsRequest(chat, req):
	setOpenCommandFunc(chat.chatId, None)
	chat.sendMessage(ratingsOfUsers(cf.getAllFriends(chat)))

# ----- Add Friend -----
def handleAddFriendRequestCont(chat, req):
	handles = [util.cleanString(s) for s in req.split(',')]
	userInfos = cf.getUserInfos(handles)
	if userInfos == False or len(userInfos) == 0 or "handle" not in userInfos[0]:
		chat.sendMessage("👻 No user with this handle! Please try again:")
	else:
		for user in userInfos:
			if "handle" in user:
				db.addFriends(chat.chatId, [user['handle']], chat.notifyLevel)
				rating = user.get('rating', 0)
				chat.sendMessage(util.getUserSmiley(rating) + " User `" + user['handle'] + "` with rating " + str(rating) + " added.")
		setOpenCommandFunc(chat.chatId, None)

def handleAddFriendRequest(chat, req):
	setOpenCommandFunc(chat.chatId, handleAddFriendRequestCont)
	chat.sendMessage("Codeforces handle(s), comma seperated:")

# ----- Remove Friend -----
def handleRemoveFriendRequestCont(chat, req):
	handles = [util.cleanString(s) for s in req.split(',')]
	userInfos = cf.getUserInfos(handles)
	if userInfos == False or len(userInfos) == 0 or "handle" not in userInfos[0]:
		chat.sendMessage("👻 No user with this handle!")
	else:
		for user in userInfos:
			if "handle" in user:
				db.deleteFriendOfUser(user['handle'], chat.chatId)
				chat.sendMessage("💀 User `" + user['handle'] + "` was removed from your friends. If this is one of your Codeforces friends, they will be added automatically again in case you added your API-key. If so, just disable notifications for this user in the settings.")
	setOpenCommandFunc(chat.chatId, None)

def handleRemoveFriendRequest(chat, req):
	setOpenCommandFunc(chat.chatId, handleRemoveFriendRequestCont)
	chat.sendMessage("Codeforces handle(s), comma seperated:")

#------ Start -------------
def handleStart(chat, text):
	setOpenCommandFunc(chat.chatId, general_settings.handleSetTimezone)
	msg = ("🔥*Welcome to the Codeforces Live Bot!*🔥\n\n"
	"You will receive reminders for upcoming Codeforces Contests. Please tell me your *timezone* so that "
	"the contest start time will be displayed correctly. So text me the name of the city you live in, for example "
	"'Munich'.")
	if chat.chatId.startswith('-'): # group chat
		msg += "\nAs you are in a group, be sure to *reply* to one of my messages so that I receive your text.\n\n*Your city:*"
	chat.sendMessage(msg)

def sendSetupFinished(chat:ChatClass):
	friends = db.getFriends(chat.chatId) # [(handle, showInList, notfiy)]
	friendsTotal = len(friends) if friends else 0
	setOpenCommandFunc(chat.chatId, None)
	msg = ("*Setup Completed*\n\n"
	"You completed the bot setup, now feel free to use the bot.\n"
	"Your current settings are:\n"
	f"Timezone: {chat.timezone}\n"
	f"Handle: {util.formatHandle(chat.handle) if chat.handle else '❌'}\n"
	f"API key added: {'✅' if chat.apikey else '❌'}\n"
	f"Friends: {friendsTotal}\n"
	"\nYou can change the settings with /settings")
	chat.sendMessage(msg)

#-------- HELP ------------
def handleHelp(chat, text):
	msg = ("🔥*Codeforces Live Bot*🔥\n\n"
	+ "With this bot you can:\n"
	+ "• receive reminders about upcoming _Codeforces_ contest\n"
	+ "• list upcoming _Codeforces_ contest via /upcoming\n"
	+ "• see the current contest standings of your friends via /current\_standings\n"
	+ "• receive notifications if your friends solve tasks - during the contest or in the upsolving\n"
	+ "• look at the leaderboard of your friends via /friend\_ratings\n"
	+ "• get the current rating of a specific user with /rating\n"
	+ "• manage your friends with /add\_friend and /remove\_friend\n"
	+ "• import your Codeforces friends by adding a Codeforces API key in /settings\n"
	+ "• configure your time zone, contest reminders, table width and more in /settings\n"
	+ "• modify the bot's behaviour (politeness, replies, …) in /settings\n"
	+ "\nWe use the following ranking system:\n"
	+ "• " + util.getUserSmiley(2400) + ": rating ≥ 2400\n"
	+ "• " + util.getUserSmiley(2100) + ": rating ≥ 2100\n"
	+ "• " + util.getUserSmiley(1900) + ": rating ≥ 1900\n"
	+ "• " + util.getUserSmiley(1600) + ": rating ≥ 1600\n"
	+ "• " + util.getUserSmiley(1400) + ": rating ≥ 1400\n"
	+ "• " + util.getUserSmiley(1200) + ": rating ≥ 1200\n"
	+ "• " + util.getUserSmiley(1199) + ": rating < 1200\n"
	)
	if chat.chatId.startswith('-'): # group chat
		msg += "\n\nAs you are in a group, be sure to *reply* to one of my messages so that I receive your text."
	chat.sendMessage(msg)

# ------ Other --------
def invalidCommand(chat, msg):
	emoji = ["😅", "😬", "😑", "😠", "😡", "🤬"]
	c = invalidCommandCount(chat.chatId)
	chat.sendMessage("Invalid command!" + ("" if chat.polite else emoji[min(len(emoji)-1, c)]))

def randomMessage(chat, msg):
	provocations = [
		"Better watch your mouth☝🏻",
		"What are you talking?",
		"Stop it! \nTomorrow 12:00\n*1 on 1 on Codeforces*\nwithout cheatsheet!\nIf you dare…",
		"Watch out!"
	]
	funnyComments = [
		"Ok.",
		"I will consider that next time",
		"Good point!",
		"Haha lol😂",
		"🤔",
		"🤨",
		"WTF",
		"No, are you stupid?",
		"No way!",
		"I didn't get that, can you please repeat it?",
		"Sure.",
		"Why not",
		"Are you sure?",
		"No! Don't leave me!😢 The insults after the last contest were just a joke. " +
			"I didn't mean to hurt you. Pleeeaasee stay! " +
			"I was always kind to you, provided you with the latest contest results and even had a uptime > 0! " +
			"Forgive me, please!\n" +
			"Ok, apparently you have blocked me now, so I'm gonna delete all your data...\n\n" +
			"EDIT: sry, wrong chat"
	] + provocations

	if re.match(r'.*\bbot\b', msg.lower()): # msg contains the word 'bot'
		if random.randint(0,1) == 0:
			chat.sendMessage(provocations[random.randint(0,len(provocations)-1)])
	elif random.randint(0,6) == 0: #random comment
		chat.sendMessage(funnyComments[random.randint(0,len(funnyComments)-1)])

def noCommand(chat, msg):
	if chat.chatId in openCommandFunc:
		openCommandFunc[chat.chatId](chat, msg)
	elif chat.reply:
		if msg.startswith("/"):
			invalidCommand(chat, msg)
		elif not chat.polite:
			randomMessage(chat, msg)

#-----
def handleMessage(chat, text):
	logger.info("-> " + text + " <- (" + ((chat.handle + ": ") if chat.handle else "") + str(chat.chatId) + ")")
	text = text.replace("@codeforces_live_bot", "")
	text = text.replace("@codeforces_live_testbot", "")
	msgSwitch = {
		"/start": handleStart,
		"/rating": handleRatingRequest,
		"/friend_ratings": handleFriendRatingsRequest,
		"/add_friend": handleAddFriendRequest,
		"/remove_friend": handleRemoveFriendRequest,
		"/settings": settings.handleSettings,
		"/current_standings": standings.sendStandings,
		"/upcoming": upcoming.handleUpcoming,
		"/help": handleHelp
	}
	func = msgSwitch.get(util.cleanString(text), noCommand)
	func(chat, text)

def initContestServices():
	Chat.initChats()
	standings.initDB()
	services = [
		cf.ContestListService(),
		cf.FriendUpdateService(),
		AnalyseStandingsService.AnalyseStandingsService(),
		UpcomingService.UpcomingService(),
		SummarizingService.SummarizingService()
	]
	for service in services:
		service.start()

def startTestingMode():
	tg.testFlag = True
	initContestServices()
	while True:
		msg = input()
		handleMessage(Chat.getChat('0'), msg)

def startTelegramBot():
	initContestServices()
	tg.TelegramUpdateService().start()
	while True:
		msg = input()
		handleMessage(Chat.getChat('0'), msg)
