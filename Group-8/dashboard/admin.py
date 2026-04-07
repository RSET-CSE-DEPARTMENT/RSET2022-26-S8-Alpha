# dashboard/admin.py
from django.contrib import admin
from .models import Task, JournalEntry

admin.site.register(Task)
admin.site.register(JournalEntry)
