import json, requests, urllib, simplejson
import sys, traceback, random, hashlib, time
import queue, threading
import database as db
import util
import UpdateService

codeforcesUrl = 'https://codeforces.com/api/'
friendUpdLock = threading.Lock()
friendsLastUpdated = {}

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
			util.log(traceback.format_exc(), isError=True)
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
		util.log("Timeout on Codeforces.", isError=True)
		return False
	finally:
		endTimes.put(time.time())
	if r.status_code != requests.codes.ok:
		if(r.status_code == 429):
			util.log("too many cf requests... trying again", isError=True)
			return sendRequest(method, params, authorized, chat)
		else:
			try:
				r = r.json()
				util.log("codeforces error: " + str(r['comment']) + "\n" +
								 "error appeared with stack: " + repr(traceback.extract_stack()) + "\n" +
								 "this request caused the error:\n" + str(request),
								 isError=True)
				handleCFError(r, chat)
			except simplejson.errors.JSONDecodeError as jsonErr:
				util.log("status code for cf request: " + str(r.status_code) + "\n" +
								 "error appeared with stack: " + repr(traceback.extract_stack()) + "\n" +
								 "this request caused the error:\n" + str(request),
								 isError=True)
			return False
	r = r.json()
	if r['status'] == 'OK':
		return r['result']
	else:
		util.log("Invalid Codeforces request: " + r['comment'], isError=True)
		return False

def handleCFError(r, chat):
	if r['status'] == 'FAILED':
		#delete nonexisting friends
		startS = "handles: User with handle "
		endS = " not found"
		if r['comment'].startswith(startS) and r['comment'].endswith(endS):
			handle = r['comment'][len(startS):-len(endS)]
			db.deleteFriend(handle)
		#remove wrong authentification
		if r['comment'] == 'apiKey: Incorrect API key;onlyOnline: You have to be authenticated to use this method':
			chat.apikey = None
			chat.secret = None


def getUserInfos(userNameArr):
	usrList = ';'.join(userNameArr)
	util.log('requesting info of ' + str(len(userNameArr)) + ' users ')
	r = sendRequest('user.info', {'handles':usrList})
	return r

def getUserRating(handle):
	info = getUserInfos([handle])
	if info == False or "rating" not in info[0]:
		return 0
	return info[0]["rating"]

def getFriendsWithDetails(chat):
	global friendsLastUpdated
	with friendUpdLock:
		if time.time() - friendsLastUpdated.get(chat.chatId, 0) > 1200:
			p = {}
			p['onlyOnline'] = 'false'
			util.log('request friends of chat with chat_id ' + str(chat.chatId))
			f = sendRequest("user.friends", p, True, chat)
			util.log('requesting friends finished')
			if f != False:
				db.addFriends(chat.chatId, f)
				friendsLastUpdated[chat.chatId] = time.time()
				util.log('friends updated for chat ' + str(chat.chatId))
	friends = db.getFriends(chat.chatId)
	return friends

def getFriends(chat):
	friends = getFriendsWithDetails(chat)
	return [f[0] for f in friends if f[1] == 1] # only output if ratingWatch is enabled

def mergeStandings(s1, s2):
	if s1 == True:
		return s2
	if s1 and "contest" in s1: 
		if s2 and "contest" in s2: 
			s1['rows'].extend(s2['rows'])
			return s1
		else:
			return False
	else:
		return False

def updateStandings(contestId):
	global aktuelleContests
	global globalStandings
	handleList = db.getAllFriends()
	standings = True
	l = 0
	r = 0
	while r < len(handleList):
		handleString = ";".join(handleList[l:r])
		while r < len(handleList) and len(";".join(handleList[l:r+1])) < 6000:
			r += 1
			handleString = ";".join(handleList[l:r+1])
		util.log('updating standings for contest '+str(contestId)+' for '+str(r-l)+' of '+str(len(handleList))+' users')
		stNew = sendRequest('contest.standings', {'contestId':contestId, 'handles':handleString, 'showUnofficial':True})
		standings = mergeStandings(standings, stNew)
		l = r 
	if standings and "contest" in standings:
		contest = standings["contest"]
		with contestListLock:
			aktuelleContests = [contest if contest["id"] == c["id"] else c for c in aktuelleContests]
		globalStandings[contestId] = {"time": time.time(), "standings": standings}
		util.log('standings received')
	else:
		util.log('standings not updated', isError=True)
		if contestId not in globalStandings:
			globalStandings[contestId] = False

def getStandings(contestId, handleList):
	with standingsLock:
		toUpd = not contestId in globalStandings or globalStandings[contestId] is False or time.time() - globalStandings[contestId]["time"] > 30
		if toUpd:
			updateStandings(contestId)

	with standingsLock:
		if globalStandings[contestId] is False:
			return False
		allStandings = globalStandings[contestId]["standings"]
		allRows = allStandings["rows"]
		# filter only users from handleList
		rows = [r for r in allRows if r["party"]["members"][0]["handle"] in handleList]
		standings = allStandings
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

class ContestListService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 3600)
		self.name = "contestListService"
		self._doTask()

	def _doTask(self):
		util.log('loading current contests')
		allContests = sendRequest('contest.list', {'gym':'false'})
		if allContests is False:
			util.log('failed to load current contest - maybe cf is not up', isError=True)
		else:
			with contestListLock:
				selectImportantContests(allContests)
		util.log('loding contests finished')
