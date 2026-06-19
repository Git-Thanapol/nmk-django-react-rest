from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Note

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}} # Password should not be readable

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data) # Use create_user to hash the password
        return user
    
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'user', 'title', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at'] # user will be set from request, timestamps are read-only
        extra_kwargs = {"user": {"read_only": True}}

# --- VAT Tracking Serializers ---
from .models import VatOrderBuyItem, VatOrderSaleItem

class VatOrderSaleItemSerializer(serializers.ModelSerializer):
    document_no = serializers.CharField(source='vat_order.document_no', read_only=True)
    date = serializers.DateField(source='vat_order.date', read_only=True)
    customer_name = serializers.CharField(source='vat_order.customer_name', read_only=True)

    class Meta:
        model = VatOrderSaleItem
        fields = ['id', 'serial_no', 'product_name', 'sale_price', 'payment_method_out', 'company_out', 'document_no', 'date', 'customer_name']

class VatOrderBuyItemSerializer(serializers.ModelSerializer):
    document_no = serializers.CharField(source='vat_order.document_no', read_only=True)
    date = serializers.DateField(source='vat_order.date', read_only=True)
    supplier_name = serializers.CharField(source='vat_order.supplier_name', read_only=True)
    
    # We map the Sale item details via Serial No. 
    # Use SerializerMethodField for easier joining
    sale_match = serializers.SerializerMethodField()

    class Meta:
        model = VatOrderBuyItem
        fields = [
            'id', 'serial_no', 'product_name', 'purchase_price', 
            'vat_company', 'payment_method_in', 'bank_in', 
            'document_no', 'date', 'supplier_name',
            'sale_match'
        ]

    def get_sale_match(self, obj):
        sale_item = VatOrderSaleItem.objects.filter(serial_no=obj.serial_no).first()
        if sale_item:
            return VatOrderSaleItemSerializer(sale_item).data
        return None