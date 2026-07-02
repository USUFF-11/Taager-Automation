from __future__ import annotations

from datetime import datetime
import logging
import time
import uuid
from typing import Any, Dict, Optional

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
from countries import COUNTRY_CONFIGS, get_country_config, CountryConfig
from orders import OrderService


ASK_NAME, ASK_PHONE, ASK_PHONE2, ASK_PROVINCE, ASK_ADDRESS, ASK_QUANTITY, ASK_NOTES, ASK_FACEBOOK_PAGE, ASK_FACEBOOK_LINK = range(9)
logger = logging.getLogger(__name__)

PROVINCE_MATCH_THRESHOLD = 80


def _parse_country_and_product_id(raw: str) -> tuple[str, str]:
    for sep in ("_", "-"):
        parts = raw.split(sep, 1)
        if len(parts) == 2 and parts[0].upper() in COUNTRY_CONFIGS:
            return parts[0].upper(), parts[1]
    return "EG", raw


def _make_order_service(country_code: str) -> OrderService:
    settings = get_settings()
    return OrderService(settings, country_code=country_code)


class OrderConversation:
    """Handles the interactive order-taking flow for Telegram users."""

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start a new ordering conversation from a deep link or command."""
        message = update.effective_message
        user_id = update.effective_user.id if update.effective_user else None
        msg_text = message.text if message else None
        args = context.args or []

        logger.info(
            "=== START HANDLER === user_id=%s msg_text=%s context_args=%s update_id=%s",
            user_id, msg_text, args, update.update_id,
        )

        if message is None:
            logger.warning("start handler: no effective message")
            return ConversationHandler.END

        if self._check_update_dedup(update, context):
            logger.info("start dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ConversationHandler.END)

        raw_id = args[0] if args else None
        logger.info("start raw_id=%s has_args=%s", raw_id, bool(args))

        last_raw_id = context.user_data.get("_last_start_raw_id")
        last_time = context.user_data.get("_last_start_time", 0)
        now = time.time()
        if raw_id and raw_id == last_raw_id and (now - last_time) < 6:
            logger.info("ignoring duplicate start raw_id=%s (within 6s)", raw_id)
            return context.user_data.get("current_state", ConversationHandler.END)
        context.user_data["_last_start_raw_id"] = raw_id
        context.user_data["_last_start_time"] = now

        if not raw_id:
            await message.reply_text(
                "يرجى استخدام الرابط من القناة أو إرسال /start <ProductID> للبدء."
            )
            return ConversationHandler.END

        country_code, product_id = _parse_country_and_product_id(raw_id)
        country_config = get_country_config(country_code)
        order_service = _make_order_service(country_code)

        product = order_service.get_product_by_id(str(product_id))
        if product is None:
            await message.reply_text("لم أتمكن من العثور على هذا المنتج، يرجى المحاولة لاحقاً.")
            return ConversationHandler.END

        context.user_data["product"] = product
        context.user_data["product_id"] = str(product_id)
        context.user_data["country_code"] = country_code
        context.user_data["order_service"] = order_service
        context.user_data["order_data"] = {}
        context.user_data["current_state"] = ASK_NAME

        await self._send_product_summary(update, product, country_config)
        await message.reply_text("أولاً، اكتب اسمك الكامل:")
        logger.info("Started order flow for product_id=%s country=%s", product_id, country_code)
        return ASK_NAME

    @staticmethod
    def _check_update_dedup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        msg = update.effective_message
        if msg is None:
            return False
        last = context.user_data.get("_dedup_msg_id")
        if last == msg.message_id:
            return True
        context.user_data["_dedup_msg_id"] = msg.message_id
        return False

    async def handle_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if self._check_update_dedup(update, context):
            logger.info("handle_name dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_NAME)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_phone dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_PHONE)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_phone2 dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_PHONE2)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_province dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_PROVINCE)
        logger.info("handle_province received update")
        message = update.effective_message
        if message is None:
            logger.warning("handle_province received an update without an effective message")
            return ASK_PROVINCE

        province = self._sanitize_text(message.text)
        if not province:
            await message.reply_text("يرجى إدخال المحافظة.")
            return ASK_PROVINCE

        country_code = context.user_data.get("country_code", "EG")
        country_config = get_country_config(country_code)
        normalized_province = self._normalize_province(province, country_config.provinces)
        if normalized_province is None:
            await message.reply_text("لم أتمكن من معرفة المحافظة، يرجى إعادة كتابتها.")
            return ASK_PROVINCE

        context.user_data.setdefault("order_data", {})["Province"] = normalized_province
        context.user_data["current_state"] = ASK_ADDRESS
        await message.reply_text("اكتب العنوان بالتفصيل:")
        return ASK_ADDRESS

    async def handle_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if self._check_update_dedup(update, context):
            logger.info("handle_address dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_ADDRESS)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_quantity dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_QUANTITY)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_notes dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_NOTES)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_facebook_page dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_FACEBOOK_PAGE)
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
        if self._check_update_dedup(update, context):
            logger.info("handle_facebook_link dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ASK_FACEBOOK_LINK)
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
        country_code = context.user_data.get("country_code", "EG")
        country_config = get_country_config(country_code)

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
            "Country": country_config.order_country_code,
            "Color": "",
            "Size": "",
            "Order Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Status": "New",
        }

        order_service = context.user_data.get("order_service")
        if order_service is not None:
            order_service.save_order(record)
        else:
            logger.error("No order_service found in user_data, cannot save order")
        await message.reply_text("✅ تم استلام طلبك بنجاح")
        context.user_data["current_state"] = ConversationHandler.END
        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the current order conversation."""
        if self._check_update_dedup(update, context):
            logger.info("cancel dedup blocked update_id=%s", update.update_id)
            return context.user_data.get("current_state", ConversationHandler.END)
        logger.info("cancel handler received update")
        message = update.effective_message
        if message is not None:
            await message.reply_text("تم إلغاء الطلب.")
        context.user_data["current_state"] = ConversationHandler.END
        context.user_data.clear()
        return ConversationHandler.END

    async def _send_product_summary(self, update: Update, product: Dict[str, Any], country_config: CountryConfig) -> None:
        """Send the product summary to the customer before collecting order details."""
        name = product.get("Name") or ""
        price = product.get("Selling Price") or product.get("Taager Price") or ""
        image = product.get("Image") or product.get("image")

        caption = f"📦 {name}\n💰 السعر: {price} {country_config.currency_symbol}"
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
    def _normalize_province(user_input: str, provinces: list[str]) -> str | None:
        """Match the user's province input to the closest province in the list."""
        if not user_input:
            return None

        normalized_input = user_input.strip()
        best_match = process.extractOne(normalized_input, provinces)
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
    conversation = OrderConversation()

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
