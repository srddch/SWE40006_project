import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def register_and_login(page, url, username):
    page.goto(url + "/account.html")
    page.locator("#register-tab").click()
    page.locator("#register-username").fill(username)
    page.locator("#register-password").fill("browser-password")
    page.locator("#confirm-password").fill("browser-password")
    page.locator("#register-form button").click()
    expect(page.locator("#register-message")).to_contain_text("Registration successful")
    expect(page.locator("#login-section")).to_be_visible()
    page.locator("#login-username").fill(username)
    page.locator("#login-password").fill("browser-password")
    page.locator("#login-form button").click()
    expect(page.locator("#current-username")).to_have_text(username)
    expect(page.locator("#save-button")).to_be_enabled()


def test_complete_user_workflow_and_reload(page, live_url):
    register_and_login(page, live_url, "browseralice")
    page.locator("#task-title").fill("Original task")
    page.locator("#task-description").fill("Persistent details")
    page.locator("#save-button").click()
    expect(page.locator(".task-card h3")).to_have_text("Original task")
    page.reload()
    expect(page.locator(".task-card h3")).to_have_text("Original task")
    page.locator(".edit-button").click()
    page.locator("#task-title").fill("Updated task")
    page.locator("#save-button").click()
    expect(page.locator(".task-card h3")).to_have_text("Updated task")
    page.locator(".task-status input").check()
    expect(page.locator("#completed-tasks")).to_have_text("1")
    page.locator(".delete-button").click()
    expect(page.locator("#empty-message")).to_be_visible()
    expect(page.locator("#total-tasks")).to_have_text("0")
    page.locator("#logout-button").click()
    expect(page.locator("#login-section")).to_be_visible()
    page.goto(live_url + "/index.html")
    expect(page.locator("#login-section")).to_be_visible()


def test_browser_users_have_separate_task_lists(browser, live_url):
    context_a = browser.new_context()
    context_b = browser.new_context()
    try:
        alice = context_a.new_page()
        register_and_login(alice, live_url, "firstuser")
        alice.locator("#task-title").fill("Only first user")
        alice.locator("#save-button").click()
        expect(alice.locator(".task-card")).to_have_count(1)
        bob = context_b.new_page()
        register_and_login(bob, live_url, "seconduser")
        expect(bob.locator(".task-card")).to_have_count(0)
        alice.reload()
        expect(alice.locator(".task-card h3")).to_have_text("Only first user")
    finally:
        context_a.close()
        context_b.close()
