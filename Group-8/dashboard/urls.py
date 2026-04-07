from django.urls import path,include
from . import views
from .views import ColourfulLoginView

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', ColourfulLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('select-mode/', views.select_mode, name='select_mode'),
    path('todo/', views.todo_list, name='todo_list'),
    path('todo/add/', views.add_task, name='add_task'),
    path('todo/complete/<int:task_id>/', views.complete_task, name='complete_task'),
    path('todo/delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('game/', views.game_page, name='game_page'),
    path('memory-game/', views.memory_game, name='memory_game'),
    path('breathing-exercise/', views.breathing_exercise, name='breathing_exercise'),
    path('voice/', views.voice, name='voice'),
    path('journal/mode/', views.journal_mode_select, name='journal_mode_select'),
    path('journal/method/', views.journal_method_select, name='journal_method_select'),
    path('journal/', views.journal, name='journal'),
    path('journal/delete/<int:entry_id>/', views.delete_entry, name='delete_entry'),
    path('transcribe/', views.transcribe_view, name='transcribe'),
    path('save-voice-entry/', views.save_voice_entry, name='save_voice_entry'),
    path('generate-from-keywords/', views.generate_from_keywords, name='generate_from_keywords'),
    path('save-custom-names/', views.save_custom_names, name='save_custom_names'),
    path("nlp/", include("echoapp.urls")),
    
]
