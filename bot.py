import json, requests, time
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
  if userInfos == False:
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
    tg.sendMessage(chatId, "User `" + userInfos[0]['handle'] + "` with rating " +
      str(userInfos[0]['rating']) + " added.")

def handleAddFriendRequest(chatId, req):
  #offenes Request adden
  global openCommandFunc
  openCommandFunc[chatId] = handleAddFriendRequestCont
  tg.sendMessage(chatId, "Codeforces handle:")

#------ Notification Settings------

def getButtons(handle, ratingWatch, contestWatch):
  text1 = handle + " list ["+ ("X" if ratingWatch else " ") + "]"
  text2 = handle + " notify ["+ ("X" if contestWatch else " ") + "]"
  data1 = handle + ";0;" + ("0" if ratingWatch else "1")
  data2 = handle + ";1;" + ("0" if contestWatch else "1")
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

def handleCallbackQuery(callback):
  chatId = callback['message']['chat']['id']
  data = callback['data']
  [handle, button, gesetzt] = data.split(';')
  if button == "0":
    notf = "You will " + ("" if gesetzt else "no longer") + " see "+ handle +" on your list."
    db.setFriendSettings(chatId, handle, 'ratingWatch', gesetzt)
  else:
    notf = "You will " + ("" if gesetzt else "no longer") + " receive notifications for "+ handle +"."
    db.setFriendSettings(chatId, handle, 'contestWatch', gesetzt)
  tg.sendAnswerCallback(callback['id'], notf)

  if 'message' in callback:
    updateButtons(chatId, callback['message'])
  else:
    log("Message probably too old")

# ------ Current Standings  -------

def getRatingChanges(contestId):
  r = requests.get(cfPredictorUrl + str(contestId))
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
    tg.sendMessage(chatId, "You have no friends :(")
    return
  standings = cf.getStandings(contestId, friends)
  if standings == False:
    tg.sendMessage(chatId, "Invalid contest or handle")
    return
  contest = standings["contest"]
  msg = contest["name"] + " "
  if contest["relativeTimeSeconds"] >= contest["durationSeconds"]:
    msg += "*FINISHED*\n\n"
  else:
    msg += "*"+ util.formatSeconds(contest["relativeTimeSeconds"]) + "* / "
    msg += util.formatSeconds(contest["durationSeconds"]) + "\n\n"

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

def sendContestStandings(chatId, contestId):
  global standingsSent
  id = tg.sendMessage(chatId, getFriendStandings(chatId, contestId))
  if chatId not in standingsSent:
    standingsSent[chatId] = {}
  if id != False:
    standingsSent[chatId][contestId] = id
  print('standings initialized:')
  print(standingsSent)

def notifyTaskSolved(handle, task, rejectedAttemptCount, time, official):
  if official:
    msg = "*["+ util.formatSeconds(time) +"]* "
  else:
    msg = "*[UPSOLVING]* "
  msg += "`"+handle + "` has solved task " + task
  if rejectedAttemptCount > 0:
    msg += " *after " + str(rejectedAttemptCount) + " wrong submissions*"
  for chatId in db.getWhoseFriends(handle):
    tg.sendMessage(chatId, msg)

def notifyTaskTested(handle, task, accepted):
  if accepted:
    msg = handle + " got accepted on system tests for task " + task
  else:
    msg = handle + " failed on system tests for task " + task
  for chatId in db.getWhoseFriends(handle):
    tg.sendMessage(chatId, msg)

def sendStandings(chatId, msg):
  for c in cf.getCurrentContests():
    sendContestStandings(chatId, c)

def updateStadingForUser(contest, user, messageId):
  msg = getFriendStandings(user, contest)
  tg.editMessageText(user, messageId, msg)

def updateStandings(contest, users):
  global standingsSent
  for user in users:
    if user not in standingsSent:
      standingsSent[user] = {}
    util.log('update stadings for ' + str(user) + '?')
    util.log('standingsSent: ' + str(standingsSent))
    if contest in standingsSent[user]:
      util.log('update stadings for ' + str(user) + '!')
      updateStadingForUser(contest, user, standingsSent[user][contest])

def analyseFriendStandings(firstRead=False):
  global standingsSent
  print('standings at other point:')
  print(standingsSent)
  global points
  global notFinal
  friends = db.getAllFriends()
  for c in cf.getCurrentContests():
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
        notFinal[c][handle] = {}
      for taski in range(len(r["problemResults"])):
        task = r["problemResults"][taski]
        flag = False
        if task["points"] > 0 and taski not in lastPoints[handle]:
          #notify all users who have this friend
          taskName = standings["problems"][taski]["index"]
          if not firstRead:
            notifyTaskSolved(handle, taskName, task["rejectedAttemptCount"],
                 task["bestSubmissionTimeSeconds"], r["rank"] != 0)
            updateStandings(c, db.getWhoseFriends(handle))
          lastPoints[handle].append(taski)
          flag = True
          if task['type'] == 'PRELIMINARY':
            notFinal[c][handle].append(taski)
        if task['type'] == 'FINAL' and taski in notFinal[c][handle]:
          notFinal[c][handle].remove(taski)
          notifyTaskTested(handle, taskName, task['points'] > 0)
          updateStandings(c, db.getWhoseFriends(handle))

# ------- Add API KEY -----
def handleAddSecret(chatId, req):
  db.setApiSecret(chatId, req)
  global openCommandFunc
  openCommandFunc[chatId] = handleAddFriendRequestCont
  util.log('new secret added for user ' + str(chatId))
  tg.sendMessage(chatId, "Key added. Your friends are now added. Please enter your own handle:")

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
  msgSwitch = {
    "/rating": handleRatingRequest,
    "/friend_ratings":handleFriendRatingsRequest,
    "/add_friend":handleAddFriendRequest,
    "/set_authorization":handleSetAuthorization,
    "/current_standings":sendStandings,
    "/friend_settings":sendFriendSettingsButtons
  }
  func = msgSwitch.get(util.cleanString(text), noCommand)
  func(chatId, text)

def mainLoop():
  tg.readRequestUrl()

  cf.loadCurrentContests()
  analyseFriendStandings(True)
  callbacks = [
  (cf.loadCurrentContests, 3600, time.time()),
  (analyseFriendStandings, 30, 0),
  (tg.startPolling,1,0)
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
    time.sleep(0.01)

if __name__ == "__main__":
  mainLoop()
