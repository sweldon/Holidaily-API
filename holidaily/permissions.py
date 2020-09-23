from rest_framework.permissions import BasePermission

from api.models import UserProfile, Comment
from logging import getLogger

logger = getLogger(__name__)


class UpdateObjectPermission(BasePermission):
    """
    Only allow update on object if device id and profile are valid,
    and the device that created the object is the device editing
    """

    def has_object_permission(self, request, view, update_object):

        # Allow report patch from anyone, vote is legacy and should become 'like'
        if (
            request.data.get("report", None)
            or request.data.get("like")
            or request.data.get("vote")
        ):
            return True

        device_id = request.data.get("device_id", None)
        username = request.data.get("username", None)

        if not device_id or not username:
            # TODO legacy, <2.0 not sending device_id/username for comment detail
            if isinstance(update_object, Comment):
                return True
            logger.warning(
                f"Device/user not found for {type(update_object)} update: {device_id}/{username}"
            )
            return False

        device_profile = UserProfile.objects.filter(
            user__username=username, device_id=device_id
        ).first()
        if not device_profile:
            logger.warning(
                f"Profile not found for device/user {device_id}/{username} on {type(update_object)} update"
            )
            return False

        device_user = device_profile.user.id
        object_user = update_object.user.id
        if device_user != object_user:
            logger.warning(
                f"Rejected {type(update_object)} update, does not belong to {username}"
            )
            return False
        return True
