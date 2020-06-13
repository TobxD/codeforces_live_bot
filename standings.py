import requests, threading, time
from collections import defaultdict

import bot
import codeforces as cf
import telegram as tg
import util
from Table import Table
from util import logger

# ------ Current Standings	-------

standingsSentLock = threading.Lock()
standingsSent = defaultdict(lambda : defaultdict()) # [chatId][contest] = (msgId, msg)

cfPredictorLock = threading.Lock()
handleToRatingChanges = defaultdict(lambda : {})
cfPredictorLastRequest = defaultdict(lambda : 0)
cfPredictorUrl = "https://cf-predictor-frontend.herokuapp.com/GetNextRatingServlet?contestId="

def getRatingChanges(contestId):
	with cfPredictorLock:
		if time.time() > cfPredictorLastRequest[contestId] + 20:
			logger.debug('request rating changes from cf-predictor')
			cfPredictorLastRequest[contestId] = time.time()
			try:
				r = requests.get(cfPredictorUrl + str(contestId), timeout=10)
			except requests.exceptions.Timeout as errt:
				logger.error("Timeout on CF-predictor.")
				return handleToRatingChanges[contestId]
			if r.status_code != requests.codes.ok:
				logger.error("CF-Predictor request failed with code "+ str(r.status_code) + ", "+ str(r.reason))
				return handleToRatingChanges[contestId]
			logger.debug('rating changes received')
			r = r.json()
			if r['status'] != 'OK':
				return handleToRatingChanges[contestId]
			r = r['result']
			handleToRatingChanges[contestId] = {}
			for row in r:
				handleToRatingChanges[contestId][row['handle']] = (row['oldRating'], row['newRating'])
			cfPredictorLastRequest[contestId] = time.time()
		return handleToRatingChanges[contestId]

# if !sendIfEmpty and standings are empty then False is returned
def getFriendStandings(chat, contestId, sendIfEmpty=True):
	friends = cf.getFriends(chat)
	if len(friends) == 0:
		if sendIfEmpty:
			chat.sendMessage(("You have no friends :(\n"
				"Please add your API key in the settings or add friends with `/add_friend`."))
			logger.debug("user has no friends -> empty standings")
		return False
	standings = cf.getStandings(contestId, friends)
	if standings == False:
		logger.debug("failed to get standings for " + str(friends))
		return False
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
				if sub["points"] > 0:
					val = "+"
				elif sub["rejectedAttemptCount"] > 0:
					val = "-"

				if sub["rejectedAttemptCount"] > 0:
					val += str(sub["rejectedAttemptCount"])
				subs.append(val)
		else:		#official
			handlename = row["party"]["members"][0]["handle"]
			#rating changes
			if handlename in ratingChanges:
				(oldR, newR) = ratingChanges[handlename]
				ratingC = newR-oldR
				ratingC = ("+" if ratingC >= 0 else "") + str(ratingC)
				nrow["head2"] = str(oldR) + " -> " + str(newR) + " (" + ratingC + ")"

			if row["party"]["participantType"] == "VIRTUAL": #mark virtual participants
				handlename = "* " + handlename
			if len(handlename) > 11:
				handlename = handlename[:10] + "…"
			nrow["head"] = handlename + " (" + str(row["rank"]) +".)"
			for sub in row["problemResults"]:
				if sub["points"] > 0:
					timeStr = util.formatSeconds(sub["bestSubmissionTimeSeconds"], sub["rejectedAttemptCount"] != 0, longOk=False)
					subs.append(timeStr)
				else:
					status = ""
					if sub["type"] == "PRELIMINARY" and contest['phase'] == 'SYSTEM_TEST':
						status = "?"
					if sub["rejectedAttemptCount"] > 0:
						status += "-" + str(sub["rejectedAttemptCount"])
					subs.append(status)
		nrow["body"] = subs
		res.append(nrow)
	if not sendIfEmpty and len(res) == 0:
		return False
	table = Table(problems, res)
	msg += table.formatTable()
	return msg

def sendContestStandings(chat, contestId, sendIfEmpty=True):
	global standingsSent
	msg = getFriendStandings(chat, contestId, sendIfEmpty=sendIfEmpty)
	if msg is False: # CF is down or (standings are emtpy and !sendIfEmpty)
		return
	def callbackFun(id):
		if id != False:
			with standingsSentLock:
				standingsSent[chat.chatId][contestId] = (id, msg)
	chat.sendMessage(msg, callback=callbackFun)

def sendStandings(chat, msg):
	bot.setOpenCommandFunc(chat.chatId, None)
	contestIds = cf.getCurrentContestsId()
	if len(contestIds) > 0:
		for c in contestIds:
			sendContestStandings(chat, c)
	else:
		chat.sendMessage("No contests in the last two days 🤷🏻")

# updates only, if message exists and the standings-message has changed
def updateStandingsForChat(contest, chat):
	with standingsSentLock:
		if contest not in standingsSent[chat.chatId]:
			return
	logger.debug('update standings for ' + str(chat.chatId) + '!')
	msg = getFriendStandings(chat, contest)
	if msg is False:
		return
	edit = False
	with standingsSentLock:
		if contest not in standingsSent[chat.chatId]:
			return
		msgId, oldMsg = standingsSent[chat.chatId][contest]
		if tg.shortenMessage(oldMsg) != tg.shortenMessage(msg):
			standingsSent[chat.chatId][contest] = (msgId, msg)
			edit = True
	if edit:
		chat.editMessageText(msgId, msg)
