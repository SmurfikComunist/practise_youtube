from typing import NamedTuple, Dict, Optional, Any, Type
from abc import ABC, abstractmethod
from enum import Enum


class ValidationType(Enum):
    String_Max_255 = 0
    Int = 1


class ValidationSettings(NamedTuple):
    validation_type: ValidationType
    is_required: bool = True


class ValidationResult:
    __slots__ = ('error', 'is_valid')

    def __init__(self, error: Optional[str], is_valid: bool):
        self.error = error
        self.is_valid = is_valid

    def add_error(self, error: str, key: str = None):
        if key is None:
            self.error = error
        else:
            self.error = "invalid " + key + ":" + error
        self.is_valid = False


class ValidateStrategy(ABC):
    @abstractmethod
    def validate_value(self, value: Any):
        pass


class Context:
    __slots__ = ("validate_strategy",)

    def __init__(self, validate_strategy: ValidateStrategy) -> None:
        self.validate_strategy = validate_strategy

    def validate_value(self, value: Any) -> str:
        return self.validate_strategy.validate_value(value)


class ValidateStringMax255(ValidateStrategy):
    def validate_value(self, value: Any) -> str:
        error: str = ""
        if type(value) is str:
            if len(value) == 0:
                error = "string is empty"
            elif len(value) > 255:
                error = "string max size 255 chars"
        else:
            error = "value is not string"
        return error


class ValidateInt(ValidateStrategy):
    def validate_value(self, value: Any) -> str:
        error: str = ""
        if type(value) is not int:
            error = "value is not int"
        return error


def validate_value(value: Any, validation_type: ValidationType) -> str:
    dict_how_validate: Dict[ValidationType, Type[ValidateStrategy]] = {
        ValidationType.String_Max_255: ValidateStringMax255,
        ValidationType.Int: ValidateInt
    }

    context: Context = Context(dict_how_validate.get(validation_type)())
    return context.validate_value(value)


def validate_json(json_request_data: Dict, how_validate: Dict[str, ValidationSettings]) -> ValidationResult:
    for key, validation_settings in how_validate.items():
        value = json_request_data.get(key)
        if value is not None:
            error: str = validate_value(value, validation_settings.validation_type)
            if error != "":
                return ValidationResult(error=key + " is invalid: " + error, is_valid=False)
        else:
            if validation_settings.is_required:
                return ValidationResult(error=key + " not found, but required", is_valid=False)
    return ValidationResult(error=None, is_valid=True)
