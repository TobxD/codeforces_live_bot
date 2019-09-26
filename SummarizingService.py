import codeforces as cf
import database as db
import telegram as tg
import standings
import UpdateService

class SummarizingService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 60)
		self._summarized = set()
		self._doTask(True)

	def _doTask(self, quiet=False):
		for c in cf.getCurrentContests():
			if cf.getContestStatus(c) == 'finished' and not c['id'] in self._summarized:
				self._summarized.add(c['id'])
				if not quiet:
					self._sendAllSummary(c)

	def _sendAllSummary(self, contest):
		for chatId in db.getAllChatPartners():
			chat = Chat.getChat(chatId)
			msg = contest['name'] + " has finished.\n"
			msg += self._getContestAnalysis(contest, chat)
			chat.sendMessage(msg)
			standings.sendContestStandings(chat, contest['id'])

	def _getContestAnalysis(self, contest, chat):
		msg = ""
		((minHandle, minRC, minOldR),
		 (maxHandle, maxRC, maxOldR),
		 (myRC, myOldR, nowBetter, nowWorse)) = self._getWinnerLooser(chat, contest['id'])
		if myRC is not None:
			msg += self._getYourPerformance(myRC, myOldR, nowBetter, nowWorse)
		if minRC < -30:
			msg += "📉 The looser of the day is `%s` with a rating loss of %s!\n" % (minHandle, minRC)
		elif minRC > 0:
			msg += "What a great contest!🎉\n"

		if maxRC > 30:
			msg += "🏆 Today's king is 👑`%s`👑 with a stunning rating win of +%s!\n" % (maxHandle, maxRC)
		elif maxRC < 0:
			msg += "What a terrible contest!😑\n"

		return msg

	def _getYourPerformance(self, myRC, myOldR, nowBetter, nowWorse):
		msg = ""
		if myOldR == -1: 
			return ""
		# took part and was rated
		if myRC < 0:
			msg += "Ohh that hurts.😑 You lost *%s* rating points." % myRC
			if myRC < -70:
				msg += " You should maybe look for a different hobby.💁🏻‍♂️👋🏻\n"
			else :
				msg += "\n"
			
		else:
			msg += "🎉 Nice! You gained *+%s* rating points.🎉\n" % myRC
			
		if len(nowBetter) > 0:
			l = ", ".join(["`"+n+"`" for n in nowBetter])
			msg += l + (" is" if len(nowBetter) == 1 else " are") + " now better than you👎🏻."
		msg += "\n"
		if len(nowWorse) > 0:
			l = ", ".join(["`"+n+"`" for n in nowWorse])
			msg += "You passed " + l + "👍🏻."
		msg += "\n"
		return msg

	def _getWinnerLooser(self, chat, contestId):
		curStandings = cf.getStandings(contestId, cf.getFriends(chatId))
		rows = curStandings["rows"]
		# are changes already applied?
		myRating = -1 if chat.handle is None else cf.getUserRating(chat.handle) 
		minRC, maxRC = 0, 0
		minOldR, maxOldR = -1, -1
		minHandle, maxHandle = 0, 0
		myRC, myOldR = None, myRating
		nowBetter, nowWorse = [], []
		ratingChanges = standings.getRatingChanges(contestId)
		for row in [r for r in rows if r["rank"] != 0]: #official results only
			handlename = row["party"]["members"][0]["handle"]
			if handlename in ratingChanges:
				(oldR, newR) = ratingChanges[handlename]
				ratingC = newR-oldR
				if ratingC < minRC:
					minRC, minOldR, minHandle = ratingC, oldR, handlename
				if ratingC > maxRC:
					maxRC, maxOldR, maxHandle = ratingC, oldR, handlename
				if handlename == chat.handle:
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
