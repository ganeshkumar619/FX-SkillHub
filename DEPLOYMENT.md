# FX SkillHub Production Deployment & Email Architecture Guide

This guide outlines the production deployment setup for FX SkillHub on Render, including the migration to the Resend HTTPS API for reliable email delivery.

---

## 1. Network Constraints & Email Architecture

### Confirmed Platform Behavior on Render
- **Outbound Direct SMTP (Ports 25, 465, 587)**: Blocked at the container network egress level by Render's security firewall. Direct TCP connections to `smtp.gmail.com:587` fail with `[Errno 101] Network is unreachable` or `Connection timed out`.
- **Outbound HTTPS (Port 443)**: Fully functional and open. Live latency to `api.resend.com:443` is ~14ms.

### Production Solution: Resend HTTPS API
FX SkillHub uses `django-anymail[resend]` to route all transactional emails (student OTPs, faculty activations, and certificate PDFs) via **HTTPS REST POST requests to `https://api.resend.com/emails` over port 443**.

---

## 2. Required Render Environment Variables

To activate production email delivery, configure the following environment variables in the **Render Dashboard → Backend Web Service → Environment**:

| Variable Name | Required | Example Value | Purpose |
| :--- | :---: | :--- | :--- |
| `EMAIL_BACKEND` | **Yes** | `anymail.backends.resend.EmailBackend` | Selects Resend HTTPS API email backend |
| `ANYMAIL_RESEND_API_KEY` | **Yes** | `re_123456789_abcdef...` | Your Resend API Key from [resend.com/api-keys](https://resend.com/api-keys) |
| `DEFAULT_FROM_EMAIL` | **Yes** | `FX SkillHub <onboarding@resend.dev>` *(or your verified domain sender)* | From header for all system emails |
| `FRONTEND_URL` | **Yes** | `https://fx-skillhub-frontend.onrender.com` | Used for QR verification, activation links & CORS |
| `PUBLIC_PORTAL_URL` | **Yes** | `https://fx-skillhub-frontend.onrender.com` | Base public URL |
| `EMAIL_TIMEOUT` | No | `10` | Request timeout in seconds |

> [!NOTE]
> For initial testing or before custom domain DNS verification on Resend, you can use:  
> `DEFAULT_FROM_EMAIL=FX SkillHub <onboarding@resend.dev>`  
> When testing with `onboarding@resend.dev`, Resend allows sending to the email address registered with your Resend account. Once your college/institution domain (e.g. `francisxavier.ac.in`) is verified in Resend Domains, set:  
> `DEFAULT_FROM_EMAIL=FX SkillHub <skills@francisxavier.ac.in>` (or any address on your verified domain).

---

## 3. Verification Endpoints

Once deployed and configured with `ANYMAIL_RESEND_API_KEY`, verify the system using these endpoints:

### A. Check Email Status & Configuration
```http
GET https://fx-skillhub.onrender.com/api/notifications/status/
```
Expected Healthy Output:
```json
{
  "status": "healthy",
  "email_backend": "anymail.backends.resend.EmailBackend",
  "resend_api_key_configured": true,
  "sender_configured": true,
  "https_api_connectivity": true,
  "default_from_email": "FX SkillHub <...>",
  "error_type": null,
  "error_message": null,
  "latency_ms": 25,
  "recommendations": []
}
```

### B. Network Egress Probe
```http
GET https://fx-skillhub.onrender.com/api/notifications/network-audit/
```
Confirms DNS resolution and raw TCP socket status across all email ports.

### C. Admin Live Test Dispatch
```http
POST https://fx-skillhub.onrender.com/api/notifications/test-email/
Authorization: Bearer <ADMIN_JWT_TOKEN>
Content-Type: application/json

{
  "recipient": "your-email@example.com"
}
```

---

## 4. Email Flows Supported

All existing business logic and Django standard email abstractions are preserved without modification:
1. **Student Registration OTP**: 6-digit verification code with 10-minute expiry and rate limiting.
2. **OTP Resend**: Cooldown protected email verification resend.
3. **Faculty Account Creation / Invitation**: Activation link using `FRONTEND_URL/activate-faculty/`.
4. **Faculty Invitation Resend**: Admin-triggered invitation resend.
5. **Course Completion Certificate**: Automatic digital certificate generation with attached PDF (`reportlab`) and online QR verification.
