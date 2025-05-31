import random
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db.models import Sum
from django.shortcuts import render
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import GenericAPIView, CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.models import Debt, Contact, User
from apps.serializers import RegisterSerializer, OverdueDebtSerializer, LoginSerializer, ContactSerializer, \
    DebtModelSerializer, MyDebtSerializer, ContactUpdateSerializer, SummaryModelSerializer, \
    CreateContactModelSerializer, VerifyOTPSerializer, ResendOTPSerializer
from root import settings


# Create your views here.

@extend_schema(
    tags=["Register Post"],
    request=RegisterSerializer,
    responses={201: RegisterSerializer}
)
class RegisterView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user =  serializer.save()
            return Response(serializer.to_representation(user), status=status.HTTP_201_CREATED)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["Login"],
    request=LoginSerializer,
    responses={200: {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "data": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "email": {"type": "string"},
                            "full_name": {"type": "string"},
                        }
                    },
                    "token": {"type": "string"},
                }
            }
        }
    }}
)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "success": True,
                "data": {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "fullname": user.fullname,
                    },
                    "token": token.key
                }
            }, status=status.HTTP_200_OK)

        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["Debt Overdue"])
class OverdueDebtListApiView(APIView):
    def post(self, request, *args, **kwargs):
        now = datetime.now()
        overdue_debts = Debt.objects.filter(is_paid_back=False, due_date__lte=now)
        serializer = OverdueDebtSerializer(overdue_debts, many=True)
        return  Response({
            "success": True,
            "data": {
                "debts": serializer.data,
            }
        }, status=status.HTTP_200_OK)

@extend_schema(tags=["Contacts"])
class ContactDeleteView(GenericAPIView):
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.all()

    def delete(self, request, id):
        queryset = self.get_queryset()
        try:
            contact = queryset.get(pk=id)
        except Contact.DoesNotExist:
            return Response({
                "success": False,
                "message": "Contact not found"
            }, status=status.HTTP_404_NOT_FOUND)

        if contact.debts.filter(is_active=True).exists():
            return Response({
                "success": False,
                "message": "Cannot delete contact with active debts"
            }, status=status.HTTP_400_BAD_REQUEST)

        contact.delete()
        return Response({
            "success": True,
            "message": "Contact deleted successfully"
        }, status=status.HTTP_200_OK)

@extend_schema(tags=["Contacts"])
class ContactListView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(name='search', type=str, required=False, description='Search by contact name'),

        ],
        responses={200: ContactSerializer(many=True)}
    )
    def get(self, request):
        search = request.query_params.get('search', '')
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))

        contacts = Contact.objects.filter(fullname__icontains=search)
        total = contacts.count()
        paginated_contacts = contacts[offset:offset + limit]

        serializer = ContactSerializer(paginated_contacts, many=True)
        return Response({
            'success': True,
            'data': {
                'contacts': serializer.data,
                'total': total
            }
        })


@extend_schema(tags=['Debt']
               )
class DebtCreateAPIView(CreateAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtModelSerializer

@extend_schema(tags=['Debt'])
class MyDebtAPIView(ListAPIView):
    serializer_class = MyDebtSerializer
    def get_queryset(self):
        return Debt.objects.filter(is_my_debt=True, contact__user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "success": True,
            "data": {
                "debts": serializer.data
            }
        })

@extend_schema(tags=['Contact'])
class UpdateContactView(UpdateAPIView):
    queryset = Contact.objects.all()
    serializer_class = ContactUpdateSerializer

@extend_schema(tags=['debt'])
class DebtCreateAPIView(CreateAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtModelSerializer


@extend_schema(tags=['Payments'])
class PaymentHistoryListAPIView(ListAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtModelSerializer

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'data': {"payments": [serializer.data]},
                'message': 'Payment history retrieved successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'data': [],
                'message': f'Error retrieving payment history: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Payments'])
class PaymentsTheirListAPIview(ListAPIView):
    queryset = Debt.objects.all()
    serializer_class = DebtModelSerializer

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'success': True,
                'data': {"payments": [serializer.data]},
                'message': 'Payment history retrieved successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'data': [],
                'message': f'Error retrieving payment history: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
            l


