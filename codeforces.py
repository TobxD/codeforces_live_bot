import requests, urllib, simplejson
import random, time
import queue, threading
import database as db
import util
from util import logger
import UpdateService

codeforcesUrl = 'https://codeforces.com/api/'

contestListLock = threading.Lock()
aktuelleContests = [] # display scoreboard + upcoming
currentContests = [] # display scoreboard

standingsLock = threading.Lock()
globalStandings = {}

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
	waitTime = endTimes.get() + 1 - time.time()
	if waitTime > 0:
		time.sleep(waitTime)
	try:
		r = requests.get(request, timeout=15)
	except requests.exceptions.Timeout as errt:
		logger.error("Timeout on Codeforces.")
		return False
	except requests.exceptions.ChunkedEncodingError as e:
		logger.error("ChunkedEncodingError on CF: %s", e)
	except Exception as e:
		logger.critical('Failed to request codeforces: \nexception: %s\n', e, exc_info=True)
		return False
	finally:
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
		r = r.json()
		if r['status'] == 'OK':
			return r['result']
		else:
			logger.critical("Invalid Codeforces request: " + r['comment'])
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
		if r['comment'] == 'apiKey: Incorrect API key;onlyOnline: You have to be authenticated to use this method':
			chat.apikey = None
			chat.secret = None
			chat.sendMessage("Your API-key did not work 😢. Please add a valid key and secret in the settings.")
			return
		if "contestId: Contest with id" in r['comment'] and "has not started" in r['comment']:
			return # TODO fetch new contest start time
	logger.critical("codeforces error: " + str(r['comment']) + "\n" +
					 "this request caused the error:\n" + (str(request)[:200]),
					 exc_info=True)

def getUserInfos(userNameArr):
	usrList = ';'.join(userNameArr)
	logger.debug('requesting info of ' + str(len(userNameArr)) + ' users ')
	r = sendRequest('user.info', {'handles':usrList})
	return r

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
		db.addFriends(chat.chatId, f)
		logger.debug('friends updated for chat ' + str(chat.chatId))

def getFriendsWithDetails(chat):
	return db.getFriends(chat.chatId)

def getFriends(chat):
	friends = getFriendsWithDetails(chat)
	return [f[0] for f in friends if f[1] == 1] # only output if ratingWatch is enabled

def mergeStandings(rowDict, newSt, oldSt):
	if newSt:
		if "contest" in newSt: 
			for row in newSt['rows']:
				handle = row['party']['members'][0]['handle'] 
				pType = row["party"]["participantType"]
				rowDict[(handle, pType)] = row
			return newSt, rowDict
	return oldSt, rowDict

def updateStandings(contestId):
	global aktuelleContests
	global globalStandings
	handleList = db.getAllFriends()
	if contestId not in globalStandings:
		globalStandings[contestId] = {"time": 0, "standings": False}
	standings = globalStandings[contestId]["standings"]
	rowDict = {}
	if standings:
		for row in standings['rows']:
			handle = row['party']['members'][0]['handle'] 
			pType = row["party"]["participantType"]
			rowDict[(handle, pType)] = row
	l = 0
	r = 0
	while r < len(handleList):
		handleString = ";".join(handleList[l:r])
		while r < len(handleList) and len(";".join(handleList[l:r+1])) < 6000:
			r += 1
			handleString = ";".join(handleList[l:r+1])
		logger.debug('updating standings for contest '+str(contestId)+' for '+str(r-l)+' of '+str(len(handleList))+' users')
		stNew = sendRequest('contest.standings', {'contestId':contestId, 'handles':handleString, 'showUnofficial':True})
		standings, rowDict = mergeStandings(rowDict, stNew, standings)
		l = r 

	if standings and "contest" in standings:
		standings['rows'] = []
		for key in rowDict:
			standings['rows'].append(rowDict[key])
		# sort: first official (rank > 0), then unoffical with desc by points
		standings['rows'].sort(key= lambda row: row["rank"] if row["rank"] != 0 else 10000000 - row["points"])

		contest = standings["contest"]
		with contestListLock:
			aktuelleContests = [contest if contest["id"] == c["id"] else c for c in aktuelleContests]
		globalStandings[contestId] = {"time": time.time(), "standings": standings}
		logger.debug('standings received')
	else:
		logger.error('standings not updated')

def getStandings(contestId, handleList):
	with standingsLock:
		toUpd = not contestId in globalStandings or globalStandings[contestId] is False or time.time() - globalStandings[contestId]["time"] > 30
		if toUpd:
			updateStandings(contestId)

	with standingsLock:
		if globalStandings[contestId] is False or globalStandings[contestId]["standings"] is False:
			return False
		allStandings = globalStandings[contestId]["standings"]
		allRows = allStandings["rows"]
		# filter only users from handleList
		rows = [r for r in allRows if r["party"]["members"][0]["handle"] in handleList]
		standings = {}
		standings['problems'] = allStandings['problems']
		standings['contest'] = allStandings['contest']
		standings["rows"] = rows
		return standings


def getContestStatus(contest):
	if contest['startTimeSeconds'] >= time.time():
		return 'before'
	elif contest['startTimeSeconds']+contest['durationSeconds'] >= time.time():
		return 'running'
	elif contest['phase'] != 'FINISHED':
		return 'testing'
	else:
		return 'finished'

def selectImportantContests(contestList):
	global aktuelleContests
	global currentContests
	lastStart = 0
	currentContests = []
	aktuelleContests = []
	for c in contestList:
		status = getContestStatus(c)
		if status != 'before':
			lastStart = max(lastStart, c.get('startTimeSeconds', -1))
	for c in contestList:
		twoDaysOld = time.time()-(c.get('startTimeSeconds', -2)+c.get('durationSeconds', -2)) > 60*60*24*2
		status = getContestStatus(c)
		if not twoDaysOld:
			aktuelleContests.append(c)
		if status == 'running' or status == 'testing' or c.get('startTimeSeconds', -2) == lastStart or (not twoDaysOld and status != 'before'):
			currentContests.append(c)
	currentContests = list(reversed(currentContests))

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

class FriendUpdateService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 24*3600)
		self.name = "FriendUpdateService"
		self._doTask()

	def _doTask(self):
		logger.debug('starting to update all friends')
		for chatId, chat in Chat.chats.items():
			updateFriends(chat)
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
		logger.debug('loding contests finished')
