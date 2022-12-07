import requests, urllib, simplejson
import random, time
import queue, threading
from collections import defaultdict

from utils import database as db
from utils import util
from telegram import Chat
from utils.util import logger, perfLogger
from services import UpdateService

codeforcesUrl = 'https://codeforces.com/api/'

contestListLock = threading.Lock()
aktuelleContests = [] # display scoreboard + upcoming
currentContests = [] # display scoreboard

standingsLock = defaultdict(lambda : threading.Condition())
globalStandings = {} # contest-id -> {time, standings}

endTimes = queue.Queue()
for i in range(1):
	endTimes.put(-1)

def sendRequest(method, params, authorized = False, chat = None):
	rnd = random.randint(0, 100000)
	rnd = str(rnd).zfill(6)
	tailPart = method + '?'

	if authorized:
		try:
			if chat == None or chat.apikey == None or chat.secret == None:
				# maybe we don't have apikey so we cannot request friends or smt
				return False
			params['apiKey'] = str(chat.apikey)
			params['time'] = str(int(time.time()))
		except Exception as e:
			logger.critical("%s", e, exc_info=True)
			return False

	for key,val in sorted(params.items()):
		tailPart += str(key) + "=" + urllib.parse.quote(str(val)) + "&"
	tailPart = tailPart[:-1]

	if authorized:
		hsh = util.sha512Hex(rnd + '/' + tailPart + '#' + chat.secret)
		tailPart += '&apiSig=' + rnd + hsh
	request = codeforcesUrl + tailPart
	startWait = time.time()
	waitTime = endTimes.get() + 1 - time.time()
	if waitTime > 0:
		time.sleep(waitTime)
	startT = time.time()
	try:
		r = requests.get(request, timeout=15)
	except requests.exceptions.Timeout as errt:
		logger.error("Timeout on Codeforces.")
		return False
	except requests.exceptions.ChunkedEncodingError as e:
		logger.error("ChunkedEncodingError on CF: %s", e)
		return False
	except Exception as e:
		logger.critical('Failed to request codeforces: \nexception: %s\n', e, exc_info=True)
		return False
	finally:
		perfLogger.info("cf request " + method + ": {:.3f}s; waittime: {:.3f}".format(time.time()-startT, startT-startWait))
		endTimes.put(time.time())
	if r.status_code != requests.codes.ok:
		if r.status_code == 429:
			logger.error("too many cf requests... trying again")
			return sendRequest(method, params, authorized, chat)
		elif r.status_code//100 == 5:
			logger.error("Codeforces Http error " + str(r.reason) + " (" + str(r.status_code) + ")")
		else:
			try:
				r = r.json()
				handleCFError(request, r, chat)
			except simplejson.errors.JSONDecodeError as jsonErr:
				logger.critical("no valid json; status code for cf request: " + str(r.status_code) + "\n" +
								 "this request caused the error:\n" + str(request),
								 exc_info=True)
		return False
	else:
		try:
			r = r.json()
			if r['status'] == 'OK':
				return r['result']
			else:
				logger.critical("Invalid Codeforces request: " + r['comment'])
				return False
		except Exception as e: #TODO why does CF send an invalid json with http 200?
			logger.critical("json decoding failed; status code for cf request: " + str(r.status_code) + "\n" +
							 "this request caused the error:\n" + str(request) + "\n" +
							 "text got back:\n" + str(r.text),
							 exc_info=True)
			return False

def handleCFError(request, r, chat):
	if r['status'] == 'FAILED':
		#delete nonexisting friends
		startS = "handles: User with handle "
		endS = " not found"
		if r['comment'].startswith(startS) and r['comment'].endswith(endS):
			handle = r['comment'][len(startS):-len(endS)]
			db.deleteFriend(handle)
			return
		#remove wrong authentification
		if 'Incorrect API key' in r['comment'] or 'Incorrect signature' in r['comment']:
			chat.apikey = None
			chat.secret = None
			chat.sendMessage("Your API-key did not work 😢. Please add a valid key and secret in the settings.")
			return
		if "contestId: Contest with id" in r['comment'] and "has not started" in r['comment']:
			return # TODO fetch new contest start time
		if "contestId: Contest with id" in r['comment'] and "not found" in r['comment']:
			logger.debug("codeforces error: " + r['comment'])
			return
	logger.critical("codeforces error: " + str(r['comment']) + "\n" +
					 "this request caused the error:\n" + (str(request)[:200]),
					 exc_info=True)

