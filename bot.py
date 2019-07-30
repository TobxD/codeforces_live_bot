import json, requests, time, datetime
from pytz import timezone
import sys, traceback, random, hashlib
import database as db
import telegram as tg
import codeforces as cf
import util


cfPredictorUrl = "https://cf-predictor-frontend.herokuapp.com/GetNextRatingServlet?contestId="
openCommandFunc = {}
standingsSent = {}
points = {}
notFinal = {}


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

# ------ Current Standings  -------

def getRatingChanges(contestId):
  util.log('request rating changes from cf-predictor')
  r = requests.get(cfPredictorUrl + str(contestId))
  util.log('rating changes received')
  r = r.json()
  if r['status'] != 'OK':
    return {}
  r = r['result']
  handleToRatingChanges = {}
  for row in r:
    handleToRatingChanges[row['handle']] = (row['oldRating'], row['newRating'])
  return handleToRatingChanges

def getFriendStandings(chatId, contestId):
  friends = cf.getFriends(chatId)
  if len(friends) == 0:
    #tg.sendMessage(chatId, "You have no friends :(")
    return
  standings = cf.getStandings(contestId, friends)
  if standings == False:
    #tg.sendMessage(chatId, "Invalid contest or handle")
    return
  contest = standings["contest"]
  msg = contest["name"] + " "
  if contest["relativeTimeSeconds"] < contest["durationSeconds"]:
    msg += "*"+ util.formatSeconds(contest["relativeTimeSeconds"]) + "* / "
    msg += util.formatSeconds(contest["durationSeconds"]) + "\n\n"
  elif contest['phase'] != 'FINISHED':
    msg += "*TESTING*\n\n"
  else:
    msg += "*FINISHED*\n\n"

  problems = [p["index"] for p in standings["problems"]]
  ratingChanges = getRatingChanges(contestId)

  rows = standings["rows"]
  res = []
  for row in rows:
    nrow = {}
    subs = []
    if row["rank"] == 0: #unofficial
      handle = row["party"]["members"][0]["handle"]
      nrow["head"] = "* " + handle
      for sub in row["problemResults"]:
        val = ""
        if sub["type"] == "PRELIMINARY":
          val = "?"
        else:
          if sub["points"] > 0:
            val = "+"
          elif sub["rejectedAttemptCount"] > 0:
            val = "-"

          if sub["rejectedAttemptCount"] > 0:
            val += str(sub["rejectedAttemptCount"])
        subs.append(val)
    else:   #official
      handlename = row["party"]["members"][0]["handle"]
      #rating changes
      if handlename in ratingChanges:
        (oldR, newR) = ratingChanges[handlename]
        ratingC = newR-oldR
        ratingC = ("+" if ratingC >= 0 else "") + str(ratingC)
        nrow["head2"] = str(oldR) + " -> " + str(newR) + " (" + ratingC + ")"

      if len(handlename) > 11:
        handlename = handlename[:10] + "…"
      nrow["head"] = handlename + " (" + str(row["rank"]) +".)"
      for sub in row["problemResults"]:
        if sub["points"] > 0:
          timeStr = util.formatSeconds(sub["bestSubmissionTimeSeconds"], sub["rejectedAttemptCount"] != 0)
          subs.append(timeStr)
        elif sub["rejectedAttemptCount"] > 0:
          subs.append("-" + str(sub["rejectedAttemptCount"]))
        else:
          subs.append("")
    nrow["body"] = subs
    res.append(nrow)
  msg += util.formatTable(problems, res)
  return msg

def getWinnerLooser(chatId, contestId):
  myHandle = db.getHandle(chatId)
  standings = cf.getStandings(contestId, cf.getFriends(chatId))
  rows = standings["rows"]
  # are changes already applied?
  myRating = -1 if myHandle is None else cf.getUserRating(myHandle) 
  minRC, maxRC = 0, 0
  minOldR, maxOldR = -1, -1
  minHandle, maxHandle = 0, 0
  myRC, myOldR = None, myRating
  nowBetter, nowWorse = [], []
  ratingChanges = getRatingChanges(contestId)
  for row in [r for r in rows if r["rank"] != 0]: #official results only
    handlename = row["party"]["members"][0]["handle"]
    if handlename in ratingChanges:
      (oldR, newR) = ratingChanges[handlename]
      ratingC = newR-oldR
      if ratingC < minRC:
        minRC, minOldR, minHandle = ratingC, oldR, handlename
      if ratingC > maxRC:
        maxRC, maxOldR, maxHandle = ratingC, oldR, handlename
      if handlename == myHandle:
        myRC, myOldR = ratingC, oldR
        if myRating == myOldR:
          myRating += myRC

  # get better and worse
  # TODO what about people not participating which you passed?
  for row in [r for r in rows if r["rank"] != 0]: #official results onl
    handlename = row["party"]["members"][0]["handle"]
    if handlename in ratingChanges:
      (oldR, newR) = ratingChanges[handlename]
      if oldR < myOldR and newR > myRating:
        nowBetter.append(handlename)
      if oldR > myOldR and newR < myRating:
        nowWorse.append(handlename)


  return ((minHandle, minRC, minOldR), (maxHandle, maxRC, maxOldR),
    (myRC, myOldR, nowBetter, nowWorse))

