
from datetime import datetime

from django.contrib.auth import get_user_model, authenticate
from drf_spectacular.utils import extend_schema
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CharField, IntegerField, BooleanField, SerializerMethodField, EmailField, \
    DateTimeField
from rest_framework.serializers import ModelSerializer, Serializer

from apps.models import User, Debt, Contact


class RegisterSerializer(ModelSerializer):
    password = CharField(max_length=10, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'fullname', 'phone_number']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            fullname=validated_data['fullname'] ,
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],

        )
        return user

    def to_representation(self, info):

        return {
            "success": True,
            "data": {
                "user": {
                    "id": info.id,
                    "email": info.email,
                    "fullname": info.fullname,
                    "phone_number": info.phone_number,
                },
            }
        }

class LoginSerializer(ModelSerializer):
    email = EmailField()
    password = CharField(write_only=True)
    class Meta:
        model = User
        fields = ['email', 'password']
    def validate(self, data):
        user = authenticate(email=data.get('email'), password=data.get('password'))
        if not user:
            raise ValidationError("noto'g'ri email yoki password")
        data['user'] = user
        return data



class OverdueDebtSerializer(ModelSerializer):
    contact_id = IntegerField(source='contact_id')
    contact_name = CharField(source='contact_name')
    is_overdue = BooleanField(source='is_overdue')
    days_until_due = SerializerMethodField()
    class Meta:
        model = Debt
        fields = ['id', 'contact_id', 'contact_name',
                  'debt_amount', 'is_overdue', 'days_until_due',
                  'description', 'is_my_debt', 'created_at', 'due_date',
                  'is_paid_back'

        ]
    def get_is_overdue(self, obj):
        return not obj.is_paid_back and obj.due_date > datetime.now(obj.due_date.tzinfo)

    def get_days_until_due(self, obj):
        difference_time = obj.due_date - datetime.now(obj.due_date.tzinfo)
        return difference_time.days




class ContactSerializer(ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'

class ContactUpdateSerializer(ModelSerializer):
    class Meta:
        model = Contact
        fields = 'fullname', 'phone_number'




class DebtModelSerializer(ModelSerializer):
    class Meta:
        model = Debt
        fields = 'contact', 'debt_amount', 'description', 'is_my_debt', 'due_date',
    def to_representation(self, instance):
        return {
            "success": True,
            "data": {
                "user": {
                    "id": instance.id,
                    'contact_name': instance.contact.fullname,
                    'description': instance.description,




                },
            }
        }


class MyDebtSerializer(ModelSerializer):
    contact_id = IntegerField(source='contact.id')
    contact_name = CharField(source='contact.name')
    debt_description = CharField(source='description')
    created_date = DateTimeField(source='created_at')
    days_until_due = SerializerMethodField()

    class Meta:
        model = Debt
        fields = [
            'id',
            'contact_id',
            'contact_name',
            'debt_amount',
            'debt_description',
            'is_my_debt',
            'created_date',
            'due_date',
            'is_paid_back',
            'is_overdue',
            'days_until_due',
        ]

    def get_days_until_due(self, obj):
        from datetime import date
        if obj.due_date:
            delta = (obj.due_date - date.today()).days
            return max(delta, 0)
        return None



class ContactModelSerializer(ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'

class SummaryModelSerializer(ModelSerializer):
    class Meta:
        model = Debt
        fields = 'contact',"debt_amount","is_my_debt","is_paid_back","is_overdue"

class CreateContactModelSerializer(ModelSerializer):
    class Meta:
        model = Contact
        fields = 'fullname', 'phone_number', 'user'
        extra_kwargs = {'user': {'read_only': True}}

    def validate(self, data):
        token = self.context['request'].headers.get('Authenticate')
        user = Token.objects.get(key=f"{token}")

        data['user'] = user
        return data

class ContactDebtModelSerializer(ModelSerializer):
        class Meta:
            model = Debt
            fields = 'contact', "debt_amount", "is_my_debt", "is_paid_back", "is_overdue"


class VerifyOTPSerializer(Serializer):
    email = EmailField()
    otp = CharField()

class ResendOTPSerializer(Serializer):
    email = EmailField()
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise ValidationError("Bunday email mavjud.")
        return value