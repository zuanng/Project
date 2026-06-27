from django.urls import path
from . import views

app_name = "reservations"

urlpatterns = [
    path("book/", views.reservation_create, name="reservation_create"),
    path("my-reservations/", views.reservation_list, name="reservation_list"),
    path(
        "reservation/<str:reservation_number>/",
        views.reservation_detail,
        name="reservation_detail",
    ),
    path(
        "reservation/<str:reservation_number>/cancel/",
        views.cancel_reservation,
        name="cancel_reservation",
    ),
]
