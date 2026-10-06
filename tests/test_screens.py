from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Page, expect


SCREENS = [
    ("pathways", "Goal Roadmaps"),
    ("dashboard", "Dashboard"),
    ("workout", "Workouts & Fitness"),
    ("timeview", "Focus Timer"),
    ("planner", "Plan your day"),
    ("dailytools", "Habits & Reminders"),
    ("stories", "Projects & Milestones"),
    ("projects", "Task Board"),
    ("audit", "Activity History"),
    ("finance", "Money overview"),
    ("budget", "Budget & bills"),
    ("transactions", "Transactions"),
    ("brain", "Notes & Ideas"),
    ("snapshots", "Backup Snapshots"),
    ("legal", "Privacy, Security & Use Notices"),
]


def navigate_to_view(page: Page, view: str) -> None:
    item = page.locator(f'.nav-item[data-view="{view}"]')
    if not item.is_visible():
        item.locator("xpath=ancestor::details[1]").locator("summary").click()
    item.click()


@pytest.mark.parametrize(("view", "heading"), SCREENS)
def test_every_screen_renders_from_navigation(app_page: Page, view: str, heading: str) -> None:
    navigate_to_view(app_page, view)
    expect(app_page.locator("#content h2").first).to_have_text(heading)


def test_dashboard_is_default_and_includes_energy_heatmap_and_trophies(app_page: Page) -> None:
    expect(app_page.locator("#sidebar .nav-item.active")).to_have_attribute("data-view", "dashboard")
    expect(app_page.locator("#content h2").first).to_have_text("Dashboard")
    expect(app_page.locator("#content")).to_contain_text("Top 5 tasks")
    expect(app_page.locator("#content")).to_contain_text("Energy balance")
    expect(app_page.locator("#content")).to_contain_text("Trophy Case")
    expect(app_page.locator("#content .heatmap-cell")).to_have_count(364 + 5)
    expect(app_page.locator("#content .heatmap-cell[data-tooltip]")).to_have_count(364)
    expect(app_page.locator("#sidebar-trophy-case .badge-tile")).to_have_count(6)
    expect(app_page.locator("#sidebar-trophy-case")).to_contain_text("0/10h")


def test_legacy_tasks_gain_default_energy_and_badge_storage(app_page: Page) -> None:
    normalized = app_page.evaluate(
        """() => normalizeWorkspaceState({
            tasks: [{ id: 'legacy', title: 'Legacy task', status: 'todo', priority: 'med' }],
            user: { level: 1, xp: 0 }
        })"""
    )
    assert normalized["tasks"][0]["energy"] == "deep"
    assert normalized["user"]["badges"] == []


def test_sidebar_navigation_uses_one_icon_per_item(app_page: Page) -> None:
    nav_items = app_page.locator("#sidebar .nav-item")
    assert nav_items.count() == 17
    expect(app_page.locator("#sidebar .nav-item .material-symbols-outlined")).to_have_count(0)
    for index in range(nav_items.count()):
        expect(nav_items.nth(index).locator(":scope > span")).to_have_count(2)
        expect(nav_items.nth(index).locator(":scope > .nav-icon svg")).to_have_count(1)


def test_pathway_steps_fit_iphone_touch_targets(app_page: Page) -> None:
    app_page.set_viewport_size({"width": 393, "height": 852})
    app_page.locator('#bottom-nav .bnav-item[data-view="pathways"]').click()
    app_page.get_by_role("button", name="Create Path").click()
    app_page.locator("#pathway-title").fill("Mobile layout path")
    app_page.locator(".pathway-step-title").nth(0).fill("First mobile milestone")
    app_page.get_by_role("button", name="Add Milestone").click()
    app_page.locator(".pathway-step-title").nth(1).fill("Second mobile milestone")
    app_page.get_by_role("button", name="Save Path").click()

    step = app_page.locator(".pathway-step-item").nth(1)
    checkbox = step.locator('input[type="checkbox"]')
    action = step.locator(".pathway-step-actions button")

    expect(step).to_be_visible()
    expect(checkbox).to_be_visible()
    expect(action).to_be_visible()
    layout = app_page.evaluate(
        """() => {
            const content = document.getElementById('content');
            const step = document.querySelectorAll('.pathway-step-item')[1];
            const label = step.querySelector('.pathway-step-label');
            const checkbox = step.querySelector('input[type="checkbox"]');
            const action = step.querySelector('.pathway-step-actions button');
            return {
                noHorizontalOverflow: content.scrollWidth <= content.clientWidth,
                labelHeight: label.getBoundingClientRect().height,
                checkboxWidth: checkbox.getBoundingClientRect().width,
                checkboxHeight: checkbox.getBoundingClientRect().height,
                checkboxAppearance: getComputedStyle(checkbox).webkitAppearance,
                actionHeight: action.getBoundingClientRect().height,
                actionHasRoom: action.getBoundingClientRect().right <= content.getBoundingClientRect().right
            };
        }"""
    )
    assert layout["noHorizontalOverflow"]
    assert layout["labelHeight"] >= 44
    assert layout["checkboxWidth"] == 22
    assert layout["checkboxHeight"] == 22
    assert layout["checkboxAppearance"] == "none"
    assert layout["actionHeight"] >= 44
    assert layout["actionHasRoom"]

    checkbox.check()
    expect(checkbox).to_be_checked()


