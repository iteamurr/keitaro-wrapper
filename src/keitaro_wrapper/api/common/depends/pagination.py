from keitaro_wrapper.api.common.schemas.pagination import PaginationIn
from keitaro_wrapper.common.pagination import Pagination


def get_pagination(params: PaginationIn) -> Pagination:
    return Pagination(limit=params.limit, offset=params.offset)
