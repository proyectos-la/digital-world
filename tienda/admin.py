from django.contrib import admin
from .models import Brand, Category, Product, ProductImage, Order, OrderItem, Comment
from django.utils.html import format_html


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ("product_images",)

    def product_images(self, obj):
        images = obj.product.images.all()
        if images:
            return format_html(
                " ".join(
                    [
                        f'<img src="{image.image.url}" style="width: 50px; height: auto;" />'
                        for image in images
                    ]
                )
            )
        return "No Images"

    product_images.short_description = "Product Images"


class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = ("name", "description", "price", "category", "brand")
    search_fields = ("name", "description", "category__name", "brand__name")


class BrandAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "image")
    search_fields = ("product__name",)


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ("id", "user", "total_amount", "order_date")
    search_fields = ("user__email", "user__username")
    ordering = ("order_date",)


class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "rating", "comment_text", "created_at")
    list_filter = ("rating", "created_at", "product")  # Agregar filtros
    search_fields = ("user__username", "product__name", "comment_text")


admin.site.register(Comment, CommentAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage, ProductImageAdmin)
admin.site.register(Order, OrderAdmin)
