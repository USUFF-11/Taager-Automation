from __future__ import annotations

from datetime import datetime
import logging
import uuid
from typing import Any, Dict

from rapidfuzz import process
from telegram._update import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import get_settings
from orders import OrderService


ASK_NAME, ASK_PHONE, ASK_PHONE2, ASK_PROVINCE, ASK_ADDRESS, ASK_QUANTITY, ASK_NOTES, ASK_FACEBOOK_PAGE, ASK_FACEBOOK_LINK = range(9)
logger = logging.getLogger(__name__)

EGYPTIAN_GOVERNORATES = [
    "القاهرة",
    "الإسكندرية",
    "الجيزة",
    "الدقهلية",
    "البحر الأحمر",
    "البحيرة",
    "الفيوم",
    "الغربية",
    "الإسماعيلية",
    "المنوفية",
    "المنيا",
    "القليوبية",
    "الوادي الجديد",
    "السويس",
    "الاسماعيلية",
    "اسيوط",
    "بني سويف",
    "بورسعيد",
    "دمياط",
    "الشرقية",
    "جنوب سيناء",
    "كفر الشيخ",
    "مطروح",
    "الأقصر",
    "قنا",
    "شمال سيناء",
    "سوهاج",
    "أسيوط",
    "السويس",
    "المنصورة",
    "طنطا",
    "6 أكتوبر",
    "حلوان",
    "العاشر من رمضان",
    "العبور",
    "الفيوم",
    "الجيزة",
]

PROVINCE_MATCH_THRESHOLD = 80


