import atexit
import logging
from logging.handlers import QueueHandler
from logging.config import ConvertingDict, valid_ident, ConvertingList
from multiprocessing import Queue


def _resolve_handlers(l):
	if not isinstance(l, ConvertingList):
		return l

	# Indexing the list performs the evaluation.
	return [l[i] for i in range(len(l))]


def _resolve_queue(q: Queue):
	if not isinstance(q, ConvertingDict):
		return q
	if '__resolved_value__' in q:
		return q['__resolved_value__']

	cname = q.pop('class')
	klass = q.configurator.resolve(cname)
	props = q.pop('.', None)
	kwargs = {k: q[k] for k in q if valid_ident(k)}
	result = klass(**kwargs)
	if props:
		for name, value in props.items():
			setattr(result, name, value)

	q['__resolved_value__'] = result
	return result


class QueueListenerHandler(logging.handlers.QueueHandler):
	def __init__(self, handlers: list[logging.Handler], respect_handler_level: bool=False, auto_run: bool=True, queue: Queue=Queue(-1)):
		queue = _resolve_queue(queue)
		super().__init__(queue)
		handlers = _resolve_handlers(handlers)
		self._listener = logging.handlers.QueueListener(
			self.queue,
			*handlers,
			respect_handler_level=respect_handler_level)
		if auto_run:
			self.start()
			atexit.register(self.stop)

	def start(self):
		self._listener.start()

	def stop(self):
		self._listener.stop()

	def emit(self, record):
		return super().emit(record)

	def handle(self, record):
		print(f'In QueueListenerHandler.handle method: {self}, {record}')
		if isinstance(self, str):
			print(f'QueueListenerHandler.handle got a string: {record}')
			return None
		else:
			return super().handle(record)

	def handleError(self, record):
		if isinstance(self, str):
			print(f'QueueListenerHandler.handle got a string: {record}')
			return None
		else:
			return super().handleError(record)
