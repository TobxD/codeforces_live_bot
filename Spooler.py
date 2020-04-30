import time
from threading import Thread
import queue

class Spooler:
	def __init__(self, function, threadCount, name="", timeInterval=0):
		self._q = queue.Queue()
		self._function = function
		self._timeInterval = timeInterval
		for i in range(threadCount):
			Thread(target=self._run, name=name + " spooler #" + str(i)).start()

	def put(self, *posArgs, callback=None, **kwArgs):
		info = {'callback':callback, 'posArgs':posArgs, 'kwArgs':kwArgs}
		self._q.put(info)

	def _run(self):
		while True:
			curArg = self._q.get()
			callback = curArg['callback']
			posArgs = curArg['posArgs']
			kwArgs = curArg['kwArgs']
			startT = time.time()
			result = self._function(*posArgs, **kwArgs)
			if callback:
				callback(result)
			sleepT = startT + self._timeInterval - time.time()
			if sleepT > 0:
				time.sleep(sleepT)
