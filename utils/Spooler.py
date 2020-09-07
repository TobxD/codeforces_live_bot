import time
from threading import Thread
import queue

from utils.util import logger, perfLogger

class Spooler:
	def __init__(self, threadCount, name="", timeInterval=0):
		self._q = queue.Queue()
		self._timeInterval = timeInterval
		self._threadCount = threadCount
		self._name = name
		for i in range(threadCount):
			Thread(target=self._run, name=name + " spooler #" + str(i)).start()

	def put(self, callbackFun):
		self._q.put((time.time(), callbackFun))

	def _run(self):
		while True:
			(timeStamp, callbackFun) = self._q.get()
			startT = time.time()
			timeUsed = startT-timeStamp
			if timeUsed > 0.001:
				perfLogger.info("time in spooler: {:.3f}s".format(timeUsed))
			try:
				callbackFun()
			except Exception as e:
				logger.critical('%s spooler error %s', self._name, e, exc_info=True)
			sleepT = startT + self._timeInterval - time.time()
			if sleepT > 0:
				time.sleep(sleepT)
