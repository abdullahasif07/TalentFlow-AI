import strawberry

from app.graphql.mutations import AIProcessingMutation, ApplicationMutation, JobMutation
from app.graphql.queries import ApplicationQuery, JobQuery


@strawberry.type
class Query(JobQuery, ApplicationQuery):
    pass


@strawberry.type
class Mutation(AIProcessingMutation, JobMutation, ApplicationMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
