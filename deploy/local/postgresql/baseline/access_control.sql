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
-- Name: customer_access_grant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_access_grant (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    customer_id uuid NOT NULL
);


--
-- Name: department; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.department (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    archived_at timestamp with time zone
);


--
-- Name: invitation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invitation (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    email character varying(320) NOT NULL,
    token_digest character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone NOT NULL,
    created_by uuid NOT NULL
);


--
-- Name: notification_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_outbox (
    id uuid NOT NULL,
    recipient character varying(320) NOT NULL,
    template character varying(100) NOT NULL,
    payload_ciphertext text NOT NULL,
    status character varying(32) NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone NOT NULL,
    sent_at timestamp with time zone,
    last_error text
);


--
-- Name: password_reset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_digest character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    revoked_at timestamp with time zone
);


--
-- Name: refresh_session; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_session (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_digest character varying(64) NOT NULL,
    family_id uuid NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    replaced_by_id uuid
);


--
-- Name: role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    permissions jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    has_global_resource_access boolean DEFAULT false NOT NULL
);


--
-- Name: security_audit_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.security_audit_event (
    id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    actor_user_id uuid,
    subject_user_id uuid,
    occurred_at timestamp with time zone NOT NULL,
    outcome character varying(32) NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: task_access_grant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_access_grant (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid NOT NULL,
    task_id uuid NOT NULL
);


--
-- Name: tenant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant (
    id uuid NOT NULL,
    code character varying(80) NOT NULL,
    name character varying(200) NOT NULL,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    disabled_at timestamp with time zone
);


--
-- Name: user_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_account (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    email character varying(320) NOT NULL,
    display_name character varying(200) NOT NULL,
    status character varying(32) NOT NULL,
    password_hash text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    department_id uuid,
    auth_provider character varying(32) DEFAULT 'password'::character varying NOT NULL,
    last_login_at timestamp with time zone,
    invited_at timestamp with time zone,
    deleted_at timestamp with time zone
);


--
-- Name: user_role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_role (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    role_id uuid NOT NULL
);


--
-- Name: customer_access_grant customer_access_grant_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grant
    ADD CONSTRAINT customer_access_grant_pkey PRIMARY KEY (id);


--
-- Name: department department_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_pkey PRIMARY KEY (id);


--
-- Name: invitation invitation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitation
    ADD CONSTRAINT invitation_pkey PRIMARY KEY (id);


--
-- Name: invitation invitation_token_digest_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitation
    ADD CONSTRAINT invitation_token_digest_key UNIQUE (token_digest);


--
-- Name: notification_outbox notification_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_outbox
    ADD CONSTRAINT notification_outbox_pkey PRIMARY KEY (id);


--
-- Name: password_reset password_reset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset
    ADD CONSTRAINT password_reset_pkey PRIMARY KEY (id);


--
-- Name: password_reset password_reset_token_digest_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset
    ADD CONSTRAINT password_reset_token_digest_key UNIQUE (token_digest);


--
-- Name: refresh_session refresh_session_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_session
    ADD CONSTRAINT refresh_session_pkey PRIMARY KEY (id);


--
-- Name: refresh_session refresh_session_token_digest_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_session
    ADD CONSTRAINT refresh_session_token_digest_key UNIQUE (token_digest);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- Name: security_audit_event security_audit_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.security_audit_event
    ADD CONSTRAINT security_audit_event_pkey PRIMARY KEY (id);


--
-- Name: task_access_grant task_access_grant_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_access_grant
    ADD CONSTRAINT task_access_grant_pkey PRIMARY KEY (id);


--
-- Name: tenant tenant_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT tenant_code_key UNIQUE (code);


--
-- Name: tenant tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant
    ADD CONSTRAINT tenant_pkey PRIMARY KEY (id);


--
-- Name: user_account user_account_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT user_account_email_key UNIQUE (email);


--
-- Name: user_account user_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT user_account_pkey PRIMARY KEY (id);


--
-- Name: user_role user_role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT user_role_pkey PRIMARY KEY (id);


--
-- Name: department ux_department_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT ux_department_tenant_name UNIQUE (tenant_id, name);


--
-- Name: role ux_role_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT ux_role_tenant_name UNIQUE (tenant_id, name);


--
-- Name: customer_access_grant ux_tenant_user_customer_grant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grant
    ADD CONSTRAINT ux_tenant_user_customer_grant UNIQUE (tenant_id, user_id, customer_id);


--
-- Name: task_access_grant ux_tenant_user_task_grant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_access_grant
    ADD CONSTRAINT ux_tenant_user_task_grant UNIQUE (tenant_id, user_id, task_id);


--
-- Name: user_role ux_user_role; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT ux_user_role UNIQUE (user_id, role_id);


--
-- Name: ix_customer_access_grant_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_access_grant_tenant_id ON public.customer_access_grant USING btree (tenant_id);


--
-- Name: ix_department_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_department_tenant_id ON public.department USING btree (tenant_id);


--
-- Name: ix_notification_outbox_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_outbox_pending ON public.notification_outbox USING btree (status, created_at);


--
-- Name: ix_refresh_session_family_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_session_family_id ON public.refresh_session USING btree (family_id);


--
-- Name: ix_role_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_role_tenant_id ON public.role USING btree (tenant_id);


--
-- Name: ix_security_audit_event_occurred_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_event_occurred_at ON public.security_audit_event USING btree (occurred_at DESC);


--
-- Name: ix_task_access_grant_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_task_access_grant_tenant_id ON public.task_access_grant USING btree (tenant_id);


--
-- Name: ix_user_account_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_account_tenant_id ON public.user_account USING btree (tenant_id);


--
-- Name: customer_access_grant customer_access_grant_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grant
    ADD CONSTRAINT customer_access_grant_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: customer_access_grant customer_access_grant_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_access_grant
    ADD CONSTRAINT customer_access_grant_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


--
-- Name: department department_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.department
    ADD CONSTRAINT department_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: invitation invitation_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitation
    ADD CONSTRAINT invitation_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.user_account(id);


--
-- Name: invitation invitation_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invitation
    ADD CONSTRAINT invitation_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


--
-- Name: password_reset password_reset_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset
    ADD CONSTRAINT password_reset_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


--
-- Name: refresh_session refresh_session_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_session
    ADD CONSTRAINT refresh_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


--
-- Name: role role_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: task_access_grant task_access_grant_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_access_grant
    ADD CONSTRAINT task_access_grant_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: task_access_grant task_access_grant_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_access_grant
    ADD CONSTRAINT task_access_grant_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


--
-- Name: user_account user_account_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT user_account_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.department(id);


--
-- Name: user_account user_account_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_account
    ADD CONSTRAINT user_account_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenant(id);


--
-- Name: user_role user_role_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT user_role_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.role(id) ON DELETE RESTRICT;


--
-- Name: user_role user_role_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_role
    ADD CONSTRAINT user_role_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.user_account(id) ON DELETE CASCADE;


COMMIT;

--
-- PostgreSQL database dump complete
--

\unrestrict AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
