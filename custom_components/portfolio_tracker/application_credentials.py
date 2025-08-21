"""Application credentials platform for Portfolio Tracker."""
from __future__ import annotations

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import DOMAIN

AUTHORIZATION_SERVER = AuthorizationServer(
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
)


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AUTHORIZATION_SERVER


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return description placeholders."""
    return {
        "oauth_consent_url": (
            "https://console.cloud.google.com/apis/credentials/consent"
        ),
        "more_info_url": "https://developers.google.com/sheets/api/quickstart/python",
        "oauth_creds_url": "https://console.cloud.google.com/apis/credentials",
    }