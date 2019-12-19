import factory
import uuid
from django.contrib.auth.models import User
from api.models import UserProfile


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"UserName{n}")
    email = factory.Sequence(lambda n: f"test_user_{n}@example.com")
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)

    class Meta:
        model = User


class UserProfileFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory("api.factories.UserFactory")
    device_id = factory.LazyFunction(uuid.uuid4)

    class Meta:
        model = UserProfile
