from django.http import HttpRequest, HttpResponse, JsonResponse
import json

from .validator import validate_json, ValidationSettings, ValidationType, ValidationResult
from enum import Enum
from django.db.models.query import QuerySet, RawQuerySet
from video.models import FavoriteVideo, SavedSearchQuery, SavedSearchVideo, Page, SavedSearchResult
from django.core import serializers
from typing import Optional, Dict, List, Set
import requests as send_request
from .local_settings import YOUTUBE_API_KEY
from django.forms.models import model_to_dict
from django.db import transaction
import iso8601
from django.core.exceptions import ObjectDoesNotExist
# Create your views here.


class MyResponse:
    __slots__ = ('is_valid', 'error', 'response_json')

    def __init__(self, is_valid: bool, error: Optional[str], response_json: Optional[Dict]):
        self.is_valid = is_valid
        self.error = error
        self.response_json: Dict = {}
        if response_json is not None:
            self.response_json = response_json

    def return_json_response(self) -> JsonResponse:
        self.response_json.update({"success": self.is_valid})
        if self.error is not None and self.error != "":
            self.response_json.update({"error": self.error})
        res: JsonResponse = JsonResponse(self.response_json)
        if self.is_valid:
            res.status_code = 200
        else:
            res.status_code = 400
        return res


def get_array_of_jsonobjects(dict_video_result: RawQuerySet) -> List[Dict]:
    json_data = json.loads(serializers.serialize("json", dict_video_result))
    list_of_objects: List[Dict] = []
    for item in json_data:
        list_of_objects.append(item.get("fields"))
    return list_of_objects


