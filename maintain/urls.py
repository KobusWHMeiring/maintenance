from django.urls import path
from maintain import views

urlpatterns = [
    # 1. Landing page is now the root URL of the app
    path('', views.index, name='landing_page'), 
    
    # 2. The wizard starts at its own dedicated URL
    path('start/', views.claim_wizard, name='wizard_start'),

    path('summary/', views.summary_page, name='summary_page'),
    path('generate_pdf/', views.generate_pdf, name='generate_pdf'),
    path('dev-autofill/', views.dev_autofill_and_redirect, name='dev_autofill'),
     path('downloads/', views.downloads_page, name='downloads_page'),
]