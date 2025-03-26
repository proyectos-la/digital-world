from rest_framework import serializers
from django.db import models
from django.contrib.auth.models import User
from .models import Product, Category, Brand, ProductImage, Order, OrderItem, Comment, UserProfile
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.db.models import Avg


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['image']
        

class UserRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=150, 
        required=True, 
        allow_blank=False
    )

    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirm_password", "id", "image"]
        
    def get_image(self, obj):
       
        
        if hasattr(obj, 'profile') and obj.profile.image:
            
            return obj.profile.image.url
    
        return None 

    def validate(self, data):
        username = data.get("username", "")

        if " " in username:
            raise serializers.ValidationError(
                {"username": "El Usuario no puede contener espacios. Usa '_' o '-' o '.' en su lugar."}
            )
        
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"password": "Las contraseñas no coinciden"}
            )

        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError(
                {"username": "El nombre de usuario ya está en uso"}
            )

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError(
                {"email": "El correo electrónico ya está en uso"}
            )

        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        unexpected_fields = set(data.keys()) - {"username_or_email", "password"}
        if unexpected_fields:
            raise serializers.ValidationError(
                f"Campos no permitidos: {', '.join(unexpected_fields)}"
            )

        username_or_email = data.get("username_or_email")
        password = data.get("password")

        if not username_or_email:
            raise serializers.ValidationError(
                "Debe proporcionar un nombre de usuario o un correo electrónico."
            )
        if not password:
            raise serializers.ValidationError("Debe proporcionar una contraseña.")

        return data


class UserUpdateSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_username = serializers.CharField(required=False)
    new_email = serializers.EmailField(required=False)
    new_password = serializers.CharField(write_only=True, required=False)
    new_password_repeat = serializers.CharField(write_only=True, required=False)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not check_password(value, user.password):
            raise serializers.ValidationError("La contraseña actual no es correcta.")
        return value

    def validate(self, data):
        user = self.context["request"].user

        # Validar si se está intentando cambiar el username
        if "new_username" in data:
            new_username = data["new_username"]
            if User.objects.filter(username=new_username).exists():
                raise serializers.ValidationError(
                    "El nombre de usuario ya está en uso."
                )

        # Validar si se está intentando cambiar el email
        if "new_email" in data:
            new_email = data["new_email"]
            if User.objects.filter(email=new_email).exists():
                raise serializers.ValidationError(
                    "El correo electrónico ya está en uso."
                )

        # Validar si se está intentando cambiar la contraseña
        if "new_password" in data or "new_password_repeat" in data:
            new_password = data.get("new_password")
            new_password_repeat = data.get("new_password_repeat")

            if new_password != new_password_repeat:
                raise serializers.ValidationError(
                    "Las nuevas contraseñas no coinciden."
                )

        return data

    def update(self, instance, validated_data):
        # Cambiar el nombre de usuario
        if "new_username" in validated_data:
            instance.username = validated_data["new_username"]

        # Cambiar el correo electrónico
        if "new_email" in validated_data:
            instance.email = validated_data["new_email"]

        # Cambiar la contraseña
        if "new_password" in validated_data:
            instance.set_password(validated_data["new_password"])

        instance.save()
        return instance


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image"]
        

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())
    category_detail = CategorySerializer(source="category", read_only=True)
    brand_detail = BrandSerializer(source="brand", read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)
    final_price = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_sold = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "category",
            "brand",
            "category_detail",
            "brand_detail",
            "images",
            "is_on_sale",
            "discount_percentage",
            "final_price",
            "average_rating",
            "total_sold"
        ]
        

    def get_final_price(self, obj):
        final_price = obj.price

        if obj.discount_percentage:
            final_price = obj.price - (obj.price * obj.discount_percentage / 100)
        
        # Redondea a 2 decimales
        return round(final_price, 2)
    
    def get_total_sold(self, obj):
        total_sold = OrderItem.objects.filter(product=obj).aggregate(total_sold=models.Sum('quantity'))['total_sold']
        return total_sold or 0
    
    def get_average_rating(self,obj):
        average_rating = Comment.objects.filter(product = obj).aggregate(Avg('rating'))['rating__avg']
        return average_rating or 0

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        product = Product.objects.create(**validated_data)
        for image_data in images_data:
            ProductImage.objects.create(product=product, **image_data)
        return product


class CommentSerializer(serializers.ModelSerializer):
    user = UserRegistrationSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "product",
            "rating",
            "comment_text",
            "created_at",
            "page_id",
        ]
        read_only_fields = ["id", "user", "created_at"]

    def validate(self, data):
        request = self.context["request"]
        user = request.user
        product = data.get("product")

        if request.method == "POST":
            if product:
                if Comment.objects.filter(user=user, product=product).exists():
                    raise serializers.ValidationError("Ya has comentado este producto.")

        if product:
            if not data.get("rating"):
                raise serializers.ValidationError(
                    "El rating es obligatorio para los comentarios de productos."
                )
            if not data.get("comment_text") or data.get("comment_text").strip() == "":
                raise serializers.ValidationError(
                    "El texto del comentario es obligatorio para los comentarios de productos."
                )

        if data.get("page_id"):
            if not data.get("comment_text") or data.get("comment_text").strip() == "":
                raise serializers.ValidationError(
                    "El texto del comentario es obligatorio para los comentarios de la página."
                )

            if request.method == "POST":
                if Comment.objects.filter(user=user, page_id=data["page_id"]).exists():
                    raise serializers.ValidationError(
                        "Ya has comentado en esta página."
                    )

        return data


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "name",
            "phone_number",
            "dni",
            "street",
            "number_of_street",
            "comment",
            "payment_method",
            "order_items",
            "total_amount",
            "order_date",
            "status",
        ]
        read_only_fields = ["order_date", "total_amount", "status"]

    def create(self, validated_data):
        order_items_data = validated_data.pop("order_items")
        user = self.context["request"].user

        total_amount = 0

        for order_item_data in order_items_data:
            product = order_item_data["product"]
            quantity = order_item_data["quantity"]
            price = order_item_data["price"]

            total_amount += price * quantity

        order = Order.objects.create(
            user=user,
            name=validated_data["name"],
            phone_number=validated_data["phone_number"],
            dni=validated_data["dni"],
            street=validated_data["street"],
            number_of_street=validated_data["number_of_street"],
            payment_method=validated_data["payment_method"],
            comment=validated_data.get("comment", ""),
            total_amount=total_amount,
        )

        # Crear los OrderItems después de crear la orden
        for order_item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                product=order_item_data["product"],
                quantity=order_item_data["quantity"],
                price=order_item_data["price"],
            )

        return order
