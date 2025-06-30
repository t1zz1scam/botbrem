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
        payout = Payout(user_id=data['user_id'], amount=int(message.text), issued_by=message.from_user.id)
        s.add(payout)
        user = await s.get(User, data['user_id'])
        user.payout += int(message.text)
        await s.commit()
    await message.answer("Выплата проведена.")
    await state.clear()

# Автопостинг новостей (через каждые 3600 сек)
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

if name == "__main__":
    asyncio.run(init_db())
    loop = asyncio.get_event_loop()
    loop.create_task(auto_post_news())
    executor.start_polling(dp, skip_updates=True)