class OrderConversation:
    """Handles the interactive order-taking flow for Telegram users."""

    def __init__(self, order_service: OrderService) -> None:
        self.order_service = order_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start a new ordering conversation from a deep link or command."""
        logger.info("start handler received update")
        args = context.args or []
        product_id = args[0] if args else None

        message = update.effective_message
        if message is None:
            logger.warning("start handler received an update without an effective message")
            return ConversationHandler.END

        if not product_id:
            await message.reply_text(
                "يرجى استخدام الرابط من القناة أو إرسال /start <ProductID> للبدء."
            )
            return ConversationHandler.END

        product = self.order_service.get_product_by_id(str(product_id))
        if product is None:
            await message.reply_text("لم أتمكن من العثور على هذا المنتج، يرجى المحاولة لاحقاً.")
            return ConversationHandler.END

        context.user_data["product"] = product
        context.user_data["product_id"] = str(product_id)
        context.user_data["order_data"] = {}
        context.user_data["current_state"] = ASK_NAME

        await self._send_product_summary(update, product)
        await message.reply_text("أولاً، اكتب اسمك الكامل:")
        logger.info("Started order flow for product_id=%s", product_id)
        return ASK_NAME

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_name received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_name received an update without an effective message")
            return ASK_NAME

        name = self._sanitize_text(message.text)
        if not name:
            await message.reply_text("يرجى إدخال اسمك الكامل.")
            return ASK_NAME

        context.user_data.setdefault("order_data", {})["Customer Name"] = name
        context.user_data["current_state"] = ASK_PHONE
        await message.reply_text("اكتب رقم الهاتف:")
        return ASK_PHONE

    async def handle_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_phone received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_phone received an update without an effective message")
            return ASK_PHONE

        phone = self._sanitize_text(message.text)
        if not phone:
            await message.reply_text("يرجى إدخال رقم الهاتف.")
            return ASK_PHONE

        context.user_data.setdefault("order_data", {})["Phone"] = phone
        context.user_data["current_state"] = ASK_PHONE2
        await message.reply_text("اكتب رقم الهاتف الثاني (اختياري) أو اكتب skip:")
        return ASK_PHONE2

    async def handle_phone2(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_phone2 received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_phone2 received an update without an effective message")
            return ASK_PHONE2

        value = self._sanitize_text(message.text)
        context.user_data.setdefault("order_data", {})["Phone2"] = "" if self._is_optional_skip(value) else value
        context.user_data["current_state"] = ASK_PROVINCE
        await message.reply_text("اكتب المحافظة:")
        return ASK_PROVINCE

    async def handle_province(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_province received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_province received an update without an effective message")
            return ASK_PROVINCE

        province = self._sanitize_text(message.text)
        if not province:
            await message.reply_text("يرجى إدخال المحافظة.")
            return ASK_PROVINCE

        normalized_province = self._normalize_province(province)
        if normalized_province is None:
            await message.reply_text("لم أتمكن من معرفة المحافظة، يرجى إعادة كتابتها.")
            return ASK_PROVINCE

        context.user_data.setdefault("order_data", {})["Province"] = normalized_province
        context.user_data["current_state"] = ASK_ADDRESS
        await message.reply_text("اكتب العنوان بالتفصيل:")
        return ASK_ADDRESS

    async def handle_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_address received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_address received an update without an effective message")
            return ASK_ADDRESS

        address = self._sanitize_text(message.text)
        if not address:
            await message.reply_text("يرجى إدخال العنوان.")
            return ASK_ADDRESS

        context.user_data.setdefault("order_data", {})["Address"] = address
        context.user_data["current_state"] = ASK_QUANTITY
        await message.reply_text("اكتب الكمية المطلوبة:")
        return ASK_QUANTITY

    async def handle_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_quantity received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_quantity received an update without an effective message")
            return ASK_QUANTITY

        value = self._sanitize_text(message.text)
        if not value.isdigit() or int(value) <= 0:
            await message.reply_text("يرجى إدخال كمية صحيحة أكبر من صفر.")
            return ASK_QUANTITY

        context.user_data.setdefault("order_data", {})["Quantity"] = int(value)
        context.user_data["current_state"] = ASK_NOTES
        await message.reply_text("اكتب الملاحظات (اختياري) أو اكتب skip:")
        return ASK_NOTES

    async def handle_notes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_notes received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_notes received an update without an effective message")
            return ASK_NOTES

        value = self._sanitize_text(message.text)
        context.user_data.setdefault("order_data", {})["Notes"] = "" if self._is_optional_skip(value) else value
        context.user_data["current_state"] = ASK_FACEBOOK_PAGE
        await message.reply_text("اكتب اسم الصفحة على فيسبوك (اختياري) أو اكتب skip:")
        return ASK_FACEBOOK_PAGE

    async def handle_facebook_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_facebook_page received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_facebook_page received an update without an effective message")
            return ASK_FACEBOOK_PAGE

        value = self._sanitize_text(message.text)
        context.user_data.setdefault("order_data", {})["Facebook Page"] = "" if self._is_optional_skip(value) else value
        context.user_data["current_state"] = ASK_FACEBOOK_LINK
        await message.reply_text("اكتب رابط الصفحة على فيسبوك (اختياري) أو اكتب skip:")
        return ASK_FACEBOOK_LINK

    async def handle_facebook_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        logger.info("handle_facebook_link received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_facebook_link received an update without an effective message")
            return ASK_FACEBOOK_LINK

        value = self._sanitize_text(message.text)
        context.user_data.setdefault("order_data", {})["Facebook Link"] = "" if self._is_optional_skip(value) else value

        order_data = context.user_data.get("order_data", {})
        product = context.user_data.get("product", {})
        product_id = context.user_data.get("product_id", "")

        record = {
            "Order ID": str(uuid.uuid4()),
            "Product ID": product_id,
            "Product Name": product.get("Name") or "",
            "Selling Price": product.get("Selling Price") or product.get("Taager Price") or "",
            "Quantity": order_data.get("Quantity", 0),
            "Customer Name": order_data.get("Customer Name", ""),
            "Province": order_data.get("Province", ""),
            "Address": order_data.get("Address", ""),
            "Phone": order_data.get("Phone", ""),
            "Phone2": order_data.get("Phone2", ""),
            "Notes": order_data.get("Notes", ""),
            "Facebook Page": order_data.get("Facebook Page", ""),
            "Facebook Link": order_data.get("Facebook Link", ""),
            "Country": "EGY",
            "Color": "",
            "Size": "",
            "Order Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "New",
        }

        self.order_service.save_order(record)
        await message.reply_text("✅ تم استلام طلبك بنجاح")
        context.user_data["current_state"] = ConversationHandler.END
        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the current order conversation."""
        logger.info("cancel handler received update")
        message = update.effective_message
        if message is not None:
            await message.reply_text("تم إلغاء الطلب.")
        context.user_data["current_state"] = ConversationHandler.END
        context.user_data.clear()
        return ConversationHandler.END

    async def _send_product_summary(self, update: Update, product: Dict[str, Any]) -> None:
        """Send the product summary to the customer before collecting order details."""
        name = product.get("Name") or ""
        price = product.get("Selling Price") or product.get("Taager Price") or ""
        image = product.get("Image") or product.get("image")

        caption = f"📦 {name}\n💰 السعر: {price}"
        message = update.effective_message
        if message is None:
            logger.warning("_send_product_summary received an update without an effective message")
            return

        if image:
            await message.reply_photo(photo=image, caption=caption)
        else:
            await message.reply_text(caption)

    @staticmethod
    def _sanitize_text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _normalize_province(user_input: str) -> str | None:
        """Match the user's province input to the closest Egyptian governorate."""
        if not user_input:
            return None

        normalized_input = user_input.strip()
        best_match = process.extractOne(normalized_input, EGYPTIAN_GOVERNORATES)
        if best_match is None:
            return None

        _, score, _ = best_match
        if score >= PROVINCE_MATCH_THRESHOLD:
            return best_match[0]
        return None

    @staticmethod
    def _is_optional_skip(value: str) -> bool:
        return value.lower() in {"skip", "s", "no", "none", "بدون", "لا يوجد", "غير متاح", "لا"}


def build_conversation_handler() -> ConversationHandler:
    """Create the bot's conversation handler for placing orders."""
    settings = get_settings()
    order_service = OrderService(settings)
    conversation = OrderConversation(order_service)

    return ConversationHandler(
        entry_points=[CommandHandler("start", conversation.start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_name)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_phone)],
            ASK_PHONE2: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_phone2)],
            ASK_PROVINCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_province)],
            ASK_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_address)],
            ASK_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_quantity)],
            ASK_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_notes)],
            ASK_FACEBOOK_PAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_facebook_page)],
            ASK_FACEBOOK_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_facebook_link)],
        },
        fallbacks=[CommandHandler("cancel", conversation.cancel)],
        allow_reentry=True,
    )
