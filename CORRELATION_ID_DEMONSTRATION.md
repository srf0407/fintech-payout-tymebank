# Correlation ID Demonstration Across Boundaries

This document demonstrates how correlation IDs are propagated across frontend, backend, and third-party service boundaries in our fintech payout application.

## Overview

Correlation IDs enable end-to-end request tracing across distributed systems, allowing us to track a single business operation (like creating a payout) through multiple services and components.

## Key Correlation ID: `75db2fb1-d32f-4bbf-aba5-7a4f9852e703`

This demonstration follows a single payout creation request through the entire system.

## 1. Frontend Request Initiation

**Network Headers (Browser DevTools):**
```
Request Method: POST
URL: http://localhost:8000/payouts/
Status Code: 201 Created
Response Headers:
  x-correlation-id: 75db2fb1-d32f-4bbf-aba5-7a4f9852e703
```

**Frontend Implementation:**
- The frontend generates or receives a correlation ID for the payout creation request
- This ID is included in the request headers and propagated to the backend

## 2. Backend Request Processing

**Request Start:**
```
2025-09-11T20:42:20.462468Z [info] Creating payout
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '75db2fb1-d32f-4bbf-aba5-7a4f9852e703', 
       'user_id': '6771861b-e7bc-4af4-9d59-b5bc030d26d9', 
       'amount': '88', 'currency': 'ZAR', 
       'idempotency_key': 'payout_1757623337995_i76sofxcs'}
```

**Database Operations:**
```
2025-09-11T20:42:25.924266Z [info] Payout created in database
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '75db2fb1-d32f-4bbf-aba5-7a4f9852e703', 
       'payout_id': UUID('737447d9-24ee-4127-808a-2d526b07a387'), 
       'reference': 'PAY_D84D44A541F74C8E', 
       'status': <PayoutStatus.pending: 'pending'>}
```

## 3. Third-Party Provider Integration

**Provider Call Initiation:**
```
2025-09-11T20:42:25.942717Z [info] Processing payout with provider
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '75db2fb1-d32f-4bbf-aba5-7a4f9852e703', 
       'payout_id': UUID('737447d9-24ee-4127-808a-2d526b07a387'), 
       'amount': '88.00', 'currency': 'ZAR'}
```

**Provider Response:**
```
2025-09-11T20:42:26.307620Z [info] Mock provider: Creating payout
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '6d218581-0db9-4923-8ab3-82378a043880', 
       'payout_id': '737447d9-24ee-4127-808a-2d526b07a387', 
       'amount': '88.00', 'currency': 'ZAR', 
       'reference': 'PAY_D84D44A541F74C8E'}
```

**Note:** The provider generates its own correlation ID (`6d218581-0db9-4923-8ab3-82378a043880`) while maintaining the original for traceability.

## 4. Webhook Processing

**Webhook Scheduling:**
```
2025-09-11T20:42:28.967635Z [info] Mock provider: Scheduling webhook callback
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '6d218581-0db9-4923-8ab3-82378a043880', 
       'payout_id': '737447d9-24ee-4127-808a-2d526b07a387', 
       'provider_reference': 'mock_ref_573b61c44a5e484a', 
       'status': 'succeeded', 'delay_seconds': 9.387756629697954}
```

**Webhook Execution:**
```
2025-09-11T20:42:38.450558Z [info] Mock provider: Sending webhook callback
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '6d218581-0db9-4923-8ab3-82378a043880', 
       'payout_id': '737447d9-24ee-4127-808a-2d526b07a387', 
       'provider_reference': 'mock_ref_573b61c44a5e484a', 
       'status': 'succeeded', 
       'webhook_data': {'id': 'PAY_D84D44A541F74C8E', 
                       'provider_reference': 'mock_ref_573b61c44a5e484a', 
                       'status': 'succeeded', 
                       'timestamp': '2025-09-11T20:42:38.450558', 
                       'correlation_id': '6d218581-0db9-4923-8ab3-82378a043880'}}
```

**Webhook Processing:**
```
2025-09-11T20:42:38.483740Z [info] Processing webhook event
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
extra={'correlation_id': '6d218581-0db9-4923-8ab3-82378a043880', 
       'event_type': <WebhookEventType.PAYMENT_STATUS_CHANGED: 'payment.status_changed'>, 
       'event_id': 'mock_event_PAY_D84D44A541F74C8E_1757616158', 
       'payment_id': 'mock_ref_573b61c44a5e484a', 
       'reference': 'PAY_D84D44A541F74C8E', 'status': 'succeeded'}
```

## 5. Request Completion

**Final Response:**
```
2025-09-11T20:42:30.998918Z [info] request_completed
correlation_id=75db2fb1-d32f-4bbf-aba5-7a4f9852e703
method=POST process_time=11.3842 status_code=201 url=/payouts/
```

## 6. Frontend Response Processing

**Response Data:**
```json
{
  "id": "737447d9-24ee-4127-808a-2d526b07a387",
  "reference": "PAY_D84D44A541F74C8E",
  "amount": "88.00",
  "currency": "ZAR",
  "correlation_id": "75db2fb1-d32f-4bbf-aba5-7a4f9852e703",
  "status": "processing",
  "provider_reference": "mock_ref_573b61c44a5e484a",
  "created_at": "2025-09-11T20:42:20.390177Z",
  "updated_at": "2025-09-11T18:42:28.943264Z"
}
```

## Correlation ID Flow Diagram

```
Frontend Request
       ↓
   [75db2fb1...] → Backend API
       ↓
   [75db2fb1...] → Database Operations
       ↓
   [75db2fb1...] → Provider Service
       ↓
   [6d218581...] → Provider Processing
       ↓
   [6d218581...] → Webhook Callback
       ↓
   [75db2fb1...] → Webhook Processing
       ↓
   [75db2fb1...] → Response to Frontend
```

## Key Benefits Demonstrated

1. **End-to-End Tracing**: Single correlation ID tracks the entire payout lifecycle
2. **Cross-Service Correlation**: Provider generates its own ID while maintaining parent correlation
3. **Asynchronous Processing**: Webhook events maintain correlation with original request
4. **Error Debugging**: Any failure can be traced back to the original request
5. **Performance Monitoring**: Request duration tracked across all components

## Implementation Details

### Backend Middleware
- Generates correlation ID if not provided
- Propagates ID through all service calls
- Includes ID in all log entries
- Returns ID in response headers

### Frontend Integration
- Sends correlation ID in request headers
- Receives correlation ID in response
- Can use ID for client-side error tracking

### Provider Integration
- Maintains parent correlation ID
- Generates child correlation ID for internal tracking
- Includes both IDs in webhook payloads

### Database Operations
- All database operations include correlation ID
- Audit trails maintain correlation context
- Error logs include correlation for debugging

## Observability Benefits

1. **Request Tracing**: Complete request lifecycle visibility
2. **Performance Analysis**: Identify bottlenecks across services
3. **Error Correlation**: Link errors to specific user requests
4. **Business Metrics**: Track payout success rates by correlation
5. **Debugging**: Rapid issue resolution with full context

This correlation ID implementation provides comprehensive observability across all system boundaries, enabling effective monitoring, debugging, and performance optimization in our fintech application.
