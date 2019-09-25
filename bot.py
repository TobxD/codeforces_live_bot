import json, requests, time, datetime
from pytz import timezone
import sys, traceback, random, hashlib
import database as db
import telegram as tg
import codeforces as cf
import util
import AnalyseStandingsService
import UpcomingService
import SummarizingService
import standings
import upcoming


openCommandFunc = {}

#------------------------ Callback functions -----------------------------------
#-------------------------------------------------------------------------------

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

def handleRatingRequestCont(chatId, handle):
  tg.sendMessage(chatId, ratingsOfUsers([util.cleanString(handle)]))

def handleRatingRequest(chatId, req):
  #offenes Request adden
  global openCommandFunc
  openCommandFunc[chatId] = handleRatingRequestCont
  tg.sendMessage(chatId, "Codeforces handle:")

def handleFriendRatingsRequest(chatId, req):
  tg.sendMessage(chatId, ratingsOfUsers(cf.getFriends(chatId)))

# ----- Add Friend -----
def handleAddFriendRequestCont(chatId, req):
  handle = util.cleanString(req)
  userInfos = cf.getUserInfos([handle])
  if userInfos == False:
    tg.sendMessage(chatId, "No user with this handle!")
  else:
    db.addFriends(chatId, [handle])
    tg.sendMessage(chatId, "👦 User `" + userInfos[0]['handle'] + "` with rating " +
      str(userInfos[0]['rating']) + " added.")

def handleAddFriendRequest(chatId, req):
  #offenes Request adden
  global openCommandFunc
  openCommandFunc[chatId] = handleAddFriendRequestCont
  tg.sendMessage(chatId, "Codeforces handle:")



#######################################################
##--------------------- Settings --------------------##
#######################################################

def handleSettings(chatId, req):
  buttons = getButtonSettings(chatId)
  replyMarkup = {"inline_keyboard": buttons}
  replyMarkup = json.dumps(replyMarkup)
  tg.sendMessage(chatId, "What do you want to change?", replyMarkup)

def getButtonSettings(chatId):
  buttons = [
    [{"text": "Change time zone",                       "callback_data": "settings:timezone"}],
    [{"text": "Change your CF handle",                  "callback_data": "settings:handle"}],
    [{"text": "Change Codeforces API key",              "callback_data": "settings:apikey"}],
    [{"text": "Change friends & notification settings", "callback_data": "settings:notf"}],
  ]
  return buttons

# all button presses
def handleCallbackQuery(callback):
  chatId = str(callback['message']['chat']['id'])
  data = callback['data']

  if not ":" in data:
    log("Invalid callback data: "+ data)
    return

  pref, data = data.split(":", 1)

  if pref == "settings":
    handleSettingsCallback(chatId, data, callback)
  elif pref == "friend_notf":
    handleFriendNotSettingsCallback(chatId, data, callback)
  else:
    log("Invalid callback prefix: "+ pref + ", data: "+ data)

def handleSettingsCallback(chatId, data, callback):
  funs = {
    "timezone": handleChangeTimezone,
    "handle": handleSetUserHandlePrompt,
    "apikey": handleSetAuthorization,
    "notf": sendFriendSettingsButtons,
  }
  funs[data](chatId, "")
  tg.sendAnswerCallback(callback['id'])

#------ Notification Settings------

def getButtons(handle, ratingWatch, contestWatch):
  text1 = handle + " list ["+ ("X" if ratingWatch else " ") + "]"
  text2 = handle + " notify ["+ ("X" if contestWatch else " ") + "]"
  data1 = "friend_notf:" + handle + ";0;" + ("0" if ratingWatch else "1")
  data2 = "friend_notf:" + handle + ";1;" + ("0" if contestWatch else "1")
  return [{"text":text1, "callback_data":data1}, {"text":text2, "callback_data":data2}]

def getButtonRows(chatId):
  buttons = []
  friends = cf.getFriendsWithDetails(chatId)
  if friends == None:
    tg.sendMessage(chatId, "You don't have any friends :(")
    return

  for [handle, ratingWatch, contestWatch] in friends:
    buttons.append(getButtons(handle, ratingWatch == 1, contestWatch == 1))
  return buttons

def sendFriendSettingsButtons(chatId, msg):
  buttons = getButtonRows(chatId)

  replyMarkup = {"inline_keyboard": buttons}
  replyMarkup = json.dumps(replyMarkup)
  tg.sendMessage(chatId, "Click the buttons to change the friend settings.", replyMarkup)

def updateButtons(chatId, msg):
  buttons = getButtonRows(chatId)

  replyMarkup = {"inline_keyboard": buttons}
  replyMarkup = json.dumps(replyMarkup)
  tg.editMessageReplyMarkup(chatId, msg['message_id'], replyMarkup)


def handleFriendNotSettingsCallback(chatId, data, callback):
  [handle, button, gesetzt] = data.split(';')
  gesetzt = (gesetzt == '1')
  if button == "0":
    notf = "You will" + ("" if gesetzt else " no longer") + " see "+ handle +" on your list."
    db.setFriendSettings(chatId, handle, 'ratingWatch', gesetzt)
  else:
    notf = "You will" + ("" if gesetzt else " no longer") + " receive notifications for "+ handle +"."
    db.setFriendSettings(chatId, handle, 'contestWatch', gesetzt)
  tg.sendAnswerCallback(callback['id'], notf)

  updateButtons(chatId, callback['message'])

