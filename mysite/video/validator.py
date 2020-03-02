from typing import Optional, Any, Type, Callable, TypeVar, Tuple, List, Dict
from enum import Enum
import json
import marshmallow_dataclass
import marshmallow.validate
from recordclass import RecordClass


class ValidationType(Enum):
    """Класс для хранения пользовательских типов."""

    String_Max_255 = marshmallow_dataclass.NewType(
        "String_Max_255", str, validate=marshmallow.validate.Length(min=1, max=255))


class ValidationResult(RecordClass):
    """Класс для хранения результата валидации."""

    is_valid: bool
    validation_error: Optional[str]

    def add_error(self, validation_error: str):
        self.validation_error = validation_error
        self.is_valid = False


_U = TypeVar("_U")


def create_field(
        is_required: bool,
        validate_func: Callable[[_U], _U],
        **kwargs
) -> Dict[str, Any]:
    """Создание словаря для dataclasses.field(), чтобы не ошибиться в написании ключей.

    :param is_required: Если True, то поле обязательное, иначе поле опционально
    :param validate_func: Функция для валидации
    :param kwargs: Дополнительные параметры
    :return: Словарь, который содержит метаданные для dataclasses.field()
    """

    return dict(metadata=dict(required=is_required, validate=validate_func, **kwargs))


def create_field_int(
        is_required: bool,
        validate_func: Callable[[_U], _U]
) -> Dict[str, Any]:
    """Нужно использовать эту функцию для создание int полей,
    так как по умолчанию для int типа параметр strict = False.
    А параметр 'strict' – If True, only integer types are valid. Otherwise, any value castable to int is valid.
    То есть если strict = False и ожидаемый тип является int'ом и
    нам прийдут такие данные - {"id_video_id": "1"}
    то такие данные пройдут валидацию, хотя это неправильно, так как мы ожидаем int.

    :param is_required: Если True, то поле обязательное, иначе поле опционально
    :param validate_func: Функция для валидации
    :return: Словарь, который содержит метаданные для dataclasses.field()
    """

    return create_field(is_required=is_required, validate_func=validate_func, strict=True)


def validate_body_and_get_deserialized_object(
        request_body: bytes,
        cls: Type[Any]
) -> Tuple[ValidationResult, Optional[object]]:
    """Десерилизируем присланные данные(request_body) в Python object и проверяем, что нам прислали json object(dict).
    Генерируем marshmallow схему на основе переданного класса(cls) и валидируем данные.
    Возвращаем результат валидации(ValidationResult)
    и если мы получили валидные данные, то возвращаем десерилизированный обьект типа(cls),
    иначе возвращаем None.
    (Примечание: Десерилизация request_body в Python object происходит в этой функции,
    так как полученный обьект нужен только в этой функции,
    а в остальной программе мы будем использовать десерилизированный обьект типа(cls).)

    :param request_body: Данные содержащие JSON документ
    :param cls: Класс на основе которого происходит валидация
    и обьект этого класса возвращается с содержанием валидных данных
    :return: tuple, содержащий результат валидации и десерилизированный обьект типа(cls), либо None
    """
    try:
        json_body: Any = json.loads(request_body)
        # Проверяем, что нам прислали json object(dict), а не что-то другое
        if type(json_body) is not dict:
            return ValidationResult(is_valid=False, validation_error="Received data is not json object"), None

        schema: Type[marshmallow.Schema] = marshmallow_dataclass.class_schema(cls)
        cls_object: cls = schema().load(json_body)
        return ValidationResult(is_valid=True, validation_error=None), cls_object

    except json.JSONDecodeError as exc:
        return ValidationResult(is_valid=False, validation_error="Invalid JSON"), None

    except marshmallow.exceptions.ValidationError as exc:
        # TODO: Изменить так как exc.messages может быть typing.Union[str, typing.List, typing.Dict]
        key: str
        error_message_list: List[str]
        key, error_message_list = next(iter(exc.messages.items()))
        validation_error: str = "invalid key '{}': {}".format(key, error_message_list[0])
        return ValidationResult(is_valid=False, validation_error=validation_error), None
