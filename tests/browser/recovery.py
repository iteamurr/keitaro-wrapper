"""Exercise ambiguous HTTP responses against the synthetic browser application."""

import asyncio
import json

from playwright.async_api import Route, async_playwright, expect


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto("http://127.0.0.1:8008")
        await page.get_by_label("Название", exact=True).fill("recovery_launch")
        await page.get_by_label("Страна геопотока").select_option("FR")
        await page.get_by_role("searchbox").fill("Essential care")
        await page.get_by_label("Выбранный оффер").select_option("2")

        async def reject_before_start(route: Route) -> None:
            await route.fulfill(
                status=503,
                json={
                    "error": {
                        "message": "Synthetic preflight rejection",
                        "details": {"command_state": "not_started"},
                    }
                },
            )

        await page.route("**/api/v1/campaigns", reject_before_start, times=1)
        await page.get_by_role("button", name="Создать кампанию", exact=True).click()
        await expect(page.locator("#notice")).to_contain_text("Synthetic preflight rejection")
        await expect(page.locator("body")).not_to_have_attribute("aria-busy", "true")
        assert await page.evaluate("sessionStorage.getItem('keitaro-wrapper-pending')") is None

        keys: list[str] = []
        created: dict[str, str] = {}

        async def lose_response_after_creation(route: Route) -> None:
            keys.append(route.request.headers["idempotency-key"])
            response = await route.fetch()
            assert response.status == 201
            created.update(await response.json())
            await route.fulfill(status=503, json={"error": {"code": "service_unavailable"}})

        await page.route("**/api/v1/campaigns", lose_response_after_creation, times=1)
        await page.get_by_role("button", name="Создать кампанию", exact=True).click()
        retry = page.get_by_role("button", name="Повторить тот же запрос")
        await expect(retry).to_be_visible()
        pending = json.loads(
            await page.evaluate("sessionStorage.getItem('keitaro-wrapper-pending')")
        )
        assert pending["key"] == keys[0]
        await expect(page.locator("body")).not_to_have_attribute("aria-busy", "true")

        # A rejected retry cannot disprove the first request's successful write.
        async def reject_retry(route: Route) -> None:
            keys.append(route.request.headers["idempotency-key"])
            await route.fulfill(status=403, json={"error": {"code": "csrf_failed"}})

        await page.route("**/api/v1/campaigns", reject_retry, times=1)
        await retry.click()
        await expect(page.locator("body")).not_to_have_attribute("aria-busy", "true")
        await expect(retry).to_be_visible()
        pending = json.loads(
            await page.evaluate("sessionStorage.getItem('keitaro-wrapper-pending')")
        )
        assert pending["key"] == keys[0]

        async def malformed_success(route: Route) -> None:
            keys.append(route.request.headers["idempotency-key"])
            await route.fulfill(status=200, json={})

        await page.route("**/api/v1/campaigns", malformed_success, times=1)
        await retry.click()
        await expect(page.locator("body")).not_to_have_attribute("aria-busy", "true")
        await expect(retry).to_be_visible()

        async def repeat_original_command(route: Route) -> None:
            keys.append(route.request.headers["idempotency-key"])
            await route.continue_()

        await page.route("**/api/v1/campaigns", repeat_original_command, times=1)
        await retry.click()
        await page.get_by_role("heading", name="test_demo_recovery_launch").wait_for()
        assert keys == [keys[0]] * 4
        assert created["campaign_id"] in page.url
        catalog = await (await page.request.get("http://127.0.0.1:8008/api/v1/campaigns")).json()
        assert sum(item["name"] == "test_demo_recovery_launch" for item in catalog["items"]) == 1
        assert await page.evaluate("sessionStorage.getItem('keitaro-wrapper-pending')") is None

        # The mutation succeeds even if the subsequent screen refresh fails.
        section = page.locator("section.stream").filter(
            has=page.get_by_role("heading", name="Offers", exact=True)
        )
        await section.get_by_role("searchbox").fill("New arrival")
        await section.get_by_role("combobox").select_option("4")

        async def fail_refresh(route: Route) -> None:
            await route.fulfill(status=503, json={"error": {"message": "Synthetic read failure"}})

        await page.route(f"**/api/v1/campaigns/{created['campaign_id']}", fail_refresh, times=1)
        await section.get_by_role("button", name="Добавить", exact=True).click()
        await expect(page.locator("#notice")).to_contain_text("Ответ на команду получен")
        assert await page.evaluate("sessionStorage.getItem('keitaro-wrapper-pending')") is None
        await page.get_by_role("button", name="Обновить экран").click()
        await page.get_by_text("Добавлен в черновик", exact=True).wait_for()
        assert await section.locator(".weight").all_text_contents() == ["50%", "50%"]
        assert not errors, errors
        await browser.close()
    print(
        "Browser recovery passed: stable idempotency key after 503/403, no duplicate campaign, confirmed result survives refresh failure."
    )


if __name__ == "__main__":
    asyncio.run(main())
