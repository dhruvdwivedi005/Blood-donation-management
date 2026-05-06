from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.show_users),

    
    path('add-request/', views.add_request),
    path('', views.login_view),
    path('login/', views.login_view),
    path('user-dashboard/', views.user_dashboard),
    path('hospital-dashboard/', views.hospital_dashboard),
    path('signup/', views.signup_view),
    path('my-requests/', views.my_requests),
    path('my-donations/', views.my_donations),
    path('logout/', views.logout_view),
    path('add-donation/', views.add_donation),
    
    path('hospital-dashboard/', views.hospital_dashboard),
    path('hospital-requests/', views.hospital_requests),
    path('process/<int:req_id>/', views.process_request_view),
    path('hospital-donations/', views.hospital_donations),
    path('approve-donation/<int:d_id>/', views.approve_donation_view),
    path('blood-stock/', views.blood_stock_view),
]