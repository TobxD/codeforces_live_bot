import time

from services import UpdateService
from codeforces import upcoming
from codeforces import codeforces as cf
from utils import database as db
from telegram import Chat

class UpcomingService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 30)
		self._notified = {}
		self._notifyTimes = [3600*24*3+59, 3600*24+59, 3600*2+59, -100000000]
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
						shouldNotifyFun = lambda chat: False
						if i==0:
							shouldNotifyFun = lambda chat: chat.reminder3d
						elif i==1:
							shouldNotifyFun = lambda chat: chat.reminder1d
						elif i==2:
							shouldNotifyFun = lambda chat: chat.reminder2h
						self._notifyAllUpcoming(c, shouldNotifyFun)

	def _notifyAllNewContestAdded(self, contest):
		for chatId in db.getAllChatPartners():
			chat = Chat.getChat(chatId)
			description = "new contest added:\n"
			description += upcoming.getDescription(contest, chat)
			chat.sendMessage(description)

	def _notifyAllUpcoming(self, contest, shouldNotifyFun):
		for chatId in db.getAllChatPartners():
			chat = Chat.getChat(chatId)
			if shouldNotifyFun(chat):
				description = upcoming.getDescription(contest, chat)
				chat.sendMessage(description)
