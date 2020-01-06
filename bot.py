import database as db
import telegram as tg
import codeforces as cf
import util
import AnalyseStandingsService
import UpcomingService
import SummarizingService
import standings
import upcoming
import settings
import Chat

import threading

# chatId -> function
openCommandFunc = {}

def setOpenCommandFunc(chatId, func):
	global openCommandFunc
	if func is None:
		del openCommandFunc[chatId]
	else:
		openCommandFunc[chatId] = func


#------------------------- Rating request --------------------------------------
def ratingsOfUsers(userNameArr):
	userInfos = cf.getUserInfos(userNameArr)
	if userInfos is False or len(userInfos) == 0:
		return "Unknown user in this list"
	res = "```\n"
	maxNameLen = max([len(user['handle']) for user in userInfos])
	userInfos = sorted(userInfos, key= lambda k: k.get('rating', 0), reverse=True)
	for user in userInfos:
		res += user['handle'].ljust(maxNameLen) + ': ' + str(user.get('rating', 0)) + '\n'
	res += "```"
	return res

def handleRatingRequestCont(chat, handle):
	chat.sendMessage(ratingsOfUsers([util.cleanString(handle)]))

def handleRatingRequest(chat, req):
	#offenes Request adden
	global openCommandFunc
	openCommandFunc[chat.chatId] = handleRatingRequestCont
	chat.sendMessage("Codeforces handle:")

def handleFriendRatingsRequest(chat, req):
	chat.sendMessage(ratingsOfUsers(cf.getFriends(chat)))

# ----- Add Friend -----
def handleAddFriendRequestCont(chat, req):
	handle = util.cleanString(req)
	userInfos = cf.getUserInfos([handle])
	if userInfos == False:
		chat.sendMessage("No user with this handle!")
	else:
		db.addFriends(chat.chatId, [userInfos[0]['handle']])
		chat.sendMessage("👦 User `" + userInfos[0]['handle'] + "` with rating " +
			str(userInfos[0].get('rating', 0)) + " added.")

def handleAddFriendRequest(chat, req):
	#offenes Request adden
	global openCommandFunc
	openCommandFunc[chat.chatId] = handleAddFriendRequestCont
	chat.sendMessage("Codeforces handle:")

#------ Start -------------
def handleStart(chat, text):
	global openCommandFunc
	openCommandFunc[chat.chatId] = settings.handleSetTimezone
	chat.sendMessage("*Welcome to the Codeforces Live Bot!*\n\n"
	+ "You will receive reminders for upcoming Codeforces Contests. Please tell me your *timezone* so that "
	+ "the contest start time will be displayed correctly. So text me the name of the city you live in, for example "
	+ "'Munich'.")

# ------ Other --------
def invalidCommand(chat, msg):
	chat.sendMessage("Invalid command!")

def noCommand(chat, msg):
	if chat.chatId in openCommandFunc:
		openCommandFunc[chat.chatId](chat, msg)
	else:
		invalidCommand(chat, msg)

#-----
def handleMessage(chat, text):
	util.log("-> " + text + " <-")
	text = text.replace("@codeforces_live_bot", "")
	text = text.replace("@codeforces_live_testbot", "")
	msgSwitch = {
		"/start": handleStart,
		"/rating": handleRatingRequest,
		"/friend_ratings": handleFriendRatingsRequest,
		"/add_friend": handleAddFriendRequest,
		"/settings": settings.handleSettings,
		"/current_standings": standings.sendStandings,
		"/upcoming": upcoming.handleUpcoming
	}
	func = msgSwitch.get(util.cleanString(text), noCommand)
	func(chat, text)

def initContestServices():
	Chat.initChats()
	services = [
		cf.ContestListService(),
		AnalyseStandingsService.AnalyseStandingsService(),
		UpcomingService.UpcomingService(),
		SummarizingService.SummarizingService()
	]

	for service in services:
		service.start()

def startTestingMode():
	tg.RESTART = 10000000000
	tg.RESTART_WAIT = 10000000000
	initContestServices()

	while True:
		msg = input()
		handleMessage(Chat.getChat('0'), msg)

def startTelegramBot():
	initContestServices()
	tg.TelegramUpdateService().start()
	while True:
		msg = input()
		if msg == 'quit':
			#TODO halt all threads
			return
