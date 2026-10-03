from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page, expect


SCREENS = [
    ("pathways", "Guided Execution Pathways"),
    ("dashboard", "Executive Command Center"),
    ("workout", "Kinetic Performance Lab"),
    ("timeview", "Chrono Engine & Telemetry"),
    ("stories", "Work Stories & Epics"),
    ("projects", "Project Kanban Pipeline"),
    ("audit", "Universal Audit Stream"),
    ("finance", "Wealth & Capital Ledger"),
    ("brain", "Second Brain Knowledge Base"),
    ("snapshots", "Checkpoints & Vault Backups"),
    ("legal", "Privacy, Security & Use Notices"),
]


@pytest.mark.parametrize(("view", "heading"), SCREENS)
def test_every_screen_renders_from_navigation(app_page: Page, view: str, heading: str) -> None:
    app_page.locator(f'.nav-item[data-view="{view}"]').click()
    expect(app_page.locator("#content h2").first).to_have_text(heading)


def test_new_vault_rejects_short_passphrases(app_url: str, browser) -> None:
    page = browser.new_page()
    page.goto(app_url, wait_until="domcontentloaded")
    page.get_by_role("button", name="Login as New").click()
    page.locator("#new-key").fill("123456789012345")
    page.get_by_role("button", name="Initialize New Vault").click()
    expect(page.locator("#auth-error")).to_contain_text("at least 16 characters")
    expect(page.locator("#app")).not_to_be_visible()
    page.close()


def test_vault_is_saved_as_an_encrypted_v3_envelope(app_page: Page) -> None:
    envelope = app_page.evaluate(
        """async () => {
            const db = await new Promise((resolve, reject) => {
                const request = indexedDB.open('AetherVaultDB', 1);
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
            const value = await new Promise((resolve, reject) => {
                const request = db.transaction('vault_store', 'readonly')
                    .objectStore('vault_store').get('aether_os_state');
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
            db.close();
            return JSON.parse(value);
        }"""
    )
    assert envelope["v"] == 3
    assert envelope["kdf"] == "PBKDF2-SHA-256"
    assert envelope["iterations"] == 600000
    assert "Audit VPC ingress traffic" not in json.dumps(envelope)


def test_imported_task_text_renders_as_text_not_markup(app_page: Page) -> None:
    app_page.evaluate(
        """() => {
            State.tasks = [{
                id: "');alert(1)//",
                title: "<img src=x onerror=alert(1)>",
                desc: "attempted markup",
                status: "inbox",
                priority: "<svg onload=alert(1)>",
                timeSpent: 0,
                subtasks: []
            }];
            App.router('projects');
        }"""
    )
    card = app_page.locator(".task-card[data-task-index='0']")
    expect(card).to_contain_text("<img src=x onerror=alert(1)>")
    expect(card.locator("img, svg")).to_have_count(0)
    assert card.get_attribute("onclick") is None


def test_app_has_no_third_party_runtime_requests(app_url: str, browser) -> None:
    page = browser.new_page()
    external_requests: list[str] = []
    app_host = urlparse(app_url).netloc
    page.on(
        "request",
        lambda request: external_requests.append(request.url)
        if urlparse(request.url).netloc not in ("", app_host)
        else None,
    )
    page.goto(app_url, wait_until="networkidle")
    assert external_requests == []
    page.close()


def test_service_worker_caches_only_the_local_app_shell(app_page: Page) -> None:
    registration_active = app_page.evaluate(
        """async () => {
            if (!('serviceWorker' in navigator)) return false;
            await navigator.serviceWorker.ready;
            const registration = await navigator.serviceWorker.getRegistration();
            return Boolean(registration && registration.active);
        }"""
    )
    assert registration_active

    cached_urls = app_page.evaluate(
        """async () => {
            const keys = await caches.keys();
            const cache = await caches.open(keys.find(key => key.startsWith('aether-os-')));
            return (await cache.keys()).map(request => request.url);
        }"""
    )
    assert cached_urls
    assert all(urlparse(url).netloc == urlparse(app_page.url).netloc for url in cached_urls)
    assert all(any(url.endswith(path) for path in ("/", "/index.html", "/manifest.json")) for url in cached_urls)


def test_mobile_bottom_navigation_and_sidebar_work(app_page: Page) -> None:
    app_page.set_viewport_size({"width": 390, "height": 844})
    app_page.locator('#bottom-nav .bnav-item[data-view="projects"]').click()
    expect(app_page.locator("#content h2").first).to_have_text("Project Kanban Pipeline")

    app_page.locator("#bottom-nav .bnav-item").last.click()
    app_page.locator('#sidebar .nav-item[data-view="legal"]').click()
    expect(app_page.locator("#content h2").first).to_have_text("Privacy, Security & Use Notices")


def test_mobile_viewport_allows_zoom_and_github_pages_warning_is_visible(app_url: str, browser) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(app_url, wait_until="domcontentloaded")
    viewport = page.locator('meta[name="viewport"]').get_attribute("content") or ""
    assert "user-scalable=no" not in viewport
    assert "maximum-scale=1.0" not in viewport

    index_file = Path(__file__).resolve().parents[1] / "index.html"
    page.route(
        "http://aether-os-test.github.io/**",
        lambda route: route.fulfill(path=str(index_file), content_type="text/html"),
    )
    page.goto("http://aether-os-test.github.io/index.html", wait_until="domcontentloaded")
    expect(page.locator("#github-pages-origin-warning")).to_be_visible()
    page.close()
