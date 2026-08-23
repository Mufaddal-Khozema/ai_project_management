from __future__ import annotations

from enum import StrEnum


class Events(StrEnum):
    OTP_SEND = "otp:send"
    INTEGRATION_CONNECTED = "integration:connected"
    INTEGRATION_DISCONNECTED = "integration:disconnected"
    INTEGRATION_TOKEN_REFRESHED = "integration:token_refreshed"
    PAYMENT_CONFIRMATION = "payment:confirmation"
    RENEWAL_RECEIPT = "payment:renewal_receipt"
    TRIAL_EXPIRY_WARNING = "trial:expiry_warning"
    SUBSCRIPTION_CANCELLED = "subscription:cancelled"
    TOKEN_EXPIRY_WARNING = "integration:token_expiry_warning"
