"""Run against tests.browser.app; never points at a live Keitaro instance."""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def main() -> None:
    output = Path(".impeccable/review")
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:8008")
        await page.get_by_role("link", name="test_demo_autumn").click()
        await page.get_by_role("heading", name="Основные офферы").wait_for()
        section = page.locator("section.stream").filter(
            has=page.get_by_role("heading", name="Основные офферы")
        )
        await section.get_by_role("searchbox").fill("New arrival")
        await section.get_by_role("combobox").select_option("4")
        await section.get_by_role("button", name="Добавить", exact=True).click()
        await section.get_by_text("Добавлен в черновик", exact=True).wait_for()
        assert await section.locator(".weight").all_text_contents() == ["25%"] * 4
        await page.reload()
        await page.get_by_text("Добавлен в черновик", exact=True).wait_for()
        assert await page.locator("#fetch-note").is_visible()
        assert "каждого изменённого потока" in await page.locator("#fetch-note").inner_text()
        await page.screenshot(path=str(output / "desktop.png"), full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.screenshot(path=str(output / "mobile.png"), full_page=True)
        assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        await page.set_viewport_size({"width": 1440, "height": 1000})
        await section.get_by_role("button", name="Cancel", exact=True).click()
        await page.get_by_text("Изменения сохранены.", exact=True).wait_for()
        assert await section.locator(".weight").all_text_contents() == ["34%", "33%", "33%"]
        row = section.locator("tr").filter(has_text="Weekend selection")
        await row.get_by_role("button", name="Remove", exact=True).click()
        await page.get_by_text("Будет удалён", exact=True).wait_for()
        await section.get_by_role("button", name="Push to KT", exact=True).click()
        await page.get_by_text("Removed · архив", exact=True).wait_for()
        await row.get_by_role("button", name="Bring Back", exact=True).click()
        await page.get_by_text("Возвращён в черновик", exact=True).wait_for()
        await section.get_by_role("button", name="Cancel", exact=True).click()
        await page.get_by_text("Removed · архив", exact=True).wait_for()
        await page.goto("http://127.0.0.1:8008")
        await page.get_by_label("Название", exact=True).fill("browser_launch")
        await page.get_by_label("Страна геопотока").select_option("FR")
        await page.get_by_role("searchbox").fill("Essential care")
        await page.get_by_label("Выбранный оффер").select_option("2")
        await page.get_by_role("button", name="Создать кампанию", exact=True).click()
        await page.get_by_role("heading", name="test_demo_browser_launch").wait_for()
        await page.get_by_role("heading", name="Offers", exact=True).wait_for()
        assert await page.get_by_role("link", name="Открыть ссылку кампании").get_attribute("href")
        assert not errors, errors
        await browser.close()
    print(
        "Browser smoke passed: persisted draft, Cancel, Remove/Push/Bring Back, creation, responsive overflow, no JavaScript errors."
    )


if __name__ == "__main__":
    asyncio.run(main())
