--
-- PostgreSQL database dump
--

\set ON_ERROR_STOP on

\restrict AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA

BEGIN;

-- Dumped from database version 18.4 (Debian 18.4-1.pgdg13+1)
-- Dumped by pg_dump version 18.4 (Debian 18.4-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: geo_ai_platform; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_ai_platform (
    id uuid NOT NULL,
    code character varying(64) NOT NULL,
    display_name character varying(100) NOT NULL,
    provider_type character varying(32) NOT NULL,
    default_model character varying(100),
    supports_citations boolean DEFAULT false NOT NULL,
    supports_grounding boolean DEFAULT false NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_daily_run_batch; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_daily_run_batch (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    business_date date NOT NULL,
    scheduled_for timestamp with time zone NOT NULL,
    status character varying(32) NOT NULL,
    candidate_count integer DEFAULT 0 NOT NULL,
    job_count integer DEFAULT 0 NOT NULL,
    budget_enforced boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_entity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_entity (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    entity_type character varying(32) NOT NULL,
    name character varying(200) NOT NULL,
    website_url text,
    description text DEFAULT ''::text NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_entity_alias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_entity_alias (
    id uuid NOT NULL,
    entity_id uuid NOT NULL,
    alias character varying(200) NOT NULL,
    match_type character varying(32) DEFAULT 'exact'::character varying NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_external_run_reference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_external_run_reference (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    external_system character varying(100) NOT NULL,
    external_run_id character varying(200) NOT NULL,
    external_status character varying(64) NOT NULL,
    callback_received_at timestamp with time zone,
    result_location text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_job_dispatch_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_job_dispatch_event (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    event_type character varying(64) NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    actor character varying(100) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: geo_market; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_market (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    region character varying(16) NOT NULL,
    language character varying(16) NOT NULL,
    market_name character varying(100) NOT NULL,
    prompt_locale_hint text DEFAULT ''::text NOT NULL,
    serp_gl character varying(16),
    serp_hl character varying(16),
    serp_location character varying(200),
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_message_dispatch_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_message_dispatch_log (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    message_backend character varying(32) NOT NULL,
    destination character varying(200) NOT NULL,
    message_id character varying(200),
    payload jsonb NOT NULL,
    publish_status character varying(32) NOT NULL,
    published_at timestamp with time zone,
    error_message text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_project (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid,
    name character varying(200) NOT NULL,
    default_region character varying(16) DEFAULT 'TW'::character varying NOT NULL,
    default_language character varying(16) DEFAULT 'zh-TW'::character varying NOT NULL,
    status character varying(32) NOT NULL,
    daily_run_budget integer DEFAULT 0 NOT NULL,
    daily_cost_budget numeric(12,6),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    archived_at timestamp with time zone
);


--
-- Name: geo_project_query_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_project_query_settings (
    project_id uuid NOT NULL,
    research_provider character varying(64) NOT NULL,
    run_provider character varying(64) NOT NULL,
    keywords jsonb DEFAULT '[]'::jsonb NOT NULL,
    market_type character varying(32) NOT NULL,
    max_queries integer NOT NULL,
    audience_name character varying(200) NOT NULL,
    audience_description text NOT NULL,
    intents jsonb NOT NULL,
    should_mention_own_brand boolean NOT NULL,
    should_mention_competitor boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_geo_project_query_settings_audience_description CHECK (((btrim(audience_description) <> ''::text) AND (length(audience_description) <= 2000))),
    CONSTRAINT ck_geo_project_query_settings_audience_name CHECK ((btrim((audience_name)::text) <> ''::text)),
    CONSTRAINT ck_geo_project_query_settings_intents CHECK (((jsonb_typeof(intents) = 'array'::text) AND ((jsonb_array_length(intents) >= 1) AND (jsonb_array_length(intents) <= 4)) AND (max_queries >= jsonb_array_length(intents)))),
    CONSTRAINT ck_geo_project_query_settings_keywords CHECK (((jsonb_typeof(keywords) = 'array'::text) AND (jsonb_array_length(keywords) <= 10))),
    CONSTRAINT ck_geo_project_query_settings_market_type CHECK (((market_type)::text = ANY ((ARRAY['b2c'::character varying, 'b2b_procurement'::character varying])::text[]))),
    CONSTRAINT ck_geo_project_query_settings_max_queries CHECK (((max_queries >= 1) AND (max_queries <= 40))),
    CONSTRAINT ck_geo_project_query_settings_research_provider CHECK (((research_provider)::text = ANY ((ARRAY['gemini'::character varying, 'openai'::character varying])::text[]))),
    CONSTRAINT ck_geo_project_query_settings_run_provider CHECK (((run_provider)::text = 'gemini'::text))
);


--
-- Name: geo_query; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    topic_id uuid,
    query_text text NOT NULL,
    region character varying(16) NOT NULL,
    language character varying(16) NOT NULL,
    market_type character varying(32) DEFAULT 'b2b_procurement'::character varying NOT NULL,
    intent character varying(32),
    buyer_stage character varying(32),
    is_branded boolean DEFAULT false NOT NULL,
    priority character varying(32) DEFAULT 'normal'::character varying NOT NULL,
    status character varying(32) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    archived_at timestamp with time zone,
    CONSTRAINT ck_geo_query_market_type CHECK (((market_type)::text = ANY ((ARRAY['b2c'::character varying, 'b2b_procurement'::character varying])::text[])))
);


--
-- Name: geo_query_draft; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_draft (
    id uuid NOT NULL,
    generation_run_id uuid NOT NULL,
    project_id uuid NOT NULL,
    topic_id uuid,
    topic_name character varying(200) DEFAULT ''::character varying NOT NULL,
    query_text text NOT NULL,
    keywords jsonb DEFAULT '[]'::jsonb NOT NULL,
    region character varying(16) NOT NULL,
    language character varying(16) NOT NULL,
    market_type character varying(32) NOT NULL,
    intent character varying(32),
    is_branded boolean DEFAULT false NOT NULL,
    status character varying(32) DEFAULT 'draft'::character varying NOT NULL,
    selection_status character varying(32),
    accepted_query_id uuid,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_query_draft_selection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_draft_selection (
    id uuid NOT NULL,
    draft_id uuid NOT NULL,
    selection_status character varying(32) NOT NULL,
    query_id uuid,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_query_generation_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_generation_run (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    provider character varying(64) NOT NULL,
    status character varying(32) NOT NULL,
    request_payload jsonb NOT NULL,
    error_code character varying(100),
    error_message text,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: geo_query_keyword; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_keyword (
    id uuid NOT NULL,
    query_id uuid NOT NULL,
    keyword character varying(200) NOT NULL,
    search_volume integer,
    region character varying(16) NOT NULL,
    language character varying(16) NOT NULL,
    source character varying(64) DEFAULT 'manual'::character varying NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_query_platform; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_platform (
    id uuid NOT NULL,
    query_id uuid NOT NULL,
    platform_id uuid NOT NULL,
    model character varying(100),
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_query_research_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_research_run (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    provider character varying(64) NOT NULL,
    status character varying(32) NOT NULL,
    request_payload jsonb NOT NULL,
    research_context text,
    searched_keywords jsonb DEFAULT '[]'::jsonb NOT NULL,
    source_urls jsonb DEFAULT '[]'::jsonb NOT NULL,
    error_code character varying(100),
    error_message text,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: geo_query_run_job; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_run_job (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    query_id uuid NOT NULL,
    platform_id uuid NOT NULL,
    schedule_id uuid,
    job_type character varying(32) DEFAULT 'scheduled_run'::character varying NOT NULL,
    priority character varying(32) DEFAULT 'normal'::character varying NOT NULL,
    scheduled_for timestamp with time zone NOT NULL,
    business_date date GENERATED ALWAYS AS (((scheduled_for AT TIME ZONE 'Asia/Taipei'::text))::date) STORED,
    is_daily_slot_owner boolean DEFAULT true NOT NULL,
    status character varying(32) NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 3 NOT NULL,
    next_retry_at timestamp with time zone,
    dedupe_key character varying(200) NOT NULL,
    dispatch_backend character varying(32),
    dispatch_message_id character varying(200),
    external_run_id character varying(200),
    last_error_code character varying(100),
    last_error_message text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    batch_id uuid,
    source character varying(32) DEFAULT 'manual'::character varying NOT NULL,
    execution_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: geo_query_schedule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_query_schedule (
    id uuid NOT NULL,
    query_id uuid NOT NULL,
    platform_id uuid NOT NULL,
    frequency character varying(32) NOT NULL,
    priority character varying(32) DEFAULT 'normal'::character varying NOT NULL,
    timezone character varying(64) DEFAULT 'Asia/Taipei'::character varying NOT NULL,
    next_run_at timestamp with time zone,
    last_scheduled_at timestamp with time zone,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_response_semantic_fact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_response_semantic_fact (
    id uuid NOT NULL,
    analysis_id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    fact_type character varying(32) NOT NULL,
    value text NOT NULL,
    evidence_text text,
    confidence numeric(5,4),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_run_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_request (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    tracking_run_request_id character varying(200) NOT NULL,
    provider character varying(64) NOT NULL,
    timing character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    error_code character varying(100),
    error_message text,
    request_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: geo_run_result; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result (
    id uuid NOT NULL,
    run_request_id uuid NOT NULL,
    job_id uuid NOT NULL,
    tracking_result_id character varying(200) NOT NULL,
    query_id uuid NOT NULL,
    provider character varying(64) NOT NULL,
    surface character varying(100) NOT NULL,
    model character varying(100) NOT NULL,
    region character varying(16) NOT NULL,
    language character varying(16) NOT NULL,
    status character varying(32) NOT NULL,
    raw_response text DEFAULT ''::text NOT NULL,
    error text,
    run_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_run_result_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_analysis (
    id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    task_key character varying(100) NOT NULL,
    schema_version integer NOT NULL,
    status character varying(32) NOT NULL,
    summary text,
    overall_sentiment character varying(32),
    theme character varying(200),
    kmindhub_commit_batch_id character varying(200),
    kmindhub_item_id character varying(200),
    error_code character varying(100),
    error_message text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    analyzer character varying(64),
    analyzer_version character varying(100),
    analyzer_request_payload jsonb,
    analyzer_response_payload jsonb,
    validation_failures jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: geo_run_result_citation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_citation (
    id uuid NOT NULL,
    normalization_id uuid CONSTRAINT geo_run_result_citation_normalization_id_not_null1 NOT NULL,
    run_result_id uuid NOT NULL,
    reference_id uuid NOT NULL,
    url text NOT NULL,
    domain character varying(255) NOT NULL,
    title text,
    "position" integer NOT NULL,
    ownership character varying(32) NOT NULL,
    source_type character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_run_result_citation_classification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_citation_classification (
    id uuid NOT NULL,
    run_result_reference_id uuid CONSTRAINT geo_run_result_citation_classi_run_result_reference_id_not_null NOT NULL,
    analysis_id uuid NOT NULL,
    classification character varying(32) NOT NULL,
    matched_entity_id uuid,
    matched_domain character varying(255),
    confidence numeric(5,4),
    source character varying(64) DEFAULT 'rule_based'::character varying NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_run_result_citation_normalization; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_citation_normalization (
    id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    project_id uuid NOT NULL,
    normalizer_version character varying(100) CONSTRAINT geo_run_result_citation_normalizati_normalizer_version_not_null NOT NULL,
    status character varying(32) NOT NULL,
    error_code character varying(100),
    error_message text,
    skipped_reference_count integer DEFAULT 0 CONSTRAINT geo_run_result_citation_normal_skipped_reference_count_not_null NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: geo_run_result_entity_detection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_entity_detection (
    id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    detector_version character varying(100) NOT NULL,
    status character varying(32) NOT NULL,
    error_code character varying(100),
    error_message text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: geo_run_result_entity_detection_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_entity_detection_item (
    id uuid NOT NULL,
    detection_id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    entity_id uuid NOT NULL,
    entity_role character varying(32) NOT NULL,
    entity_name character varying(200) NOT NULL,
    mentioned boolean NOT NULL,
    first_mention_order integer,
    evidence_text text,
    matched_by character varying(32),
    matched_value text,
    match_type character varying(32),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: geo_run_result_entity_mention; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_entity_mention (
    id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    analysis_id uuid NOT NULL,
    entity_id uuid,
    entity_name character varying(200) NOT NULL,
    entity_type character varying(32) NOT NULL,
    mention_count integer NOT NULL,
    sentiment character varying(32) NOT NULL,
    evidence_text text DEFAULT ''::text NOT NULL,
    kmindhub_item_id character varying(200),
    created_at timestamp with time zone NOT NULL,
    entity_role character varying(32),
    mentioned boolean,
    first_mention_order integer,
    confidence numeric(5,4)
);


--
-- Name: geo_run_result_reference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_reference (
    id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    url text NOT NULL,
    title text,
    domain character varying(255),
    "position" integer NOT NULL
);


--
-- Name: geo_run_result_statement; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_run_result_statement (
    id uuid NOT NULL,
    run_result_id uuid NOT NULL,
    analysis_id uuid NOT NULL,
    statement_text text NOT NULL,
    theme character varying(200) DEFAULT ''::character varying NOT NULL,
    sentiment character varying(32) NOT NULL,
    subject_entity_name character varying(200),
    evidence_text text DEFAULT ''::text NOT NULL,
    kmindhub_item_id character varying(200),
    created_at timestamp with time zone NOT NULL,
    entity_id uuid,
    entity_role character varying(32),
    entity_name character varying(200),
    confidence numeric(5,4)
);


--
-- Name: geo_topic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_topic (
    id uuid NOT NULL,
    project_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_worker_lease; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.geo_worker_lease (
    id uuid NOT NULL,
    job_id uuid NOT NULL,
    worker_id character varying(100) NOT NULL,
    leased_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    released_at timestamp with time zone,
    release_reason character varying(64)
);


--
-- Name: provider_pricing_rate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_pricing_rate (
    id uuid NOT NULL,
    platform_code character varying(64) NOT NULL,
    provider_code character varying(64) NOT NULL,
    model character varying(128) NOT NULL,
    provider_region_class character varying(16) NOT NULL,
    traffic_type character varying(64) NOT NULL,
    meter_code character varying(64) NOT NULL,
    unit_quantity numeric(20,4) NOT NULL,
    unit_price_usd numeric(20,10) NOT NULL,
    effective_from timestamp with time zone NOT NULL,
    effective_to timestamp with time zone,
    source_url text NOT NULL,
    source_checked_at date NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_provider_pricing_rate_meter CHECK (((meter_code)::text = ANY ((ARRAY['input_token'::character varying, 'cached_input_token'::character varying, 'output_token'::character varying, 'google_web_search_query'::character varying])::text[]))),
    CONSTRAINT ck_provider_pricing_rate_region CHECK (((provider_region_class)::text = ANY ((ARRAY['global'::character varying, 'non_global'::character varying, 'any'::character varying])::text[]))),
    CONSTRAINT ck_provider_pricing_rate_values CHECK (((unit_quantity > (0)::numeric) AND (unit_price_usd >= (0)::numeric) AND ((effective_to IS NULL) OR (effective_to > effective_from))))
);


--
-- Name: provider_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.provider_request (
    id uuid NOT NULL,
    operation_id uuid NOT NULL,
    request_number integer NOT NULL,
    request_kind character varying(32) NOT NULL,
    platform_code character varying(64) NOT NULL,
    provider_code character varying(64) NOT NULL,
    provider_operation character varying(64) NOT NULL,
    use_case character varying(64) NOT NULL,
    source_service character varying(64) NOT NULL,
    model character varying(128),
    uses_grounding boolean DEFAULT false NOT NULL,
    status character varying(16) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    duration_ms integer,
    http_status integer,
    error_code character varying(128),
    error_type character varying(128),
    tenant_id uuid,
    project_id uuid,
    job_id uuid,
    query_id uuid,
    run_request_id uuid,
    provider_region character varying(64),
    traffic_type character varying(64),
    usage_capture_status character varying(16) DEFAULT 'not_applicable'::character varying NOT NULL,
    input_token_count bigint,
    output_token_count bigint,
    total_token_count bigint,
    cached_input_token_count bigint,
    reasoning_token_count bigint,
    tool_input_token_count bigint,
    usage_metadata jsonb,
    meter_usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_provider_request_meter_usage CHECK ((jsonb_typeof(meter_usage) = 'object'::text)),
    CONSTRAINT ck_provider_request_status CHECK (((status)::text = ANY ((ARRAY['started'::character varying, 'succeeded'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_provider_request_token_counts CHECK ((((input_token_count IS NULL) OR (input_token_count >= 0)) AND ((output_token_count IS NULL) OR (output_token_count >= 0)) AND ((total_token_count IS NULL) OR (total_token_count >= 0)) AND ((cached_input_token_count IS NULL) OR (cached_input_token_count >= 0)) AND ((reasoning_token_count IS NULL) OR (reasoning_token_count >= 0)) AND ((tool_input_token_count IS NULL) OR (tool_input_token_count >= 0)))),
    CONSTRAINT ck_provider_request_usage_capture_status CHECK (((usage_capture_status)::text = ANY ((ARRAY['pending'::character varying, 'recorded'::character varying, 'unavailable'::character varying, 'not_applicable'::character varying])::text[]))),
    CONSTRAINT ck_provider_request_usage_metadata CHECK (((usage_metadata IS NULL) OR (jsonb_typeof(usage_metadata) = 'object'::text))),
    CONSTRAINT provider_request_duration_ms_check CHECK ((duration_ms >= 0)),
    CONSTRAINT provider_request_request_number_check CHECK ((request_number > 0))
);


--
-- Name: provider_request_cost_estimate; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.provider_request_cost_estimate AS
 WITH usage_quantities AS (
         SELECT request.id,
            request.operation_id,
            request.request_number,
            request.request_kind,
            request.platform_code,
            request.provider_code,
            request.provider_operation,
            request.use_case,
            request.source_service,
            request.model,
            request.uses_grounding,
            request.status,
            request.started_at,
            request.completed_at,
            request.duration_ms,
            request.http_status,
            request.error_code,
            request.error_type,
            request.tenant_id,
            request.project_id,
            request.job_id,
            request.query_id,
            request.run_request_id,
            request.provider_region,
            request.traffic_type,
            request.usage_capture_status,
            request.input_token_count,
            request.output_token_count,
            request.total_token_count,
            request.cached_input_token_count,
            request.reasoning_token_count,
            request.tool_input_token_count,
            request.usage_metadata,
            request.meter_usage,
                CASE
                    WHEN (lower((COALESCE(request.provider_region, ''::character varying))::text) = 'global'::text) THEN 'global'::text
                    WHEN (request.provider_region IS NOT NULL) THEN 'non_global'::text
                    ELSE NULL::text
                END AS provider_region_class,
            (GREATEST((COALESCE(request.input_token_count, (0)::bigint) - COALESCE(request.cached_input_token_count, (0)::bigint)), (0)::bigint) +
                CASE
                    WHEN request.uses_grounding THEN (0)::bigint
                    ELSE COALESCE(request.tool_input_token_count, (0)::bigint)
                END) AS billable_input_token_count,
            COALESCE(request.cached_input_token_count, (0)::bigint) AS billable_cached_input_token_count,
            (COALESCE(request.output_token_count, (0)::bigint) + COALESCE(request.reasoning_token_count, (0)::bigint)) AS billable_output_token_count,
                CASE
                    WHEN (jsonb_typeof((request.meter_usage -> 'google_web_search_query'::text)) = 'number'::text) THEN ((request.meter_usage ->> 'google_web_search_query'::text))::bigint
                    ELSE (0)::bigint
                END AS google_web_search_query_count
           FROM public.provider_request request
        ), matched_rates AS (
         SELECT usage.id,
            usage.operation_id,
            usage.request_number,
            usage.request_kind,
            usage.platform_code,
            usage.provider_code,
            usage.provider_operation,
            usage.use_case,
            usage.source_service,
            usage.model,
            usage.uses_grounding,
            usage.status,
            usage.started_at,
            usage.completed_at,
            usage.duration_ms,
            usage.http_status,
            usage.error_code,
            usage.error_type,
            usage.tenant_id,
            usage.project_id,
            usage.job_id,
            usage.query_id,
            usage.run_request_id,
            usage.provider_region,
            usage.traffic_type,
            usage.usage_capture_status,
            usage.input_token_count,
            usage.output_token_count,
            usage.total_token_count,
            usage.cached_input_token_count,
            usage.reasoning_token_count,
            usage.tool_input_token_count,
            usage.usage_metadata,
            usage.meter_usage,
            usage.provider_region_class,
            usage.billable_input_token_count,
            usage.billable_cached_input_token_count,
            usage.billable_output_token_count,
            usage.google_web_search_query_count,
            input_rate.id AS input_rate_id,
            input_rate.unit_quantity AS input_unit_quantity,
            input_rate.unit_price_usd AS input_unit_price_usd,
            cached_rate.id AS cached_input_rate_id,
            cached_rate.unit_quantity AS cached_input_unit_quantity,
            cached_rate.unit_price_usd AS cached_input_unit_price_usd,
            output_rate.id AS output_rate_id,
            output_rate.unit_quantity AS output_unit_quantity,
            output_rate.unit_price_usd AS output_unit_price_usd,
            search_rate.id AS search_rate_id,
            search_rate.unit_quantity AS search_unit_quantity,
            search_rate.unit_price_usd AS search_unit_price_usd
           FROM ((((usage_quantities usage
             LEFT JOIN LATERAL ( SELECT rate.id,
                    rate.platform_code,
                    rate.provider_code,
                    rate.model,
                    rate.provider_region_class,
                    rate.traffic_type,
                    rate.meter_code,
                    rate.unit_quantity,
                    rate.unit_price_usd,
                    rate.effective_from,
                    rate.effective_to,
                    rate.source_url,
                    rate.source_checked_at,
                    rate.created_at
                   FROM public.provider_pricing_rate rate
                  WHERE (((rate.platform_code)::text = (usage.platform_code)::text) AND ((rate.provider_code)::text = (usage.provider_code)::text) AND ((rate.model)::text = (usage.model)::text) AND (((rate.provider_region_class)::text = usage.provider_region_class) OR ((rate.provider_region_class)::text = 'any'::text)) AND (((rate.traffic_type)::text = (usage.traffic_type)::text) OR ((rate.traffic_type)::text = 'any'::text)) AND ((rate.meter_code)::text = 'input_token'::text) AND (rate.effective_from <= usage.started_at) AND ((rate.effective_to IS NULL) OR (rate.effective_to > usage.started_at)))
                  ORDER BY ((rate.provider_region_class)::text = usage.provider_region_class) DESC, ((rate.traffic_type)::text = (usage.traffic_type)::text) DESC, rate.effective_from DESC
                 LIMIT 1) input_rate ON (true))
             LEFT JOIN LATERAL ( SELECT rate.id,
                    rate.platform_code,
                    rate.provider_code,
                    rate.model,
                    rate.provider_region_class,
                    rate.traffic_type,
                    rate.meter_code,
                    rate.unit_quantity,
                    rate.unit_price_usd,
                    rate.effective_from,
                    rate.effective_to,
                    rate.source_url,
                    rate.source_checked_at,
                    rate.created_at
                   FROM public.provider_pricing_rate rate
                  WHERE (((rate.platform_code)::text = (usage.platform_code)::text) AND ((rate.provider_code)::text = (usage.provider_code)::text) AND ((rate.model)::text = (usage.model)::text) AND (((rate.provider_region_class)::text = usage.provider_region_class) OR ((rate.provider_region_class)::text = 'any'::text)) AND (((rate.traffic_type)::text = (usage.traffic_type)::text) OR ((rate.traffic_type)::text = 'any'::text)) AND ((rate.meter_code)::text = 'cached_input_token'::text) AND (rate.effective_from <= usage.started_at) AND ((rate.effective_to IS NULL) OR (rate.effective_to > usage.started_at)))
                  ORDER BY ((rate.provider_region_class)::text = usage.provider_region_class) DESC, ((rate.traffic_type)::text = (usage.traffic_type)::text) DESC, rate.effective_from DESC
                 LIMIT 1) cached_rate ON (true))
             LEFT JOIN LATERAL ( SELECT rate.id,
                    rate.platform_code,
                    rate.provider_code,
                    rate.model,
                    rate.provider_region_class,
                    rate.traffic_type,
                    rate.meter_code,
                    rate.unit_quantity,
                    rate.unit_price_usd,
                    rate.effective_from,
                    rate.effective_to,
                    rate.source_url,
                    rate.source_checked_at,
                    rate.created_at
                   FROM public.provider_pricing_rate rate
                  WHERE (((rate.platform_code)::text = (usage.platform_code)::text) AND ((rate.provider_code)::text = (usage.provider_code)::text) AND ((rate.model)::text = (usage.model)::text) AND (((rate.provider_region_class)::text = usage.provider_region_class) OR ((rate.provider_region_class)::text = 'any'::text)) AND (((rate.traffic_type)::text = (usage.traffic_type)::text) OR ((rate.traffic_type)::text = 'any'::text)) AND ((rate.meter_code)::text = 'output_token'::text) AND (rate.effective_from <= usage.started_at) AND ((rate.effective_to IS NULL) OR (rate.effective_to > usage.started_at)))
                  ORDER BY ((rate.provider_region_class)::text = usage.provider_region_class) DESC, ((rate.traffic_type)::text = (usage.traffic_type)::text) DESC, rate.effective_from DESC
                 LIMIT 1) output_rate ON (true))
             LEFT JOIN LATERAL ( SELECT rate.id,
                    rate.platform_code,
                    rate.provider_code,
                    rate.model,
                    rate.provider_region_class,
                    rate.traffic_type,
                    rate.meter_code,
                    rate.unit_quantity,
                    rate.unit_price_usd,
                    rate.effective_from,
                    rate.effective_to,
                    rate.source_url,
                    rate.source_checked_at,
                    rate.created_at
                   FROM public.provider_pricing_rate rate
                  WHERE (((rate.platform_code)::text = (usage.platform_code)::text) AND ((rate.provider_code)::text = (usage.provider_code)::text) AND ((rate.model)::text = (usage.model)::text) AND (((rate.provider_region_class)::text = usage.provider_region_class) OR ((rate.provider_region_class)::text = 'any'::text)) AND (((rate.traffic_type)::text = (usage.traffic_type)::text) OR ((rate.traffic_type)::text = 'any'::text)) AND ((rate.meter_code)::text = 'google_web_search_query'::text) AND (rate.effective_from <= usage.started_at) AND ((rate.effective_to IS NULL) OR (rate.effective_to > usage.started_at)))
                  ORDER BY ((rate.provider_region_class)::text = usage.provider_region_class) DESC, ((rate.traffic_type)::text = (usage.traffic_type)::text) DESC, rate.effective_from DESC
                 LIMIT 1) search_rate ON (true))
        ), cost_components AS (
         SELECT rates.id,
            rates.operation_id,
            rates.request_number,
            rates.request_kind,
            rates.platform_code,
            rates.provider_code,
            rates.provider_operation,
            rates.use_case,
            rates.source_service,
            rates.model,
            rates.uses_grounding,
            rates.status,
            rates.started_at,
            rates.completed_at,
            rates.duration_ms,
            rates.http_status,
            rates.error_code,
            rates.error_type,
            rates.tenant_id,
            rates.project_id,
            rates.job_id,
            rates.query_id,
            rates.run_request_id,
            rates.provider_region,
            rates.traffic_type,
            rates.usage_capture_status,
            rates.input_token_count,
            rates.output_token_count,
            rates.total_token_count,
            rates.cached_input_token_count,
            rates.reasoning_token_count,
            rates.tool_input_token_count,
            rates.usage_metadata,
            rates.meter_usage,
            rates.provider_region_class,
            rates.billable_input_token_count,
            rates.billable_cached_input_token_count,
            rates.billable_output_token_count,
            rates.google_web_search_query_count,
            rates.input_rate_id,
            rates.input_unit_quantity,
            rates.input_unit_price_usd,
            rates.cached_input_rate_id,
            rates.cached_input_unit_quantity,
            rates.cached_input_unit_price_usd,
            rates.output_rate_id,
            rates.output_unit_quantity,
            rates.output_unit_price_usd,
            rates.search_rate_id,
            rates.search_unit_quantity,
            rates.search_unit_price_usd,
            (((rates.billable_input_token_count)::numeric / NULLIF(rates.input_unit_quantity, (0)::numeric)) * rates.input_unit_price_usd) AS estimated_input_cost_usd,
            (((rates.billable_cached_input_token_count)::numeric / NULLIF(rates.cached_input_unit_quantity, (0)::numeric)) * rates.cached_input_unit_price_usd) AS estimated_cached_input_cost_usd,
            (((rates.billable_output_token_count)::numeric / NULLIF(rates.output_unit_quantity, (0)::numeric)) * rates.output_unit_price_usd) AS estimated_output_cost_usd,
            (((rates.google_web_search_query_count)::numeric / NULLIF(rates.search_unit_quantity, (0)::numeric)) * rates.search_unit_price_usd) AS estimated_search_cost_usd
           FROM matched_rates rates
        ), classified AS (
         SELECT costs.id,
            costs.operation_id,
            costs.request_number,
            costs.request_kind,
            costs.platform_code,
            costs.provider_code,
            costs.provider_operation,
            costs.use_case,
            costs.source_service,
            costs.model,
            costs.uses_grounding,
            costs.status,
            costs.started_at,
            costs.completed_at,
            costs.duration_ms,
            costs.http_status,
            costs.error_code,
            costs.error_type,
            costs.tenant_id,
            costs.project_id,
            costs.job_id,
            costs.query_id,
            costs.run_request_id,
            costs.provider_region,
            costs.traffic_type,
            costs.usage_capture_status,
            costs.input_token_count,
            costs.output_token_count,
            costs.total_token_count,
            costs.cached_input_token_count,
            costs.reasoning_token_count,
            costs.tool_input_token_count,
            costs.usage_metadata,
            costs.meter_usage,
            costs.provider_region_class,
            costs.billable_input_token_count,
            costs.billable_cached_input_token_count,
            costs.billable_output_token_count,
            costs.google_web_search_query_count,
            costs.input_rate_id,
            costs.input_unit_quantity,
            costs.input_unit_price_usd,
            costs.cached_input_rate_id,
            costs.cached_input_unit_quantity,
            costs.cached_input_unit_price_usd,
            costs.output_rate_id,
            costs.output_unit_quantity,
            costs.output_unit_price_usd,
            costs.search_rate_id,
            costs.search_unit_quantity,
            costs.search_unit_price_usd,
            costs.estimated_input_cost_usd,
            costs.estimated_cached_input_cost_usd,
            costs.estimated_output_cost_usd,
            costs.estimated_search_cost_usd,
                CASE
                    WHEN ((costs.provider_code)::text <> 'google_vertex_ai'::text) THEN 'not_supported'::text
                    WHEN (((costs.status)::text = 'failed'::text) AND ((costs.http_status >= 400) AND (costs.http_status <= 599))) THEN 'not_billable'::text
                    WHEN ((costs.status)::text <> 'succeeded'::text) THEN 'billing_uncertain'::text
                    WHEN (((costs.usage_capture_status)::text <> 'recorded'::text) OR (costs.input_token_count IS NULL) OR (costs.output_token_count IS NULL)) THEN 'usage_unavailable'::text
                    WHEN ((costs.input_rate_id IS NULL) OR (costs.output_rate_id IS NULL) OR ((costs.billable_cached_input_token_count > 0) AND (costs.cached_input_rate_id IS NULL)) OR ((costs.google_web_search_query_count > 0) AND (costs.search_rate_id IS NULL))) THEN 'rate_missing'::text
                    ELSE 'estimated'::text
                END AS estimation_status
           FROM cost_components costs
        )
 SELECT id,
    operation_id,
    request_number,
    request_kind,
    platform_code,
    provider_code,
    provider_operation,
    use_case,
    source_service,
    model,
    uses_grounding,
    status,
    started_at,
    completed_at,
    duration_ms,
    http_status,
    error_code,
    error_type,
    tenant_id,
    project_id,
    job_id,
    query_id,
    run_request_id,
    provider_region,
    traffic_type,
    usage_capture_status,
    input_token_count,
    output_token_count,
    total_token_count,
    cached_input_token_count,
    reasoning_token_count,
    tool_input_token_count,
    usage_metadata,
    meter_usage,
    provider_region_class,
    billable_input_token_count,
    billable_cached_input_token_count,
    billable_output_token_count,
    google_web_search_query_count,
    input_rate_id,
    input_unit_quantity,
    input_unit_price_usd,
    cached_input_rate_id,
    cached_input_unit_quantity,
    cached_input_unit_price_usd,
    output_rate_id,
    output_unit_quantity,
    output_unit_price_usd,
    search_rate_id,
    search_unit_quantity,
    search_unit_price_usd,
    estimated_input_cost_usd,
    estimated_cached_input_cost_usd,
    estimated_output_cost_usd,
    estimated_search_cost_usd,
    estimation_status,
        CASE
            WHEN (estimation_status = 'not_billable'::text) THEN (0)::numeric
            WHEN (estimation_status = 'estimated'::text) THEN (((COALESCE(estimated_input_cost_usd, (0)::numeric) + COALESCE(estimated_cached_input_cost_usd, (0)::numeric)) + COALESCE(estimated_output_cost_usd, (0)::numeric)) + COALESCE(estimated_search_cost_usd, (0)::numeric))
            ELSE NULL::numeric
        END AS estimated_list_cost_usd
   FROM classified;


--
-- Name: provider_request_daily_cost_estimate; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.provider_request_daily_cost_estimate AS
 SELECT ((started_at AT TIME ZONE 'Asia/Taipei'::text))::date AS usage_date,
    platform_code,
    provider_code,
    model,
    provider_region,
    traffic_type,
    use_case,
    request_kind,
    count(*) AS request_count,
    count(*) FILTER (WHERE (estimation_status = 'estimated'::text)) AS estimated_request_count,
    count(*) FILTER (WHERE (estimation_status <> ALL (ARRAY['estimated'::text, 'not_billable'::text]))) AS unestimated_request_count,
    count(*) FILTER (WHERE (estimation_status = 'billing_uncertain'::text)) AS billing_uncertain_request_count,
    sum(COALESCE(input_token_count, (0)::bigint)) AS input_token_count,
    sum(COALESCE(output_token_count, (0)::bigint)) AS output_token_count,
    sum(COALESCE(total_token_count, (0)::bigint)) AS total_token_count,
    sum(COALESCE(reasoning_token_count, (0)::bigint)) AS reasoning_token_count,
    sum(COALESCE(cached_input_token_count, (0)::bigint)) AS cached_input_token_count,
    sum(COALESCE(tool_input_token_count, (0)::bigint)) AS tool_input_token_count,
    sum(billable_input_token_count) AS billable_input_token_count,
    sum(billable_cached_input_token_count) AS billable_cached_input_token_count,
    sum(billable_output_token_count) AS billable_output_token_count,
    sum(google_web_search_query_count) AS google_web_search_query_count,
    sum(estimated_input_cost_usd) FILTER (WHERE (estimation_status = 'estimated'::text)) AS estimated_input_cost_usd,
    sum(estimated_cached_input_cost_usd) FILTER (WHERE (estimation_status = 'estimated'::text)) AS estimated_cached_input_cost_usd,
    sum(estimated_output_cost_usd) FILTER (WHERE (estimation_status = 'estimated'::text)) AS estimated_output_cost_usd,
    sum(estimated_search_cost_usd) FILTER (WHERE (estimation_status = 'estimated'::text)) AS estimated_search_cost_usd,
    sum(estimated_list_cost_usd) AS estimated_list_cost_usd
   FROM public.provider_request_cost_estimate
  GROUP BY (((started_at AT TIME ZONE 'Asia/Taipei'::text))::date), platform_code, provider_code, model, provider_region, traffic_type, use_case, request_kind;


--
-- Name: tenant_kmindhub_extraction_task_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_kmindhub_extraction_task_mapping (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    task_key character varying(100) NOT NULL,
    schema_version integer NOT NULL,
    kmindhub_task_id uuid CONSTRAINT tenant_kmindhub_extraction_task_mappi_kmindhub_task_id_not_null NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: tenant_kmindhub_workspace_mapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_kmindhub_workspace_mapping (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    workspace_id uuid NOT NULL,
    display_name character varying(200) NOT NULL,
    provisioning_mode character varying(32) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: geo_ai_platform geo_ai_platform_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_ai_platform
    ADD CONSTRAINT geo_ai_platform_code_key UNIQUE (code);


--
-- Name: geo_ai_platform geo_ai_platform_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_ai_platform
    ADD CONSTRAINT geo_ai_platform_pkey PRIMARY KEY (id);


--
-- Name: geo_daily_run_batch geo_daily_run_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_daily_run_batch
    ADD CONSTRAINT geo_daily_run_batch_pkey PRIMARY KEY (id);


--
-- Name: geo_entity_alias geo_entity_alias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_entity_alias
    ADD CONSTRAINT geo_entity_alias_pkey PRIMARY KEY (id);


--
-- Name: geo_entity geo_entity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_entity
    ADD CONSTRAINT geo_entity_pkey PRIMARY KEY (id);


--
-- Name: geo_external_run_reference geo_external_run_reference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_external_run_reference
    ADD CONSTRAINT geo_external_run_reference_pkey PRIMARY KEY (id);


--
-- Name: geo_job_dispatch_event geo_job_dispatch_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_job_dispatch_event
    ADD CONSTRAINT geo_job_dispatch_event_pkey PRIMARY KEY (id);


--
-- Name: geo_market geo_market_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_market
    ADD CONSTRAINT geo_market_pkey PRIMARY KEY (id);


--
-- Name: geo_message_dispatch_log geo_message_dispatch_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_message_dispatch_log
    ADD CONSTRAINT geo_message_dispatch_log_pkey PRIMARY KEY (id);


--
-- Name: geo_project geo_project_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_project
    ADD CONSTRAINT geo_project_pkey PRIMARY KEY (id);


--
-- Name: geo_project_query_settings geo_project_query_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_project_query_settings
    ADD CONSTRAINT geo_project_query_settings_pkey PRIMARY KEY (project_id);


--
-- Name: geo_query_draft geo_query_draft_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft
    ADD CONSTRAINT geo_query_draft_pkey PRIMARY KEY (id);


--
-- Name: geo_query_draft_selection geo_query_draft_selection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft_selection
    ADD CONSTRAINT geo_query_draft_selection_pkey PRIMARY KEY (id);


--
-- Name: geo_query_generation_run geo_query_generation_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_generation_run
    ADD CONSTRAINT geo_query_generation_run_pkey PRIMARY KEY (id);


--
-- Name: geo_query_keyword geo_query_keyword_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_keyword
    ADD CONSTRAINT geo_query_keyword_pkey PRIMARY KEY (id);


--
-- Name: geo_query geo_query_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query
    ADD CONSTRAINT geo_query_pkey PRIMARY KEY (id);


--
-- Name: geo_query_platform geo_query_platform_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_platform
    ADD CONSTRAINT geo_query_platform_pkey PRIMARY KEY (id);


--
-- Name: geo_query_research_run geo_query_research_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_research_run
    ADD CONSTRAINT geo_query_research_run_pkey PRIMARY KEY (id);


--
-- Name: geo_query_run_job geo_query_run_job_dedupe_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_dedupe_key_key UNIQUE (dedupe_key);


--
-- Name: geo_query_run_job geo_query_run_job_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_pkey PRIMARY KEY (id);


--
-- Name: geo_query_schedule geo_query_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_schedule
    ADD CONSTRAINT geo_query_schedule_pkey PRIMARY KEY (id);


--
-- Name: geo_response_semantic_fact geo_response_semantic_fact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_response_semantic_fact
    ADD CONSTRAINT geo_response_semantic_fact_pkey PRIMARY KEY (id);


--
-- Name: geo_run_request geo_run_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_request
    ADD CONSTRAINT geo_run_request_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_analysis geo_run_result_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_analysis
    ADD CONSTRAINT geo_run_result_analysis_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_citation_classification geo_run_result_citation_classification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_classification
    ADD CONSTRAINT geo_run_result_citation_classification_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_citation_normalization geo_run_result_citation_normalization_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_normalization
    ADD CONSTRAINT geo_run_result_citation_normalization_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_citation geo_run_result_citation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation
    ADD CONSTRAINT geo_run_result_citation_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_entity_detection_item geo_run_result_entity_detection_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection_item
    ADD CONSTRAINT geo_run_result_entity_detection_item_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_entity_detection geo_run_result_entity_detection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection
    ADD CONSTRAINT geo_run_result_entity_detection_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_entity_mention geo_run_result_entity_mention_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_mention
    ADD CONSTRAINT geo_run_result_entity_mention_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result geo_run_result_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result
    ADD CONSTRAINT geo_run_result_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_reference geo_run_result_reference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_reference
    ADD CONSTRAINT geo_run_result_reference_pkey PRIMARY KEY (id);


--
-- Name: geo_run_result_statement geo_run_result_statement_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_statement
    ADD CONSTRAINT geo_run_result_statement_pkey PRIMARY KEY (id);


--
-- Name: geo_topic geo_topic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_topic
    ADD CONSTRAINT geo_topic_pkey PRIMARY KEY (id);


--
-- Name: geo_worker_lease geo_worker_lease_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_worker_lease
    ADD CONSTRAINT geo_worker_lease_pkey PRIMARY KEY (id);


--
-- Name: provider_pricing_rate provider_pricing_rate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_pricing_rate
    ADD CONSTRAINT provider_pricing_rate_pkey PRIMARY KEY (id);


--
-- Name: provider_request provider_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_request
    ADD CONSTRAINT provider_request_pkey PRIMARY KEY (id);


--
-- Name: tenant_kmindhub_extraction_task_mapping tenant_kmindhub_extraction_task_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_kmindhub_extraction_task_mapping
    ADD CONSTRAINT tenant_kmindhub_extraction_task_mapping_pkey PRIMARY KEY (id);


--
-- Name: tenant_kmindhub_workspace_mapping tenant_kmindhub_workspace_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_kmindhub_workspace_mapping
    ADD CONSTRAINT tenant_kmindhub_workspace_mapping_pkey PRIMARY KEY (id);


--
-- Name: geo_daily_run_batch ux_geo_daily_run_batch_project_date; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_daily_run_batch
    ADD CONSTRAINT ux_geo_daily_run_batch_project_date UNIQUE (project_id, business_date);


--
-- Name: geo_entity_alias ux_geo_entity_alias; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_entity_alias
    ADD CONSTRAINT ux_geo_entity_alias UNIQUE (entity_id, alias);


--
-- Name: geo_entity ux_geo_entity_scope_type_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_entity
    ADD CONSTRAINT ux_geo_entity_scope_type_name UNIQUE (project_id, entity_type, name);


--
-- Name: geo_market ux_geo_market_scope; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_market
    ADD CONSTRAINT ux_geo_market_scope UNIQUE (project_id, region, language);


--
-- Name: geo_query_platform ux_geo_query_platform; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_platform
    ADD CONSTRAINT ux_geo_query_platform UNIQUE (query_id, platform_id);


--
-- Name: geo_query_schedule ux_geo_query_schedule; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_schedule
    ADD CONSTRAINT ux_geo_query_schedule UNIQUE (query_id, platform_id);


--
-- Name: geo_run_result_analysis ux_geo_run_result_analysis_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_analysis
    ADD CONSTRAINT ux_geo_run_result_analysis_version UNIQUE (run_result_id, task_key, schema_version);


--
-- Name: geo_run_result_citation_normalization ux_geo_run_result_citation_normalization_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_normalization
    ADD CONSTRAINT ux_geo_run_result_citation_normalization_version UNIQUE (run_result_id, normalizer_version);


--
-- Name: geo_run_result_entity_detection_item ux_geo_run_result_entity_detection_item_entity; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection_item
    ADD CONSTRAINT ux_geo_run_result_entity_detection_item_entity UNIQUE (detection_id, entity_id);


--
-- Name: geo_run_result_entity_detection ux_geo_run_result_entity_detection_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection
    ADD CONSTRAINT ux_geo_run_result_entity_detection_version UNIQUE (run_result_id, detector_version);


--
-- Name: geo_topic ux_geo_topic_scope_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_topic
    ADD CONSTRAINT ux_geo_topic_scope_name UNIQUE (project_id, name);


--
-- Name: provider_pricing_rate ux_provider_pricing_rate_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_pricing_rate
    ADD CONSTRAINT ux_provider_pricing_rate_version UNIQUE (platform_code, provider_code, model, provider_region_class, traffic_type, meter_code, effective_from);


--
-- Name: provider_request ux_provider_request_operation_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.provider_request
    ADD CONSTRAINT ux_provider_request_operation_number UNIQUE (operation_id, request_number);


--
-- Name: tenant_kmindhub_extraction_task_mapping ux_tenant_kmindhub_extraction_task_mapping_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_kmindhub_extraction_task_mapping
    ADD CONSTRAINT ux_tenant_kmindhub_extraction_task_mapping_version UNIQUE (tenant_id, task_key, schema_version);


--
-- Name: tenant_kmindhub_workspace_mapping ux_tenant_kmindhub_workspace_mapping_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_kmindhub_workspace_mapping
    ADD CONSTRAINT ux_tenant_kmindhub_workspace_mapping_tenant UNIQUE (tenant_id);


--
-- Name: ix_geo_daily_run_batch_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_daily_run_batch_date ON public.geo_daily_run_batch USING btree (business_date, status);


--
-- Name: ix_geo_project_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_project_customer_id ON public.geo_project USING btree (customer_id);


--
-- Name: ix_geo_project_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_project_status ON public.geo_project USING btree (status);


--
-- Name: ix_geo_project_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_project_tenant_id ON public.geo_project USING btree (tenant_id);


--
-- Name: ix_geo_query_project_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_project_status ON public.geo_query USING btree (project_id, status);


--
-- Name: ix_geo_query_region_language; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_region_language ON public.geo_query USING btree (region, language);


--
-- Name: ix_geo_query_run_job_pickup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_run_job_pickup ON public.geo_query_run_job USING btree (status, scheduled_for, priority);


--
-- Name: ix_geo_query_run_job_project_preparing; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_run_job_project_preparing ON public.geo_query_run_job USING btree (project_id, business_date, status) WHERE (is_daily_slot_owner = true);


--
-- Name: ix_geo_query_run_job_query_platform; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_run_job_query_platform ON public.geo_query_run_job USING btree (query_id, platform_id);


--
-- Name: ix_geo_query_run_job_scheduler_pickup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_run_job_scheduler_pickup ON public.geo_query_run_job USING btree (source, status, scheduled_for, next_retry_at);


--
-- Name: ix_geo_query_schedule_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_schedule_due ON public.geo_query_schedule USING btree (status, next_run_at, priority);


--
-- Name: ix_geo_query_topic_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_query_topic_id ON public.geo_query USING btree (topic_id);


--
-- Name: ix_geo_response_semantic_fact_analysis; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_response_semantic_fact_analysis ON public.geo_response_semantic_fact USING btree (analysis_id);


--
-- Name: ix_geo_response_semantic_fact_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_response_semantic_fact_result ON public.geo_response_semantic_fact USING btree (run_result_id, fact_type);


--
-- Name: ix_geo_run_request_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_request_job_id ON public.geo_run_request USING btree (job_id);


--
-- Name: ix_geo_run_result_analysis_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_analysis_result ON public.geo_run_result_analysis USING btree (run_result_id, status);


--
-- Name: ix_geo_run_result_citation_classification_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_classification_reference ON public.geo_run_result_citation_classification USING btree (run_result_reference_id, classification);


--
-- Name: ix_geo_run_result_citation_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_domain ON public.geo_run_result_citation USING btree (domain);


--
-- Name: ix_geo_run_result_citation_normalization_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_normalization_result ON public.geo_run_result_citation_normalization USING btree (run_result_id, normalizer_version);


--
-- Name: ix_geo_run_result_citation_ownership; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_ownership ON public.geo_run_result_citation USING btree (ownership);


--
-- Name: ix_geo_run_result_citation_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_reference ON public.geo_run_result_citation USING btree (reference_id);


--
-- Name: ix_geo_run_result_citation_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_result ON public.geo_run_result_citation USING btree (run_result_id);


--
-- Name: ix_geo_run_result_citation_source_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_citation_source_type ON public.geo_run_result_citation USING btree (source_type);


--
-- Name: ix_geo_run_result_entity_detection_completed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_entity_detection_completed ON public.geo_run_result_entity_detection USING btree (run_result_id, updated_at DESC) WHERE ((status)::text = 'completed'::text);


--
-- Name: ix_geo_run_result_entity_detection_item_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_entity_detection_item_result ON public.geo_run_result_entity_detection_item USING btree (run_result_id, entity_role, mentioned);


--
-- Name: ix_geo_run_result_entity_mention_analysis; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_entity_mention_analysis ON public.geo_run_result_entity_mention USING btree (analysis_id);


--
-- Name: ix_geo_run_result_entity_mention_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_entity_mention_result ON public.geo_run_result_entity_mention USING btree (run_result_id, entity_type, entity_name);


--
-- Name: ix_geo_run_result_entity_mention_semantic; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_entity_mention_semantic ON public.geo_run_result_entity_mention USING btree (run_result_id, entity_role, mentioned);


--
-- Name: ix_geo_run_result_job_run_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_job_run_at ON public.geo_run_result USING btree (job_id, run_at DESC);


--
-- Name: ix_geo_run_result_query_run_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_query_run_at ON public.geo_run_result USING btree (query_id, run_at DESC);


--
-- Name: ix_geo_run_result_reference_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_reference_result ON public.geo_run_result_reference USING btree (run_result_id, "position");


--
-- Name: ix_geo_run_result_statement_analysis; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_statement_analysis ON public.geo_run_result_statement USING btree (analysis_id);


--
-- Name: ix_geo_run_result_statement_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_statement_result ON public.geo_run_result_statement USING btree (run_result_id);


--
-- Name: ix_geo_run_result_statement_semantic; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_geo_run_result_statement_semantic ON public.geo_run_result_statement USING btree (run_result_id, entity_id, sentiment);


--
-- Name: ix_provider_pricing_rate_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_pricing_rate_lookup ON public.provider_pricing_rate USING btree (platform_code, provider_code, model, meter_code, effective_from);


--
-- Name: ix_provider_request_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_job ON public.provider_request USING btree (job_id) WHERE (job_id IS NOT NULL);


--
-- Name: ix_provider_request_platform_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_platform_started ON public.provider_request USING btree (platform_code, started_at);


--
-- Name: ix_provider_request_provider_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_provider_started ON public.provider_request USING btree (provider_code, started_at);


--
-- Name: ix_provider_request_query; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_query ON public.provider_request USING btree (query_id) WHERE (query_id IS NOT NULL);


--
-- Name: ix_provider_request_run_request; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_run_request ON public.provider_request USING btree (run_request_id) WHERE (run_request_id IS NOT NULL);


--
-- Name: ix_provider_request_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_started_at ON public.provider_request USING btree (started_at);


--
-- Name: ix_provider_request_started_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_started_status ON public.provider_request USING btree (started_at) WHERE ((status)::text = 'started'::text);


--
-- Name: ix_provider_request_tenant_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_tenant_started ON public.provider_request USING btree (tenant_id, started_at);


--
-- Name: ix_provider_request_usage_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_usage_status ON public.provider_request USING btree (usage_capture_status, started_at);


--
-- Name: ix_provider_request_use_case_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_provider_request_use_case_started ON public.provider_request USING btree (use_case, started_at);


--
-- Name: ix_tenant_kmindhub_extraction_task_mapping_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_kmindhub_extraction_task_mapping_status ON public.tenant_kmindhub_extraction_task_mapping USING btree (status);


--
-- Name: ix_tenant_kmindhub_extraction_task_mapping_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_kmindhub_extraction_task_mapping_tenant ON public.tenant_kmindhub_extraction_task_mapping USING btree (tenant_id);


--
-- Name: ix_tenant_kmindhub_workspace_mapping_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_kmindhub_workspace_mapping_status ON public.tenant_kmindhub_workspace_mapping USING btree (status);


--
-- Name: ix_tenant_kmindhub_workspace_mapping_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_kmindhub_workspace_mapping_tenant_id ON public.tenant_kmindhub_workspace_mapping USING btree (tenant_id);


--
-- Name: ux_geo_query_run_job_daily_slot; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_geo_query_run_job_daily_slot ON public.geo_query_run_job USING btree (query_id, platform_id, business_date) WHERE (is_daily_slot_owner = true);


--
-- Name: ux_geo_query_run_job_scheduled_identity; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_geo_query_run_job_scheduled_identity ON public.geo_query_run_job USING btree (query_id, platform_id, scheduled_for) WHERE ((source)::text = 'scheduled'::text);


--
-- Name: geo_daily_run_batch geo_daily_run_batch_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_daily_run_batch
    ADD CONSTRAINT geo_daily_run_batch_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_entity_alias geo_entity_alias_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_entity_alias
    ADD CONSTRAINT geo_entity_alias_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES public.geo_entity(id) ON DELETE CASCADE;


--
-- Name: geo_entity geo_entity_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_entity
    ADD CONSTRAINT geo_entity_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_external_run_reference geo_external_run_reference_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_external_run_reference
    ADD CONSTRAINT geo_external_run_reference_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.geo_query_run_job(id) ON DELETE CASCADE;


--
-- Name: geo_job_dispatch_event geo_job_dispatch_event_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_job_dispatch_event
    ADD CONSTRAINT geo_job_dispatch_event_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.geo_query_run_job(id) ON DELETE CASCADE;


--
-- Name: geo_market geo_market_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_market
    ADD CONSTRAINT geo_market_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_message_dispatch_log geo_message_dispatch_log_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_message_dispatch_log
    ADD CONSTRAINT geo_message_dispatch_log_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.geo_query_run_job(id) ON DELETE CASCADE;


--
-- Name: geo_project_query_settings geo_project_query_settings_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_project_query_settings
    ADD CONSTRAINT geo_project_query_settings_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_query_draft geo_query_draft_accepted_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft
    ADD CONSTRAINT geo_query_draft_accepted_query_id_fkey FOREIGN KEY (accepted_query_id) REFERENCES public.geo_query(id) ON DELETE SET NULL;


--
-- Name: geo_query_draft geo_query_draft_generation_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft
    ADD CONSTRAINT geo_query_draft_generation_run_id_fkey FOREIGN KEY (generation_run_id) REFERENCES public.geo_query_generation_run(id) ON DELETE CASCADE;


--
-- Name: geo_query_draft geo_query_draft_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft
    ADD CONSTRAINT geo_query_draft_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_query_draft_selection geo_query_draft_selection_draft_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft_selection
    ADD CONSTRAINT geo_query_draft_selection_draft_id_fkey FOREIGN KEY (draft_id) REFERENCES public.geo_query_draft(id) ON DELETE CASCADE;


--
-- Name: geo_query_draft_selection geo_query_draft_selection_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft_selection
    ADD CONSTRAINT geo_query_draft_selection_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.geo_query(id) ON DELETE SET NULL;


--
-- Name: geo_query_draft geo_query_draft_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_draft
    ADD CONSTRAINT geo_query_draft_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.geo_topic(id) ON DELETE SET NULL;


--
-- Name: geo_query_generation_run geo_query_generation_run_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_generation_run
    ADD CONSTRAINT geo_query_generation_run_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_query_keyword geo_query_keyword_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_keyword
    ADD CONSTRAINT geo_query_keyword_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.geo_query(id) ON DELETE CASCADE;


--
-- Name: geo_query_platform geo_query_platform_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_platform
    ADD CONSTRAINT geo_query_platform_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.geo_ai_platform(id) ON DELETE RESTRICT;


--
-- Name: geo_query_platform geo_query_platform_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_platform
    ADD CONSTRAINT geo_query_platform_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.geo_query(id) ON DELETE CASCADE;


--
-- Name: geo_query geo_query_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query
    ADD CONSTRAINT geo_query_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_query_research_run geo_query_research_run_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_research_run
    ADD CONSTRAINT geo_query_research_run_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_query_run_job geo_query_run_job_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.geo_daily_run_batch(id) ON DELETE SET NULL;


--
-- Name: geo_query_run_job geo_query_run_job_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.geo_ai_platform(id) ON DELETE RESTRICT;


--
-- Name: geo_query_run_job geo_query_run_job_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_query_run_job geo_query_run_job_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.geo_query(id) ON DELETE CASCADE;


--
-- Name: geo_query_run_job geo_query_run_job_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_run_job
    ADD CONSTRAINT geo_query_run_job_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.geo_query_schedule(id) ON DELETE SET NULL;


--
-- Name: geo_query_schedule geo_query_schedule_platform_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_schedule
    ADD CONSTRAINT geo_query_schedule_platform_id_fkey FOREIGN KEY (platform_id) REFERENCES public.geo_ai_platform(id) ON DELETE RESTRICT;


--
-- Name: geo_query_schedule geo_query_schedule_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query_schedule
    ADD CONSTRAINT geo_query_schedule_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.geo_query(id) ON DELETE CASCADE;


--
-- Name: geo_query geo_query_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_query
    ADD CONSTRAINT geo_query_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.geo_topic(id) ON DELETE SET NULL;


--
-- Name: geo_response_semantic_fact geo_response_semantic_fact_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_response_semantic_fact
    ADD CONSTRAINT geo_response_semantic_fact_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.geo_run_result_analysis(id) ON DELETE CASCADE;


--
-- Name: geo_response_semantic_fact geo_response_semantic_fact_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_response_semantic_fact
    ADD CONSTRAINT geo_response_semantic_fact_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_request geo_run_request_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_request
    ADD CONSTRAINT geo_run_request_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.geo_query_run_job(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_analysis geo_run_result_analysis_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_analysis
    ADD CONSTRAINT geo_run_result_analysis_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation_classification geo_run_result_citation_classifica_run_result_reference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_classification
    ADD CONSTRAINT geo_run_result_citation_classifica_run_result_reference_id_fkey FOREIGN KEY (run_result_reference_id) REFERENCES public.geo_run_result_reference(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation_classification geo_run_result_citation_classification_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_classification
    ADD CONSTRAINT geo_run_result_citation_classification_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.geo_run_result_analysis(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation geo_run_result_citation_normalization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation
    ADD CONSTRAINT geo_run_result_citation_normalization_id_fkey FOREIGN KEY (normalization_id) REFERENCES public.geo_run_result_citation_normalization(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation_normalization geo_run_result_citation_normalization_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_normalization
    ADD CONSTRAINT geo_run_result_citation_normalization_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation_normalization geo_run_result_citation_normalization_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation_normalization
    ADD CONSTRAINT geo_run_result_citation_normalization_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation geo_run_result_citation_reference_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation
    ADD CONSTRAINT geo_run_result_citation_reference_id_fkey FOREIGN KEY (reference_id) REFERENCES public.geo_run_result_reference(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_citation geo_run_result_citation_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_citation
    ADD CONSTRAINT geo_run_result_citation_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_entity_detection_item geo_run_result_entity_detection_item_detection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection_item
    ADD CONSTRAINT geo_run_result_entity_detection_item_detection_id_fkey FOREIGN KEY (detection_id) REFERENCES public.geo_run_result_entity_detection(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_entity_detection_item geo_run_result_entity_detection_item_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection_item
    ADD CONSTRAINT geo_run_result_entity_detection_item_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_entity_detection geo_run_result_entity_detection_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_detection
    ADD CONSTRAINT geo_run_result_entity_detection_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_entity_mention geo_run_result_entity_mention_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_mention
    ADD CONSTRAINT geo_run_result_entity_mention_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.geo_run_result_analysis(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_entity_mention geo_run_result_entity_mention_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_entity_mention
    ADD CONSTRAINT geo_run_result_entity_mention_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result geo_run_result_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result
    ADD CONSTRAINT geo_run_result_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.geo_query_run_job(id) ON DELETE CASCADE;


--
-- Name: geo_run_result geo_run_result_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result
    ADD CONSTRAINT geo_run_result_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.geo_query(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_reference geo_run_result_reference_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_reference
    ADD CONSTRAINT geo_run_result_reference_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_run_result geo_run_result_run_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result
    ADD CONSTRAINT geo_run_result_run_request_id_fkey FOREIGN KEY (run_request_id) REFERENCES public.geo_run_request(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_statement geo_run_result_statement_analysis_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_statement
    ADD CONSTRAINT geo_run_result_statement_analysis_id_fkey FOREIGN KEY (analysis_id) REFERENCES public.geo_run_result_analysis(id) ON DELETE CASCADE;


--
-- Name: geo_run_result_statement geo_run_result_statement_run_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_run_result_statement
    ADD CONSTRAINT geo_run_result_statement_run_result_id_fkey FOREIGN KEY (run_result_id) REFERENCES public.geo_run_result(id) ON DELETE CASCADE;


--
-- Name: geo_topic geo_topic_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_topic
    ADD CONSTRAINT geo_topic_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.geo_project(id) ON DELETE CASCADE;


--
-- Name: geo_worker_lease geo_worker_lease_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.geo_worker_lease
    ADD CONSTRAINT geo_worker_lease_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.geo_query_run_job(id) ON DELETE CASCADE;


COMMIT;

--
-- PostgreSQL database dump complete
--

\unrestrict AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
