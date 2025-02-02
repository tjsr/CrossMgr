import threading

from Log import getLogger


def startDaemon(target = None, name=None,
                 args=()) -> threading.Thread:
	log = getLogger(name)
	log.info('Starting daemon thread: {}'.format(name))
	t = threading.Thread(daemon=True, target=target, name=name, args=args )
	t.start()
	return t


def joinAndCheckThread(t: threading.Thread, timeout: float = 5) -> bool:
	log = getLogger('joinAndCheckThread')
	t.join(timeout)
	if t.is_alive():
		log.warning('Failed to join {} thread.'.format(t.name))
		return False
	return True


def JoinAndCheckThreads(threadList: list[threading.Thread], timeout: float = 5, listName: str = None) -> bool:
	log = getLogger('JoinAndCheckThreads')
	listName = listName + ' ' if listName else ''
	for t in threadList:
		if joinAndCheckThread(t, timeout):
			threadList.remove(t)

	for t in threadList:
		if t.is_alive():
			log.warning('Thread {} is still alive after waiting on {}list.'.format(t.name, listName))
		else:
			threadList.remove(t)

	attempts = 0
	while len(threadList) > 0:
		attempts += 1
		log.warning('Failed to join all threads in {}list, attempt {}.'.format(listName, attempts))
		for t in threadList:
			log.warning('Thread {} is still waiting, waiting {} seconds...'.format(t.name, timeout))
			if joinAndCheckThread(t, timeout):
				threadList.remove(t)

	if attempts > 0:
		log.warning('Finished waiting on {}list after {} attempts.'.format(listName, attempts))

	return True
