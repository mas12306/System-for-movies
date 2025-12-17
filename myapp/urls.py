"""
URL configuration for DjangoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_user, name='login'),
    path('register/', views.register_user, name='register'),
    path('logout/', views.logout_user, name='logout'),
    path('top/', views.top_list, name='top'),
    path('movies/', views.movie_list, name='movie_list'),
    path('movies/<int:pk>/', views.movie_detail, name='movie_detail'),
    path('movies/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('movies/<int:pk>/rate/', views.rate_movie, name='rate_movie'),
    path('movies/<int:pk>/favorite/ajax/', views.toggle_favorite_api, name='toggle_favorite_api'),
    path('movies/<int:pk>/rate/ajax/', views.rate_movie_api, name='rate_movie_api'),
    path('movies/<int:pk>/comment/', views.submit_comment, name='submit_comment'),
    path('recommend/', views.recommend_view, name='recommend'),
    path('api/recommend/', views.recommend_api, name='recommend_api'),
    path('api/ai-recommend/', views.ai_recommend_api, name='ai_recommend_api'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/password/', views.profile_password, name='profile_password'),
    path('profile/stats/', views.user_stats, name='user_stats'),
]
