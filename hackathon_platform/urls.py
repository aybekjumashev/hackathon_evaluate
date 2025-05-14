# hackathon_platform/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from judging import views as judging_views
from django.conf.urls.i18n import i18n_patterns # <--- ҚЎШИНГ
from django.views.i18n import set_language as set_language_view # <--- ҚЎШИНГ

urlpatterns = [
    path('final/admin/', admin.site.urls),
    path('final/i18n/setlang/', set_language_view, name='set_language'), # <--- Тил алмаштириш учун URL
    
    # Тил префиксисиз ишлайдиган URL'лар (масалан, API)
    # Эслатма: public_results_api_view дан қайтадиган маълумотлар (team.name, direction.name, criterion.name)
    # хозирги холатда базадан олинган тилда бўлади. Уларни хам таржима қилиш кейинги босқичларда кўриб чиқилади.
    path('final/api/results/', judging_views.public_results_api_view, name='public_results_api'),
    path('final/api/team-details/<int:team_id>/', judging_views.team_evaluation_details_api_view, name='team_evaluation_details_api'),
]

# Тил префикси билан ишлайдиган URL'лар
urlpatterns += i18n_patterns(
    path('final/accounts/login/', auth_views.LoginView.as_view(template_name='judging/login.html'), name='login'),
    path('final/accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('final/evaluate/', judging_views.evaluate_view, name='evaluate'),
    path('final/', judging_views.public_results_view, name='public_results'), # Бош саҳифа
    path('final/evaluate/<int:team_id>/', judging_views.evaluate_team_view, name='evaluate_team'),
    path('final/qr/', judging_views.qr_code_view, name='qr_code'),
    
    prefix_default_language=False 
)