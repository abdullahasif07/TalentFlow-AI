import strawberry

from app.graphql.mutations import (
    AIProcessingMutation,
    ApplicationMutation,
    JobMutation,
    OutreachMutation,
)
from app.graphql.queries import ApplicationQuery, JobQuery


@strawberry.type
class Query(JobQuery, ApplicationQuery):
    pass


@strawberry.type
class Mutation(AIProcessingMutation, JobMutation, ApplicationMutation, OutreachMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
