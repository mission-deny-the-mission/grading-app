# API Documentation - Multi-User Authentication System

## Overview

This document provides comprehensive API documentation for the optional multi-user authentication system. The system supports two deployment modes:

- **Single-User Mode**: No authentication required, direct access to all features
- **Multi-User Mode**: Full authentication, user management, project sharing, and usage quotas

## Base URLs

- API Base: `/api`
- Authentication: `/api/auth`
- Admin: `/api/admin`
- Configuration: `/api/config`
- Sharing: `/api/sharing`
- Usage: `/api/usage`

## Authentication

All multi-user mode API requests require authentication via session cookies. Responses use standardized formats.

### Login

**Endpoint:** `POST /api/auth/login`

**Rate Limit:** 10 requests per 15 minutes

**Request:**
```json
{
  "email": "user@example.com",
  "password": "Password123!"
}
```

**Response (Success):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "User Name",
    "is_admin": false,
    "created_at": "2025-01-15T10:00:00Z"
  }
}
```

**Error Responses:**
- `400` - Invalid credentials or missing fields
- `429` - Too many login attempts

### Register

**Endpoint:** `POST /api/auth/register`

**Rate Limit:** 5 requests per hour

**Request:**
```json
{
  "email": "newuser@example.com",
  "password": "Password123!",
  "display_name": "New User"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character

**Response (Success):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "newuser@example.com",
    "display_name": "New User",
    "is_admin": false
  }
}
```

### Logout

**Endpoint:** `POST /api/auth/logout`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

### Get Current User

**Endpoint:** `GET /api/auth/user`

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "display_name": "User Name",
    "is_admin": false
  }
}
```

### Password Reset Request

**Endpoint:** `POST /api/auth/password-reset`

**Rate Limit:** 3 requests per hour

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset instructions sent to email"
}
```

## Admin Endpoints

All admin endpoints require authenticated admin user.

### List Users

**Endpoint:** `GET /api/admin/users`

**Rate Limit:** 50 requests per hour

**Query Parameters:**
- `limit` (optional, default 100): Maximum users to return
- `offset` (optional, default 0): Pagination offset

**Response:**
```json
{
  "success": true,
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "display_name": "User Name",
      "is_admin": false,
      "is_active": true,
      "created_at": "2025-01-15T10:00:00Z"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

### Update User

**Endpoint:** `PUT /api/admin/users/<user_id>`

**Request:**
```json
{
  "display_name": "Updated Name",
  "is_active": true
}
```

### Delete User

**Endpoint:** `DELETE /api/admin/users/<user_id>`

**Response:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

## Configuration Endpoints

### Get Deployment Mode

**Endpoint:** `GET /api/config/deployment-mode`

**Response:**
```json
{
  "mode": "multi-user",
  "authentication_required": true
}
```

## Project Sharing Endpoints

### Share Project

**Endpoint:** `POST /api/sharing/projects/<project_id>/share`

**Request:**
```json
{
  "user_email": "collaborator@example.com",
  "permission_level": "read"
}
```

**Permission Levels:**
- `read`: View only access
- `write`: Edit and modify access

**Response:**
```json
{
  "success": true,
  "share": {
    "project_id": "uuid",
    "user_email": "collaborator@example.com",
    "permission_level": "read",
    "granted_at": "2025-01-15T10:00:00Z"
  }
}
```

### Get Project Shares

**Endpoint:** `GET /api/sharing/projects/<project_id>/shares`

**Response:**
```json
{
  "success": true,
  "shares": [
    {
      "user_email": "user@example.com",
      "permission_level": "read",
      "granted_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### Revoke Share

**Endpoint:** `DELETE /api/sharing/projects/<project_id>/shares/<user_id>`

**Response:**
```json
{
  "success": true,
  "message": "Share revoked successfully"
}
```

## Usage Tracking Endpoints

### Get User Usage

**Endpoint:** `GET /api/usage/stats`

**Query Parameters:**
- `provider` (optional): Filter by AI provider
- `start_date` (optional): ISO 8601 date
- `end_date` (optional): ISO 8601 date

**Response:**
```json
{
  "success": true,
  "usage": {
    "tokens_consumed": 125000,
    "quota_limit": 100000,
    "percentage_used": 125.0,
    "over_quota": true
  },
  "breakdown": [
    {
      "provider": "openrouter",
      "tokens_consumed": 75000,
      "requests": 150
    }
  ]
}
```

### Get Usage History

**Endpoint:** `GET /api/usage/history`

**Response:**
```json
{
  "success": true,
  "records": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "provider": "openrouter",
      "tokens_consumed": 1000,
      "operation_type": "grading",
      "model_name": "anthropic/claude-3-5-sonnet"
    }
  ]
}
```

## Error Response Format

All errors follow this standardized format:

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "details": {}
}
```

### Error Codes

- `VALIDATION_ERROR`: Input validation failed
- `AUTHENTICATION_FAILED`: Login credentials invalid
- `NOT_FOUND`: Resource doesn't exist
- `FORBIDDEN`: No permission to access resource
- `CONFLICT`: Duplicate resource or constraint violation
- `INTERNAL_ERROR`: Server error
- `RATE_LIMITED`: Too many requests
- `QUOTA_EXCEEDED`: Usage quota exceeded

## Rate Limiting

All endpoints have rate limits enforced. When exceeded, returns:

**Status Code:** `429 Too Many Requests`

**Response:**
```json
{
  "error": "RATE_LIMITED",
  "message": "Too many requests. Please try again later.",
  "retry_after": 300
}
```

**Headers:**
- `Retry-After`: Seconds until rate limit resets

## Security Headers

All responses include security headers:
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (HTTPS only)

## Testing

Use the test client:

```python
# Single-user mode
response = client.get("/")  # No auth needed

# Multi-user mode
response = client.post("/api/auth/login", json={
    "email": "test@example.com",
    "password": "Password123!"
})
response = client.get("/api/auth/user")
```

## Support

For issues or questions, see the deployment guide and user documentation.
