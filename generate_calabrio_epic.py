#!/usr/bin/env python3
"""
Generate Calabrio Integration Epic Ticket content.
"""

def create_calabrio_epic():
    """Create comprehensive epic ticket for Calabrio integration."""
    
    epic_content = """# Epic: Calabrio Workforce Management Integration - Backend Implementation

## 🧑‍💻 User Story

As a **workforce management system**, I need **backend APIs and data pipelines** to integrate Calabrio WFM with our contact center infrastructure (Salesforce and Genesys), so that **Calabrio can access real-time contact volume data, agent schedules, and SLA metrics** to enable automated scheduling, forecasting, and real-time adherence monitoring.

## ✅ Acceptance Criteria

### Backend API Requirements
- [ ] RESTful APIs exposed for Calabrio to consume contact volume data
- [ ] Real-time data streaming endpoint for live contact center metrics
- [ ] Agent schedule synchronization API (bidirectional)
- [ ] SLA and performance metrics API endpoint
- [ ] Historical data export API for forecasting models
- [ ] Authentication and authorization implemented (API keys/OAuth)
- [ ] Rate limiting and API versioning configured
- [ ] API documentation published (OpenAPI/Swagger)

### Data Integration Requirements
- [ ] Data pipeline to extract contact volume data from Genesys
- [ ] Data pipeline to extract agent schedule data from Salesforce
- [ ] Data pipeline to extract SLA metrics and performance data
- [ ] Data transformation layer to normalize data formats for Calabrio
- [ ] Real-time data sync mechanism (WebSocket or polling)
- [ ] Historical data backfill capability
- [ ] Data validation and error handling
- [ ] Data retention and archival strategy

### Integration Points
- [ ] Genesys Cloud API integration for contact volume and queue metrics
- [ ] Salesforce Service Cloud API integration for agent data and schedules
- [ ] Calabrio API integration for schedule push/pull operations
- [ ] Webhook endpoints for real-time event notifications
- [ ] Error handling and retry logic for API failures
- [ ] Monitoring and alerting for integration health

### Technical Requirements
- [ ] Database schema for storing integration metadata
- [ ] Message queue setup for async data processing
- [ ] Caching layer for frequently accessed data
- [ ] Logging and observability (structured logs, metrics, traces)
- [ ] Unit tests with >80% coverage
- [ ] Integration tests for all API endpoints
- [ ] Performance testing (handle expected load)
- [ ] Security review and compliance check

### Documentation
- [ ] Technical design document
- [ ] API documentation
- [ ] Integration runbook
- [ ] Data flow diagrams
- [ ] Error handling guide

## 📝 Description

### Background

We are implementing Calabrio Workforce Management (WFM) to optimize agent scheduling, forecasting, and real-time adherence. Currently, workforce planning is manual and reactive, resulting in under-staffing during peaks and over-staffing during low-volume periods. This negatively impacts SLA performance, cost-efficiency, and agent wellbeing.

### Objective

This epic focuses on the **backend infrastructure** required to enable Calabrio integration. The backend work will provide the APIs and data pipelines necessary for:
1. Calabrio team to integrate with our systems
2. Salesforce team to work with Calabrio team on their integration
3. Real-time data flow between Genesys, Salesforce, and Calabrio

### Scope

**In Scope:**
- Backend API development for Calabrio consumption
- Data pipelines from Genesys and Salesforce
- Data transformation and normalization
- API authentication and security
- Integration infrastructure setup
- Monitoring and observability

**Out of Scope:**
- Frontend UI development (separate epic)
- Calabrio configuration and setup (Calabrio team)
- Salesforce-side integration work (Salesforce team)
- Genesys configuration changes
- Agent training and change management

### Technical Architecture

**Data Sources:**
- **Genesys Cloud:** Contact volume, queue metrics, real-time agent status
- **Salesforce Service Cloud:** Agent schedules, shift data, agent profiles
- **Internal Systems:** SLA metrics, performance data, historical trends

**Integration Components:**
- **API Gateway:** Expose RESTful APIs for Calabrio
- **Data Pipeline:** ETL processes for data extraction and transformation
- **Message Queue:** Async processing for real-time updates
- **Database:** Store integration metadata and cached data
- **Webhook Service:** Handle real-time event notifications

**Data Flow:**
1. Genesys → Data Pipeline → Normalized Format → Calabrio API
2. Salesforce → Data Pipeline → Normalized Format → Calabrio API
3. Calabrio → API Gateway → Schedule Updates → Salesforce
4. Real-time Events → Webhook Service → Calabrio

### Integration Points

**Genesys Cloud Integration:**
- Contact volume metrics (calls, chats, emails)
- Queue performance metrics
- Real-time agent status
- Historical contact data for forecasting

**Salesforce Integration:**
- Agent schedule data (shifts, breaks, time-off)
- Agent profile information
- Schedule updates from Calabrio
- Agent availability and capacity

**Calabrio Integration:**
- Schedule push/pull operations
- Forecast data consumption
- Real-time adherence monitoring
- Performance metrics feedback

### Technical Specifications

**API Endpoints Required:**
- `GET /api/v1/calabrio/contact-volume` - Real-time and historical contact volume
- `GET /api/v1/calabrio/agent-schedules` - Current and future agent schedules
- `GET /api/v1/calabrio/sla-metrics` - SLA performance metrics
- `POST /api/v1/calabrio/schedule-updates` - Receive schedule updates from Calabrio
- `GET /api/v1/calabrio/agent-status` - Real-time agent status from Genesys
- `GET /api/v1/calabrio/forecast-data` - Historical data for forecasting models

**Data Pipeline Requirements:**
- Extract contact volume data from Genesys every 15 minutes
- Extract agent schedule data from Salesforce daily (with real-time updates)
- Transform data to Calabrio-compatible format
- Handle data schema changes gracefully
- Support backfill of historical data (last 12 months)

**Performance Requirements:**
- API response time: < 500ms p95
- Data pipeline processing: < 5 minutes for full sync
- Real-time updates: < 30 seconds latency
- Support 1000+ concurrent API requests

**Security Requirements:**
- API key authentication for Calabrio
- OAuth 2.0 for Salesforce and Genesys integrations
- Encrypted data in transit (TLS 1.3)
- Encrypted data at rest
- Rate limiting: 1000 requests/minute per API key
- Audit logging for all API access

### Dependencies

**External Dependencies:**
- Genesys Cloud API access and credentials
- Salesforce Service Cloud API access and credentials
- Calabrio API documentation and sandbox access
- Network connectivity between systems

**Internal Dependencies:**
- Database infrastructure (PostgreSQL)
- Message queue infrastructure (RabbitMQ/Kafka)
- API gateway setup
- Monitoring and logging infrastructure
- Security team review and approval

**Blocking Dependencies:**
- API credentials from Genesys (required for development)
- API credentials from Salesforce (required for development)
- Calabrio API documentation (required for integration design)

### Success Criteria

- [ ] All API endpoints implemented and tested
- [ ] Data pipelines successfully extracting data from Genesys and Salesforce
- [ ] Data transformation working correctly
- [ ] Calabrio can successfully consume all required data
- [ ] Schedule updates can be pushed from Calabrio to Salesforce
- [ ] Real-time data sync working (< 30 seconds latency)
- [ ] API documentation complete and published
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Security review passed

### Risks and Mitigation

**Risk:** API rate limits from Genesys/Salesforce
- **Mitigation:** Implement caching and batch processing

**Risk:** Data schema changes in source systems
- **Mitigation:** Build flexible transformation layer with versioning

**Risk:** Real-time sync performance issues
- **Mitigation:** Use message queue for async processing, optimize queries

**Risk:** Integration complexity between three systems
- **Mitigation:** Phased rollout, comprehensive testing, clear API contracts

### Timeline Estimate

**Phase 1: API Design and Infrastructure (2 weeks)**
- API endpoint design
- Database schema design
- Infrastructure setup
- Authentication implementation

**Phase 2: Data Pipeline Development (3 weeks)**
- Genesys integration
- Salesforce integration
- Data transformation layer
- Error handling

**Phase 3: Calabrio Integration (2 weeks)**
- Calabrio API integration
- Schedule push/pull operations
- Real-time sync implementation

**Phase 4: Testing and Documentation (2 weeks)**
- Integration testing
- Performance testing
- API documentation
- Runbook creation

**Total Estimated Duration:** 9 weeks

### Notes

- This epic enables the Calabrio team to proceed with their integration work
- Salesforce team will work in parallel once APIs are available
- Regular sync meetings with Calabrio and Salesforce teams required
- API contracts should be finalized before development starts
- Consider using API versioning from the start to support future changes

---

**Epic Type:** Backend Integration  
**Priority:** High  
**Labels:** `backend`, `integration`, `calabrio`, `salesforce`, `genesys`, `wfm`  
**Components:** Backend Services, Data Pipeline, API Gateway  
**Sprint:** TBD"""
    
    return epic_content


if __name__ == "__main__":
    content = create_calabrio_epic()
    print(content)



