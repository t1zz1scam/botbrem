# Хендлер публикации новости
@dp.message_handler(commands=["post_news"])  # или замени на свой триггер
async def post_news_handler(message: types.Message, state: FSMContext):
    async with SessionLocal() as s:
        s.add(News(content=message.text))
        await s.commit()

    for ch in CHANNEL_IDS:
        await bot.send_message(ch, message.text)

    await message.answer("Пост опубликован.")
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


# Главная асинхронная точка входа
async def main():
    await init_db()
    loop = asyncio.get_event_loop()
    loop.create_task(auto_post_news())
    executor.start_polling(dp, skip_updates=True)


# Запуск бота
if name == "__main__":
    asyncio.run(main())
