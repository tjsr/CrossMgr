import asyncio
from threading import Thread
from typing import Callable, Any

import Log


def spawn_event(handler: Callable[..., Any], **kwargs: Any):
	def sync_handler() -> Any | None:
		try:
			return handler(**kwargs)
		except Exception as e:
			Log.getLogger('UltraThreadUtils').exception(f'Error in {handler.__name__}', exc_info=e)
			pass

	async def async_handler() -> Any | None:
		try:
			return await handler(**kwargs)
		except Exception as e:
			Log.getLogger('UltraThreadUtils').exception(f'Error in {handler.__name__}', exc_info=e)
			pass

	if asyncio.iscoroutinefunction(handler):
		spawned_thread = Thread(target=asyncio.run, args=(async_handler(),))
		spawned_thread.name = f'Ultra {handler.__name__} async handler'
		Log.getLogger(name='spawn_event').debug(f'Spawning async thread for {spawned_thread.name}.')
	else:
		spawned_thread = Thread(target=sync_handler, kwargs=kwargs)
		spawned_thread.name = f'Ultra {handler.__name__} handler'
		Log.getLogger(name='spawn_event').debug(f'Spawning sync thread for {spawned_thread.name}.')

	spawned_thread.daemon = True
	spawned_thread.start()

