import secrets
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Business(models.Model):
    """One business profile per signup flow MVP (user can extend to many later)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="businesses",
    )
    name = models.CharField(max_length=200)
    service = models.CharField(max_length=200, help_text="e.g. junk removal, detailing")
    city = models.CharField(max_length=120)
    slug = models.SlugField(max_length=96, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name}-{self.city}")[:80] or "business"
            self.slug = base
            while Business.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
                suffix = secrets.token_hex(2)
                self.slug = f"{base}-{suffix}"[:96]
        super().save(*args, **kwargs)


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CLOSED = "closed", "Closed"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        WEB_FORM = "web_form", "Website"

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="leads",
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    notes = models.TextField(blank=True)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


class GeneratedContent(models.Model):
    class Kind(models.TextChoices):
        FACEBOOK_POSTS = "facebook_posts", "Facebook posts bundle"
        GOOGLE_BUSINESS = "google_business", "Google Business update"
        SHORT_AD = "short_ad", "Short ad"

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="generated_contents",
    )
    kind = models.CharField(max_length=40, choices=Kind.choices)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Website(models.Model):
    """Stores copy for the single public landing page (regenerate overwrites)."""

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="website",
    )
    hero_title = models.CharField(max_length=240, blank=True)
    hero_subtitle = models.TextField(blank=True)
    services_text = models.TextField(blank=True, help_text="Plain text bullets or lines")
    testimonials_text = models.TextField(blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Website ({self.business.name})"
