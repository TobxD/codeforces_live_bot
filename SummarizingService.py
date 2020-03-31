import codeforces as cf
import database as db
import telegram as tg
import standings
import util
import UpdateService
import Chat

class SummarizingService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 60)
		self.name = "summarizeService"
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
			msg = self._getContestAnalysis(contest, chat)
			if len(msg) > 0:  # only send if analysis is not empty
				msg = contest['name'] + " has finished:\n" + msg
				chat.sendMessage(msg)
			standings.sendContestStandings(chat, contest['id'], sendIfEmpty=False)

	def _getContestAnalysis(self, contest, chat):
		msg = ""
		((minHandle, minRC, minOldR),
		 (maxHandle, maxRC, maxOldR),
		 (myRC, myOldR, nowBetter, nowWorse)) = self._getWinnerLooser(chat, contest['id'])
		if myRC is not None:
			msg += self._getYourPerformance(myRC, myOldR, nowBetter, nowWorse)
		if minRC <= -30:
			msg += "📉 The looser of the day is %s `%s` with a rating loss of %s!\n" % (util.getUserSmiley(minRC+minOldR), minHandle, minRC)
		elif minRC > 0:
			msg += "What a great contest!🎉\n"

		if maxRC >= 30:
			msg += "🏆 Today's king is 👑 %s`%s` 👑 with a stunning rating win of +%s!\n" % (util.getUserSmiley(maxRC+maxOldR), maxHandle, maxRC)
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
			if myOldR >= 2000 and myRC < -70:
				msg += " You should maybe look for a different hobby.💁🏻‍♂️👋🏻\n"
			else :
				msg += "\n"
			
		else:
			msg += "🎉 Nice! You gained *+%s* rating points.🎉\n" % myRC
		if util.getUserSmiley(myOldR) != util.getUserSmiley(myOldR+myRC):
			msg += "You are now a " + util.getUserSmiley(myOldR+myRC) + ".\n"
			
		if len(nowBetter) > 0:
			l = ", ".join([util.getUserSmiley(rating) + "`" + name + "`" for (name,rating) in nowBetter])
			msg += l + (" is" if len(nowBetter) == 1 else " are") + " now better than you👎🏻."
		msg += "\n"
		if len(nowWorse) > 0:
			l = ", ".join([util.getUserSmiley(rating) + "`" + name + "`" for (name,rating) in nowWorse])
			msg += "You passed " + l + "👍🏻."
		msg += "\n"
		return msg

	def _getWinnerLooser(self, chat, contestId):
		curStandings = cf.getStandings(contestId, cf.getFriends(chat))
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
				if ratingC < minRC and oldR >= 2000: # looser of the day has to have rating >= 2000
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
					nowBetter.append((handlename, newR))
				if oldR > myOldR and newR < myRating:
					nowWorse.append((handlename, newR))


		return ((minHandle, minRC, minOldR), (maxHandle, maxRC, maxOldR),
			(myRC, myOldR, nowBetter, nowWorse))
