import UpdateService
import telegram as tg
import codeforces as cf
import util
import database as db
import standings
import random

class AnalyseStandingsService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 30)
		self._points = {}
		self._notFinal = {}
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
			tg.sendMessage(chatId, msg)

	def _notifyTaskTested(self, handle, task, accepted):
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

	def _sendStandings(self, chatId, msg):
		for c in cf.getCurrentContestsId():
			standings.sendContestStandings(chatId, c)

	def _updateStadingForUser(self, contest, user, messageId):
		msg = standings.getFriendStandings(user, contest)
		tg.editMessageText(user, messageId, msg)

	def _updateStandings(self, contest, users):
		for user in users:
			if user not in standings.standingsSent:
				standings.standingsSent[user] = {}
			if contest in standings.standingsSent[user]:
				util.log('update stadings for ' + str(user) + '!')
				self._updateStandingsForUser(contest, user, standings.standingsSent[user][contest])

	def _doTask(self, firstRead=False):
		friends = db.getAllFriends()
		for c in cf.getCurrentContestsId():
			if c not in self._points:
				self._points[c] = {}
			if c not in self._notFinal:
				self._notFinal[c] = {}
			lastPoints = self._points[c]
			standings = cf.getStandings(c, friends)
			if standings == False:
				return
			results = standings['rows']
			#{"handle":[0,3], }
			for r in results:
				handle = r["party"]["members"][0]["handle"]
				if handle not in lastPoints:
					lastPoints[handle] = []
				if handle not in self._notFinal[c]:
					self._notFinal[c][handle] = []
				for taski in range(len(r["problemResults"])):
					task = r["problemResults"][taski]
					flag = False
					taskName = standings["problems"][taski]["index"]
					if task["points"] > 0 and taski not in lastPoints[handle]:
						#notify all users who have this friend
						if not firstRead:
							self._notifyTaskSolved(handle, taskName, task["rejectedAttemptCount"],
									 task["bestSubmissionTimeSeconds"], r["rank"] != 0)
							# now updating every 30sec during contest
							# update only if after contest
							if standings["contest"]['phase'] == 'FINISHED':
								self._updateStandings(c, db.getWhoseFriends(handle, allList=True))
						lastPoints[handle].append(taski)
						flag = True
						if task['type'] == 'PRELIMINARY' and (taski not in self._notFinal[c][handle]):
							util.log('adding non-final task ' + str(taski) + ' for user ' + str(handle))
							self._notFinal[c][handle].append(taski)
					if task['type'] == 'FINAL' and (taski in self._notFinal[c][handle]):
						util.log('finalizing non-final task ' + str(taski) + ' for user ' + str(handle))
						self._notFinal[c][handle].remove(taski)
						self._notifyTaskTested(handle, taskName, task['points'] > 0)
						self._updateStandings(c, db.getWhoseFriends(handle, allList=True))
			if standings["contest"]['phase'] != 'FINISHED':
				self._updateStandings(c, db.getAllChatPartners())
