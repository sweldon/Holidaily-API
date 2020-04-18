"""Temporary one-off to set up image names"""

from django.core.management.base import BaseCommand
from django.db.models import Sum

from api.models import UserProfile, Comment


class Command(BaseCommand):
    def handle(self, *args, **options):
        all_users = UserProfile.objects.all()
        for u in all_users:
            points = u.rewards
            comment_votes = Comment.objects.filter(user=u.user).aggregate(Sum("votes"))
            if comment_votes["votes__sum"]:
                comment_points = (
                    comment_votes["votes__sum"]
                    if comment_votes["votes__sum"] > 0
                    else 0
                )
            else:
                comment_points = 0
            points += comment_points
            u.confetti = points
            u.save()
