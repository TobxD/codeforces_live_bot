import codeforces as cf
import telegram as tg
import util
from Table import Table

import requests
from collections import defaultdict

# ------ Current Standings	-------

standingsSent = defaultdict(lambda : defaultdict()) # [chatId][contest] = (msgId, msg)
cfPredictorUrl = "https://cf-predictor-frontend.herokuapp.com/GetNextRatingServlet?contestId="

def getRatingChanges(contestId):
	util.log('request rating changes from cf-predictor')
	try:
		r = requests.get(cfPredictorUrl + str(contestId), timeout=10)
	except requests.exceptions.Timeout as errt:
		util.log("Timeout on CF-predictor.", isError=True)
		return {}
	util.log('rating changes received')
	r = r.json()
	if r['status'] != 'OK':
		return {}
	r = r['result']
	handleToRatingChanges = {}
	for row in r:
		handleToRatingChanges[row['handle']] = (row['oldRating'], row['newRating'])
	return handleToRatingChanges

# if !sendIfEmpty and standings are empty then False is returned
def getFriendStandings(chat, contestId, sendIfEmpty=True):
	friends = cf.getFriends(chat)
	if len(friends) == 0:
		if sendIfEmpty:
			chat.sendMessage(("You have no friends :(\n"
				"Please add your API key in the settings or add friends with `/add_friend`."))
			util.log("user has no friends -> empty standings")
		return False
	standings = cf.getStandings(contestId, friends)
	if standings == False:
		#chat.sendMessage("Invalid contest or handle")
		util.log("failed to get standings for " + str(friends), isError=True)
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
					timeStr = util.formatSeconds(sub["bestSubmissionTimeSeconds"], sub["rejectedAttemptCount"] != 0)
					subs.append(timeStr)
				else:
					status = ""
					if sub["type"] == "PRELIMINARY" and contest['phase'] == 'SYSTEM_TEST' and "bestSubmissionTimeSeconds" in sub:
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
	id = chat.sendMessage(msg)
	if id != False:
		standingsSent[chat.chatId][contestId] = (id, msg)

def sendStandings(chat, msg):
	for c in cf.getCurrentContestsId():
		sendContestStandings(chat, c)

# updates only, if the standings-message has changed
def updateStandingsForChat(contest, chat):
	msgId, oldMsg = standingsSent[chat.chatId][contest]
	msg = getFriendStandings(chat, contest)
	if msg is False:
		return
	if oldMsg != msg:
		standingsSent[chat.chatId][contest] = (msgId, msg)
		chat.editMessageText(msgId, msg)
