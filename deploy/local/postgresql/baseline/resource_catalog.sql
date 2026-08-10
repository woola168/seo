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
-- Name: customer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: seo_task; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seo_task (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: customer customer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT customer_pkey PRIMARY KEY (id);


--
-- Name: seo_task seo_task_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seo_task
    ADD CONSTRAINT seo_task_pkey PRIMARY KEY (id);


--
-- Name: customer ux_customer_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer
    ADD CONSTRAINT ux_customer_tenant_name UNIQUE (tenant_id, name);


--
-- Name: ix_customer_tenant_status_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_tenant_status_name ON public.customer USING btree (tenant_id, status, name);


--
-- Name: ix_seo_task_tenant_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seo_task_tenant_customer_id ON public.seo_task USING btree (tenant_id, customer_id);


--
-- Name: ix_seo_task_customer_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seo_task_customer_id ON public.seo_task USING btree (customer_id);


--
-- Name: ix_seo_task_tenant_status_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_seo_task_tenant_status_name ON public.seo_task USING btree (tenant_id, status, name);


--
-- Name: seo_task seo_task_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seo_task
    ADD CONSTRAINT seo_task_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customer(id) ON DELETE RESTRICT;


COMMIT;

--
-- PostgreSQL database dump complete
--

\unrestrict AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
