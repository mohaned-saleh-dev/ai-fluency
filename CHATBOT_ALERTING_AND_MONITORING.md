# Chatbot Alerting & Monitoring Framework

> **Comprehensive monitoring, alerting, and observability strategy for Tamara's Chat System — covering all services, APIs, conversation flows, product metrics, infrastructure, and business continuity.**

---

**Version:** 1.0 | **Status:** Draft | **Created:** March 17, 2026 | **Owner:** Product / Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Landscape](#2-system-landscape)
3. [Alert Severity Classification](#3-alert-severity-classification)
4. [Service & API Health Alerts](#4-service--api-health-alerts)
5. [Conversation Flow Alerts](#5-conversation-flow-alerts)
6. [Product Metrics Alerts](#6-product-metrics-alerts)
7. [Infrastructure Alerts](#7-infrastructure-alerts)
8. [Security & Abuse Alerts](#8-security--abuse-alerts)
9. [Business Continuity Alerts](#9-business-continuity-alerts)
10. [Alert Routing & Escalation](#10-alert-routing--escalation)
11. [Dashboard Requirements](#11-dashboard-requirements)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [Runbook Index](#13-runbook-index)
14. [Appendix](#14-appendix)

---

## 1. Executive Summary

### Why This Matters

Tamara's chat system handles **18,000–30,000 daily conversations** across Customer and Partner apps, web widgets, and support sites. The system spans multiple services — Chat Backend, AI Chatbot Orchestrator, Salesforce Service Cloud, WebSocket infrastructure, and supporting data stores — all of which must operate reliably to maintain customer experience and operational efficiency.

**Today's gap:** There is minimal alerting on service health, conversation flow integrity, or product metric degradation. If APIs fail, chats get stuck in loops, handovers to Salesforce break, or deflection rates plummet — there is no automated detection or notification. This document closes that gap.

### Objectives

- **Zero silent failures** — every service failure, flow breakdown, or metric degradation triggers an alert
- **Fast detection** — critical issues detected within 1–5 minutes, not hours
- **Clear ownership** — every alert has a defined owner, escalation path, and runbook
- **Noise control** — alerts are tuned to minimize false positives while catching real issues
- **Comprehensive coverage** — spanning APIs, conversation flows, product KPIs, infrastructure, security, and business continuity

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Chat Backend Service | Tamara Core APIs (separate monitoring) |
| AI Chatbot Orchestrator | Payment/checkout flows |
| Salesforce integration (Cases, Messaging Sessions, Omni-Channel) | Salesforce admin configuration |
| WebSocket/Socket.IO infrastructure | Mobile app build/release |
| Flutter SDK & Web Widget client-side health | Third-party CDN/DNS |
| MongoDB, PostgreSQL, Redis health | General cloud infrastructure (handled by platform team) |
| Product metrics (BSAT, deflection, abandonment) | |
| File upload & storage (S3) | |
| Push notification delivery | |
| Auth service (chat-related) | |

---

## 2. System Landscape

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Flutter SDK   │  │ Web Widget   │  │ Partner Portal Widget │ │
│  │ (iOS/Android) │  │ (React)      │  │ (React)               │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
└─────────┼─────────────────┼───────────────────────┼─────────────┘
          │                 │                       │
          ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CHAT BACKEND SERVICE                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ REST API  │  │ WebSocket/   │  │ File Upload  │              │
│  │ Endpoints │  │ Socket.IO    │  │ Service      │              │
│  └──────────┘  └──────────────┘  └──────────────┘              │
└────────┬───────────────┬──────────────────┬─────────────────────┘
         │               │                  │
         ▼               ▼                  ▼
┌────────────────┐ ┌───────────────┐ ┌──────────────┐
│ AI Chatbot     │ │ Salesforce    │ │ File Storage  │
│ Orchestrator   │ │ Service Cloud │ │ (S3)          │
└────────────────┘ └───────────────┘ └──────────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│                  DATA LAYER                         │
│  ┌────────────┐  ┌────────┐  ┌──────────────────┐ │
│  │ PostgreSQL │  │ Redis  │  │ MongoDB           │ │
│  │ (Chat Hist)│  │ (Cache)│  │ (Knowledge Base)  │ │
│  └────────────┘  └────────┘  └──────────────────┘ │
└────────────────────────────────────────────────────┘
```

### Monitored Services Inventory

| # | Service | Type | Owner | Monitoring Tool |
|---|---------|------|-------|-----------------|
| 1 | Chat Backend Service | Microservice | Backend Team | DataDog APM |
| 2 | WebSocket/Socket.IO Server | Real-time infra | Backend Team | DataDog APM + Custom |
| 3 | AI Chatbot Orchestrator | AI Service | AI Team | DataDog APM + Custom |
| 4 | Salesforce Integration Layer | Integration | Backend Team | DataDog + SF Event Monitoring |
| 5 | File Upload Service | Microservice | Backend Team | DataDog APM |
| 6 | Push Notification Service | External integration | Mobile Team | DataDog + FCM/APNs dashboards |
| 7 | Auth Service (Chat) | Shared service | Platform Team | DataDog APM |
| 8 | PostgreSQL | Database | Platform Team | DataDog Database Monitoring |
| 9 | Redis | Cache/Pub-Sub | Platform Team | DataDog Redis Integration |
| 10 | MongoDB | Knowledge store | AI Team | DataDog MongoDB Integration |
| 11 | S3 (File Storage) | Object store | Platform Team | CloudWatch |
| 12 | Event Pipeline (Pub/Sub → BigQuery) | Data pipeline | Data Team | DataDog + Cloud Monitoring |

---

## 3. Alert Severity Classification

### Severity Levels

| Severity | Label | Response Time | Notification Channel | Example |
|----------|-------|---------------|----------------------|---------|
| **P0** | **Critical** | Immediate (< 5 min) | PagerDuty → Phone + SMS + Slack | Chat system fully down, all handovers failing |
| **P1** | **High** | < 15 min | PagerDuty → Slack + SMS | Salesforce case creation failing > 10%, BSAT drop > 15 points |
| **P2** | **Medium** | < 1 hour | Slack alert channel | Elevated error rates, latency degradation, moderate metric dips |
| **P3** | **Low** | < 4 hours | Slack alert channel (daily digest) | Minor anomalies, approaching thresholds, informational |
| **P4** | **Informational** | Next business day | Email digest / Dashboard | Trend alerts, capacity warnings |

### Alert Lifecycle

```
FIRING → ACKNOWLEDGED → INVESTIGATING → MITIGATED → RESOLVED → POST-MORTEM (P0/P1 only)
```

| State | Max Duration | Action Required |
|-------|-------------|-----------------|
| Firing → Acknowledged | P0: 5 min, P1: 15 min, P2: 1 hr | Responder acknowledges ownership |
| Acknowledged → Investigating | 15 min | Root cause analysis begins |
| Investigating → Mitigated | P0: 30 min, P1: 1 hr, P2: 4 hr | Temporary fix or workaround applied |
| Mitigated → Resolved | 24 hours | Permanent fix deployed |
| Resolved → Post-Mortem | 72 hours (P0/P1 only) | Blameless post-mortem documented |

---

## 4. Service & API Health Alerts

### 4.1 Chat Backend Service

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| S-01 | **Chat Backend Down** | Health check endpoint returns non-200 for 3 consecutive checks | 1 min intervals | P0 | 3 consecutive failures |
| S-02 | **Chat Backend High Error Rate** | 5xx error rate on REST API exceeds threshold | 5 min rolling | P1 | > 5% of requests |
| S-03 | **Chat Backend Elevated Error Rate** | 5xx error rate trending up | 15 min rolling | P2 | > 1% of requests |
| S-04 | **Chat Backend Latency Degradation (P95)** | REST API P95 latency exceeds threshold | 5 min rolling | P2 | > 2 seconds |
| S-05 | **Chat Backend Latency Degradation (P99)** | REST API P99 latency exceeds threshold | 5 min rolling | P1 | > 5 seconds |
| S-06 | **Chat Backend Request Volume Anomaly** | Significant deviation from expected request volume | 15 min rolling | P2 | ±50% from baseline (same day/hour) |
| S-07 | **Chat Backend 4xx Spike** | Client error rate spike | 10 min rolling | P3 | > 10% of requests |

### 4.2 WebSocket / Socket.IO Server

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| W-01 | **WebSocket Server Down** | No active WebSocket connections and health check failing | 1 min intervals | P0 | 3 consecutive failures |
| W-02 | **WebSocket Connection Failure Rate** | New connection attempts failing at high rate | 5 min rolling | P1 | > 5% failure rate |
| W-03 | **WebSocket Connection Drop Spike** | Abnormal rate of disconnections (non-user-initiated) | 5 min rolling | P1 | > 10% of active connections drop |
| W-04 | **WebSocket Message Delivery Failure** | Messages failing to deliver via WebSocket | 5 min rolling | P1 | > 1% of messages |
| W-05 | **WebSocket Active Connections Anomaly** | Active connections significantly below expected | 15 min rolling | P2 | < 50% of baseline for same hour |
| W-06 | **WebSocket Reconnection Storm** | High rate of reconnection attempts indicating instability | 5 min rolling | P2 | > 500 reconnections/min |
| W-07 | **WebSocket Handshake Latency** | Time for new WebSocket connections to establish | 5 min rolling | P2 | P95 > 3 seconds |

### 4.3 AI Chatbot Orchestrator

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| O-01 | **Orchestrator Down** | Health check failing | 1 min intervals | P0 | 3 consecutive failures |
| O-02 | **Orchestrator High Error Rate** | Bot response generation failing | 5 min rolling | P1 | > 5% of requests |
| O-03 | **Orchestrator Response Latency** | Time to generate bot response exceeds threshold | 5 min rolling | P2 | P95 > 5 seconds |
| O-04 | **Orchestrator Response Latency Critical** | Extreme response delay | 5 min rolling | P1 | P95 > 10 seconds |
| O-05 | **Orchestrator Fallback Rate** | Rate of fallback/generic responses (low confidence) | 30 min rolling | P2 | > 25% of responses |
| O-06 | **Orchestrator Knowledge Retrieval Failure** | MongoDB knowledge base queries failing | 5 min rolling | P1 | > 5% failure rate |
| O-07 | **Orchestrator Intent Classification Failure** | Unable to classify user intent | 30 min rolling | P3 | > 15% unclassified |
| O-08 | **Orchestrator Loop Detection** | Bot sending repetitive responses to same user | Per session | P1 | Same response pattern ≥ 3 times in a session |
| O-09 | **Orchestrator LLM/Model Timeout** | Upstream model provider timeouts | 5 min rolling | P1 | > 10% timeout rate |
| O-10 | **Orchestrator Conversation Stuck** | Sessions with no bot response for extended period | Per session | P2 | No response for > 60 seconds after user message |

### 4.4 Salesforce Integration

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| SF-01 | **Salesforce API Unreachable** | Cannot connect to Salesforce REST API | 1 min intervals | P0 | 3 consecutive failures |
| SF-02 | **Salesforce Case Creation Failure** | Cases failing to be created during handover | 5 min rolling | P0 | > 5% failure rate |
| SF-03 | **Salesforce Messaging Session Failure** | Messaging sessions failing to be created | 5 min rolling | P0 | > 5% failure rate |
| SF-04 | **Salesforce Account Lookup Failure** | Customer/Partner account lookup failing | 5 min rolling | P1 | > 10% failure rate |
| SF-05 | **Salesforce Sync Latency** | Time to create case + messaging session exceeds threshold | 5 min rolling | P2 | P95 > 10 seconds |
| SF-06 | **Salesforce Auth Token Refresh Failure** | OAuth token refresh to Salesforce failing | Per occurrence | P1 | Any failure |
| SF-07 | **Salesforce File Sync Failure** | File attachments failing to sync to Salesforce ContentVersion | 15 min rolling | P2 | > 10% failure rate |
| SF-08 | **Salesforce Queue Routing Error** | Cases routed to wrong queue (Partner Care vs. Onboarding) | Per occurrence | P1 | Any misroute detected |
| SF-09 | **Salesforce Omni-Channel Unavailable** | Omni-Channel routing not functioning | 5 min rolling | P1 | Routing failures > 5% |
| SF-10 | **Salesforce API Rate Limit Approaching** | Nearing Salesforce API daily limits | Hourly | P2 | > 70% of daily limit consumed |
| SF-11 | **Salesforce API Rate Limit Exceeded** | Hit Salesforce API daily limit | Per occurrence | P0 | Limit reached |
| SF-12 | **Salesforce Case-Session Orphan** | Messaging session created without linked case (or vice versa) | 15 min rolling | P2 | Any occurrence |

### 4.5 File Upload Service

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| F-01 | **File Upload Failure Rate** | File uploads to S3 failing | 10 min rolling | P2 | > 5% failure rate |
| F-02 | **File Upload Latency** | Upload time exceeding threshold | 10 min rolling | P3 | P95 > 10 seconds |
| F-03 | **S3 Bucket Unreachable** | Cannot connect to S3 bucket | 1 min intervals | P1 | 3 consecutive failures |

### 4.6 Push Notification Service

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| N-01 | **Push Notification Delivery Failure** | FCM/APNs delivery failures | 15 min rolling | P2 | > 10% failure rate |
| N-02 | **Push Notification Latency** | Time from event to notification exceeds threshold | 15 min rolling | P3 | P95 > 30 seconds |
| N-03 | **Push Notification Volume Drop** | Significantly fewer notifications sent than expected | 1 hour rolling | P3 | < 50% of baseline |

### 4.7 Auth Service (Chat Context)

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| A-01 | **Auth Token Validation Failure** | Chat token validation failures | 5 min rolling | P1 | > 10% failure rate |
| A-02 | **Auth Service Unreachable** | Auth service health check failing | 1 min intervals | P0 | 3 consecutive failures |
| A-03 | **Auth Token Refresh Failure** | Token refresh requests failing | 5 min rolling | P1 | > 5% failure rate |

---

## 5. Conversation Flow Alerts

These alerts monitor the integrity of chat conversation flows end-to-end, catching scenarios where chats get stuck, handovers break, or users experience degraded service.

### 5.1 Handover & Escalation Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| H-01 | **Handover Total Failure** | No successful handovers to Salesforce occurring | 15 min rolling | P0 | 0 successful handovers when > 5 attempted |
| H-02 | **Handover Failure Rate** | Percentage of handover attempts failing | 15 min rolling | P1 | > 5% failure rate |
| H-03 | **Handover Timeout** | Handover process exceeding time limit (session create + case create + agent assignment) | Per handover | P1 | > 60 seconds end-to-end |
| H-04 | **Handover Stuck in Queue** | Handed-over chats waiting for agent assignment beyond threshold | Per handover | P2 | > 10 minutes in queue |
| H-05 | **Handover with No Agent Response** | Chat handed to agent but no agent response received | Per handover | P1 | > 15 minutes with zero agent messages |
| H-06 | **Handover Drop** | User disconnects during handover process | 30 min rolling | P2 | > 20% of handovers |
| H-07 | **Agent-to-Bot Fallback Failure** | Chat fails to return to bot after agent ends session | Per occurrence | P2 | Any failure |
| H-08 | **Handover Context Loss** | Conversation summary or context not passed to Salesforce agent | Per handover | P2 | Any occurrence (sampled at 10%) |
| H-09 | **Double Handover** | Same session handed over to agent more than once within short window | Per session | P3 | ≥ 2 handovers within 5 minutes |

### 5.2 Conversation Loop & Stuck Chat Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| L-01 | **Bot Response Loop Detected** | Bot repeating same or semantically similar responses in a session | Per session | P1 | ≥ 3 repeated response patterns |
| L-02 | **Conversation Not Progressing** | Multiple user messages with no resolution or handover | Per session | P2 | > 8 user messages with no resolution/handover signal |
| L-03 | **Session Stuck Without Response** | User sent message but no bot/agent response received | Per session | P1 | No response > 2 minutes (bot phase) or > 5 minutes (agent phase) |
| L-04 | **Excessive Session Duration** | Chat session running abnormally long | Per session | P2 | > 45 minutes active conversation |
| L-05 | **Ghost Sessions** | Sessions that appear active but have no message activity | 30 min rolling | P3 | Sessions open > 30 min with zero messages |
| L-06 | **Infinite Intent Loop** | Same intent classified repeatedly without resolution | Per session | P1 | Same intent ≥ 4 consecutive times |
| L-07 | **High Unresolved Session Rate** | Sessions ending without resolution or proper handover | 1 hour rolling | P2 | > 30% of sessions |

### 5.3 Message Delivery Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| M-01 | **Message Send Failure Rate** | User messages failing to send | 5 min rolling | P1 | > 1% failure rate |
| M-02 | **Message Delivery Latency** | Time from send to delivery exceeds threshold | 5 min rolling | P2 | P95 > 500ms (bot), > 2s (agent via SF) |
| M-03 | **Message Ordering Violation** | Messages received out of order | Per session | P2 | Any occurrence > 0.5% of sessions |
| M-04 | **Duplicate Messages** | Same message delivered multiple times | Per session | P3 | Any occurrence > 0.5% of sessions |
| M-05 | **Bot Response Empty** | Bot returning empty or null responses | 5 min rolling | P1 | > 1% of bot responses |
| M-06 | **Rich Message Rendering Failure** | Carousel/button/list messages failing to render | 15 min rolling | P2 | > 5% render failures (client-side) |

### 5.4 Session Lifecycle Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| SL-01 | **Session Creation Failure** | New chat sessions failing to initialize | 5 min rolling | P0 | > 5% creation failure rate |
| SL-02 | **Session Volume Drop** | Total new sessions significantly below expected | 30 min rolling | P1 | < 40% of same-hour baseline for ≥ 30 min |
| SL-03 | **Session Volume Spike** | Unusual surge in new sessions | 15 min rolling | P2 | > 200% of same-hour baseline |
| SL-04 | **Session Cleanup Failure** | Ended sessions not being properly closed/archived | Daily | P3 | > 100 orphaned sessions |
| SL-05 | **Cross-Platform Session Mismatch** | Session data inconsistent between client and backend | Per session | P3 | Any occurrence > 1% |

### 5.5 Partner Classification & Routing Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| PR-01 | **Partner Classification Failure** | Unable to classify partner as onboarding/live | 15 min rolling | P1 | > 5% classification failures |
| PR-02 | **Partner Misroute Detected** | Partner routed to incorrect chatbot flow | Per occurrence | P1 | Any confirmed misroute |
| PR-03 | **Salesforce Partner Lookup Latency** | Partner account lookup exceeding threshold | 5 min rolling | P2 | P95 > 5 seconds |
| PR-04 | **Partner Status Cache Miss Rate** | Excessive cache misses causing Salesforce lookups | 30 min rolling | P3 | Cache miss rate > 30% |

---

## 6. Product Metrics Alerts

These alerts monitor business-critical KPIs. Thresholds use statistical baselines (trailing 30-day average) with both **absolute** and **percentage-change** triggers.

### 6.1 Deflection Rate

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| D-01 | **Deflection Rate Severe Drop** | Deflection rate drops significantly from baseline | 1 hour rolling | P1 | Drop ≥ 15 percentage points from 30-day avg |
| D-02 | **Deflection Rate Moderate Drop** | Deflection rate declining | 4 hour rolling | P2 | Drop ≥ 8 percentage points from 30-day avg |
| D-03 | **Deflection Rate Trend Alert** | Sustained declining trend over multiple days | 7-day trend | P3 | Declining for 3+ consecutive days |
| D-04 | **Customer Deflection Rate by Market** | Market-specific deflection rate anomaly | 4 hour rolling, per market | P2 | Any market drops ≥ 20 percentage points |
| D-05 | **Partner Deflection Rate (Onboarding)** | Onboarding partner deflection rate drop | 4 hour rolling | P2 | Drop below 35% (target: 50%) |
| D-06 | **Partner Deflection Rate (Live)** | Live partner deflection rate drop | 4 hour rolling | P2 | Drop ≥ 10 percentage points from baseline |

### 6.2 Bot Satisfaction (BSAT)

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| B-01 | **BSAT Severe Drop** | BSAT drops significantly | Daily (min 100 responses) | P1 | Drop ≥ 10 points from 30-day avg |
| B-02 | **BSAT Moderate Drop** | BSAT declining | Daily (min 100 responses) | P2 | Drop ≥ 5 points from 30-day avg |
| B-03 | **BSAT Below Target** | BSAT persistently below target | 7-day rolling | P2 | Below 88% (current baseline) for 7+ days |
| B-04 | **BSAT by Channel** | Channel-specific BSAT anomaly | Daily, per channel | P3 | Any channel ≥ 15 points below overall avg |
| B-05 | **BSAT Survey Response Rate Drop** | Fewer users completing BSAT surveys | Daily | P3 | Survey completion rate < 5% (typical: 10–15%) |

### 6.3 Chat Abandonment

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| AB-01 | **Abandonment Rate Spike** | Chat abandonment rate spikes | 1 hour rolling | P1 | > 20% (target: < 10%) |
| AB-02 | **Abandonment Rate Elevated** | Sustained elevated abandonment | 4 hour rolling | P2 | > 15% |
| AB-03 | **Pre-Handover Abandonment Spike** | Users dropping off specifically during handover wait | 1 hour rolling | P1 | > 30% of handovers abandoned |
| AB-04 | **Abandonment by Platform** | Platform-specific abandonment anomaly | 4 hour rolling, per platform | P2 | Any platform > 25% |

### 6.4 Chat Volume & Completion

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| V-01 | **Chat Volume Collapse** | Total chat volume drops dramatically | 30 min rolling | P0 | < 20% of expected volume (system may be unreachable) |
| V-02 | **Chat Volume Drop** | Total chat volume below expected | 1 hour rolling | P1 | < 50% of same-hour baseline |
| V-03 | **Chat Completion Rate Drop** | Fewer sessions reaching proper resolution | 4 hour rolling | P2 | Completion rate drops ≥ 10 percentage points |
| V-04 | **Chat Volume Spike** | Unusual surge possibly indicating incident | 15 min rolling | P2 | > 300% of same-hour baseline |

### 6.5 Response Quality & Resolution

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| Q-01 | **First Response Time Degradation** | Average time to first bot response increasing | 1 hour rolling | P2 | P95 > 3 seconds (target: < 1 second) |
| Q-02 | **Resolution Time Spike** | Average time to resolve chat increasing | 4 hour rolling | P2 | Increase ≥ 50% over 30-day avg |
| Q-03 | **Repeat Contact Rate Spike** | Same users opening multiple chat sessions for same issue | Daily | P2 | > 25% repeat contact rate |
| Q-04 | **Negative Sentiment Spike** | NLU detecting elevated frustration/anger across sessions | 1 hour rolling | P2 | > 20% of sessions with negative sentiment |

### 6.6 Agent Handover Metrics

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| AH-01 | **Handover Rate Spike** | Too many chats escalating to agents (deflection failure) | 1 hour rolling | P2 | Handover rate ≥ 70% (inverse of deflection) |
| AH-02 | **Agent Wait Time Spike** | Average wait time for agent after handover | 1 hour rolling | P1 | Average > 10 minutes |
| AH-03 | **Agent Handle Time Anomaly** | Average agent handle time significantly above/below norm | Daily | P3 | ±40% from 30-day avg |
| AH-04 | **Zero Agent Availability** | No agents available in Salesforce Omni-Channel for a queue | Per queue | P0 | 0 available agents for > 5 minutes during business hours |

---

## 7. Infrastructure Alerts

### 7.1 PostgreSQL (Chat History)

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| PG-01 | **PostgreSQL Connection Pool Exhaustion** | Available connections nearing limit | 1 min | P1 | > 85% pool utilization |
| PG-02 | **PostgreSQL Replication Lag** | Replica lag exceeding threshold | 1 min | P2 | > 30 seconds |
| PG-03 | **PostgreSQL Query Latency** | Slow queries from chat service | 5 min rolling | P2 | P95 > 500ms |
| PG-04 | **PostgreSQL Disk Usage** | Disk space nearing capacity | Hourly | P2 | > 80% utilized |
| PG-05 | **PostgreSQL Disk Critical** | Disk space critically low | Hourly | P0 | > 95% utilized |
| PG-06 | **PostgreSQL Dead Tuples** | Excessive dead tuples indicating vacuum issues | Daily | P3 | > 10M dead tuples |

### 7.2 Redis (Session Cache & Pub/Sub)

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| RD-01 | **Redis Unreachable** | Cannot connect to Redis | 1 min | P0 | 3 consecutive failures |
| RD-02 | **Redis Memory Usage** | Memory nearing maxmemory | 5 min | P1 | > 85% of maxmemory |
| RD-03 | **Redis Memory Critical** | Memory critically high, evictions occurring | 1 min | P0 | > 95% or eviction rate > 100/s |
| RD-04 | **Redis Latency** | Command latency exceeding threshold | 5 min rolling | P2 | P99 > 50ms |
| RD-05 | **Redis Connected Clients Spike** | Abnormal client connection count | 5 min | P2 | > 200% of baseline |
| RD-06 | **Redis Pub/Sub Message Backlog** | Messages backing up in pub/sub channels | 5 min | P2 | > 10,000 pending messages |
| RD-07 | **Redis Key Expiry Storm** | Mass session TTL expirations causing load spike | 5 min | P3 | Expiry rate > 500/s |

### 7.3 MongoDB (Knowledge Base)

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| MG-01 | **MongoDB Unreachable** | Cannot connect to MongoDB | 1 min | P0 | 3 consecutive failures |
| MG-02 | **MongoDB Query Latency** | Knowledge retrieval queries slow | 5 min rolling | P2 | P95 > 2 seconds |
| MG-03 | **MongoDB Replication Lag** | Replica set lag | 1 min | P2 | > 10 seconds |
| MG-04 | **MongoDB Connection Pool** | Connection pool nearing exhaustion | 5 min | P1 | > 80% utilized |
| MG-05 | **MongoDB Knowledge Collection Empty** | Knowledge collection has zero documents | Per occurrence | P0 | Count = 0 |
| MG-06 | **MongoDB Index Health** | Missing or degraded indexes on knowledge collection | Daily | P3 | Slow query log entries increasing |

### 7.4 Event Pipeline (Pub/Sub → BigQuery)

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| EP-01 | **Event Pipeline Lag** | Events backlogged in Pub/Sub | 5 min | P2 | > 5 minutes lag |
| EP-02 | **Event Pipeline Down** | No events flowing to BigQuery | 15 min | P1 | Zero events for 15+ min during business hours |
| EP-03 | **Event Schema Violation** | Events failing schema validation | 15 min rolling | P2 | > 5% violation rate |
| EP-04 | **Event Volume Anomaly** | Unexpected drop in event volume | 1 hour rolling | P2 | < 50% of expected volume |

### 7.5 Kubernetes / Compute

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| K-01 | **Pod Crash Loop** | Chat service pods in CrashLoopBackOff | Per occurrence | P0 | Any pod in CrashLoopBackOff |
| K-02 | **Pod Restart Spike** | Elevated pod restarts | 30 min rolling | P1 | > 3 restarts in 30 min |
| K-03 | **CPU Usage High** | Chat service CPU utilization high | 5 min rolling | P2 | > 80% sustained |
| K-04 | **Memory Usage High** | Chat service memory utilization high | 5 min rolling | P2 | > 85% |
| K-05 | **HPA Max Replicas** | Auto-scaler at maximum replicas | Per occurrence | P2 | At max replicas for > 15 min |
| K-06 | **Container OOM Killed** | Container killed due to out-of-memory | Per occurrence | P1 | Any OOM kill |

---

## 8. Security & Abuse Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| SEC-01 | **Rate Limit Breach** | User exceeding message rate limits (60/min) | Per user | P3 | Any breach (log + block) |
| SEC-02 | **Mass Rate Limit Breaches** | Multiple users hitting rate limits simultaneously | 5 min rolling | P1 | > 50 unique users rate-limited |
| SEC-03 | **Auth Bypass Attempt** | Requests to WebSocket/API without valid auth | 5 min rolling | P2 | > 100 unauthenticated attempts |
| SEC-04 | **PII Leak Detection** | PII detected in logs or analytics events | Per occurrence | P1 | Any confirmed PII in logs |
| SEC-05 | **Malicious File Upload** | File upload detected as malicious by scanner | Per occurrence | P2 | Any detection |
| SEC-06 | **Brute Force Session Creation** | Abnormal session creation rate from single IP/user | 5 min rolling | P2 | > 100 sessions from single source |
| SEC-07 | **TLS/Certificate Expiry** | SSL certificates nearing expiry | Daily check | P1 | < 14 days to expiry |
| SEC-08 | **TLS/Certificate Expired** | SSL certificate has expired | Per occurrence | P0 | Expired |
| SEC-09 | **Webhook Signature Validation Failure** | Salesforce webhook callbacks failing signature check | 5 min rolling | P2 | > 5% failure rate |

---

## 9. Business Continuity Alerts

| # | Alert Name | Condition | Window | Severity | Threshold |
|---|-----------|-----------|--------|----------|-----------|
| BC-01 | **Fallback to Salesforce Widget Triggered** | Automatic fallback to legacy Salesforce chat activated | Per occurrence | P0 | Any automatic trigger |
| BC-02 | **Statsig Feature Gate Failure** | Cannot read feature gate configuration | 5 min | P1 | 3 consecutive failures |
| BC-03 | **Statsig Feature Gate Changed** | Chat-related feature gate toggled | Per occurrence | P3 | Any gate change (informational) |
| BC-04 | **Health Check Cascade Failure** | Multiple services failing health checks simultaneously | 1 min | P0 | ≥ 2 core services down |
| BC-05 | **Regional Outage Indicator** | Chat volume drops in specific market/region only | 15 min, per market | P1 | Any single market < 20% of normal volume |
| BC-06 | **Disaster Recovery Readiness** | DR replica health check | Daily | P3 | Any DR replica unhealthy |
| BC-07 | **Deployment Regression Detection** | Error rates spike within 30 min of deployment | 30 min post-deploy | P1 | Error rate increase > 5x pre-deploy baseline |
| BC-08 | **Rollback Trigger** | Meets automated rollback criteria post-deploy | 15 min post-deploy | P0 | Error rate > 1%, latency P95 > 2x, SF sync failure > 5% |

---

## 10. Alert Routing & Escalation

### 10.1 Routing Matrix

| Alert Category | Primary Owner | Secondary Owner | Slack Channel | PagerDuty Service |
|----------------|---------------|-----------------|---------------|-------------------|
| Chat Backend (S-*) | Backend Team | SRE | #chat-alerts-eng | chat-backend |
| WebSocket (W-*) | Backend Team | SRE | #chat-alerts-eng | chat-backend |
| Orchestrator (O-*) | AI Team | Backend Team | #chat-alerts-ai | chatbot-orchestrator |
| Salesforce (SF-*) | Backend Team | SF Admin | #chat-alerts-sf | chat-salesforce |
| Conversation Flow (H-*, L-*, M-*, SL-*) | Backend + AI Team | Product | #chat-alerts-flow | chat-flow |
| Partner Routing (PR-*) | AI Team | Backend Team | #chat-alerts-ai | chatbot-orchestrator |
| Product Metrics (D-*, B-*, AB-*, V-*, Q-*, AH-*) | Product Team | AI + Backend | #chat-alerts-product | chat-product |
| Infrastructure (PG-*, RD-*, MG-*, EP-*, K-*) | SRE / Platform | Backend Team | #chat-alerts-infra | chat-infra |
| Security (SEC-*) | Security Team | SRE | #security-alerts | security-oncall |
| Business Continuity (BC-*) | SRE | Engineering Manager | #chat-alerts-critical | chat-critical |

### 10.2 Escalation Policy

```
Level 1 (0 min)     → On-call engineer (auto-page for P0/P1)
Level 2 (15 min)    → Team lead / secondary on-call
Level 3 (30 min)    → Engineering Manager
Level 4 (60 min)    → VP Engineering + Product Lead
Level 5 (2 hours)   → CTO (P0 only)
```

### 10.3 Business Hours vs. Off-Hours

| Severity | Business Hours (Sun–Thu 9am–6pm AST) | Off-Hours |
|----------|--------------------------------------|-----------|
| P0 | Immediate page + Slack + SMS | Immediate page + Slack + SMS |
| P1 | Immediate page + Slack | Page after 5 min unacknowledged |
| P2 | Slack notification | Slack (checked next business day unless trending P1) |
| P3 | Slack daily digest | Next business day |
| P4 | Email weekly digest | Weekly |

### 10.4 On-Call Schedule

| Team | Rotation | Coverage |
|------|----------|----------|
| Backend/SRE | Weekly rotation | 24/7 for P0/P1 |
| AI Team | Weekly rotation | 24/7 for P0/P1 |
| Product | Single POC | Business hours only |
| Security | Weekly rotation | 24/7 for P0/P1 |

---

## 11. Dashboard Requirements

### 11.1 Real-Time Operations Dashboard

**Refresh:** Every 30 seconds

| Panel | Metrics | Visualization |
|-------|---------|---------------|
| **System Health** | Health check status for all services | Traffic light grid (green/yellow/red) |
| **Active Sessions** | Total active chat sessions by platform | Counter with sparkline |
| **Message Throughput** | Messages per second (sent + received) | Time series line chart |
| **Error Rate** | Combined error rate across all services | Time series with threshold lines |
| **WebSocket Connections** | Active connections, connects/sec, disconnects/sec | Multi-line time series |
| **Handover Pipeline** | Active handovers, queue depth, success/failure rate | Funnel + counters |
| **Salesforce Health** | API response times, success rates | Gauges + time series |
| **Active Alerts** | Current firing alerts by severity | Alert table sorted by severity |

### 11.2 Conversation Health Dashboard

**Refresh:** Every 5 minutes

| Panel | Metrics | Visualization |
|-------|---------|---------------|
| **Conversation Funnel** | Sessions → Bot interaction → Resolution / Handover | Funnel chart |
| **Bot Loop Detection** | Sessions flagged for loops (last 24h) | Counter + session list |
| **Stuck Sessions** | Sessions with no activity but not closed | Table with duration |
| **Handover Success Rate** | Successful vs. failed handovers | Donut chart + time series |
| **Response Times** | Bot response time, Agent response time | Box plots (P50/P95/P99) |
| **Intent Distribution** | Top intents classified in last 24h | Bar chart |
| **Unclassified Queries** | Queries where intent was unknown | Counter + sample list |
| **Partner Routing** | Onboarding vs. Live partner classification | Pie chart + accuracy |

### 11.3 Product Metrics Dashboard

**Refresh:** Every 15 minutes

| Panel | Metrics | Visualization |
|-------|---------|---------------|
| **Deflection Rate** | Overall, by market, by channel, 30-day trend | Line chart with target |
| **BSAT Score** | Overall, by channel, by language, 30-day trend | Line chart with target |
| **Abandonment Rate** | Overall, by platform, pre/post handover | Line chart with threshold |
| **Chat Volume** | Sessions per hour, daily, weekly comparison | Multi-line comparison |
| **Completion Rate** | Sessions ending in resolution | Line chart with target |
| **First Response Time** | P50/P95/P99 over time | Box plot time series |
| **Repeat Contact Rate** | Users returning within 24h for same issue | Line chart with threshold |
| **Agent Wait Time** | Average, P95 wait after handover | Time series with threshold |

### 11.4 Salesforce Integration Dashboard

**Refresh:** Every 1 minute

| Panel | Metrics | Visualization |
|-------|---------|---------------|
| **SF API Health** | Response time, success rate, error breakdown | Time series + pie |
| **Case Creation** | Rate, success/failure, avg create time | Counter + time series |
| **Messaging Sessions** | Active sessions, creation rate, orphans | Counter + time series |
| **Queue Distribution** | Cases by queue (Customer Care, Partner Care, Onboarding) | Stacked bar |
| **File Sync** | Sync rate, failures, queue depth | Time series |
| **API Quota** | Current consumption vs. daily limit | Gauge |
| **Account Lookup** | Success rate, cache hit rate, latency | Multi-metric panel |

### 11.5 Infrastructure Dashboard

**Refresh:** Every 30 seconds

| Panel | Metrics | Visualization |
|-------|---------|---------------|
| **PostgreSQL** | Connections, query latency, replication lag, disk | Multi-panel |
| **Redis** | Memory, connected clients, ops/sec, latency, pub/sub | Multi-panel |
| **MongoDB** | Connections, query latency, replication, operations | Multi-panel |
| **Kubernetes** | Pod status, CPU, memory, restarts, HPA state | Multi-panel |
| **Event Pipeline** | Pub/Sub lag, throughput, error rate | Time series |
| **S3** | Request rate, error rate, latency | Time series |

---

## 12. Implementation Roadmap

### Phase 1: Foundation (Week 1–2)

| Task | Owner | Priority |
|------|-------|----------|
| Set up DataDog APM for Chat Backend Service | Backend/SRE | P0 |
| Set up DataDog APM for AI Chatbot Orchestrator | AI Team/SRE | P0 |
| Implement health check endpoints for all services | Backend + AI | P0 |
| Configure PagerDuty services and escalation policies | SRE | P0 |
| Create Slack alert channels (#chat-alerts-*) | SRE | P0 |
| Deploy all P0 severity alerts (system down scenarios) | SRE | P0 |
| Build Real-Time Operations Dashboard (v1) | SRE | P0 |

### Phase 2: Service Health (Week 3–4)

| Task | Owner | Priority |
|------|-------|----------|
| Deploy all Service & API Health alerts (Section 4) | Backend/SRE | P1 |
| Deploy Salesforce integration alerts (SF-01 through SF-12) | Backend | P1 |
| Deploy WebSocket monitoring alerts (W-01 through W-07) | Backend | P1 |
| Build Salesforce Integration Dashboard | Backend | P1 |
| Configure alert deduplication and grouping rules | SRE | P1 |
| Write initial runbooks for P0/P1 alerts | All teams | P1 |

### Phase 3: Conversation Flows (Week 5–6)

| Task | Owner | Priority |
|------|-------|----------|
| Implement conversation loop detection logic (L-01, L-06) | AI Team | P1 |
| Deploy all Handover & Escalation alerts (H-01 through H-09) | Backend + AI | P1 |
| Deploy all Message Delivery alerts (M-01 through M-06) | Backend | P1 |
| Deploy Session Lifecycle alerts (SL-01 through SL-05) | Backend | P1 |
| Deploy Partner Classification alerts (PR-01 through PR-04) | AI Team | P1 |
| Build Conversation Health Dashboard | AI + Backend | P1 |
| Implement stuck session detector (background job) | Backend | P1 |

### Phase 4: Product Metrics (Week 7–8)

| Task | Owner | Priority |
|------|-------|----------|
| Establish 30-day baselines for all product metrics | Data Team | P1 |
| Deploy Deflection Rate alerts (D-01 through D-06) | Product + Data | P1 |
| Deploy BSAT alerts (B-01 through B-05) | Product + Data | P1 |
| Deploy Abandonment alerts (AB-01 through AB-04) | Product + Data | P1 |
| Deploy Volume & Completion alerts (V-01 through V-04) | Product + Data | P1 |
| Deploy Response Quality alerts (Q-01 through Q-04) | Product + Data | P2 |
| Deploy Agent Handover Metrics alerts (AH-01 through AH-04) | Product + Ops | P2 |
| Build Product Metrics Dashboard | Data Team | P1 |

### Phase 5: Security, Infra & Continuity (Week 9–10)

| Task | Owner | Priority |
|------|-------|----------|
| Deploy all Security alerts (SEC-01 through SEC-09) | Security + SRE | P1 |
| Deploy all Infrastructure alerts (Section 7) | SRE | P2 |
| Deploy Business Continuity alerts (BC-01 through BC-08) | SRE | P1 |
| Build Infrastructure Dashboard | SRE | P2 |
| Complete runbooks for all P0/P1/P2 alerts | All teams | P2 |
| Conduct alert fire drill (simulate P0 scenario) | All teams | P1 |

### Phase 6: Tuning & Optimization (Ongoing)

| Task | Owner | Priority |
|------|-------|----------|
| Tune thresholds based on false positive / false negative rates | All teams | P2 |
| Implement adaptive baselines (ML-based anomaly detection) | SRE + Data | P3 |
| Add composite alerts (correlate multiple signals) | SRE | P3 |
| Monthly alert health review (noise, coverage, gaps) | SRE + Product | P2 |
| Quarterly threshold recalibration | All teams | P2 |

---

## 13. Runbook Index

Every P0 and P1 alert must have an associated runbook. Below is the template and index.

### Runbook Template

```
# Runbook: [Alert ID] — [Alert Name]

## Alert Details
- Severity: [P0/P1/P2]
- Owner: [Team]
- Escalation: [Policy]

## What This Alert Means
[Plain-language description of what triggered and why it matters]

## Immediate Actions (First 5 minutes)
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Diagnosis Steps
1. [Check X dashboard/log]
2. [Run Y query]
3. [Verify Z service]

## Common Root Causes
| Cause | Frequency | Fix |
|-------|-----------|-----|
| [Cause 1] | Common | [Fix] |
| [Cause 2] | Rare | [Fix] |

## Mitigation Options
- [Option A: Quick fix]
- [Option B: Workaround]
- [Option C: Rollback]

## Recovery Verification
- [ ] [Check 1]
- [ ] [Check 2]
- [ ] Alert auto-resolves

## Post-Incident
- Update this runbook if new root cause found
- File post-mortem if P0/P1
```

### Runbook Coverage Requirements

| Severity | Runbook Required | Deadline |
|----------|------------------|----------|
| P0 | Mandatory | Before alert goes live |
| P1 | Mandatory | Within 1 week of alert going live |
| P2 | Recommended | Within 1 month |
| P3 | Optional | Best effort |

### Priority Runbooks to Create

| # | Alert IDs | Runbook Name | Owner |
|---|-----------|-------------|-------|
| 1 | S-01, W-01, O-01 | Service Down — Chat Backend / WebSocket / Orchestrator | Backend + SRE |
| 2 | SF-01, SF-02, SF-03 | Salesforce Integration Failure | Backend + SF Admin |
| 3 | H-01, H-02 | Handover Pipeline Failure | Backend + AI |
| 4 | L-01, L-06 | Bot Loop / Intent Loop Detection | AI Team |
| 5 | BC-01 | Fallback to Salesforce Widget Triggered | SRE |
| 6 | D-01 | Deflection Rate Severe Drop | Product + AI |
| 7 | V-01 | Chat Volume Collapse | SRE + Backend |
| 8 | SF-11 | Salesforce API Rate Limit Exceeded | Backend + SF Admin |
| 9 | BC-08 | Post-Deployment Rollback | SRE + Backend |
| 10 | A-02 | Auth Service Down (Chat Impact) | Platform + SRE |

---

## 14. Appendix

### A. Alert ID Reference

| Prefix | Category | Section |
|--------|----------|---------|
| S-* | Chat Backend Service Health | 4.1 |
| W-* | WebSocket / Socket.IO | 4.2 |
| O-* | AI Chatbot Orchestrator | 4.3 |
| SF-* | Salesforce Integration | 4.4 |
| F-* | File Upload Service | 4.5 |
| N-* | Push Notifications | 4.6 |
| A-* | Auth Service | 4.7 |
| H-* | Handover & Escalation | 5.1 |
| L-* | Conversation Loop & Stuck | 5.2 |
| M-* | Message Delivery | 5.3 |
| SL-* | Session Lifecycle | 5.4 |
| PR-* | Partner Classification & Routing | 5.5 |
| D-* | Deflection Rate | 6.1 |
| B-* | Bot Satisfaction (BSAT) | 6.2 |
| AB-* | Chat Abandonment | 6.3 |
| V-* | Chat Volume & Completion | 6.4 |
| Q-* | Response Quality & Resolution | 6.5 |
| AH-* | Agent Handover Metrics | 6.6 |
| PG-* | PostgreSQL | 7.1 |
| RD-* | Redis | 7.2 |
| MG-* | MongoDB | 7.3 |
| EP-* | Event Pipeline | 7.4 |
| K-* | Kubernetes / Compute | 7.5 |
| SEC-* | Security & Abuse | 8 |
| BC-* | Business Continuity | 9 |

### B. Total Alert Count by Severity

| Severity | Count | Coverage |
|----------|-------|----------|
| P0 | 18 | System-down, total-failure scenarios |
| P1 | 41 | High-impact degradation, handover failures, metric drops |
| P2 | 52 | Moderate degradation, elevated rates, trend changes |
| P3 | 19 | Minor anomalies, informational, approaching thresholds |
| P4 | 2 | Trend reports, capacity planning |
| **Total** | **132** | |

### C. Monitoring Tool Stack

| Tool | Purpose | Alerts Covered |
|------|---------|----------------|
| **DataDog APM** | Application performance monitoring, distributed tracing | S-*, W-*, O-*, F-*, A-* |
| **DataDog Infrastructure** | Host, container, database monitoring | PG-*, RD-*, MG-*, K-* |
| **DataDog Logs** | Centralized logging, log-based alerts | SEC-*, error pattern detection |
| **DataDog Synthetic Monitoring** | Health check probes from external locations | S-01, W-01, O-01, SF-01 |
| **PagerDuty** | Incident management, escalation, on-call | P0/P1 routing |
| **Slack** | Alert notifications, team collaboration | All severities |
| **Salesforce Event Monitoring** | SF-specific event tracking | SF-* |
| **CloudWatch** | AWS resource monitoring | F-*, S3, compute |
| **BigQuery + Looker** | Product metrics calculation, dashboards | D-*, B-*, AB-*, V-*, Q-*, AH-* |
| **Statsig** | Feature gate monitoring | BC-02, BC-03 |
| **Sentry** | Client-side error tracking (SDK/Widget) | M-06, client crashes |

### D. Threshold Calibration Guidelines

Thresholds in this document are **initial recommended values** based on industry best practices and the targets defined in existing PRDs. They should be calibrated as follows:

| Phase | Action | Timeline |
|-------|--------|----------|
| **Pre-launch** | Set thresholds based on load test data and PRD targets | Before alert deployment |
| **Week 1–2** | Monitor false positive rate; tighten/loosen by 10–20% | First 2 weeks |
| **Month 1** | Establish 30-day baselines for all metrics | 30 days |
| **Monthly** | Review alert noise (target: < 5 false positives per alert per month) | Ongoing |
| **Quarterly** | Full threshold recalibration using updated baselines | Every quarter |

**Baseline Calculation Method:**
- **Static thresholds:** Based on PRD-defined SLAs (e.g., latency < 500ms P95)
- **Dynamic thresholds:** 30-day rolling average ± N standard deviations (typically 2σ for P2, 3σ for P1)
- **Percentage-change thresholds:** Measured against same hour/day of previous 4 weeks (accounts for daily/weekly seasonality)

### E. Glossary

| Term | Definition |
|------|------------|
| **BSAT** | Bot Satisfaction — customer satisfaction score for chatbot interactions |
| **Deflection Rate** | Percentage of chats resolved by bot without agent handover |
| **Handover** | Process of transferring a chat from bot to human agent via Salesforce |
| **Messaging Session** | Salesforce object representing a chat conversation with an agent |
| **Omni-Channel** | Salesforce feature for routing cases to available agents |
| **Socket.IO** | Real-time bidirectional communication library (WebSocket with fallbacks) |
| **Statsig** | Feature flagging and experimentation platform used by Tamara |
| **P95 / P99** | 95th / 99th percentile of a distribution (latency, response time) |
| **σ (sigma)** | Standard deviation — used for anomaly detection thresholds |
| **Circuit Breaker** | Pattern that stops calling a failing service to prevent cascade failures |
| **Runbook** | Step-by-step operational guide for responding to a specific alert |
| **SLA** | Service Level Agreement — committed performance target |
| **SLO** | Service Level Objective — internal performance target (typically stricter than SLA) |

### F. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | March 17, 2026 | Product | Initial comprehensive draft |

---

*End of Document*
