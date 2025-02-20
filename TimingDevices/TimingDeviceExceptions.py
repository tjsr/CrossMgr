class TimingDeviceException(Exception):
	def __init__(self, message: str, cause: BaseException = None, *args, **kwargs):
		kwargs['cause'] = cause
		kwargs['message'] = message
		super().__init__(args, kwargs)


class TimingDeviceNotConnectedException(TimingDeviceException):
	def __init__(self, message: str = 'Device is not connected', cause: BaseException = None):
		super().__init__(message=message, cause=cause)


class UnrecognisedCommandException(TimingDeviceException):
	def __init__(self, command: str):
		super().__init__(f'Unrecognised command type: {command}')