def search(request: HttpRequest):
    json_request_data = json.loads(request.body)

    # Проверяем присланные данные
    def how_validate() -> Dict:
        return {
            "query": ValidationSettings(validation_type=ValidationType.String_Max_255, is_required=True),
            "next_page_token": ValidationSettings(validation_type=ValidationType.String_Max_255, is_required=False)
        }

    validation_result: ValidationResult = validate_json(json_request_data=json_request_data, how_validate=how_validate())

    def check_is_video_exist_in_favorite(video_list: List[Dict], list_id_video: Optional[List[str]]):
        if list_id_video is None:
            list_id_video = []
            for item_object in video_list:
                list_id_video.append(item_object.get("id_video"))

        set_favorite_id_video: Set[str] = set()
        for id_video in FavoriteVideo.objects.in_bulk(list_id_video, field_name="id_video").keys():
            set_favorite_id_video.add(id_video)

        if len(set_favorite_id_video) > 0:
            for item_object in video_list:
                if item_object.get("id_video") in set_favorite_id_video:
                    item_object.update({"is_in_favorite": True})

    # Берем результат поиска из бд, если он есть
    if validation_result.is_valid:

        def get_videos_from_db(json_request_data, dict_id_saved_search_query: Dict) -> MyResponse:
            next_page_token: str = json_request_data.get("next_page_token")

            def get_videos(id_saved_search_query: int, id_page: Optional[int]):
                list_param: List[int] = [id_saved_search_query]
                add_str: str = ";"
                if id_page is not None:
                    add_str = " AND r.id_page = %s;"
                    list_param.append(id_page)

                sql_select: str = "SELECT v.id_saved_search_video, " \
                                  "v.id_video, v.title, v.published_at, v.thumbnail_url " \
                                  "FROM saved_search_video AS v " \
                                  "INNER JOIN saved_search_result AS r " \
                                  "ON v.id_saved_search_video = r.id_saved_search_video " \
                                  "WHERE r.id_saved_search_query = %s" + add_str
                dict_video_result: RawQuerySet = SavedSearchVideo.objects.raw(sql_select, list_param)
                response_json: Dict = {"video_list": get_array_of_jsonobjects(dict_video_result)}
                for item_object in response_json.get("video_list"):
                    item_object.update({"is_in_favorite": False})
                check_is_video_exist_in_favorite(video_list=response_json.get("video_list"), list_id_video=None)

                add_str = ""
                if id_page is not None:
                    add_str = " AND r.id_page = %s "
                dict_page_result: RawQuerySet = Page.objects.raw(
                    "SELECT p.id_page, p.page_token AS next_page_token "
                    "FROM page AS p "
                    "INNER JOIN saved_search_result AS r "
                    "ON p.id_page = r.id_next_page "
                    "WHERE r.id_saved_search_query = %s " + add_str +
                    "LIMIT 1;", list_param
                )

                if len(dict_page_result) > 0:
                    response_json.update({"next_page_token": get_array_of_jsonobjects(dict_page_result)[0]["page_token"]})

                return MyResponse(is_valid=True, error=None, response_json=response_json)

            if next_page_token is not None:
                dict_id_page: Dict = Page.objects.filter(**{"page_token": next_page_token}).values("id_page")[0]

                if len(dict_id_page) > 0:
                    return get_videos(dict_id_saved_search_query.get("id_saved_search_query"), dict_id_page.get("id_page"))
                else:
                    return get_videos(dict_id_saved_search_query.get("id_saved_search_query"), None)
            else:
                return get_videos(dict_id_saved_search_query.get("id_saved_search_query"), None)

        dict_id_saved_search_query: Dict = {}
        try:
            dict_id_saved_search_query = \
                SavedSearchQuery.objects.filter(**{"query": json_request_data.get("query")}).values()[0]
        except IndexError:
            pass
        need_get_from_db: bool = (len(dict_id_saved_search_query) > 0)
        if need_get_from_db and ("next_page_token" in json_request_data):
            dict_result: RawQuerySet = \
                SavedSearchResult.objects.raw(
                    "SELECT r.id_saved_search_result, p.id_page "
                    "FROM saved_search_result AS r "
                    "INNER JOIN page AS p "
                    "ON r.id_page = p.id_page "
                    "WHERE r.id_saved_search_query = %s AND p.page_token = %s;",
                    [dict_id_saved_search_query.get("id_saved_search_query"), json_request_data.get("next_page_token")])

            need_get_from_db = (len(dict_result) > 0)

        if need_get_from_db:
            return get_videos_from_db(json_request_data, dict_id_saved_search_query)

    # Берем результат поиска, используя Youtube API и сохраняем его в бд
    if validation_result.is_valid:
        def save_results_in_db(json_request_data, json_response, items: List[Dict]) -> MyResponse:
            # Сохраняем запрос
            dict_id_saved_search_query: Dict = \
                model_to_dict(SavedSearchQuery.objects.get_or_create(query=json_request_data.get("query"))[0],
                              fields="id_saved_search_query")

            # Сохраняем токен следующей страницы, если он ещё не сохрянен
            dict_id_next_page: Dict = \
                model_to_dict(Page.objects.get_or_create(page_token=json_response.get("nextPageToken"))[0],
                              fields="id_page")

            # Если нам прислали токен следущей страницы, а для этого запрос он текущий, то берем/создаем его из базы
            dict_id_recieved_next_page_token: Dict = {}
            if "next_page_token" in json_request_data.keys():
                dict_id_recieved_next_page_token = \
                    model_to_dict(Page.objects.get_or_create(page_token=json_request_data.get("next_page_token"))[0],
                                  fields="id_page")

            #
            list_id_video: List[str] = []
            video_list: List[Dict] = []
            for item_object in items:
                id_video: str = item_object.get("id").get("videoId")
                snippet: Dict = item_object.get("snippet")
                video_list.append({
                    "id_video": id_video,
                    "title": snippet.get("title"),
                    "published_at": iso8601.parse_date(snippet.get("publishedAt")),
                    "thumbnail_url": snippet.get("thumbnails").get("high").get("url"),
                    "is_in_favorite": False
                })
                list_id_video.append(id_video)

            check_is_video_exist_in_favorite(video_list=video_list, list_id_video=list_id_video)
            # Проверяем что все видео есть в бд, если некоторых нет, то сохраняем их
            # Это делается, так как при разных запросах для поиска могут возвращаться одинаковые видео
            # dict[videoId, id_video_result] -> from db , in video_list
            # for video_list
            # if videoId not in dict
            #   insert -> get last id_video_result -> dict.update(videoId, id_video_result)
            dict_video_id: Dict[str, int] = {}
            for model_object in SavedSearchVideo.objects.in_bulk(list_id_video, field_name="id_video").values():
                item_object = model_to_dict(model_object)
                dict_video_id.update({item_object.get("id_video"): item_object.get("id_saved_search_video")})

            for item_object in video_list:
                id_video: str = item_object.get("id_video")
                if id_video not in dict_video_id:
                    dict_id_saved_search_video: Dict = \
                        model_to_dict(SavedSearchVideo.objects.create(
                            id_video=item_object.get("id_video"), title=item_object.get("title"),
                            published_at=item_object.get("published_at"), thumbnail_url=item_object.get("thumbnail_url")
                        ), fields="id_saved_search_video")
                    dict_video_id.update({id_video: dict_id_saved_search_video.get("id_saved_search_video")})

            # Заполняем таблицу saved_search_result
            with transaction.atomic():
                for id_video, id_video_search_result in dict_video_id.items():
                    SavedSearchResult(
                        id_saved_search_query_id=dict_id_saved_search_query.get("id_saved_search_query"),
                        id_saved_search_video_id=id_video_search_result,
                        id_next_page_id=dict_id_next_page.get("id_page"),
                        id_page_id=dict_id_recieved_next_page_token.get("id_page")).save()

            return MyResponse(is_valid=True, error=None, response_json={
                "video_list": video_list, "next_page_token": json_response.get("nextPageToken")})

        def get_video_from_youtube(json_request_data, query: str) -> MyResponse:
            payload: Dict = {"part": "snippet", "q": query, "type": "video", "key": YOUTUBE_API_KEY, "maxResults": 10}
            if "next_page_token" in json_request_data:
                payload.update({"pageToken": json_request_data.get("next_page_token")})
            response: send_request.Response = \
                send_request.get("https://www.googleapis.com/youtube/v3/search", params=payload)

            if (response.status_code == 200) or (response.status_code == 201):
                json_response = response.json()
                items: List = json_response.get("items")
                if len(items) > 0:
                    return save_results_in_db(json_request_data=json_request_data,
                                              json_response=json_response, items=items)
                else:
                    return MyResponse(is_valid=False, error="no results", response_json=None)
            else:
                return MyResponse(is_valid=False, error="failed to find videos", response_json=None)

        return get_video_from_youtube(json_request_data=json_request_data, query=json_request_data.get("query"))

    return MyResponse(is_valid=validation_result.is_valid, error=validation_result.error, response_json=None)


