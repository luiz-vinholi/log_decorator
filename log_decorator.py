import functools
import inspect
from contextlib import contextmanager
from typing import Any, List, Optional

from .logger import logger


def log(action: Optional[str] = None, 
        identifier: Optional[str] = None,
        inject: Optional[bool] = False):
    """
    Decorator that adds logging functionality (which will automatically log start and end by default) to 
    a function.

    Args:
        action (Optional[str]): The action being performed by the function.
        identifier (Optional[str]): The identifier for the function.
        inject (Optional[bool]): Whether to inject the logger into the function's keyword arguments.

    Returns:
        The decorated function.

    Example usage:
        @log(action='performing operation', identifier='user_id', inject=True)
        def my_function(user_id, **kwargs):
            # __logger is available as a keyword argument when inject parameter is set to True
            kwargs['__logger'].info('This is a log message')
            # Function implementation

    The `log` decorator can be used to add logging functionality to a function. It wraps the function
    with a context manager that logs the start and finish of the function, as well as any exceptions
    that occur during its execution.

    The `action` parameter specifies the action being performed by the function, which will be included
    in the log message. The `identifier` parameter specifies the identifier for the function, which can
    be used to identify the specific parameter of the function being executed. The `inject` parameter
    determines whether the logger should be injected into the function's keyword arguments.

    When the decorated function is called, the logger will be available as a keyword argument named
    '__logger', if parameter `inject` setted with True. This allows the function to log additional 
    messages during its execution.

    Note: This decorator is designed to be used with synchronous and asynchronous functions.
    """
        
    def decorator(func):
        @contextmanager
        def log_context(*args, **kwargs):
            pattern = '{func_name} with args: {args}'
            if identifier:
                pattern = '{func_name} with {identifier_name}: {identifier_value}'
                identifier_value = __get_func_param_by_name(func, args, identifier)
            if action:
                pattern = '{action} with {identifier_name}: {identifier_value}'

            __logger = __Logger(
                pattern,
                action=action,
                func_name=func.__name__,
                args=args,
                identifier_name=identifier,
                identifier_value=identifier_value,
            )

            if inject:
                kwargs['__logger'] = __logger

            try:
                __logger.start()
                yield kwargs
                __logger.finish()
            except Exception as e:
                __logger.exception(str(e))
                raise e


        @functools.wraps(func)
        def wrapper_sync(*args, **kwargs):
            with log_context(*args, **kwargs) as new_kwargs:
                return func(*args, **new_kwargs)


        @functools.wraps(func)
        async def wrapper_async(*args, **kwargs):
            with log_context(*args, **kwargs) as new_kwargs:
                return await func(*args, **new_kwargs)


        if inspect.iscoroutinefunction(func):
            return wrapper_async
        return wrapper_sync
    return decorator


class __Logger():
    def __init__(self, message_pattern: str, **kwargs):
        self._message = message_pattern.format(
            action=kwargs['action'] or '',
            func_name=kwargs['func_name'],
            args=kwargs['args'],
            identifier_name=kwargs['identifier_name'] or '',
            identifier_value=kwargs['identifier_value'] or '',
        )
        self._logger = {
            'info': logger.info,
            'debug': logger.debug,
            'warning': logger.warning,
            'error': logger.error,
            'exception': logger.exception,
        }


    def __log(self, type: str, message: str):
        self._logger[type](f'{self._message} | {message}')


    def start(self):
        self._logger['info'](f'Starting {self._message}')


    def info(self, message: str):
        self.__log('info', message)


    def debug(self, message: str):
        self.__log('debug', message)

    
    def warning(self, message: str):
        self.__log('warning', message)

    
    def error(self, message: str):
        self.__log('error', message)


    def exception(self, message: str):
        self.__log('exception', message)


    def finish(self):
        self._logger['info'](f'Finished {self._message}')


def __get_func_param_by_name(func, args: List[Any], param_name: str):
    func_args = list(inspect.signature(func).parameters.keys())
    try:
        identifier_index = func_args.index(param_name)
        identifier_value = args[identifier_index]
    except ValueError:
        raise ValueError(f'Identifier {param_name} not found in function arguments')
    return identifier_value
