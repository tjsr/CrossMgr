import asyncio
from threading import Thread
from typing import Callable, Any


def spawn_event(handler: Callable[..., Any], **kwargs: Any):
	async def async_handler():
		await handler(**kwargs)

	if asyncio.iscoroutinefunction(handler):
		socket_connect_thread = Thread(target=asyncio.run, args=(async_handler(),))
	else:
		socket_connect_thread = Thread(target=handler, kwargs=kwargs)

	socket_connect_thread.name = f'Ultra {handler.__name__} handler'
	socket_connect_thread.daemon = True
	socket_connect_thread.start()

