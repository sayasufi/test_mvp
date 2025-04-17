from rest_framework.pagination import CursorPagination


class CustomCursorPagination(CursorPagination):
    page_size = 20
    ordering = ["date", "-start_time"]
    cursor_query_param = "cursor"
