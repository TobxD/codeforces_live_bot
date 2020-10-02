from typing import List, Dict
from utils import util

class Problem:
	def __init__(self):
		self.solved = False
		self.time = 0 # seconds
		self.rejCount = 0
		self.preliminary = False
		self.upsolved = False
		self.upsolvingRejCount = 0

	def toTableRow(self, isSysTesting=False):
		def formatRej(rejCount, solved=False): # returns 2 chars describing
			if rejCount == 0:
				return ("+ " if solved else "  ")
			return ("+" if solved else "-") + (str(rejCount) if rejCount <= 9 else "∞")

		if self.solved:
			return util.formatSeconds(self.time, self.rejCount != 0, longOk=False)
		if self.preliminary and isSysTesting:
			return "  ? " if self.rejCount == 0 else ("?" + formatRej(self.rejCount) + " ")
		# "-2+3" : 2xWA in contest, 3xWA in upsolving then solved
		return formatRej(self.rejCount) + formatRej(self.upsolvingRejCount, self.upsolved)

class RankingRow:
	def __init__(self, problemCnt):
		self.problems : List[Problem] = [Problem() for i in range(problemCnt)]
		self.ratingInfo : str = "" #e.g. "2800 -> 3400 (+600)"
		self.rank : int = 0
		self.isVirtual : bool = False
	
	def toTableRow(self, handle, isSysTesting=False):
		row = {}
		row["head"] = (("* " if self.isVirtual or self.rank == 0 else "") 
		             + (handle if len(handle) < 11 else handle[:10] + "…")
		             + (" (" + str(self.rank) +".)" if self.rank != 0 else ""))
		if self.ratingInfo:
			row["head2"] = self.ratingInfo
		row["body"] = [p.toTableRow(isSysTesting) for p in self.problems]
		return row

class Ranking:
	def __init__(self, rows, ratingChanges, problemCnt):
		self.ranking : Dict[str, RankingRow] = {} # handle -> RankingRow
		self.order : List[str] = [] # ordered list of handles for standings
		self.parseRanking(rows, ratingChanges, problemCnt)

	def parseRanking(self, rows, ratingChanges, problemCnt):
		def getRatingInfo(handle):
			if handle not in ratingChanges:
				return ""
			(oldR, newR) = ratingChanges[handle]
			ratingC = newR-oldR
			ratingC = ("+" if ratingC >= 0 else "") + str(ratingC)
			return str(oldR) + " -> " + str(newR) + " (" + ratingC + ")"

		for row in rows:
			handle = row["party"]["members"][0]["handle"]
			if handle not in self.ranking:
				self.order.append(handle)
			
			if row["rank"] != 0: # not upsolving but real (or virtual) participation
				rrow = RankingRow(problemCnt)
				rrow.rank = row["rank"]
				rrow.ratingInfo = getRatingInfo(handle)
				rrow.isVirtual = row["party"]["participantType"] == "VIRTUAL"
				
				for i in range(problemCnt):
					sub = row["problemResults"][i]
					problem = rrow.problems[i]
					problem.solved = sub["points"] > 0
					if problem.solved: 
						problem.time = sub["bestSubmissionTimeSeconds"]
					problem.rejCount = sub["rejectedAttemptCount"]
					problem.preliminary = sub["type"] == "PRELIMINARY"

			else: # upsolving:
				rrow = self.ranking.get(handle, RankingRow(problemCnt)) # get old row or new one if not exist
				for i in range(problemCnt):
					sub = row["problemResults"][i]
					problem = rrow.problems[i]
					problem.upsolved = sub["points"] > 0
					problem.upsolvingRejCount = sub["rejectedAttemptCount"]
			self.ranking[handle] = rrow

	def getRows(self, isSysTesting=False):
		return [self.ranking[handle].toTableRow(handle, isSysTesting) for handle in self.order]
