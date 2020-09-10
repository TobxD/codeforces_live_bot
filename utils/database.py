import mysql.connector, mysql.connector.pooling, mysql.connector.errors
import threading, time

from utils.util import logger, perfLogger
from telegram import Chat

friendsNotfLock = threading.Lock()

NOTIFY_COLUMNS = ["showInList", "notifyTest", "notifyUpsolving", "notify"]

db_creds = [line.rstrip('\n') for line in open('.database_creds')]

def openDB():
	return mysql.connector.connect(user=db_creds[0], password=db_creds[1], host=db_creds[2], port=db_creds[3], database=db_creds[4])

def queryDB(query, params):
	startT = time.time()
	db = openDB()
	cursor = db.cursor()
	cursor.execute(query, params)
	res = cursor.fetchall()
	cursor.close()
	db.close()
	perfLogger.info("db query {}: {:.3f}s".format(query, time.time()-startT))
	return res

def insertDB(query, params):
	if len(params) == 0:
		return
	db = openDB()
	cursor = db.cursor()
	cursor.execute(query, params)
	db.commit()
	db.close()

# returns (apikey, secret, timezone, handle) or None, if no such user exists
def queryChatInfos(chatId):
	query = ("SELECT apikey, secret, timezone, handle, notifyLevel, "
			"polite, reply, width, reminder2h, reminder1d, reminder3d, "
			"settings_msgid FROM tokens WHERE chatId = %s")
	res = queryDB(query, (chatId,))
	if len(res) == 0:
		return None
	else:
		return res[0]

def updateChatInfos(chatId, apikey, secret, timezone, handle, notifyLevel,
		polite, reply, width, reminder2h, reminder1d, reminder3d, settings_msgid):
	query = ("INSERT INTO "
							"tokens (chatId, apikey, secret, timezone, handle, notifyLevel, "
								"polite, reply, width, reminder2h, "
								"reminder1d, reminder3d, settings_msgid) "
					"VALUES "
							"(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
					"ON DUPLICATE KEY UPDATE "
							"apikey = %s , secret = %s , timezone = %s , handle = %s , "
							"notifyLevel = %s , polite = %s , "
							"reply = %s , width = %s , reminder2h = %s , reminder1d = %s , "
							"reminder3d = %s , settings_msgid = %s")
	insertDB(query, (chatId, apikey, secret, timezone, handle, notifyLevel,
		 polite, reply, width, reminder2h, reminder1d, reminder3d,
		 settings_msgid,
		 apikey, secret, timezone, handle, notifyLevel,
		 polite, reply, width, reminder2h, reminder1d, reminder3d,
		 settings_msgid))

def getChatIds(handle):
	query = "SELECT chatId from tokens WHERE handle = %s"
	res = queryDB(query, (handle,))
	return [r[0] for r in res]

def deleteFriend(handle):
	logger.debug("deleting friends with handle " + handle)
	query = "DELETE FROM friends WHERE friend = %s"
	insertDB(query, (handle,))

	query = "SELECT chatId FROM tokens WHERE handle = %s"
	chatIds = [r[0] for r in queryDB(query, (handle,))]
	logger.debug(f"deleting chat handle {handle} for chats {chatIds}")
	for chatId in chatIds:
		Chat.getChat(chatId).handle = None # write through to DB

def deleteFriendOfUser(handle, chatId):
	logger.debug("deleting friend with handle " + handle + " from user " + str(chatId))
	query = "DELETE FROM friends WHERE friend = %s AND chatId = %s"
	insertDB(query, (handle,chatId))

def deleteUser(chatId):
	logger.debug("deleting all data of user with chatId " + str(chatId))
	query = "DELETE FROM friends WHERE chatId = %s"
	logger.debug("deleting all friend entries: " + query)
	insertDB(query, (chatId,))
	query = "DELETE FROM tokens WHERE chatId = %s"
	logger.debug("deleting all token entries: " + query)
	insertDB(query, (chatId,))

