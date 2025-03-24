from fastadmin import TortoiseModelAdmin, register
from .models import Converter

@register(Converter)
class ConverterModelAdmin(TortoiseModelAdmin):
    model = Converter
    icon = "exchange"
    display_name = "转换器管理"
    list_display = ["id", "name", "type", "is_active", "created_at"]
    list_display_links = ["id", "name"]
    list_filter = ["type", "is_active", "created_at"]
    search_fields = ["name", "description"]
    list_per_page = 15
    ordering = ["-created_at"]