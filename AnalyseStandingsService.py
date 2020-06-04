import UpdateService
import codeforces as cf
import util
from util import logger
import database as db
import standings
import Chat
from typing import List

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
		msg += util.formatHandle(handle) + " has solved task " + task
		if rejectedAttemptCount > 0:
			msg += " *after " + str(rejectedAttemptCount) + " wrong submissions*"
		for chatId in db.getWhoseFriends(handle):
			Chat.getChat(chatId).sendMessage(msg)

	def _notifyTaskTested(self, handle, task, accepted):
		funnyInsults = ["%s failed on system tests for task %s. What a looser.💩",
										"%s should probably look for a different hobby.💁🏻‍♂️ The system tests failed for task %s.",
										"📉 %s failed the system tests for task %s. *So sad! It's true.*",
										"%s didn't manage to solve task %s. The system tests failed. You can remove this friend using the command `/remove_friend`👋🏻",
										"Hmmm...🤔 Probably the Codeblocks debugger did not work for %s. The solution for task %s was not good enough. It failed on system tests.",
										"Div. 5 is near for %s 👋🏻. The system tests failed for task %s.",
										"%s failed systest for task %s. Did they hardcode the samples?"]
		if accepted:
			msg = "✔️ You got accepted on system tests for task " + task
			for chatId in db.getChatIds(handle): # only to user with this handle
				Chat.getChat(chatId).sendMessage(msg)
		else:
			insult = funnyInsults[random.randint(0,len(funnyInsults)-1)]
			msg = insult % (util.formatHandle(handle), task)
			for chatId in db.getWhoseFriends(handle): # to all users with this friend
				Chat.getChat(chatId).sendMessage(msg)

	def _updateStandings(self, contest, chatIds : List[str]):
		for chatId in chatIds:
			chat = Chat.getChat(chatId)
			logger.debug('update standings for ' + str(chatId) + '!')
			standings.updateStandingsForChat(contest, chat)

	def _analyseRow(self, contestId, row, ranking, firstRead):
		handle = row["party"]["members"][0]["handle"]
		pointsList = self._points[contestId][handle]
		for taski in range(len(row["problemResults"])):
			task = row["problemResults"][taski]
			taskName = ranking["problems"][taski]["index"]
			if task["points"] > 0 and taski not in pointsList:
				if not firstRead:
					self._notifyTaskSolved(handle, taskName, task["rejectedAttemptCount"],
							 task["bestSubmissionTimeSeconds"], row["rank"] != 0)
					if ranking["contest"]['phase'] == 'FINISHED': # if contest is running, standings are updated automatically
						self._updateStandings(contestId, db.getWhoseFriends(handle, allList=True))
				pointsList.append(taski)
				if task['type'] == 'PRELIMINARY' and (taski not in self._notFinal[contestId][handle]):
					logger.debug('adding non-final task ' + str(taski) + ' for user ' + str(handle))
					self._notFinal[contestId][handle].append(taski)
			if task['type'] == 'FINAL' and (taski in self._notFinal[contestId][handle]):
				logger.debug('finalizing non-final task ' + str(taski) + ' for user ' + str(handle))
				self._notFinal[contestId][handle].remove(taski)
				self._notifyTaskTested(handle, taskName, task['points'] > 0)
				self._updateStandings(contestId, db.getWhoseFriends(handle, allList=True))
				if int(task['points']) == 0: #failed on system tests, now not solved
					pointsList.remove(taski)

	def _analyseContest(self, contestId, friends, firstRead):
		ranking = cf.getStandings(contestId, friends)
		if ranking is False:
			return
		results = ranking['rows']
		for row in results:
			self._analyseRow(contestId, row, ranking, firstRead)
		if ranking['contest']['phase'] != 'FINISHED' and not firstRead:
			self._updateStandings(contestId, db.getAllChatPartners())

	# analyses the standings
	def _doTask(self, firstRead=False):
		friends = db.getAllFriends()
		threads = []
		for contestId in cf.getCurrentContestsId():
			t = Thread(target=self._analyseContest, args=(contestId, friends, firstRead), name="analyseContest"+str(contestId))
			t.start()
			threads.append(t)
		for t in threads:
			t.join()

