"""Firebase Cloud Messaging (FCM) push notification adapter.

Sends push notifications to mobile devices via Firebase.  Used for
the React Native / Expo mobile app.

Dependencies: firebase-admin (or direct FCM HTTP v1 API calls)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FirebasePush:
    """Send push notifications via Firebase Cloud Messaging.

    Parameters
    ----------
    credentials_path : str
        Path to the Firebase service account JSON file.
    project_id : str
        Firebase project ID.
    """

    def __init__(
        self,
        credentials_path: str = "",
        project_id: str = "",
    ) -> None:
        self._credentials_path = credentials_path
        self._project_id = project_id
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize the Firebase Admin SDK.

        Loads credentials and sets up the FCM client.
        Must be called before sending any notifications.
        """
        raise NotImplementedError("FirebasePush.initialize() not yet implemented")

    # ------------------------------------------------------------------
    # Device-targeted notifications
    # ------------------------------------------------------------------

    async def send_push(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a push notification to a specific device.

        Parameters
        ----------
        device_token : str
            FCM registration token for the target device.
        title : str
            Notification title.
        body : str
            Notification body text.
        data : dict | None
            Optional key-value data payload (all values must be strings).

        Returns
        -------
        dict
            FCM send response including message_id.
        """
        raise NotImplementedError("FirebasePush.send_push() not yet implemented")

    # ------------------------------------------------------------------
    # Topic-targeted notifications
    # ------------------------------------------------------------------

    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a push notification to all devices subscribed to a topic.

        Parameters
        ----------
        topic : str
            FCM topic name, e.g. "trade_alerts", "daily_reports".
        title : str
            Notification title.
        body : str
            Notification body text.
        data : dict | None
            Optional key-value data payload.

        Returns
        -------
        dict
            FCM send response.
        """
        raise NotImplementedError("FirebasePush.send_to_topic() not yet implemented")
