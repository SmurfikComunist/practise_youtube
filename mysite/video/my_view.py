from django.http import HttpResponse, HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.views import View
from enum import Enum, auto
from typing import Callable
from .views import MyResponse


class Method(Enum):
    GET = 'GET'
    POST = 'POST'


class RequestSettings(object):
    __slots__ = ('method', 'func_to_call')

    def __init__(self, method: Method, func_to_call: Callable[[HttpRequest], MyResponse]):
        self.method = method
        self.func_to_call = func_to_call

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.method.value == request.method:
            return self.func_to_call(request).return_json_response()
        else:
            return HttpResponseNotAllowed(self.method.value)