def sendContestStandings(chatId, contestId):
  global standingsSent
  id = tg.sendMessage(chatId, getFriendStandings(chatId, contestId))
  if chatId not in standingsSent:
    standingsSent[chatId] = {}
  if id != False:
    standingsSent[chatId][contestId] = id

def notifyTaskSolved(handle, task, rejectedAttemptCount, time, official):
  if official:
    msg = "💡* ["+ util.formatSeconds(time) +"]* "
  else:
    msg = "💡 *[UPSOLVING]* "
  msg += "`"+handle + "` has solved task " + task
  if rejectedAttemptCount > 0:
    msg += " *after " + str(rejectedAttemptCount) + " wrong submissions*"
  for chatId in db.getWhoseFriends(handle):
    tg.sendMessage(chatId, msg)

def notifyTaskTested(handle, task, accepted):
  funnyInsults = ["%s faild on system tests for task %s. What a looser.💩",
                  "%s should probably look for a different hobby.💁🏻‍♂️ He faild the system tests for task %s.",
                  "📉 %s failed the system tests for task %s. *So sad! It's true.*",
                  "Div. 3 is near for %s 👋🏻. He failed the system tests for task %s."]
  if accepted:
    msg = "✔️ You got accepted on system tests for task " + task
    tg.sendMessage(db.getChatId(handle), msg)
  else:
    if cf.getUserRating(handle) >= 1800:
      insult = funnyInsults[random.randint(0,len(funnyInsults)-1)]
      msg = insult % (handle, task)
    else:
      msg = handle + " failed on system tests for task " + task
    
    for chatId in db.getWhoseFriends(handle):
      tg.sendMessage(chatId, msg)

def sendStandings(chatId, msg):
  for c in cf.getCurrentContestsId():
    sendContestStandings(chatId, c)

def updateStadingForUser(contest, user, messageId):
  msg = getFriendStandings(user, contest)
  tg.editMessageText(user, messageId, msg)

def updateStandings(contest, users):
  global standingsSent
  for user in users:
    if user not in standingsSent:
      standingsSent[user] = {}
    if contest in standingsSent[user]:
      util.log('update stadings for ' + str(user) + '!')
      updateStadingForUser(contest, user, standingsSent[user][contest])

def analyseFriendStandings(firstRead=False):
  global standingsSent
  global points
  global notFinal
  friends = db.getAllFriends()
  for c in cf.getCurrentContestsId():
    if c not in points:
      points[c] = {}
    if c not in notFinal:
      notFinal[c] = {}
    lastPoints = points[c]
    standings = cf.getStandings(c, friends)
    if standings == False:
      return
    results = standings['rows']
    #{"handle":[0,3], }
    for r in results:
      handle = r["party"]["members"][0]["handle"]
      if handle not in lastPoints:
        lastPoints[handle] = []
      if handle not in notFinal[c]:
        notFinal[c][handle] = []
      for taski in range(len(r["problemResults"])):
        task = r["problemResults"][taski]
        flag = False
        taskName = standings["problems"][taski]["index"]
        if task["points"] > 0 and taski not in lastPoints[handle]:
          #notify all users who have this friend
          if not firstRead:
            notifyTaskSolved(handle, taskName, task["rejectedAttemptCount"],
                 task["bestSubmissionTimeSeconds"], r["rank"] != 0)
            # now updating every 30sec during contest
            # update only if after contest
            if standings["contest"]['phase'] == 'FINISHED':
              updateStandings(c, db.getWhoseFriends(handle, allList=True))
          lastPoints[handle].append(taski)
          flag = True
          if task['type'] == 'PRELIMINARY' and (taski not in notFinal[c][handle]):
            util.log('adding non-final task ' + str(taski) + ' for user ' + str(handle))
            notFinal[c][handle].append(taski)
        if task['type'] == 'FINAL' and (taski in notFinal[c][handle]):
          util.log('finalizing non-final task ' + str(taski) + ' for user ' + str(handle))
          notFinal[c][handle].remove(taski)
          notifyTaskTested(handle, taskName, task['points'] > 0)
          updateStandings(c, db.getWhoseFriends(handle, allList=True))
    if standings["contest"]['phase'] != 'FINISHED':
      updateStandings(c, db.getAllChatPartners())
