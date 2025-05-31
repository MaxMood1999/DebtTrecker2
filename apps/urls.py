from django.urls import path

from apps.views import RegisterView, OverdueDebtListApiView, LoginView, ContactDeleteView, ContactListView, \
    DebtCreateAPIView, MyDebtAPIView, UpdateContactView, PaymentHistoryListAPIView, PaymentsTheirListAPIview, \
    PaymentAmountListAPIView, SummaryListAPIView, ContactCreateAPIView, DebtListAPIView, ContactDebtListAPIView, \
    RegisterAPIView, VerifyRegisterAPIView, ResendAPIView

urlpatterns = [
    path('auth/register', RegisterAPIView.as_view(), name='auth-register'),
    path('auth/verify-email', VerifyRegisterAPIView.as_view()),
    path('auth/resend', ResendAPIView.as_view()),
    path('auth/login', LoginView.as_view(), name='login'),


#=====Contacts==============================
    path("contact/debt/<int:pk>", ContactDebtListAPIView.as_view()),
    path('contacts/delete/<int:id>', ContactDeleteView.as_view(), name='delete-contact'),
    path('contacts/', ContactListView.as_view(), name='contact-list'),
    path("add/contacts", ContactCreateAPIView.as_view()),
    path('contact-update/<int:id>', UpdateContactView.as_view(), name='contact-update'),

#======Debts=======================================
    path("debt/<int:pk>",DebtListAPIView.as_view(),name="debt-list"),
    path('my-debts/', MyDebtAPIView.as_view(), name='my-debts'),
    path('payments', PaymentHistoryListAPIView.as_view(), name='payment_history'),
    path('payments/their-payments', PaymentsTheirListAPIview.as_view(), name='payments_their'),
    path('payments/amount', PaymentAmountListAPIView.as_view(), name='payment_amount'),
    path("debts/summary",SummaryListAPIView.as_view(),name="summary-list"),
    path('debts', DebtCreateAPIView.as_view(), name='debt-create'),
    path("debts/overdue", OverdueDebtListApiView.as_view(), name="debt-overdue"),
]