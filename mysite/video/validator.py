from typing import NamedTuple, Dict, Optional, Callable
from enum import Enum, auto


class Type(Enum):
    String_Max_255 = 0
    Int = 1


class ValidationSettings(NamedTuple):
    type: Type
    is_required: bool = True


# class ValidationResult(NamedTuple):
#     error: Optional[str]
#     is_valid: bool

class ValidationResult:
    __slots__ = ('error', 'is_valid')

    def __init__(self, error: Optional[str], is_valid: bool):
        self.error: Optional[str] = error
        self.is_valid: bool = is_valid

    def add_error(self, error: str, key: str = None):
        if key is None:
            self.error = error
        else:
            self.error = "invalid " + key + ":" + error
        self.is_valid = False


def validate_value(value, type: Type) -> str:
    error: str = ""
    if type == Type.String_Max_255:
        if len(value) == 0:
            error = "string is empty"
        elif len(value) > 255:
            error = "string max size 255 chars"
    elif type == Type.Int:
        try:
            int(value)
        except ValueError:
            error = "value is not int"
    return error


def validate_json(json_request_data: Dict, how_validate: Dict[str, ValidationSettings]) -> ValidationResult:
    for key, validation_settings in how_validate.items():
        value = json_request_data.get(key)
        if value is not None:
            error: str = validate_value(value, validation_settings.type)
            if error != "":
                return ValidationResult(error=key + " is invalid: " + error, is_valid=False)
        else:
            if validation_settings.is_required:
                return ValidationResult(error=key + " not found, but required", is_valid=False)
    return ValidationResult(error=None, is_valid=True)
