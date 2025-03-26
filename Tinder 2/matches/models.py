from django.db import models
from authentication.models import UserProfile
from requests.models import HelpRequest

class Like(models.Model):
    """
    Represents when a user "likes" another user's profile
    or a volunteer "likes" a help request
    """
    from_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='likes_given')
    to_user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='likes_received')
    request = models.ForeignKey(HelpRequest, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user', 'request')
    
    def __str__(self):
        if self.request:
            return f"{self.from_user.user.username} liked {self.to_user.user.username}'s request: {self.request.title}"
        return f"{self.from_user.user.username} liked {self.to_user.user.username}"

class Match(models.Model):
    """
    Represents a mutual match between users
    Created when both users have liked each other
    """
    military_user = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='military_matches',
        limit_choices_to={'role': 'military'}
    )
    volunteer_user = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='volunteer_matches',
        limit_choices_to={'role': 'volunteer'}
    )
    request = models.ForeignKey(HelpRequest, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('military_user', 'volunteer_user', 'request')
    
    def __str__(self):
        return f"Match: {self.military_user.user.username} and {self.volunteer_user.user.username}"