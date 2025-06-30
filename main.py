async with SessionLocal() as s:
    s.add(News(content=message.text))
    await s.commit()

for ch in CHANNEL_IDS:
    await bot.send_message(ch, message.text)

await message.answer("Пост опубликован.")
await state.clear()

# ... дальше остальные хендлеры ...

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
