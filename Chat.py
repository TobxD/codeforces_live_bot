class Chat:

	def __init__(self, chatId):
		self.chatId = chatId
		(self.apikey, self.secret, self.timezone, self.handle) = db.queryUserInfos(chatId)

	def sendMessage(self, msg):
		pass

	def updateMessage(self, msgId, newMsg):
		pass
