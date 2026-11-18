"""Capture real UI screenshots using a freshly started synthetic browser app."""

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright, expect


async def main() -> None:
    output = Path("docs/assets/screenshots")
    await asyncio.to_thread(output.mkdir, parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:8008")
        campaign = page.get_by_role("link", name="test_demo_autumn")
        await expect(campaign).to_be_visible()
        await page.evaluate("document.fonts.ready")
        await page.screenshot(path=str(output / "campaigns.png"), full_page=True)

        await campaign.click()
        section = page.locator("section.stream").filter(
            has=page.get_by_role("heading", name="Основные офферы"),
        )
        await expect(section.locator("tr:not(.inactive) .weight")).to_have_text(
            ["34%", "33%", "33%"]
        )
        archived = section.locator("tr").filter(has_text="Weekend selection")
        await archived.get_by_role("button", name="Remove", exact=True).click()
        await page.get_by_text("Будет удалён", exact=True).wait_for()
        await section.get_by_role("button", name="Push to KT", exact=True).click()
        await page.get_by_text("Removed · архив", exact=True).wait_for()

        pinned = section.locator("tr").filter(has_text="Autumn collection")
        await pinned.locator('input[name="weight"]').fill("40")
        await pinned.get_by_role("button", name="Закрепить", exact=True).click()
        await expect(section.locator("tr:not(.inactive) .weight")).to_have_text(["40%", "60%"])
        await section.get_by_role("searchbox").fill("New arrival")
        await section.get_by_role("combobox").select_option("4")
        await section.get_by_role("button", name="Добавить", exact=True).click()
        await page.get_by_text("Добавлен в черновик", exact=True).wait_for()
        await expect(section.locator("tr:not(.inactive) .weight")).to_have_text(
            ["40%", "30%", "30%"]
        )

        # Reload shows persisted state without a transient success notification.
        await page.reload()
        await expect(section.locator("tr:not(.inactive) .weight")).to_have_text(
            ["40%", "30%", "30%"]
        )
        await page.evaluate("document.fonts.ready")
        await section.screenshot(path=str(output / "editor.png"))
        await page.screenshot(path=str(output / "campaign.png"), full_page=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        await section.screenshot(path=str(output / "mobile.png"))
        assert not errors, errors
        await browser.close()
    print(
        "Screenshots captured from the application: demo data, persisted 40/30/30 draft, archive."
    )


if __name__ == "__main__":
    asyncio.run(main())
