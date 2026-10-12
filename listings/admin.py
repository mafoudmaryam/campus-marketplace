from django.contrib import admin

from .models import Category, Listing, ListingImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "category", "status", "seller", "created_at")
    list_filter = ("status", "category", "campus")
    search_fields = ("title", "description")
    inlines = [ListingImageInline]