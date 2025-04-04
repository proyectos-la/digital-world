import os
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view, api_view, permission_classes, action

from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.pagination import LimitOffsetPagination
from .models import Product, Category, Brand, Order, OrderItem, Comment, UserProfile
from tienda.models import Product, ProductImage
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    ProductSerializer,
    CategorySerializer,
    BrandSerializer,
    UserUpdateSerializer,
    OrderSerializer,
    OrderItemSerializer,
    CommentSerializer,
    UserProfileSerializer,
    ProductImageSerializer
)
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models import Q, Case, When, F, FloatField, Sum, Avg
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.shortcuts import get_object_or_404
from django.core.files import File
from django.db import transaction

from datetime import timedelta

from google.auth.transport import requests
from google.oauth2 import id_token

import cloudinary.uploader

from io import BytesIO

from PIL import Image


User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "Usuario registrado exitosamente"},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def authenticate_user(username_or_email=None, password=None):
    user = None

    if "@" in username_or_email:
        try:
            user = User.objects.get(email=username_or_email)
        except User.DoesNotExist:
            return None
    else:
        user = User.objects.filter(username=username_or_email).first()

    if user and user.check_password(password):
        return user
    return None

def optimize_image(image, max_size_kb=200, quality=80, format="WEBP"):
    
    if image.name.lower().endswith(".webp"):
        return image

    img = Image.open(image).convert("RGB")

    output_io = BytesIO()
    img.save(output_io, format=format, quality=quality)
    output_io.seek(0)

    new_image = InMemoryUploadedFile(
        output_io, "ImageField", f"{image.name.split('.')[0]}.webp",
        "image/webp", output_io.tell(), None
    )

    while new_image.size > max_size_kb * 1024 and quality > 50:
        quality -= 5
        output_io = BytesIO()
        img.save(output_io, format=format, quality=quality)
        output_io.seek(0)

        new_image = InMemoryUploadedFile(
            output_io, "ImageField", f"{image.name.split('.')[0]}.webp",
            "image/webp", output_io.tell(), None
        )

    if new_image.size > max_size_kb * 1024:
        raise ValidationError({"image": "La imagen sigue siendo demasiado grande tras la compresión."})

    return new_image

