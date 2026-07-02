from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CountryConfig:
    code: str
    channel_id: str
    products_sheet: str
    orders_sheet: str
    currency_symbol: str
    currency_name: str
    shipping_text: str
    bot_username: str
    taager_api_country_header: str
    provinces: List[str]
    order_country_code: str


EGYPTIAN_GOVERNORATES = [
    "القاهرة", "الإسكندرية", "الجيزة", "الدقهلية", "البحر الأحمر",
    "البحيرة", "الفيوم", "الغربية", "الإسماعيلية", "المنوفية",
    "المنيا", "القليوبية", "الوادي الجديد", "السويس", "الاسماعيلية",
    "اسيوط", "بني سويف", "بورسعيد", "دمياط", "الشرقية",
    "جنوب سيناء", "كفر الشيخ", "مطروح", "الأقصر", "قنا",
    "شمال سيناء", "سوهاج", "أسيوط", "السويس", "المنصورة",
    "طنطا", "6 أكتوبر", "حلوان", "العاشر من رمضان", "العبور",
    "الفيوم", "الجيزة",
]

SAUDI_REGIONS = [
    "الرياض", "جدة", "مكة المكرمة", "المدينة المنورة", "الدمام",
    "الخبر", "الظهران", "الأحساء", "القطيف", "حفر الباطن",
    "الجبيل", "ينبع", "تبوك", "الطائف", "بريدة",
    "عنيزة", "الخرج", "أبها", "خميس مشيط", "نجران",
    "جازان", "حائل", "عرعر", "سكاكا", "الباحة",
    "الليث", "القنفذة", "المخواة", "بيشة", "وادي الدواسر",
    "الدوادمي", "المجمعة", "الزلفي", "رفحاء", "طريف",
    "ضباء", "أملج", "الوجه", "القريات",
]

COUNTRY_CONFIGS: Dict[str, CountryConfig] = {
    "EG": CountryConfig(
        code="EG",
        channel_id="@taagerstore",
        products_sheet="Products_EG",
        orders_sheet="Orders_EG",
        currency_symbol="جنيه",
        currency_name="EGP",
        shipping_text="🚚 الشحن يحسب حسب المحافظة",
        bot_username="taager_products_bot",
        taager_api_country_header="EGY",
        provinces=EGYPTIAN_GOVERNORATES,
        order_country_code="EGY",
    ),
    "SA": CountryConfig(
        code="SA",
        channel_id="@taagerstoresa",
        products_sheet="Products_SA",
        orders_sheet="Orders_SA",
        currency_symbol="SAR",
        currency_name="SAR",
        shipping_text="🚚 الشحن 28 SAR في جميع أنحاء المملكة",
        bot_username="taager_products_bot",
        taager_api_country_header="SAU",
        provinces=SAUDI_REGIONS,
        order_country_code="SAU",
    ),
}


def get_country_config(country_code: Optional[str] = None) -> CountryConfig:
    if country_code is None:
        country_code = os.getenv("COUNTRY", "EG").strip().upper()
    config = COUNTRY_CONFIGS.get(country_code)
    if config is None:
        raise ValueError(f"Unsupported country code: {country_code}")
    return config
