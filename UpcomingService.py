import UpdateService
import upcoming
import telegram as tg
import codeforces as cf
import database as db
import time
import Chat

class UpcomingService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 50)
		self._notified = {}
		self._notifyTimes = [3600*24+59, 3600*2+59, -100000000]
		self._doTask(True) #initializes notified

	def _doTask(self, quiet=False):
		for c in cf.getFutureContests():
			timeLeft = c['startTimeSeconds'] - time.time()
			if c['id'] not in self._notified:
				self._notified[c['id']] = 0
				#if not quiet:
				#	self._notifyAllNewContestAdded(c)
			for i in range(len(self._notifyTimes)):
				if timeLeft <= self._notifyTimes[self._notified[c['id']]]:
					self._notified[c['id']] += 1
					if not quiet:
						# in the IOI-group only notify once
						if not (self._notified[c['id']] > 1 
							 and int(c['id']) in [-376765970, -1001417835798]):
							self._notifyAllUpcoming(c)

	def _notifyAllNewContestAdded(self, contest):
		for chatId, chat in Chat.chats.items():
			description = "new contest added:\n"
			description += upcoming.getDescription(contest, chat)
			chat.sendMessage(description)

	def _notifyAllUpcoming(self, contest):
		for chatId, chat in Chat.chats.items():
			description = upcoming.getDescription(contest, chat)
			chat.sendMessage(description)