@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        username_or_email = serializer.validated_data.get("username_or_email")
        password = serializer.validated_data.get("password")

        user = authenticate_user(username_or_email=username_or_email, password=password)
        if user:
            has_password = user.has_usable_password()

            try:
                data_profile = UserProfile.objects.get(user=user)
                image_profile = data_profile.image.url if data_profile.image else None
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(user=user)
                image_profile = None

            token, created = Token.objects.get_or_create(user=user)
            print(user)
            return Response(
                {
                    "id": user.id,
                    "token": token.key,
                    "username": user.username,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                    "is_staff": user.is_staff,
                    "image": image_profile,
                    "provider_auth": "email",
                    "has_password": has_password,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "error": "Nombre de usuario, correo electrónico o contraseña incorrectos."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):
    credential = request.data.get("credential")
    client_id = (
        "963077110039-a25ipd3d3aal87omlseibm178m2n6jht.apps.googleusercontent.com"
    )

    if not credential:
        return Response(
            {"error": "Debe proporcionar la credencial de Google"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        user_authenticated = id_token.verify_oauth2_token(
            credential, requests.Request(), client_id, clock_skew_in_seconds=60
        )

        if user_authenticated:
            email = user_authenticated.get("email")
            username = user_authenticated.get("name")
            profile_picture = user_authenticated.get("picture")

            user, created = User.objects.get_or_create(
                email=email, defaults={"username": username}
            )

            if created:
                user.set_unusable_password()
                user.save()

                if profile_picture:
                    response = requests.get(profile_picture)

                    if response.status_code == 200:
                        image_bytes = BytesIO(response.content)
                        image = optimize_image(image_bytes)
                        
                        print(image)
                        # result = cloudinary.uploader.upload(image, folder="users/", 
                        #     public_id=f"{user.id}_profile", 
                        #     overwrite=True, 
                        #     resource_type="image",
                        #     format="webp"
                        # ),

                        # user.profile_picture = result.get("secure_url")
                        # user.save()
    
            has_password = user.has_usable_password()

            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "id": user.id,
                    "token": token.key,
                    "username": user.username,
                    "email": user.email,
                    "is_superuser": user.is_superuser,
                    "is_staff": user.is_staff,
                    "image": profile_picture,
                    "provider_auth": "google",
                    "has_password": has_password,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"error": "Credencial inválida"}, status=status.HTTP_401_UNAUTHORIZED
            )

    except ValueError as e:
        print("Error de verificación de token:", e)
        return Response(
            {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def logout_user(request):
    try:
        token = request.user.auth_token.delete()
        return Response({"message": "Logout exitoso"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def password_register(request):
    user_id = request.data.get("user_id")
    password = request.data.get("password")
    password_repeat = request.data.get("passwordRepeat")

    if password != password_repeat:
        return Response(
            {"error": "Las contraseñas no coinciden"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(id=user_id)
        user.set_password(password)
        user.save()
        has_password = user.has_usable_password()
        return Response(
            {
                "has_password": has_password,
                "message": "Contraseña registrada exitosamente",
            },
            status=status.HTTP_201_CREATED,
        )

    except User.DoesNotExist:
        return Response(
            {"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND
        )


class ProductPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 50


@permission_classes([AllowAny])
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def create(self, request, *args, **kwargs):
        product_data = request.data
        product_serializer = ProductSerializer(data=product_data)
        product_serializer.is_valid(raise_exception=True)

        images = request.FILES.getlist("images")

        if not images:
            raise ValidationError({"images": "Debes subir al menos una imagen."})
        
        try:
            with transaction.atomic():
                product = product_serializer.save()

                uploaded_images = []
                for image in images:
                    optimized_image = optimize_image(image)
                    print(optimized_image)
                    result = cloudinary.uploader.upload(optimized_image, folder="products/")
                    uploaded_images.append(ProductImage(product=product, image=result["secure_url"]))

                ProductImage.objects.bulk_create(uploaded_images)

            headers = self.get_success_headers(product_serializer.data)
            return Response(product_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except Exception as e:
            raise ValidationError({"error": f"Error al subir imágenes: {str(e)}"})
    
    def perform_destroy(self, instance):
        product_images = ProductImage.objects.filter(product=instance)

        for image in product_images:
            if image.image:
                url_parts = image.image.split("/")
                public_id_with_extension = "/".join(url_parts[-2:])
                public_id = ".".join(public_id_with_extension.split(".")[:-1])
                print(public_id)
                cloudinary.uploader.destroy(public_id)

        product_images.delete()
        
        instance.delete()
    
    def get_queryset(self):
        request = self.request
        category_id = request.query_params.get("category")
        sort = request.query_params.get("sort")
        
        if not category_id:
            if sort == "discount":
                return Product.objects.filter(is_on_sale=True)
            elif sort == "latest":
                return Product.objects.order_by('-created_at')
            return Product.objects.all()

        queryset = Product.objects.filter(category__id=category_id)

        brand = request.query_params.get("brand")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        sort = request.query_params.get("sort")
            
        if brand:
            queryset = queryset.filter(brand__name=brand)
            
        queryset = queryset.annotate(
            price_final=Case(
                When(is_on_sale=True, then=F("price") * (1 - F("discount_percentage") / 100)),
                default=F("price"),
                output_field=FloatField(),
            )
        )
            
        if min_price:
            queryset = queryset.filter(price_final__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_final__lte=max_price)
            
        if sort == "best_selling":
            queryset = queryset.annotate(total_sales=Sum("order_items__quantity")).order_by("-total_sales")
        elif sort == "best_rated":
            queryset = queryset.annotate(avg_rating=Avg("comment__rating")).order_by("-avg_rating")
        elif sort == "latest":
            queryset = queryset.order_by("-created_at")
        elif sort == "discount":
            queryset = queryset.filter(is_on_sale=True).order_by("-discount_percentage")

        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        product = get_object_or_404(Product, pk=kwargs["pk"])
        serializer = self.get_serializer(product)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        search_term = request.query_params.get("search", None)
        
        if not search_term:
            return Response({"error": "No search term provided"}, status=400)

        products = Product.objects.filter(Q(name__icontains=search_term)).order_by('-id')[:10]

        categories = Category.objects.filter(
            Q(name__icontains=search_term) | Q(products__name__icontains=search_term)
        ).distinct()

        product_serializer = ProductSerializer(products, many=True)
        category_serializer = CategorySerializer(categories, many=True)

        return Response({
            "products": product_serializer.data,
            "categories": category_serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='related-products')
    def related_products(self, request, pk=None):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=404)

        final_price = product.price
        if product.discount_percentage:
            final_price = product.price - (product.price * product.discount_percentage / 100)

        price_lower_bound = final_price - 100000
        price_upper_bound = final_price + 100000


        related_products = Product.objects.filter(
            category=product.category,
            brand=product.brand,
            ).exclude(id=product.id)

        products_by_price = Product.objects.annotate(
            final_price=Case(
                When(discount_percentage__isnull=False, then=F('price') - (F('price') * F('discount_percentage') / 100)),
                default=F('price'),
                output_field=FloatField(),
            )
        ).filter(
            category=product.category,
            final_price__gte=price_lower_bound,
            final_price__lte=price_upper_bound,
        ).exclude(id=product.id)

        combined_products = related_products | products_by_price
        combined_products = combined_products.distinct()
        
        if combined_products.exists():
            serializer = ProductSerializer(combined_products, many=True, context={'request': request})
            return Response(serializer.data, status=200)
        
        return Response({"detail": "No related products found."}, status=404)
    

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        comment_data = request.data
        comment_serializer = self.get_serializer(data=comment_data)
        comment_serializer.is_valid(raise_exception=True)

        comment_serializer.save(user=request.user)
        return Response(
            {
                "message": "Comentario enviado exitosamente.",
                "data": comment_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            raise PermissionDenied("No tienes permiso para eliminar este comentario.")
        self.perform_destroy(instance)
        return Response(
            {"message": "Comentario eliminado exitosamente."}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            raise PermissionDenied("No tienes permiso para actualizar este comentario.")
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "message": "Comentario actualizado exitosamente.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def get_comments(self, request):
        page_identifier = request.query_params.get("page_id")
        product_id = request.query_params.get("product")
        user = request.user.id

        if page_identifier:
            comments = Comment.objects.filter(page_id=page_identifier)
            if user:
                comments = sorted(
                    comments, key=lambda comment: (comment.user.id != user)
                )
            serializer = CommentSerializer(
                comments, many=True, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        if product_id:
            comments = Comment.objects.filter(product=product_id)
            if user:
                comments = sorted(
                    comments, key=lambda comment: (comment.user.id != user)
                )
            serializer = CommentSerializer(
                comments, many=True, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"error": "Debe proporcionar un page_id o product_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        order_data = request.data
        order_serializer = self.get_serializer(data=order_data)
        order_serializer.is_valid(raise_exception=True)

        order_serializer.save(user=request.user)

        headers = self.get_success_headers(order_serializer.data)
        return Response(
            order_serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def get_orders(self, request):
        user_order = request.query_params.get("user_id")
        if user_order:
            orders = Order.objects.filter(user=user_order)
            if not orders:
                return Response(
                    "No tiene ninguna orden", status=status.HTTP_404_NOT_FOUND
                )
            serializer = OrderSerializer(
                orders, many=True, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            "Parámetro user_id faltante", status=status.HTTP_400_BAD_REQUEST
        )


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([AllowAny])
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def list(self, request, *args, **kwargs):
        if not self.queryset.exists():
            return Response({"message": "No categories found."}, status=404)
        
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], url_path='on-sale-categories')
    def on_sale_categories(self, request):
        categories_with_sale_products = Category.objects.filter(
            products__is_on_sale=True
        ).distinct()

        if not categories_with_sale_products:
            return Response({"message": "No categories with products on sale found."}, status=404)

        serializer = self.get_serializer(categories_with_sale_products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='recent-categories')
    def recent_categories(self, request):
        one_month_ago = timezone.now() - timedelta(days=30)
        categories_with_recent_products = Category.objects.filter(
            products__created_at__gte=one_month_ago
        ).distinct()

        if not categories_with_recent_products:
            return Response({"message": "No recent categories found."}, status=404)

        serializer = self.get_serializer(categories_with_recent_products, many=True)
        return Response(serializer.data)


@permission_classes([AllowAny])
class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    
    def get_queryset(self):
        category_id = self.request.query_params.get("category")

        if category_id:
            return Brand.objects.filter(products__category_id=category_id).distinct()

        return super().get_queryset()


class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        serializer = UserUpdateSerializer(
            instance=user, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Información actualizada correctamente"},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileImageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            user_profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return Response({"error": "Perfil de usuario no encontrado"}, status=404)

        old_image_path = user_profile.image.path if user_profile.image else None

        serializer = UserProfileSerializer(
            instance=user_profile, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()

            if old_image_path and os.path.exists(old_image_path):
                os.remove(old_image_path)

            return Response(
                {"message": "imagen cargada correctamente", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

    def perform_destroy(self, instance):
        if instance.image:
            # Extraer el public_id de la URL de Cloudinary
            public_id = instance.image.split("/")[-1].split(".")[0]  # Obtiene el ID sin la extensión
            cloudinary.uploader.destroy(public_id)  # Borra la imagen en Cloudinary
        
        instance.delete()