def getUserInfos(userNameArr):
	batchSize = 200
	split = [userNameArr[batchSize*i:batchSize*(i+1)] for i in range((len(userNameArr)+batchSize-1)//batchSize)]
	res = []
	for part in split:
		usrList = ';'.join(part)
		logger.debug('requesting info of ' + str(len(part)) + ' users ')
		r = sendRequest('user.info', {'handles':usrList})
		if r is False:
			return False
		res.extend(r)
	return res

def getUserRating(handle):
	info = getUserInfos([handle])
	if info == False or len(info) == 0 or "rating" not in info[0]:
		return 0
	return info[0]["rating"]

def updateFriends(chat):
	p = {'onlyOnline':'false'}
	logger.debug('request friends of chat with chat_id ' + str(chat.chatId))
	f = sendRequest("user.friends", p, True, chat)
	logger.debug('requesting friends finished')
	if f != False:
		db.addFriends(chat.chatId, f, chat.notifyLevel)
		logger.debug('friends updated for chat ' + str(chat.chatId))


def getAllFriends(chat):
	friends = db.getFriends(chat.chatId)
	return [f[0] for f in friends]

def getListFriends(chat):
	friends = db.getFriends(chat.chatId, selectorColumn="showInList")
	return [f[0] for f in friends]

def updateStandings(contestId):
	global aktuelleContests
	logger.debug('updating standings for contest '+str(contestId)+' for all users')
	stNew = sendRequest('contest.standings', {'contestId':contestId, 'showUnofficial':True})
	if stNew and "contest" in stNew:
		with standingsLock[contestId]:
			globalStandings[contestId] = {"time": time.time(), "standings": stNew}
		with contestListLock:
			aktuelleContests = [stNew["contest"] if stNew["contest"]["id"] == c["id"] else c for c in aktuelleContests]
		logger.debug('standings received')
	else:
		logger.error('standings not updated')

def getStandings(contestId, handleList, forceRequest=False):
	with standingsLock[contestId]:
		contestOld = contestId not in globalStandings or globalStandings[contestId] is False or time.time() - globalStandings[contestId]["time"] > 120
		toUpd = contestOld or forceRequest
		shouldUpdate = False
		if toUpd:
			if getStandings.isUpdating[contestId]:
				standingsLock[contestId].wait()
			else:
				getStandings.isUpdating[contestId] = True
				shouldUpdate = True

	if shouldUpdate:
		updateStandings(contestId)
		with standingsLock[contestId]:
			getStandings.isUpdating[contestId] = False
			standingsLock[contestId].notifyAll()

	handleSet = set(handleList)

	with standingsLock[contestId]:
		if contestId not in globalStandings or globalStandings[contestId] is False or globalStandings[contestId]["standings"] is False:
			return False
		allStandings = globalStandings[contestId]["standings"]
		allRows = allStandings["rows"]
		# filter only users from handleList
		rows = [r for r in allRows if r["party"]["members"][0]["handle"] in handleSet]
		standings = {}
		standings['problems'] = allStandings['problems']
		standings['contest'] = allStandings['contest']
		standings["rows"] = rows
		return standings
getStandings.isUpdating = defaultdict(lambda : False)

def getContestStatus(contest):
	startT = contest.get('startTimeSeconds', -1)
	if startT >= time.time():
		return 'before'
	elif startT + contest['durationSeconds'] >= time.time():
		return 'running'
	elif contest['phase'] != 'FINISHED' and startT + contest['durationSeconds'] >= time.time()-5*60*60:
		return 'testing'
	else:
		return 'finished'

def selectImportantContests(contestList):
	global aktuelleContests
	global currentContests

	def contestInfos(contest):
		endT = contest.get('startTimeSeconds', -1) + contest['durationSeconds']
		status = getContestStatus(contest)
		return {'contest':contest, 'duration':contest['durationSeconds'], 'endT':endT, 'status':status}

	contestList = list(map(contestInfos, contestList))
	futureContests = list(filter(lambda c: c['status'] == 'before', contestList))
	contestList = list(filter(lambda c: c['status']!='before', contestList))
	activeShort = list(filter((lambda c: (c['status'] in ['running', 'testing']) and c['duration'] <= 5*60*60), contestList))
	if len(activeShort) > 0:
		currentContests = activeShort
	else:
		currentContests = list(filter(lambda c: c['endT'] >= time.time()-60*60*24*2, contestList))
		if len(currentContests) == 0:
			lastFin = max(map(lambda c: c['endT'], contestList))
			currentContests = list(filter(lambda c: c['endT']==lastFin, contestList))

	aktuelleContests = currentContests + futureContests
	currentContests = list(map(lambda c: c['contest'], currentContests))
	aktuelleContests = list(map(lambda c: c['contest'], aktuelleContests))

def getCurrentContests():
	with contestListLock:
		curC = aktuelleContests
		selectImportantContests(curC)
		return currentContests

def getCurrentContestsId():
	return [c['id'] for c in getCurrentContests()]

def getFutureContests():
	res = []
	with contestListLock:
		for c in aktuelleContests:
			if c.get('startTimeSeconds', -1) > time.time():
				res.append(c)
	return res

def getFutureAndCurrentContests():
	return aktuelleContests

class FriendUpdateService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 24*3600)
		self.name = "FriendUpdateService"

	def _doTask(self):
		logger.debug('starting to update all friends')
		for chatId in db.getAllChatPartners():
			updateFriends(Chat.getChat(chatId))
		logger.debug('updating all friends finished')

class ContestListService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 3600)
		self.name = "contestListService"
		self._doTask()

	def _doTask(self):
		logger.debug('loading current contests')
		allContests = sendRequest('contest.list', {'gym':'false'})
		if allContests is False:
			logger.error('failed to load current contest - maybe cf is not up')
		else:
			with contestListLock:
				selectImportantContests(allContests)
		logger.debug('loading contests finished')
