from datetime import datetime
from typing import Protocol
from uuid import UUID

from younilab_geo_tracking_application.contracts import (
    AnswerRequest,
    AnswerResponse,
    ProjectDiscoveryInspection,
    ProjectInspectionCommand,
    ProjectSuggestionCommand,
    ProjectSuggestionResult,
    QueryDraft,
    QueryGenerationCommand,
    QueryResearchCommand,
    QueryResearchResult,
    VerifiedProjectIdentity,
)


class ProviderRequestError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AnswerProvider(Protocol):
    async def generate_answer(self, request: AnswerRequest) -> AnswerResponse: ...


class QueryGenerationProvider(Protocol):
    async def generate_drafts(
        self, command: QueryGenerationCommand
    ) -> list[QueryDraft]: ...


class QueryResearchProvider(Protocol):
    async def research(self, command: QueryResearchCommand) -> QueryResearchResult: ...


class ProjectDiscoveryProvider(Protocol):
    async def inspect_url(
        self, command: ProjectInspectionCommand
    ) -> ProjectDiscoveryInspection: ...

    async def research_suggestions(
        self,
        command: ProjectSuggestionCommand,
        identity: VerifiedProjectIdentity,
    ) -> ProjectSuggestionResult: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
