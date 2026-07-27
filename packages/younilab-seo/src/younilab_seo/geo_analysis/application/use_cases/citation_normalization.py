from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from younilab_seo.geo_analysis.application.contracts import (
    GeoRunResultCitationFact,
    GeoRunResultCitationNormalization,
    SaveRunResultCitationNormalizationCommand,
)
from younilab_seo.geo_analysis.application.interfaces import (
    CitationUrlResolver,
    Clock,
)
from younilab_seo.geo_analysis.application.interfaces.citation_normalization import (
    CitationNormalizationPersistence,
)

DEFAULT_CITATION_NORMALIZER_VERSION = "url_domain:v2"
VERTEX_GROUNDING_REDIRECT_HOST = "vertexaisearch.cloud.google.com"


class RunResultCitationNormalizationNotFound(LookupError):
    """找不到租戶可存取的 GEO run result，無法進行 citation normalization。"""


@dataclass(frozen=True)
class NormalizeRunResultCitations:
    """從 runner references 產生報表可計算的 deterministic citation facts。"""

    persistence: CitationNormalizationPersistence
    clock: Clock
    normalizer_version: str = DEFAULT_CITATION_NORMALIZER_VERSION
    url_resolver: CitationUrlResolver | None = None

    async def execute(
        self,
        tenant_id: UUID,
        run_result_id: UUID,
        force_renormalize: bool = False,
        normalizer_version: str | None = None,
    ) -> GeoRunResultCitationNormalization:
        version = normalizer_version or self.normalizer_version
        context = await self.persistence.load_citation_normalization_context(
            tenant_id,
            run_result_id,
        )
        if context is None:
            raise RunResultCitationNormalizationNotFound("run result not found")
        result = context.run_result
        if not force_renormalize:
            current = await self.persistence.get_existing_citation_normalization(
                tenant_id,
                run_result_id,
                version,
            )
            if current is not None:
                return current

        if context.project_id is None:
            return await self._save(
                tenant_id,
                self._failed(
                    run_result_id,
                    None,
                    version,
                    "query_context_missing",
                    "query context is missing",
                ),
            )

        if result.status != "completed":
            return await self._save(
                tenant_id,
                self._failed(
                    run_result_id,
                    context.project_id,
                    version,
                    "run_result_not_normalizable",
                    "run result is not completed",
                ),
            )

        owned_domains = _owned_domains(context.owned_website_urls)
        citations: list[GeoRunResultCitationFact] = []
        skipped_reference_count = 0
        for reference in result.references:
            normalized = await self._normalize_reference_url(reference.url)
            if normalized is None:
                skipped_reference_count += 1
                continue
            normalized_url, domain = normalized
            ownership = (
                "owned"
                if any(_domain_matches(domain, owned) for owned in owned_domains)
                else "other"
            )
            citations.append(
                GeoRunResultCitationFact(
                    run_result_id=result.id,
                    reference_id=reference.id,
                    url=normalized_url,
                    domain=domain,
                    title=reference.title,
                    position=reference.position,
                    ownership=ownership,
                    source_type="owned_site" if ownership == "owned" else "unknown",
                )
            )

        return await self._save(
            tenant_id,
            GeoRunResultCitationNormalization(
                run_result_id=result.id,
                project_id=context.project_id,
                normalizer_version=version,
                status="completed",
                citations=citations,
                skipped_reference_count=skipped_reference_count,
            ),
        )

    async def _normalize_reference_url(self, url: str) -> tuple[str, str] | None:
        candidate = url
        if self.url_resolver is not None and _is_provider_redirect_url(url):
            resolved = await self.url_resolver.resolve(url)
            if resolved:
                candidate = resolved
        normalized = _normalize_url(candidate)
        if normalized is not None:
            return normalized
        if candidate != url:
            return _normalize_url(url)
        return None

    def _failed(
        self,
        run_result_id: UUID,
        project_id: UUID | None,
        normalizer_version: str,
        error_code: str,
        error_message: str,
    ) -> GeoRunResultCitationNormalization:
        return GeoRunResultCitationNormalization(
            run_result_id=run_result_id,
            project_id=project_id,
            normalizer_version=normalizer_version,
            status="failed",
            error_code=error_code,
            error_message=error_message,
        )

    async def _save(
        self,
        tenant_id: UUID,
        normalization: GeoRunResultCitationNormalization,
    ) -> GeoRunResultCitationNormalization:
        saved = await self.persistence.save_citation_normalization(
            tenant_id,
            SaveRunResultCitationNormalizationCommand(normalization=normalization),
            self.clock.now(),
        )
        if saved is None:
            raise RunResultCitationNormalizationNotFound("run result not found")
        return saved


def _owned_domains(website_urls: tuple[str, ...]) -> set[str]:
    domains = set()
    for website_url in website_urls:
        normalized = _normalize_url(website_url)
        if normalized is not None:
            domains.add(normalized[1])
    return domains


def _normalize_url(value: str) -> tuple[str, str] | None:
    text = value.strip()
    if not text or any(character.isspace() for character in text):
        return None
    candidate = text if "://" in text else f"https://{text}"
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    host = parsed.hostname
    if host is None:
        return None
    domain = _normalize_domain(host)
    if not domain or "." not in domain:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    netloc = domain
    if port is not None and not _is_default_port(parsed.scheme, port):
        netloc = f"{domain}:{port}"
    path = parsed.path
    if path == "/":
        path = ""
    elif path.endswith("/"):
        path = path.rstrip("/")
    normalized_url = urlunsplit(
        (
            parsed.scheme.lower(),
            netloc,
            path,
            parsed.query,
            "",
        )
    )
    return normalized_url, domain


def _is_provider_redirect_url(value: str) -> bool:
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    host = parsed.hostname
    return (
        host is not None
        and _normalize_domain(host) == VERTEX_GROUNDING_REDIRECT_HOST
        and parsed.path.startswith("/grounding-api-redirect/")
    )


def _normalize_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    return domain[4:] if domain.startswith("www.") else domain


def _is_default_port(scheme: str, port: int) -> bool:
    return (scheme.lower() == "http" and port == 80) or (
        scheme.lower() == "https" and port == 443
    )


def _domain_matches(domain: str, owned_domain: str) -> bool:
    return domain == owned_domain or domain.endswith(f".{owned_domain}")
