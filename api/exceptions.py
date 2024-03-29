from rest_framework.exceptions import APIException
from rest_framework import status


class RequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Bad Request"


class DeniedError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Not Authorized"
