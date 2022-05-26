from django.contrib.auth.models import User
from django.db import models
from django.db.models import CASCADE
from api.constants import S3_BUCKET_IMAGES


class Product(models.Model):
    name = models.TextField()
    # Small description for preview
    blurb = models.TextField()
    # Full description for product page
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # ratings: https://django-star-ratings.readthedocs.io/en/latest/?badge=latest/
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def preview_image(self):
        image_object = self.images.first()
        link = f"{S3_BUCKET_IMAGES}/{image_object.image if image_object else 'product_default.png'}"
        return link


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=CASCADE)
    # Uploads to S3
    image = models.ImageField(default=None)


class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
