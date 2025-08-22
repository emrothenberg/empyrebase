from typing import TypeVar, Generic
import copy

T = TypeVar('T')

class Private(Generic[T]):
    def __init__(self, value: T):
        super().__setattr__('_value', value)

    def get(self) -> T:
        return copy.deepcopy(super().__getattribute__('_value'))

    def __getattribute__(self, name):
        if name == '_value':
            raise AttributeError(f"Cannot access private attribute: {name}")
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name == '_value':
            raise AttributeError(f"Cannot modify private attribute: {name}")
        super().__setattr__(name, value)
