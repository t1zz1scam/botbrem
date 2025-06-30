from aiogram import types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import asyncio

# Предположим, что у тебя есть эти импорты:
# from config import CHANNEL_IDS
# from database import SessionLocal, init_db, News, Payout, User
# from loader import dp, bot
# from states import PayoutForm

# Функция публикации поста
@dp.message_handler(commands=["post_news"])  # или другой хендлер
async def post_news_handler(message: types.Message, state: FSMContext):
    async with SessionLocal() as s:
        s.add(News(content=message.text))
        await s.commit()

    for ch in CHANNEL_IDS:
        await bot.send_message(ch, message.text)

    await message.answer("Пост опубликован.")
    await state.clear()


# Выплаты
@dp.callback_query(lambda c: c.data == "manage_payouts")
async def payout_req(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("ID пользователя:")
    await state.set_state(PayoutForm.waiting_for_user_id)


@dp.message(PayoutForm.waiting_for_user_id)
async def payout_id(message: types.Message, state: FSMContext):
    await state.update_data(user_id=int(message.text))
    await message.answer("Сумма:")
    await state.set_state(PayoutForm.waiting_for_amount)


@dp.message(PayoutForm.waiting_for_amount)
async def payout_amt(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as s:
        payout = Payout(
            user_id=data['user_id'],
            amount=int(message.text),
            issued_by=message.from_user.id
        )
        s.add(payout)
        user = await s.get(User, data['user_id'])
        user.payout += int(message.text)
        await s.commit()

    await message.answer("Выплата проведена.")
    await state.clear()


# Автопостинг новостей каждые 3600 секунд
async def auto_post_news():
    while True:
        await asyncio.sleep(3600)
        async with SessionLocal() as s:
            q = await s.execute(select(News).filter_by(sent=False))
            for n in q.scalars():
                for ch in CHANNEL_IDS:
                    await bot.send_message(ch, n.content)
                n.sent = True
            await s.commit()


# Основная точка входа
async def main():
    await init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(auto_post_news())
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)


# Запуск
if name == "__main__":
    asyncio.run(main())