@extend_schema(tags=['Payments'])
class PaymentAmountListAPIView(ListAPIView):
    serializer_class = DebtModelSerializer

    def get_queryset(self):
        # Faqat to'langan qarzlar va foydalanuvchiga tegishli ma'lumotlarni filtrlaydi
        return Debt.objects.filter(is_paid_back=True, contact__user=self.request.user).select_related('contact')

    def list(self, request, *args, **kwargs):
        try:
            # Foydalanuvchi autentifikatsiya qilinganligini tekshirish (qo'shimcha xavfsizlik)
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'message': 'Invalid or missing authentication token',
                    'error_code': 'UNAUTHORIZED',
                    'errors': {}
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Querysetni olish
            queryset = self.filter_queryset(self.get_queryset())

            # Agar hech qanday qarz topilmasa
            if not queryset.exists():
                return Response({
                    'success': False,
                    'message': 'No payment history found',
                    'error_code': 'PAYMENT_HISTORY_NOT_FOUND',
                    'errors': {}
                }, status=status.HTTP_404_NOT_FOUND)
                # Sahifalashni qo'llash
                page = self.paginate_queryset(queryset)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    payments_data = serializer.data
                else:
                    serializer = self.get_serializer(queryset, many=True)
                    payments_data = serializer.data

                # Umumiy statistikani hisoblash
                summary = self.calculate_summary(request.user)

                # Javobni tayyorlash
                response_data = {
                    'success': True,
                    'data': {
                        'payments': payments_data,
                        'summary': summary,
                        'total': len(payments_data)
                    }
                }
                return Response(response_data, status=status.HTTP_200_OK)


        except ValueError as ve:
            # Validatsiya xatolari uchun (masalan, noto'g'ri ma'lumot kiritilgan bo'lsa)
            return Response({
                'success': False,
                'message': 'Validation failed',
                'error_code': 'VALIDATION_FAILED',
                'errors': {'general': [str(ve)]}
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Umumiy xatolar uchun
            return Response({
                'success': False,
                'message': f'Error retrieving payment history: {str(e)}',
                'error_code': 'INTERNAL_SERVER_ERROR',
                'errors': {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calculate_summary(self, user):
        # Foydalanuvchiga tegishli to'langan qarzlar
        debts = Debt.objects.filter(contact__user=user, is_paid_back=True)

        # Men to'lagan qarzlar (is_my_debt=True)
        total_paid_by_me = debts.filter(is_my_debt=True).aggregate(
            total=Sum('debt_amount')
        )['total'] or Decimal('0.00')

        # Menga to'langan qarzlar (is_my_debt=False)
        total_paid_to_me = debts.filter(is_my_debt=False).aggregate(
            total=Sum('debt_amount')
        )['total'] or Decimal('0.00')

        total_payments_count = debts.count()

        return {
            'total_paid_by_me': float(total_paid_by_me),
            'total_paid_to_me': float(total_paid_to_me),
            'total_payments_count': total_payments_count
        }
from rest_framework.authtoken.models import Token
@extend_schema(tags=["debt"]
               )
class SummaryListAPIView(ListAPIView):
    queryset = Debt.objects.all()
    serializer_class = SummaryModelSerializer


    def get_queryset(self):
        print(self.request)
        user = Token.objects.get(key=f"{self.request.headers.get('Authenticate')}").user
        return super().get_queryset().filter(contact__user__pk = user.pk)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        active_debts_count = 0
        overdue_debts_count = 0
        total_i_owe = 0
        total_they_owe = 0
        data_summary = {}
        data = serializer.data

        for i in data:
            if i.get("is_overdue"):
                active_debts_count += 1
            else:
                overdue_debts_count += 1

            if i.get("is_my_debt"):
                total_i_owe += float(i.get("debt_amount"))
            else:
                total_they_owe += float(i.get("debt_amount"))
        data_summary["total_i_owe"] = total_i_owe
        data_summary["total_they_owe"] = total_they_owe
        data_summary["active_debts_count"] = active_debts_count
        data_summary["overdue_debts_count"] = overdue_debts_count
        return Response(data_summary)

@extend_schema(tags=["debt"],
              responses={200: CreateContactModelSerializer(many=True)})
class ContactCreateAPIView(CreateAPIView):
    queryset = Contact.objects.all()
    serializer_class = CreateContactModelSerializer
    def perform_create(self, serializer):
        user = Token.objects.get(key=f"{self.request.headers.get('Authenticate')}").user
        serializer.save(user=user)

# from rest_framework.authtoken.models import Token
# user = Token.objects.get(key='token string').user





from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView,ListAPIView
from rest_framework import status
from datetime import date, datetime, timedelta
from apps.models import Debt
from apps.serializers import DebtModelSerializer, ContactDebtModelSerializer

@extend_schema(tags=['debt']
               )
class DebtListAPIView(ListAPIView):
    serializer_class = DebtModelSerializer

    def get_queryset(self):
        user = Token.objects.get(key=f"{self.request.headers.get('Authenticate')}").user
        return Debt.objects.filter(contact__user = user)


    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        datas = []
        active_debts_count = 0
        overdue_debts_count = 0
        total_i_owe = 0
        total_they_owe = 0
        data_summary = {}
        for i in data:
            if i.get("is_overdue"):
                active_debts_count +=1
            else:
                overdue_debts_count+=1

            if i.get("is_my_debt"):
                total_i_owe += float(i.get("debt_amount"))
            else:
                total_they_owe += float(i.get("debt_amount"))


            due = i.get("due_date")
            due_date = datetime.fromisoformat(due).date()
            total = due_date-date.today()
            response_data = {
                "success": True,
                "data":{
                "debts": i ,
                "summary":data_summary,
                "total":total.days
            }
            }
            data_summary["total_i_owe"] = total_i_owe
            data_summary["total_they_owe"] = total_they_owe
            data_summary["active_debts_count"] = active_debts_count
            data_summary["overdue_debts_count"] = overdue_debts_count
            datas.append(response_data)
        return Response(datas)

@extend_schema(tags=["debt"])
class ContactDebtListAPIView(ListAPIView):
    serializer_class = ContactDebtModelSerializer


    def get_queryset(self):
        pk = self.kwargs.get("pk")
        return Debt.objects.filter(contact_id = pk)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        total_i_owe = 0
        total_they_owe = 0
        data_summary = {}
        data = serializer.data

        for i in data:
            if i.get("is_my_debt"):
                total_i_owe += float(i.get("debt_amount"))
            else:
                total_they_owe += float(i.get("debt_amount"))
        data_summary["total_i_owe"] = total_i_owe
        data_summary["total_they_owe"] = total_they_owe
        return Response(data_summary)



from django.core.cache import cache


@extend_schema(
    tags=['Auth'],
    request=RegisterSerializer,
    responses={200: OpenApiResponse(description='OTP kod emailga yuborildi'),
               400: OpenApiResponse(description='Xatolik roʻy berdi')},
    examples=[
        OpenApiExample(
            'Roʻyxatdan oʻtish uchun misol',
            value={
                "email": "user@example.com",
                "phone_number": "user123",
                "password": "secret123",
                "fullname": "Ali"
            },
            request_only=True
        )
    ]
)
class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            first_name = serializer.validated_data['fullname']
            username = serializer.validated_data['phone_number']

            otp = str(random.randint(100000, 999999))

            cache.set(f"register:{email}", {
                'email': email,
                'username': username,
                'password': password,
                'first_name': first_name,
                'otp': otp,
            }, timeout=480)

            send_mail(
                subject="Ro'yxatdan o'tish uchun OTP kodi",
                message=f"Sizning tasdiqlash kodingiz: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({'message': 'OTP kod emailga yuborildi'}, status=status.HTTP_200_OK)
        return Response({'message':'email yoki passwordda xatolik mavjud'}, status=status.HTTP_400_BAD_REQUEST)



@extend_schema(
tags=['Auth'],
    request=VerifyOTPSerializer,
    responses={
        201: OpenApiResponse(description='Foydalanuvchi muvaffaqiyatli yaratildi'),
        400: OpenApiResponse(description='Xatolik: noto‘g‘ri email yoki OTP')
    },
    examples=[
        OpenApiExample(
            'Tasdiqlash uchun misol',
            value={"email": "user@example.com", "otp": "123456"},
            request_only=True
        )
    ]
)
class VerifyRegisterAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({'error': 'Email va OTP kerak.'}, status=400)

        cached_data = cache.get(f"register:{email}")
        if not cached_data:
            return Response({'error': 'Maʼlumot topilmadi yoki muddati tugagan.'}, status=400)

        if cached_data['otp'] != otp:
            return Response({'error': 'OTP noto‘g‘ri.'}, status=400)

        user = User.objects.create(
            email=cached_data['email'],
            password=make_password(cached_data['password']),
            first_name=cached_data['fullname']
        )
        cache.delete(f"register:{email}")

        return Response({'message': 'Foydalanuvchi muvaffaqiyatli yaratildi.'}, status=201)


@extend_schema(
tags=['Auth'],
    request=ResendOTPSerializer,
    responses={
        201: OpenApiResponse(description='Foydalanuvchi muvaffaqiyatli yaratildi'),
        400: OpenApiResponse(description='Xatolik: noto‘g‘ri email yoki OTP')
    },
    examples=[
        OpenApiExample(
            'Tasdiqlash uchun misol',
            value={"email": "user@example.com",},
            request_only=True
        )
    ]
)
class ResendAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = str(random.randint(100000, 999999))
            cache.set(f"forgetpassword:{email}", {
                'email': email,
                'otp': otp,
            }, timeout=480)
            send_mail(
                subject="Parolni yangilash uchun tasdiqlash uchun OTP kodi",
                message=f"Sizning tasdiqlash kodingiz: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
            )
            return Response({'message': 'OTP kod emailga yuborildi'}, status=status.HTTP_200_OK)
        return Response({'message':'Bunday email mavjud'}, status=status.HTTP_400_BAD_REQUEST)