# ------- Upcoming Contests -----




def getDescription(contest, chatId, timez = None):
  if timez is None:
    timez = db.getUserTimezone(chatId)
  tim = contest['startTimeSeconds']

  timeLeft = int(contest['startTimeSeconds'] - time.time())
  delta = datetime.timedelta(seconds=timeLeft)

  timeStr = "*" + util.displayTime(tim, timez)
  timeStr += '* (in ' + ':'.join(str(delta).split(':')[:2]) + ' hours' + ')'

  res = timeStr.ljust(35)
  res += ":\n" + contest['name'] + ""
  res += '\n'
  return res

def handleUpcoming(chatId, req):
  timez = db.getUserTimezone(chatId)
  msg = ""
  for c in sorted(cf.getFutureContests(), key=lambda x: x['startTimeSeconds']):
    if msg != "":
      msg += "\n"
    msg += getDescription(c, chatId, timez)
  tg.sendMessage(chatId, msg)

def notifyAllUpcoming(contest):
  for chatId in db.getAllChatPartners():
    description = getDescription(contest, chatId)
    tg.sendMessage(chatId, description)

def getYourPerformance(myRC, myOldR, nowBetter, nowWorse):
  msg = ""
  if myOldR == -1: 
    return ""
  # took part and was rated
  if myRC < 0:
    msg += "Ohh that hurts.😑 You lost *%s* rating points." % myRC
    if myRC < -70:
      msg += "You should maybe look for a different hobby.💁🏻‍♂️👋🏻\n"
    else :
      msg += "\n"
    
  else:
    msg += "🎉 Nice! You gained *+%s* rating points.🎉\n" % myRC
    
  if len(nowBetter) > 0:
    l = ", ".join(["`"+n+"`" for n in nowBetter])
    msg += l + " are now better than you👎🏻."
  msg += "\n"
  if len(nowWorse) > 0:
    l = ", ".join(["`"+n+"`" for n in nowWorse])
    msg += "You passed " + l + "👍🏻."
  msg += "\n"
  return msg

def getContestAnalysis(contest, chatId):
  msg = ""
  ((minHandle, minRC, minOldR),
   (maxHandle, maxRC, maxOldR),
   (myRC, myOldR, nowBetter, nowWorse)) = getWinnerLooser(chatId, contest['id'])
  if myRC is not None:
    msg += getYourPerformance(myRC, myOldR, nowBetter, nowWorse)
  if minRC < -30:
    msg += "📉 The looser of the day is `%s` with a rating loss of %s!\n" % (minHandle, minRC)
  elif minRC > 0:
    msg += "What a great contest!🎉\n"

  if maxRC > 30:
    msg += "🏆 Today's king is 👑`%s`👑 with a stunning rating win of +%s!\n" % (maxHandle, maxRC)
  elif minRC < 0:
    msg += "What a terrible contest!😑\n"

  return msg
    
def sendAllSummary(contest):
  for chatId in db.getAllChatPartners():
    msg = contest['name'] + " has finished.\n"
    msg += getContestAnalysis(contest, chatId)
    tg.sendMessage(chatId, msg)
    sendContestStandings(chatId, contest['id'])

notified = {}
summarized = set()

def checkUpcomingContest():
  global notified
  global summarized
  notifyTimes = [3600*24+59, 3600*2+59, -100000000]
  for c in cf.getFutureContests():
    timeLeft = c['startTimeSeconds'] - time.time()
    endtime = c['startTimeSeconds'] + c['durationSeconds']
    for i in range(len(notifyTimes)):
      if timeLeft <= notifyTimes[notified.get(c['id'], 0)]:
        notified[c['id']] = notified.get(c['id'], 0) + 1
        notifyAllUpcoming(c)
  # current contests
  for c in cf.getCurrentContests():
    if cf.getContestStatus(c) == 'finished' and not c['id'] in summarized:
      summarized.add(c['id'])
      sendAllSummary(c)


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
  msgSwitch = {
    "/start": handleStart,
    "/rating": handleRatingRequest,
    "/friend_ratings":handleFriendRatingsRequest,
    "/add_friend":handleAddFriendRequest,
    "/settings":handleSettings,
    "/current_standings":sendStandings,
    "/upcoming": handleUpcoming
  }
  func = msgSwitch.get(util.cleanString(text), noCommand)
  func(str(chatId), text)


def mainLoop():
  # with -r restart and dont send msg for 30sec
  if len(sys.argv) >= 2 and sys.argv[1] == "-r":
    tg.RESTART = time.time()
  else:
    tg.RESTART = 0
  tg.readRequestUrl()

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
