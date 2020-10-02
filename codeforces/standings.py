from __future__ import annotations
import requests, threading, time
from collections import defaultdict
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from telegram.Chat import Chat

from commands import bot
from codeforces import codeforces as cf, Ranking
from telegram import telegram as tg
from telegram import Chat
from utils import util
from utils.Table import Table
from utils.util import logger, perfLogger
from utils import database as db

standingsSentLock = threading.Lock()
standingsSent = defaultdict(lambda : defaultdict(lambda : None)) # [chatId][contest] = (msgId, msg)

cfPredictorLock = threading.Lock()
handleToRatingChanges = defaultdict(lambda : {})
cfPredictorLastRequest = defaultdict(lambda : 0)
cfPredictorUrl = "https://cf-predictor-frontend.herokuapp.com/GetNextRatingServlet?contestId="

def getRatingChanges(contestId):
	with cfPredictorLock:
		if time.time() > cfPredictorLastRequest[contestId] + 20:
			logger.debug('request rating changes from cf-predictor')
			cfPredictorLastRequest[contestId] = time.time()
			try:
				startT = time.time()
				r = requests.get(cfPredictorUrl + str(contestId), timeout=10)
				perfLogger.info("cf predictor request {:.3f}s".format(time.time()-startT))
			except requests.exceptions.Timeout as errt:
				logger.error("Timeout on CF-predictor.")
				return handleToRatingChanges[contestId]
			except Exception as e:
				logger.critical('Failed to request cf-predictor: \nexception: %s\n', e, exc_info=True)
				return handleToRatingChanges[contestId]
			if r.status_code != requests.codes.ok:
				logger.error("CF-Predictor request failed with code "+ str(r.status_code) + ", "+ str(r.reason))
				return handleToRatingChanges[contestId]
			logger.debug('rating changes received')
			r = r.json()
			if r['status'] != 'OK':
				return handleToRatingChanges[contestId]
			r = r['result']
			handleToRatingChanges[contestId] = {}
			for row in r:
				handleToRatingChanges[contestId][row['handle']] = (row['oldRating'], row['newRating'])
			cfPredictorLastRequest[contestId] = time.time()
		return handleToRatingChanges[contestId]

def getContestHeader(contest):
	msg = contest["name"] + " "
	if contest["relativeTimeSeconds"] < contest["durationSeconds"]:
		msg += "*"+ util.formatSeconds(contest["relativeTimeSeconds"]) + "* / "
		msg += util.formatSeconds(contest["durationSeconds"]) + "\n\n"
	elif contest['phase'] != 'FINISHED':
		msg += "*TESTING*\n\n"
	else:
		msg += "*FINISHED*\n\n"
	return msg


# if !sendIfEmpty and standings are empty then False is returned
def getFriendStandings(chat:Chat, contestId, sendIfEmpty=True):
	friends = cf.getListFriends(chat)
	if len(friends) == 0:
		if sendIfEmpty:
			chat.sendMessage(("You have no friends :(\n"
				"Please add your API key in the settings or add friends with `/add_friend`."))
			logger.debug("user has no friends -> empty standings")
		return False
	standings = cf.getStandings(contestId, friends)
	if standings == False:
		logger.debug("failed to get standings for " + str(friends))
		return False
	
	msg = getContestHeader(standings["contest"])
	problemNames = [p["index"] for p in standings["problems"]]
	ratingChanges = getRatingChanges(contestId)
	ranking = Ranking.Ranking(standings["rows"], ratingChanges, len(problemNames))
	tableRows = ranking.getRows(standings["contest"]['phase'] == 'SYSTEM_TEST')

	if not sendIfEmpty and len(tableRows) == 0:
		return False
	table = Table(problemNames, tableRows)
	msg += table.formatTable(chat.width)
	return msg	

def sendContestStandings(chat:Chat, contestId, sendIfEmpty=True):
	msg = getFriendStandings(chat, contestId, sendIfEmpty=sendIfEmpty)
	if msg is False: # CF is down or (standings are emtpy and !sendIfEmpty)
		return
	def callbackFun(id):
		if id != False:
			with standingsSentLock:
				if standingsSent[chat.chatId][contestId]:
					chat.deleteMessage(standingsSent[chat.chatId][contestId][0])
				updateStandingsSent(chat.chatId, contestId, id, msg)
	chat.sendMessage(msg, callback=callbackFun)

def sendStandings(chat:Chat, msg):
	bot.setOpenCommandFunc(chat.chatId, None)
	contestIds = cf.getCurrentContestsId()
	if len(contestIds) > 0:
		for c in contestIds:
			sendContestStandings(chat, c)
	else:
		chat.sendMessage("No contests in the last two days 🤷🏻")

# updates only, if message exists and the standings-message has changed
def updateStandingsForChat(contest, chat:Chat):
	with standingsSentLock:
		if contest not in standingsSent[chat.chatId]: # only used as speed-up, checked again later
			return
	msg = getFriendStandings(chat, contest)
	if msg is False:
		return
	logger.debug('update standings for ' + str(chat.chatId) + '!')
	with standingsSentLock:
		if contest not in standingsSent[chat.chatId]:
			return
		msgId, oldMsg = standingsSent[chat.chatId][contest]
		if tg.shortenMessage(oldMsg) != tg.shortenMessage(msg):
			updateStandingsSent(chat.chatId, contest, msgId, msg)
			chat.editMessageTextLater(msgId, contest, lambda chat, contest: getFriendStandings(chat, contest))

def initDB():
	data = db.getAllStandingsSentList()
	with standingsSentLock:
		for (chatId, contestId, msgId, msgIdNotf) in data:
			if msgId: # maybe only msgIdNotf is set
				standingsSent[chatId][contestId] = (msgId, "")

def updateStandingsSent(chatId, contestId, msgId, msg):
	standingsSent[chatId][contestId] = (msgId, msg)
	db.saveStandingsSent(chatId, contestId, msgId)
