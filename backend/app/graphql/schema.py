import strawberry

from app.graphql.mutations import ApplicationMutation, JobMutation
from app.graphql.queries import ApplicationQuery, JobQuery


@strawberry.type
class Query(JobQuery, ApplicationQuery):
    pass


@strawberry.type
class Mutation(JobMutation, ApplicationMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)

