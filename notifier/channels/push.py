"""Firebase Cloud Messaging (FCM) push notification channel.

Sends push notifications to user devices via Firebase Admin SDK.
Device tokens are managed per-user with platform info (iOS/Android).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PushChannel:
    """Sends push notifications via Firebase Cloud Messaging."""

    def __init__(self, project_id: str = "", credentials_path: str = "") -> None:
        self.project_id = project_id
        self.credentials_path = credentials_path
        self._initialized = False
        # TODO: initialise firebase_admin app with credentials

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    async def send(
        self,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send a push notification to a single device.

        Args:
            device_token: FCM device registration token.
            title: Notification title.
            body: Notification body text.
            data: Optional key-value payload for the app to process.

        Returns:
            True on success, False on failure.
        """
        # TODO: implement with firebase_admin.messaging
        # message = messaging.Message(
        #     notification=messaging.Notification(title=title, body=body),
        #     data={k: str(v) for k, v in (data or {}).items()},
        #     token=device_token,
        # )
        # response = messaging.send(message)
        raise NotImplementedError(
            "Firebase push notifications not yet implemented. "
            "Requires firebase-admin SDK and service account credentials."
        )

    async def send_to_user(
        self,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send a push notification to all devices registered for a user.

        Args:
            user_id: The user's ID (used to look up device tokens from DB).
            title: Notification title.
            body: Notification body text.
            data: Optional key-value payload.

        Returns:
            True if at least one device was notified successfully.
        """
        # TODO: query device tokens for user_id from database
        # tokens = await self._get_user_tokens(user_id)
        # results = [await self.send(token, title, body, data) for token in tokens]
        # return any(results)
        raise NotImplementedError(
            "User device token lookup not yet implemented. "
            "Requires database integration."
        )

    async def register_device(
        self,
        user_id: str,
        token: str,
        platform: str = "android",
    ) -> bool:
        """Register a device token for push notifications.

        Args:
            user_id: The user's ID.
            token: FCM registration token from the device.
            platform: Device platform ('android', 'ios', 'web').

        Returns:
            True on success.
        """
        # TODO: store token in database (user_id, token, platform, created_at)
        # Deduplicate: if token already exists for this user, update timestamp
        raise NotImplementedError(
            "Device registration not yet implemented. "
            "Requires database integration."
        )
