import UpdateService
import telegram as tg
import codeforces as cf
import util
import database as db
import standings
import Chat

import random
from collections import defaultdict
from threading import Thread

class AnalyseStandingsService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 30)
		self.name = "analyseStandings"
		self._points = defaultdict(lambda : defaultdict(list))
		self._notFinal = defaultdict(lambda : defaultdict(list))
		self._doTask(True)

	def _notifyTaskSolved(self, handle, task, rejectedAttemptCount, time, official):
		if official:
			msg = "💡* ["+ util.formatSeconds(time) +"]* "
		else:
			msg = "💡 *[UPSOLVING]* "
		msg += "`"+handle + "` has solved task " + task
		if rejectedAttemptCount > 0:
			msg += " *after " + str(rejectedAttemptCount) + " wrong submissions*"
		for chatId in db.getWhoseFriends(handle):
			Thread(target=Chat.getChat(chatId).sendMessage, args=(msg,), name="sendMsg").start()

	def _notifyTaskTested(self, handle, task, accepted):
		funnyInsults = ["%s faild on system tests for task %s. What a looser.💩",
										"%s should probably look for a different hobby.💁🏻‍♂️ He failed the system tests for task %s.",
										"📉 %s failed the system tests for task %s. *So sad! It's true.*",
										"Div. 3 is near for %s 👋🏻. He failed the system tests for task %s."]
		if accepted:
			msg = "✔️ You got accepted on system tests for task " + task
		else:
			if cf.getUserRating(handle) >= 1800:
				insult = funnyInsults[random.randint(0,len(funnyInsults)-1)]
				msg = insult % (handle, task)
			else:
				msg = handle + " failed on system tests for task " + task
		for chatId in db.getChatIds(handle):
			Thread(target=Chat.getChat(chatId).sendMessage, args=(msg,), name="sendMsg").start()

	def _updateStandings(self, contest, chatIds):
		for chatId in chatIds:
			chat = Chat.getChat(chatId)
			if contest in standings.standingsSent[chatId]:
				util.log('update stadings for ' + str(chatId) + '!')
				standings.updateStandingsForChat(contest, chat)

	def _analyseRow(self, contestId, row, ranking, firstRead):
		handle = row["party"]["members"][0]["handle"]
		pointsList = self._points[contestId][handle]
		for taski in range(len(row["problemResults"])):
			task = row["problemResults"][taski]
			taskName = ranking["problems"][taski]["index"]
			if task["points"] > 0 and taski not in pointsList:
				if not firstRead:
					Thread(target=self._notifyTaskSolved, args=(handle, taskName, task["rejectedAttemptCount"],
							 task["bestSubmissionTimeSeconds"], row["rank"] != 0), name="notifySolved").start()
					if ranking["contest"]['phase'] == 'FINISHED':
						Thread(target=self._updateStandings, args=(contestId, db.getWhoseFriends(handle, allList=True)), name="updStandings").start()
				pointsList.append(taski)
				if task['type'] == 'PRELIMINARY' and (taski not in self._notFinal[contestId][handle]):
					util.log('adding non-final task ' + str(taski) + ' for user ' + str(handle))
					self._notFinal[contestId][handle].append(taski)
			if task['type'] == 'FINAL' and (taski in self._notFinal[contestId][handle]):
				util.log('finalizing non-final task ' + str(taski) + ' for user ' + str(handle))
				self._notFinal[contestId][handle].remove(taski)
				Thread(target=self._notifyTaskTested, args=(handle, taskName, task['points'] > 0), name="notifyTested").start()
				Thread(target=self._updateStandings, args=(contestId, db.getWhoseFriends(handle, allList=True)), name="updStandings").start()

	def _analyseContest(self, contestId, friends, firstRead):
		ranking = cf.getStandings(contestId, friends)
		if ranking is False:
			return
		results = ranking['rows']
		for row in results:
			self._analyseRow(contestId, row, ranking, firstRead)
		if ranking['contest']['phase'] != 'FINISHED' and not firstRead:
			Thread(target=self._updateStandings, args=(contestId, db.getAllChatPartners()), name="updStandings").start()

	# analyses the standings
	def _doTask(self, firstRead=False):
		friends = db.getAllFriends()
		for contestId in cf.getCurrentContestsId():
			Thread(target=self._analyseContest, args=(contestId, friends, firstRead), name="analyseContest"+str(contestId)).start()
