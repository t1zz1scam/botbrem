from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Application, SessionLocal
from sqlalchemy.future import select
from sqlalchemy import update
from datetime import datetime

router = Router()

@router.callback_query(F.data == "view_applications")
async def view_applications(callback: types.CallbackQuery):
    async with SessionLocal() as session:
        result = await session.execute(select(Application).where(Application.status == "pending"))
        applications = result.scalars().all()

    if not applications:
        await callback.message.answer("Нет новых заявок.")
        await callback.answer()
        return

    for app in applications:
        text = (
            f"<b>Заявка от пользователя {app.user_id}</b>\n\n"
            f"Сообщение:\n{app.message}\n\n"
            f"Статус: {app.status}"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{app.id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{app.id}")
            ]
        ])
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_application(callback: types.CallbackQuery):
    app_id = int(callback.data.split("_")[1])
    admin_id = callback.from_user.id

    async with SessionLocal() as session:
        await session.execute(
            update(Application).where(Application.id == app_id).values(
                status="approved",
                resolved_by=admin_id,
                resolved_at=datetime.utcnow()
            )
        )
        await session.commit()
        app = await session.get(Application, app_id)

    await callback.message.answer(f"Заявка #{app_id} одобрена.")
    try:
        await callback.bot.send_message(app.user_id, "Ваша заявка одобрена администратором!")
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject_application(callback: types.CallbackQuery):
    app_id = int(callback.data.split("_")[1])
    admin_id = callback.from_user.id

    async with SessionLocal() as session:
        await session.execute(
            update(Application).where(Application.id == app_id).values(
                status="rejected",
                resolved_by=admin_id,
                resolved_at=datetime.utcnow()
            )
        )
        await session.commit()
        app = await session.get(Application, app_id)

    await callback.message.answer(f"Заявка #{app_id} отклонена.")
    try:
        await callback.bot.send_message(app.user_id, "Ваша заявка отклонена администратором.")
    except Exception:
        pass
    await callback.answer()
