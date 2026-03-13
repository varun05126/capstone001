from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    grade = models.CharField(max_length=20)
    school = models.CharField(max_length=100)

    github = models.CharField(max_length=100, blank=True)
    leetcode = models.CharField(max_length=100, blank=True)
    codechef = models.CharField(max_length=100, blank=True)
    hackerrank = models.CharField(max_length=100, blank=True)

    last_updated = models.DateTimeField(auto_now=True)

    target_company = models.CharField(max_length=100, blank=True)
    target_role = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username
    