# ---- Set User Handle ------
def handleSetUserHandlePrompt(chatId, msg):
  global openCommandFunc
  openCommandFunc[chatId] = handleSetUserHandle
  tg.sendMessage(chatId, "Please enter your Codeforces handle:")

def handleSetUserHandle(chatId, handle):
  handle = util.cleanString(handle)
  userInfos = cf.getUserInfos([handle])
  if userInfos == False:
    tg.sendMessage(chatId, "No user with this handle! Try again:")
  else:
    del openCommandFunc[chatId]
    db.setUserHandle(chatId, handle)
    db.addFriends(chatId, [handle])
    #db.setFriendSettings(chatId, handle, "contestWatch", 0) #no solved notifications for yourself --YES
    tg.sendMessage(chatId, "Welcome `" + userInfos[0]['handle'] + "`. Your current rating is " +
      str(userInfos[0]['rating']) + ".")
    if not db.hasAuth(chatId):
      tg.sendMessage(chatId, "Do you want import your friends from Codeforces? Then, I need your Codeforces API key.")
      handleSetAuthorization(chatId, "")

# ------- Add API KEY -----
def handleAddSecret(chatId, req):
  db.setApiSecret(chatId, req)
  global openCommandFunc
  del openCommandFunc[chatId]
  util.log('new secret added for user ' + str(chatId))
  tg.sendMessage(chatId, "Key added. Your friends are now added.")

def handleAddKey(chatId, req):
  db.setApiKey(chatId, req)
  global openCommandFunc
  openCommandFunc[chatId] = handleAddSecret
  tg.sendMessage(chatId, "Enter your secret:")

def handleSetAuthorization(chatId, req):
  #offenes Request adden
  global openCommandFunc
  openCommandFunc[chatId] = handleAddKey
  tg.sendMessage(chatId, "Go to https://codeforces.com/settings/api and generate a key.\n"
  + "Then text me two seperate messages - the first one containing the key and the second one containing the secret")

#------ Start -------------
def handleStart(chatId, text):
  global openCommandFunc
  openCommandFunc[chatId] = handleSetTimezone
  tg.sendMessage(chatId, "*Welcome to the Codeforces Live Bot!*\n\n"
  + "You will receive reminders for upcoming Codeforces Contests. Please tell me your *timezone* so that "
  + "the contest start time will be displayed correctly. So text me the name of the city you live in, for example "
  + "'Munich'.")

# ------- Time zone -------------
def handleChangeTimezone(chatId, text):
  global openCommandFunc
  openCommandFunc[chatId] = handleSetTimezone
  tg.sendMessage(chatId, "Setting up your time zone... Please enter the city you live in:")

def handleSetTimezone(chatId, req):
  global openCommandFunc
  req = req.lstrip().rstrip()
  tz = util.getTimeZone(req)
  if not tz:
    tg.sendMessage(chatId, "Name lookup failed. Please use a different city:")
  else:
    del openCommandFunc[chatId]
    db.setTimezone(chatId, tz)
    tg.sendMessage(chatId, "Timezone set to '" + tz + "'")
    # if in setup after start, ask for user handle
    if not db.hasHandle(chatId):
      tg.sendMessage(chatId, "Now I need *your* handle.")
      handleSetUserHandlePrompt(chatId, "")

# ------ Other --------
def invalidCommand(cid, msg):
  tg.sendMessage(cid, "Invalid command!")

def noCommand(cid, msg):
  global openCommandFunc
  if cid in openCommandFunc:
    openCommandFunc[cid](cid, msg)
  else:
    invalidCommand(cid, msg)

#-----
def handleMessage(chatId, text):
  util.log("-> " + text + " <-")
  text = text.replace("@codeforces_live_bot", "")
  msgSwitch = {
    "/start": handleStart,
    "/rating": handleRatingRequest,
    "/friend_ratings":handleFriendRatingsRequest,
    "/add_friend":handleAddFriendRequest,
    "/settings":handleSettings,
    "/current_standings":standings.sendStandings,
    "/upcoming":upcoming.handleUpcoming
  }
  func = msgSwitch.get(util.cleanString(text), noCommand)
  func(str(chatId), text)

def initContestServices():
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
		handleMessage('0', msg)
	time.sleep(1000);

def startTelegramBot():
	initContestServices()
	rg.TelegramUpdateService().start()

"""
def mainLoop():
  cf.loadCurrentContests()
  analyseFriendStandings(True)
  callbacks = [
    (cf.loadCurrentContests, 3600, time.time()),
    (analyseFriendStandings, 30, 0),
    (tg.startPolling,1,0),
    (checkUpcomingContest,50,0)
  ]
  while True:
    for i in range(len(callbacks)):
      (fun, timeIt, lastTimeStamp) = callbacks[i]
      if time.time() - lastTimeStamp >= timeIt:
        callbacks[i] = (fun, timeIt, time.time())
        try:
          fun()
        except Exception as e:
          traceback.print_exc()
          util.log(traceback.format_exc(), isError=True)
    time.sleep(0.01)
"""
