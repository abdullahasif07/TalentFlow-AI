import strawberry


@strawberry.input
class OffsetPaginationInput:
    limit: int = 25
    offset: int = 0
