import codeforces as cf
import telegram as tg
import util
import requests
from Table import Table

# ------ Current Standings	-------

standingsSent = {}
cfPredictorUrl = "https://cf-predictor-frontend.herokuapp.com/GetNextRatingServlet?contestId="

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

def getFriendStandings(chat, contestId):
	friends = cf.getFriends(chat)
	if len(friends) == 0:
		#chat.sendMessage("You have no friends :(")
		util.log("user has no friends -> empty standings")
		return
	standings = cf.getStandings(contestId, friends)
	util.log('standings received: ' + str(standings))
	if standings == False:
		#chat.sendMessage("Invalid contest or handle")
		util.log("failed to get standings for " + str(friends))
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
				elif sub["type"] == "PRELIMINARY" and contest['phase'] != 'SYSTEM_TEST' and "bestSubmissionTimeSeconds" in sub:
					subs.append("?")
				elif sub["rejectedAttemptCount"] > 0:
					subs.append("-" + str(sub["rejectedAttemptCount"]))
				else:
					subs.append("")
		nrow["body"] = subs
		res.append(nrow)
	table = Table(problems, res)
	msg += table.formatTable()
	return msg

def sendContestStandings(chat, contestId):
	global standingsSent
	id = chat.sendMessage(getFriendStandings(chat, contestId))
	if chat.chatId not in standingsSent:
		standingsSent[chat.chatId] = {}
	if id != False:
		standingsSent[chat.chatId][contestId] = id

def sendStandings(chat, msg):
	for c in cf.getCurrentContestsId():
		sendContestStandings(chat, c)

def updateStandingsForChat(contest, chat, messageId):
	msg = getFriendStandings(chat, contest)
	chat.editMessageText(messageId, msg)
