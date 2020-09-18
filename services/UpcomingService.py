import time

from services import UpdateService
from codeforces import upcoming
from codeforces import codeforces as cf
from utils import database as db
from telegram import Chat
from collections import defaultdict

class UpcomingService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 30)
		self.name = "upcomingService"
		self._notified = {}
		self._notifyTimes = [3600*24*3+59, 3600*24+59, 3600*2+59, -15*60, -100000000]
		self._initDB()
		self._doTask(True) #initializes notified

	def _initDB(self):
		self._reminderSent = defaultdict(lambda : defaultdict(lambda : None)) # [chatId][contest] = msgId
		data = db.getAllStandingsSentList()
		for (chatId, contestId, msgId, msgIdNotf) in data:
			if msgIdNotf: # maybe only msgId is set
				self._reminderSent[chatId][contestId] = msgIdNotf

	def _updateReminderSent(self, chatId, contestId, msgId):
		self._reminderSent[chatId][contestId] = msgId
		db.saveReminderSent(chatId, contestId, msgId)

	def _doTask(self, quiet=False):
		for c in cf.getFutureAndCurrentContests():
			timeLeft = c['startTimeSeconds'] - time.time()
			if c['id'] not in self._notified:
				self._notified[c['id']] = 0
			oldLevel = self._notified[c['id']]
			while timeLeft <= self._notifyTimes[self._notified[c['id']]]:
				self._notified[c['id']] += 1
			if oldLevel != self._notified[c['id']] and not quiet:
				shouldNotifyFun = lambda chat: False
				if self._notified[c['id']] == 1:
					shouldNotifyFun = lambda chat: chat.reminder3d
				elif self._notified[c['id']] == 2:
					shouldNotifyFun = lambda chat: chat.reminder1d
				elif self._notified[c['id']] == 3:
					shouldNotifyFun = lambda chat: chat.reminder2h
				elif self._notified[c['id']] == 4:
					shouldNotifyFun = lambda chat: False # contest started -> no new reminder, only delete old reminder
				self._notifyAllUpcoming(c, shouldNotifyFun)

	def _notifyAllUpcoming(self, contest, shouldNotifyFun):
		for chatId in db.getAllChatPartners():
			chat = Chat.getChat(chatId)
			if self._reminderSent[chat.chatId][contest['id']]:
				msgId = self._reminderSent[chat.chatId][contest['id']]
				chat.deleteMessage(msgId)
				self._updateReminderSent(chat.chatId, contest['id'], None)
			if shouldNotifyFun(chat):
				description = upcoming.getDescription(contest, chat)
				callback = lambda msgId, chatId=chatId, contestId=contest['id'] : self._updateReminderSent(chatId, contestId, msgId)
				chat.sendMessage(description, callback=callback)
