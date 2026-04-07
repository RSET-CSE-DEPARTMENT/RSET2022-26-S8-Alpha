from django.urls import path
from . import views

app_name = "echoapp"

urlpatterns = [
    path("", views.nlp_demo, name="nlp_demo"),
    path("keyword-to-sentence/", views.nlp_demo, name="keyword_to_sentence"),
]
