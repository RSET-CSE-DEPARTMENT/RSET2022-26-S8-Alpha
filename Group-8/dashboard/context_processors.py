from django.utils import timezone
from .models import Task


def notifications(request):
    """
    Context processor to add notification data to all templates.
    Returns pending tasks with overdue status.
    """
    if request.user.is_authenticated:
        now = timezone.now()
        
        # Get all pending tasks for the user
        pending_tasks = Task.objects.filter(
            user=request.user,
            completed=False
        ).order_by('due_date')[:10]  # Limit to 10 most urgent
        
        # Separate overdue and upcoming tasks
        overdue_tasks = []
        upcoming_tasks = []
        
        for task in pending_tasks:
            if task.due_date < now:
                overdue_tasks.append(task)
            else:
                upcoming_tasks.append(task)
        
        notification_count = len(pending_tasks)
        
        return {
            'notification_count': notification_count,
            'overdue_tasks': overdue_tasks,
            'upcoming_tasks': upcoming_tasks,
            'has_overdue': len(overdue_tasks) > 0,
        }
    
    return {
        'notification_count': 0,
        'overdue_tasks': [],
        'upcoming_tasks': [],
        'has_overdue': False,
    }
