from django.contrib.auth.models import User
from django.db import models

# User class extensions
def user_unicode(self):
    """Use email address for string representation of user."""
    return self.email
User.add_to_class('__unicode__', user_unicode)

class Scan(models.Model):
    scan_id = models.CharField(max_length=100, primary_key = True)
    scan_creator = models.CharField(max_length=150)
    scan_date = models.DateTimeField(auto_now_add=True)
    scan_url = models.URLField()
    scan_plan = models.CharField(max_length=100)
