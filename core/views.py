from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import (
    BusinessSetupForm,
    ManualLeadForm,
    PublicLeadForm,
    SignUpForm,
)
from .models import Business, GeneratedContent, Lead, Website
from .services.ai import (
    ai_facebook_posts,
    ai_google_update,
    ai_short_ad,
    ai_website_bundle,
    fallback_website_copy,
)
from .services.notify import notify_new_web_lead


def primary_business(user):
    return Business.objects.filter(user=user).order_by("-created_at").first()


def home(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "core/landing.html")


def health(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        return redirect(next_url(request) or "dashboard")
    return render(request, "registration/login.html", {"form": form})


def next_url(request: HttpRequest) -> str | None:
    n = (request.POST.get("next") or request.GET.get("next") or "").strip()
    return n if n.startswith("/") and not n.startswith("//") else None


@login_required
@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    from django.contrib.auth import logout as auth_logout

    auth_logout(request)
    return redirect("login")


@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        messages.success(request, "Account ready — finish your business setup.")
        return redirect("setup")
    return render(request, "core/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def setup(request: HttpRequest) -> HttpResponse:
    existing = primary_business(request.user)
    if existing:
        return redirect("dashboard")
    form = BusinessSetupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        biz: Business = form.save(commit=False)
        biz.user = request.user
        biz.slug = ""
        biz.save()

        bundle = ai_website_bundle(biz)
        Website.objects.update_or_create(
            business=biz,
            defaults={
                "hero_title": bundle.get("hero_title", ""),
                "hero_subtitle": bundle.get("hero_subtitle", ""),
                "services_text": bundle.get("services_text", ""),
                "testimonials_text": bundle.get("testimonials_text", ""),
                "meta_description": bundle.get("meta_description", ""),
                "generated_at": bundle.get("generated_at"),
            },
        )
        GeneratedContent.objects.create(
            business=biz,
            kind=GeneratedContent.Kind.FACEBOOK_POSTS,
            body=ai_facebook_posts(biz),
        )
        demos = (
            Lead(
                business=biz,
                name="Sample — Maria Lopez",
                phone="(555) 010-4521",
                email="demo1@example.com",
                notes="Imported demo row. Replace with real prospects.",
                source=Lead.Source.MANUAL,
                status=Lead.Status.NEW,
            ),
            Lead(
                business=biz,
                name="Sample — Chris Patel",
                phone="(555) 010-8890",
                email="demo2@example.com",
                notes="Demo lead for your dashboard preview.",
                source=Lead.Source.MANUAL,
                status=Lead.Status.CONTACTED,
            ),
            Lead(
                business=biz,
                name="Sample — Jordan Kim",
                phone="(555) 010-2044",
                email="demo3@example.com",
                notes="Close deals by updating status as you progress.",
                source=Lead.Source.MANUAL,
                status=Lead.Status.NEW,
            ),
        )
        Lead.objects.bulk_create(demos)

        site_url = request.build_absolute_uri(reverse("public_site", args=[biz.slug]))
        messages.success(request, f"You're set. Your public page: {site_url}")
        messages.info(request, "We added starter posts under Content and sample rows in Leads.")
        return redirect("dashboard")
    return render(request, "core/setup.html", {"form": form})


def _dashboard_redirect(filter_status: str | None = None) -> HttpResponse:
    allowed = [c.value for c in Lead.Status]
    url = reverse("dashboard")
    if filter_status and filter_status in allowed:
        url = f"{url}?status={filter_status}"
    return redirect(url)


@login_required
@require_http_methods(["GET", "POST"])
def dashboard(request: HttpRequest) -> HttpResponse:
    business = primary_business(request.user)
    if not business:
        return redirect("setup")

    allowed_status = [c.value for c in Lead.Status]
    qs = business.leads.all()

    booking_url = request.build_absolute_uri(reverse("public_site", args=[business.slug]))

    if request.method == "POST":
        lead_filter = (request.POST.get("filter_status") or "").strip()
    else:
        lead_filter = (request.GET.get("status") or "").strip()
    if lead_filter not in allowed_status:
        lead_filter = ""

    stats = {
        "total": qs.count(),
        "new": qs.filter(status=Lead.Status.NEW).count(),
        "contacted": qs.filter(status=Lead.Status.CONTACTED).count(),
        "closed": qs.filter(status=Lead.Status.CLOSED).count(),
    }

    manual_form = ManualLeadForm(prefix="lead")

    if request.method == "POST":
        action = request.POST.get("action")

        post_filter_raw = (request.POST.get("filter_status") or "").strip()
        post_filter = post_filter_raw if post_filter_raw in allowed_status else ""

        if action == "add_lead":
            manual_form = ManualLeadForm(request.POST, prefix="lead")
            if manual_form.is_valid():
                ln = manual_form.save(commit=False)
                ln.business = business
                ln.source = Lead.Source.MANUAL
                ln.save()
                messages.success(request, "Lead saved — follow up fast while you're top of mind.")
                return _dashboard_redirect(post_filter)
        elif action == "update_status":
            lid = request.POST.get("lead_id")
            ns = request.POST.get("lead_status") or ""
            if lid and ns in allowed_status:
                lead = get_object_or_404(Lead, pk=lid, business=business)
                lead.status = ns
                lead.save(update_fields=["status"])
                messages.success(request, "Status updated.")
                return _dashboard_redirect(post_filter)
            messages.error(request, "Could not update status.")
        elif action == "delete_lead":
            lid = request.POST.get("lead_id")
            if lid:
                lead = get_object_or_404(Lead, pk=lid, business=business)
                lead.delete()
                messages.success(request, "Lead deleted.")
                return _dashboard_redirect(post_filter)
            messages.error(request, "Couldn't delete lead.")

        lead_filter = post_filter

    leads_qs = business.leads.order_by("-created_at")
    if lead_filter:
        leads_qs = leads_qs.filter(status=lead_filter)

    leads_qs = leads_qs[:500]
    return render(
        request,
        "core/dashboard.html",
        {
            "business": business,
            "manual_form": manual_form,
            "leads": leads_qs,
            "status_options": Lead.Status.choices,
            "lead_filter": lead_filter,
            "stats": stats,
            "booking_url": booking_url,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def content_tool(request: HttpRequest) -> HttpResponse:
    business = primary_business(request.user)
    if not business:
        return redirect("setup")

    kind = ""
    body = ""

    def post_redirect(msg: str) -> HttpResponse:
        messages.success(request, msg)
        return redirect("content_tool")

    if request.method == "POST":
        kind = request.POST.get("generate_kind") or ""
        kind_map = {
            "facebook": GeneratedContent.Kind.FACEBOOK_POSTS,
            "google": GeneratedContent.Kind.GOOGLE_BUSINESS,
            "ad": GeneratedContent.Kind.SHORT_AD,
        }
        gc_kind = kind_map.get(kind)
        if gc_kind == GeneratedContent.Kind.FACEBOOK_POSTS:
            obj = GeneratedContent.objects.create(business=business, kind=gc_kind, body=ai_facebook_posts(business))
            body = obj.body
            return post_redirect("Generated 3 Facebook-style posts.")
        if gc_kind == GeneratedContent.Kind.GOOGLE_BUSINESS:
            obj = GeneratedContent.objects.create(business=business, kind=gc_kind, body=ai_google_update(business))
            body = obj.body
            return post_redirect("Google Business update drafted.")
        if gc_kind == GeneratedContent.Kind.SHORT_AD:
            obj = GeneratedContent.objects.create(business=business, kind=gc_kind, body=ai_short_ad(business))
            body = obj.body
            return post_redirect("Short ad drafted.")
        return HttpResponseBadRequest("Unknown kind")

    items = GeneratedContent.objects.filter(business=business)[:80]
    return render(
        request,
        "core/content.html",
        {
            "business": business,
            "items": items,
            "last_body": body,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def website_tool(request: HttpRequest) -> HttpResponse:
    business = primary_business(request.user)
    if not business:
        return redirect("setup")

    if request.method == "POST":
        bundle = ai_website_bundle(business)
        ws, _ = Website.objects.update_or_create(
            business=business,
            defaults={
                "hero_title": bundle.get("hero_title", ""),
                "hero_subtitle": bundle.get("hero_subtitle", ""),
                "services_text": bundle.get("services_text", ""),
                "testimonials_text": bundle.get("testimonials_text", ""),
                "meta_description": bundle.get("meta_description", ""),
                "generated_at": bundle.get("generated_at"),
            },
        )
        messages.success(request, "Website copy regenerated.")
        return redirect("website_tool")

    ws, _created = Website.objects.get_or_create(
        business=business,
        defaults={**fallback_website_copy(business), "generated_at": None},
    )
    preview = reverse("public_site", args=[business.slug])
    public_abs = request.build_absolute_uri(preview)
    return render(
        request,
        "core/website.html",
        {
            "business": business,
            "website": ws,
            "public_path": preview,
            "public_absolute": public_abs,
        },
    )


def _public_site_context(business: Business, form: PublicLeadForm | None = None):
    fb = fallback_website_copy(business)
    wbundle = getattr(business, "website", None)
    if wbundle is None:
        return {"business": business, **fb, "form": form or PublicLeadForm()}
    return {
        "business": business,
        "hero_title": wbundle.hero_title or fb["hero_title"],
        "hero_subtitle": wbundle.hero_subtitle or fb["hero_subtitle"],
        "services_text": wbundle.services_text or fb["services_text"],
        "testimonials_text": wbundle.testimonials_text or fb["testimonials_text"],
        "meta_description": wbundle.meta_description or fb["meta_description"],
        "form": form or PublicLeadForm(),
    }


@require_http_methods(["GET"])
def public_site(request: HttpRequest, slug: str) -> HttpResponse:
    business = get_object_or_404(Business, slug=slug)
    return render(request, "core/public_site.html", _public_site_context(business))


@require_http_methods(["POST"])
def public_lead_capture(request: HttpRequest, slug: str) -> HttpResponse:
    business = get_object_or_404(Business, slug=slug)
    form = PublicLeadForm(request.POST)
    if form.is_valid():
        lead = form.save(commit=False)
        lead.business = business
        lead.source = Lead.Source.WEB_FORM
        lead.status = Lead.Status.NEW
        lead.save()
        notify_new_web_lead(lead)
        messages.success(request, "Thanks — we'll be in touch soon.")
        return redirect("public_site", slug=business.slug)
    messages.error(request, "Please fix the highlighted fields.")
    ctx = _public_site_context(business, form=form)
    return render(request, "core/public_site.html", ctx)
