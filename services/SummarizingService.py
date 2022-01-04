import random
import time
from collections import defaultdict

from codeforces import codeforces as cf
from utils import database as db
from codeforces import standings
from utils import util
from utils.util import logger
from services import UpdateService
from telegram import Chat

class SummarizingService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 60)
		self.name = "summarizeService"
		self.userRatings = defaultdict(lambda : -1)
		self._summarized = set()
		self._doTask(True)

	def _doTask(self, quiet=False):
		for c in cf.getCurrentContests():
			if cf.getContestStatus(c) == 'finished' and not c['id'] in self._summarized and cf.getStandings(c['id'], []):
				self._summarized.add(c['id'])
				if not quiet:
					self._sendAllSummary(c)

	def _sendAllSummary(self, contest):
		# cache rating for all users
		chats = [Chat.getChat(c) for c in db.getAllChatPartners()]

		# The getUserInfo command returns False if there is a unknown user in the list
		# the user is then removed by the CF error handling routine. A retry is neccessary though.
		retries = 20
		while retries > 0:
			handles = [c.handle for c in chats if c.handle]
			infos = cf.getUserInfos(handles)
			if infos:
				for info in infos:
					self.userRatings[info['handle']] = info.get('rating', -1)
				break
			retries -= 1
			time.sleep(5)
		logger.debug(f"sending summary for contest {contest['id']}. Cached {len(self.userRatings)} ratings in {20-retries+1} try.")

		for chat in chats:
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
			msg += self._getYourPerformance(myRC, myOldR, nowBetter, nowWorse, chat)
		if minRC <= -30 and not chat.polite:
			msg += "📉 The looser of the day is %s with a rating loss of %s!\n" % (util.formatHandle(minHandle, minRC+minOldR), minRC)
		elif minRC > 0:
			msg += "What a great contest!🎉\n"

		if maxRC >= 30:
			msg += "🏆 Today's king is 👑 %s 👑 with a stunning rating win of +%s!\n" % (util.formatHandle(maxHandle, maxRC+maxOldR), maxRC)
		elif maxRC < 0:
			msg += "What a terrible contest!😑\n"

		return msg

	def _getYourPerformance(self, myRC, myOldR, nowBetter, nowWorse, chat):
		funnyInsults = ["Maybe you should look for a different hobby.💁🏻‍♂️👋🏻",
										"Have you thought about actually solving the tasks next time?🤨",
										"Are you trying to get your rating below 0?🧐",
										"Tip for next time: solve more problems.☝🏻",
										"Fun fact: Continue like this and you have negative rating in " + str(-myOldR//(myRC if myRC != 0 else 1)) + " contests.📉",
										"My machine learning algorithm has found the perfect training problem for your level: Check out [this problem](https://codeforces.com/problemset/problem/1030/A) on CF.🤯",
										"Check out [this article](https://www.learnpython.org/en/Hello%2C_World%21), you can learn a lot from it!🐍"]
		funnyCompliments = ["Now you have more rating to loose in the next contest.😬",
												"`tourist` would be proud of you.☺️",
												str((2999-myOldR)//(myRC if myRC != 0 else 1)) + " more contest and you are a 👑Legendary Grandmaster."]
		if chat.polite:
			funnyInsults = ["No worries, you will likely increase your rating next time :)"]
			funnyCompliments = funnyCompliments[1:]
		msg = ""
		if myOldR == -1: 
			return ""
		# took part and was rated
		if myRC < 0:
			msg += "Ohh that hurts.😑 You lost *%s* rating points." % myRC
			if myRC < -60:
				msg += " " + funnyInsults[random.randint(0,len(funnyInsults)-1)]
		else:
			msg += "🎉 Nice! You gained *+%s* rating points.🎉" % myRC
			if myRC > 60:
				msg += " " + funnyCompliments[random.randint(0, len(funnyCompliments)-1)]
		msg += "\n"

		if util.getUserSmiley(myOldR) != util.getUserSmiley(myOldR+myRC):
			msg += "You are now a " + util.getUserSmiley(myOldR+myRC) + ".\n"
			
		if len(nowBetter) > 0:
			l = ", ".join([util.formatHandle(name, rating) for (name,rating) in nowBetter])
			msg += l + (" is" if len(nowBetter) == 1 else " are") + " now better than you👎🏻."
		msg += "\n"
		if len(nowWorse) > 0:
			l = ", ".join([util.formatHandle(name, rating) for (name,rating) in nowWorse])
			msg += "You passed " + l + "👍🏻."
		msg += "\n"
		return msg

	def _getWinnerLooser(self, chat, contestId):
		curStandings = cf.getStandings(contestId, cf.getListFriends(chat))
		rows = curStandings["rows"]
		# are changes already applied?
		myRating = self.userRatings[chat.handle] # could be -1 if CF requests fail 20 times - happens during new year special
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
					if myRating == myOldR or myRating == -1:
						myRating = myOldR + myRC

		# get better and worse
		# TODO what about people not participating which you passed?
		for row in [r for r in rows if r["rank"] != 0]: #official results only
			handlename = row["party"]["members"][0]["handle"]
			if handlename in ratingChanges:
				(oldR, newR) = ratingChanges[handlename]
				if myRating != -1 and oldR < myOldR and newR > myRating:
					nowBetter.append((handlename, newR))
				if myRating != -1 and oldR > myOldR and newR < myRating:
					nowWorse.append((handlename, newR))


		return ((minHandle, minRC, minOldR), (maxHandle, maxRC, maxOldR),
			(myRC, myOldR, nowBetter, nowWorse))
