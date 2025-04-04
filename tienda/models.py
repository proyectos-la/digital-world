from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    image = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class Brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="products", null=True, blank=True
    )
    is_on_sale = models.BooleanField(default=False)
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=0, null=True, blank=True
    )

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    image = models.URLField()
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    

class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('tarjeta', 'Tarjeta de crédito/débito'),
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia bancaria')
    ]

    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    dni = models.CharField(max_length=12)
    street = models.CharField(max_length=50)
    number_of_street = models.CharField(max_length=10)
    order_date = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pendiente')

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
   
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.id})"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_user')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comment', null=True, blank=True)
    comment_text = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    page_id = models.CharField(max_length=100, blank=True)