def addFriends(chatId, friends, notifyLevel):
	query = "INSERT INTO friends (chatId, friend, showInList, notifyTest, notifyUpsolving, notify) VALUES "
	for f in friends:
		query += "(%s, %s, %s, %s, %s, %s), "
	query = query[:-2] + " ON DUPLICATE KEY UPDATE chatId=chatId"

	params = []
	for f in friends:
		params.append(chatId)
		params.append(f)
		for i in range(4): #TODO
			params.append(i < notifyLevel)

	insertDB(query, tuple(params))

def getFriends(chatId, selectorColumn = "True"):
	query = f"SELECT friend, {', '.join(NOTIFY_COLUMNS)} FROM friends WHERE chatId = %s AND {selectorColumn}=True"
	res = queryDB(query, (chatId,))
	return res

def getAllFriends():
	query = "SELECT DISTINCT friend FROM friends"
	res = queryDB(query, ())
	return [x[0] for x in res]


def getWhoseFriendsListed(handle):
	query = "SELECT DISTINCT chatId FROM friends WHERE friend = %s AND showInList=True"
	res = queryDB(query, (handle,))
	return [row[0] for row in res]

def getWhoseFriendsSystemTestFail(handle):
	query = "SELECT DISTINCT chatId FROM friends WHERE friend = %s AND notifyTest=True"
	res = queryDB(query, (handle,))
	return [row[0] for row in res]

def getWhoseFriendsUpsolving(handle):
	query = "SELECT DISTINCT chatId FROM friends WHERE friend = %s AND notifyUpsolving=True"
	res = queryDB(query, (handle,))
	return [row[0] for row in res]

def getWhoseFriendsContestSolved(handle):
	query = "SELECT DISTINCT chatId FROM friends WHERE friend = %s AND notify=True"
	res = queryDB(query, (handle,))
	return [row[0] for row in res]

def getAllChatPartners():
	query = "SELECT chatId FROM tokens"
	res = queryDB(query, ())
	ret = []
	for x in res:
		ret.append(x[0])
	return ret

def toggleFriendSettings(chatId, friend, columnNum):
	column = NOTIFY_COLUMNS[columnNum]
	with friendsNotfLock:
		query = f"SELECT {column} FROM friends WHERE chatId = %s AND friend = %s"
		gesetzt = str(queryDB(query, (chatId, friend))[0][0]) == '1'
		newVal = not gesetzt
		query = f"UPDATE friends SET {column}= %s WHERE chatId = %s AND friend = %s"
		insertDB(query, (newVal, chatId, friend))
		return newVal

def updateToNotifyLevel(chatId, newLev, oldLev=None, reset=False):
	with friendsNotfLock:
		colsSet = [f"{NOTIFY_COLUMNS[i]} = {i < newLev}" for i in range(len(NOTIFY_COLUMNS))]
		query = "UPDATE friends SET "
		query += ", ".join(colsSet)
		query += " WHERE chatId = %s"
		if not reset:
			oldColsCond = [f"{NOTIFY_COLUMNS[i]} = {i < oldLev}" for i in range(len(NOTIFY_COLUMNS))]
			query += " AND " + (" AND ".join(oldColsCond))
		insertDB(query, (chatId,))

# ---------- standingsSent --------------
def getAllStandingsSentList():
	query = "SELECT * FROM standingsSent"
	return queryDB(query, ())

def saveStandingsSent(chatId, contestId, msgid):
	query = (
		"INSERT INTO standingsSent (chatId, contestId, msgid_standings)"
		"VALUES (%s, %s, %s)"
		"ON DUPLICATE KEY UPDATE msgid_standings = %s"
	)
	insertDB(query, (chatId, contestId, msgid, msgid))

def saveReminderSent(chatId, contestId, msgid):
	query = (
		"INSERT INTO standingsSent (chatId, contestId, msgid_reminder)"
		"VALUES (%s, %s, %s)"
		"ON DUPLICATE KEY UPDATE msgid_reminder = %s"
	)
	insertDB(query, (chatId, contestId, msgid, msgid))
