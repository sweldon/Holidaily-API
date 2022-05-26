from django.contrib import admin
from .models import Product, ProductReview, ProductImage


class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "blurb", "featured")
    search_fields = ("name",)


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "content", "timestamp", "user")
    search_fields = ("content",)
    raw_id_fields = ("user", "product")


class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "image")
    raw_id_fields = ("product",)


admin.site.register(Product, ProductAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(ProductImage, ProductImageAdmin)