def test_new_vault_rejects_short_passphrases(app_url: str, browser) -> None:
    page = browser.new_page()
    page.goto(app_url, wait_until="domcontentloaded")
    page.get_by_role("button", name="I accept — continue").click()
    page.get_by_role("button", name="Create New Vault").click()
    page.locator("#new-key").fill("123456789012345")
    page.get_by_role("button", name="Initialize New Vault").click()
    expect(page.locator("#auth-error")).to_contain_text("at least 16 characters")
    expect(page.locator("#app")).not_to_be_visible()
    page.close()


def test_personal_use_acceptance_precedes_vault_login(app_url: str, browser) -> None:
    page = browser.new_page()
    page.goto(app_url, wait_until="domcontentloaded")

    expect(page.get_by_role("dialog", name="Personal use")).to_be_visible()
    expect(page.locator("#auth-screen")).to_be_visible()
    expect(page.locator("#auth-panel-fetch button").first).to_be_visible()
    page.evaluate("App.loadDemoData()")
    expect(page.locator("#app")).not_to_be_visible()
    page.get_by_role("button", name="I accept — continue").click()
    expect(page.get_by_role("dialog", name="Personal use")).to_have_count(0)
    page.get_by_role("button", name="Load Demo").click()
    expect(page.locator("#app")).to_be_visible()
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
            const cache = await caches.open(keys.find(key => key.startsWith('astralsurge-os-')));
            return (await cache.keys()).map(request => request.url);
        }"""
    )
    assert cached_urls
    assert all(urlparse(url).netloc == urlparse(app_page.url).netloc for url in cached_urls)
    app_shell_paths = (
        "/",
        "/index.html",
        "/index.html?storage=local",
        "/manifest.json",
        "/standalone.html",
    )
    assert all(any(url.endswith(path) for path in app_shell_paths) for url in cached_urls)


def test_mobile_bottom_navigation_and_sidebar_work(app_page: Page) -> None:
    app_page.set_viewport_size({"width": 390, "height": 844})
    app_page.locator('#bottom-nav .bnav-item[data-view="projects"]').click()
    expect(app_page.locator("#content h2").first).to_have_text("Task Board")

    app_page.locator("#bottom-nav .bnav-item").last.click()
    app_page.locator('#sidebar summary:has-text("Privacy")').click()
    app_page.locator('#sidebar .nav-item[data-view="legal"]').click()
    expect(app_page.locator("#content h2").first).to_have_text("Privacy, Security & Use Notices")


def test_mobile_content_scrolls_within_iphone_sized_shell(app_page: Page) -> None:
    app_page.set_viewport_size({"width": 393, "height": 852})
    app_page.locator("#topbar .topbar-group:first-child button").click()
    app_page.locator('#sidebar summary:has-text("Health & Focus")').click()
    app_page.locator('#sidebar .nav-item[data-view="planner"]').click()
    content = app_page.locator("#content")
    layout = content.evaluate(
        """element => ({
            contentFitsViewport: element.clientHeight > 0,
            scrollable: element.scrollHeight > element.clientHeight,
            shellFitsViewport: document.getElementById('app').clientHeight === window.innerHeight
        })"""
    )
    assert layout["contentFitsViewport"]
    assert layout["scrollable"]
    assert layout["shellFitsViewport"]
    content.evaluate("(element) => element.scrollTo(0, element.scrollHeight)")
    assert content.evaluate("(element) => element.scrollTop > 0")


def test_sidebar_dimensions_collapse_navigation(app_page: Page) -> None:
    dimensions = app_page.locator("#sidebar .nav-dimension")
    expect(dimensions).to_have_count(5)
    expect(app_page.locator('#sidebar .nav-dimension:has(.nav-item[data-view="dashboard"])')).to_have_attribute("open", "")
    expect(app_page.locator('#sidebar .nav-item[data-view="workout"]')).to_have_count(1)
    expect(app_page.locator('#sidebar .nav-item[data-view="workout"]')).to_be_hidden()
    app_page.locator('#sidebar summary:has-text("Health & Focus")').click()
    expect(app_page.locator('#sidebar .nav-item[data-view="workout"]')).to_be_visible()
    expect(app_page.locator('#sidebar .nav-dimension:has(.nav-item[data-view="dashboard"])')).not_to_have_attribute("open", "")


def test_calculators_are_removed_from_navigation_and_views(app_page: Page) -> None:
    expect(app_page.locator('#sidebar .nav-item[data-view="finance-tools"]')).to_have_count(0)
    assert app_page.evaluate("'finance-tools' in Views") is False


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
