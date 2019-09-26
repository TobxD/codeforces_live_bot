import json, requests, time
import sys, traceback, random, hashlib
import database as db
import util
import threading
import queue
import UpdateService

codeforcesUrl = 'https://codeforces.com/api/'
friendsLastUpdated = {}
aktuelleContests = [] # display scoreboard + upcoming
currentContests = [] # display scoreboard
globalStandings = {}

endTimes = queue.Queue()
for i in range(5):
	endTimes.put(-1)

def sendRequest(method, params, authorized = False, chat = None):
	rnd = random.randint(0, 100000)
	rnd = str(rnd).zfill(6)
	tailPart = method + '?'

	if authorized:
		try:
			if chat == None or chat.apikey == None or chat.secret == None:
				util.log(traceback.format_exc())
				return False
			params['apiKey'] = chat.apikey
			params['time'] = str(int(time.time()))
		except Exception as e:
			util.log(traceback.format_exc(), isError=True)
			return False

	for key in sorted(params):
		tailPart += key + '=' + str(params[key]) + '&'
	request = codeforcesUrl

	if authorized:
		hsh = util.sha512Hex(rnd + '/' + tailPart[:-1] + '#' + chat.secret) # ignore last '&'
		tailPart += 'apiSig=' + rnd + hsh
	request += tailPart
	waitTime = endTimes.get() + 1 - time.time()
	if waitTime > 0:
		time.sleep(waitTime)
	try:
		r = requests.get(request, timeout=15)
	except requests.exceptions.Timeout as errt:
		util.log("Timeout on Codeforces.",errt)
		return False
	endTimes.put(time.time())
	r = r.json()
	if r['status'] == 'OK':
		return r['result']
	else:
		util.log("Invalid Codeforces request: " + r['comment'])
		return False

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
	return db.getFriends(chat.chatId)

def getFriends(chat):
	friends = getFriendsWithDetails(chat)
	return [f[0] for f in friends if f[1] == 1] # only output if ratingWatch is enabled

def updateStandings(contestId):
	global aktuelleContests
	global globalStandings
	handleList = db.getAllFriends()
	handleString = ";".join(handleList)
	util.log('updating standings for contest ' + str(contestId) + ' for all (' + str(len(handleList)) + ') users')
	standings = sendRequest('contest.standings', {'contestId':contestId, 'handles':handleString, 'showUnofficial':True})
	if standings and "contest" in standings:
		contest = standings["contest"]
		aktuelleContests = [contest if contest["id"] == c["id"] else c for c in aktuelleContests]
	util.log('standings received')

	# safe standings globally
	globalStandings[contestId] = {"time": time.time(), "standings": standings}

def getStandings(contestId, handleList):
	if not contestId in globalStandings or time.time() - globalStandings[contestId]["time"] > 30:
		updateStandings(contestId)

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
		if status == 'running':
			aktuelleContests.append(c)
			currentContests.append(c)
		elif status == 'finished' or status == 'testing':
			lastStart = max(lastStart, c.get('startTimeSeconds', -1))
		else:
			aktuelleContests.append(c)
	if len(currentContests) == 0:
		for c in contestList:
			twoDaysOld = time.time()-(c.get('startTimeSeconds', -2)+c.get('durationSeconds', -2)) > 60*60*24*2
			if c.get('startTimeSeconds', -2) == lastStart or (not twoDaysOld and not c in aktuelleContests):
				aktuelleContests.append(c)
				currentContests.append(c)

def getCurrentContests():
	selectImportantContests(aktuelleContests)
	return currentContests

def getCurrentContestsId():
	return [c['id'] for c in getCurrentContests()]

def getFutureContests():
	res = []
	for c in aktuelleContests:
		if c.get('startTimeSeconds', -1) > time.time():
			res.append(c)
	return res

class ContestListService (UpdateService.UpdateService):
	def __init__(self):
		UpdateService.UpdateService.__init__(self, 3600)
		self._doTask()

	def _doTask(self):
		util.log('loading current contests')
		allContests = sendRequest('contest.list', {'gym':'false'})
		selectImportantContests(allContests)
		util.log('loding contests finished')
