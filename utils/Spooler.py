import time
from threading import Thread, Condition
import queue

from utils.util import logger, perfLogger

class Spooler:
	def __init__(self, threadCount, name="", timeInterval=0, priorityCount=1):
		self._q = list()
		for i in range(priorityCount):
			self._q.append(queue.Queue())
		self._timeInterval = timeInterval
		self._threadCount = threadCount
		self._name = name
		self._lock = Condition()
		for i in range(threadCount):
			Thread(target=self._run, name=name + " spooler #" + str(i)).start()

	def put(self, callbackFun, priority):
		with self._lock:
			self._q[priority].put((time.time(), callbackFun))
			self._lock.notify()

	def _run(self):
		while True:
			found = False
			with self._lock:
				for i in range(len(self._q)):
					if self._q[i].qsize() > 0:
						(timeStamp, callbackFun) = self._q[i].get()
						found = True
						break
				if not found:
					self._lock.wait()
			if found:
				startT = time.time()
				try:
					callbackFun()
					timeInSpooler = startT-timeStamp
					timeForFun = time.time()-startT
					if timeInSpooler > 0.001 or timeForFun > 0.001:
						perfLogger.info("time in spooler: {:.3f}s; time for fun: {:.3f}s".format(timeInSpooler, timeForFun))
				except Exception as e:
					logger.critical('%s spooler error %s', self._name, e, exc_info=True)
				sleepT = startT + self._timeInterval - time.time()
				if sleepT > 0:
					time.sleep(sleepT)