# Tested
def favorite_list(request: HttpRequest):
    dict_video_result: RawQuerySet = SavedSearchVideo.objects.raw(
        "SELECT v.id_saved_search_video, "
        "v.id_video, v.title, v.published_at, v.thumbnail_url "
        "FROM saved_search_video AS v "
        "INNER JOIN favorite_video AS f "
        "ON v.id_video = f.id_video;")
    response_json: Dict = {"video_list": get_array_of_jsonobjects(dict_video_result)}

    return MyResponse(is_valid=True, error=None, response_json=response_json)


# Tested
def change_video_favorite_status(request: HttpRequest):
    json_request_data = json.loads(request.body)

    # Проверяем присланные данные
    def how_validate() -> Dict:
        return {
            "id_video": ValidationSettings(validation_type=ValidationType.String_Max_255, is_required=True),
            "action": ValidationSettings(validation_type=ValidationType.Int, is_required=True)
        }

    validation_result: ValidationResult = validate_json(json_request_data=json_request_data, how_validate=how_validate())

    if validation_result.is_valid:
        class ActionType(Enum):
            Remove = 0
            Add = 1

        action: int = int(json_request_data.get("action"))
        validation_result.is_valid = (action == 0) or (action == 1)

        if validation_result.is_valid:
            id_video = json_request_data.get("id_video")
            model_favorite_video: FavoriteVideo = None
            try:
                model_favorite_video = FavoriteVideo.objects.get(id_video=id_video)
            except ObjectDoesNotExist:
                pass

            if action == ActionType.Add.value:
                if model_favorite_video is None:
                    FavoriteVideo(id_video=id_video).save()
                else:
                    validation_result.add_error("specified video already exists in favorite list")
            elif action == ActionType.Remove.value:
                if model_favorite_video is None:
                    validation_result.add_error("specified video doesn't exists")
                else:
                    model_favorite_video.delete()
        else:
            validation_result.add_error("must be 0 or 1", key="action")

    return MyResponse(is_valid=validation_result.is_valid, error=validation_result.error, response_json=None)
