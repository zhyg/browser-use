"""
Unit tests for browser navigation functionality.

Tests core browser navigation operations including:
- Page loading and navigation
- URL handling and redirects
- Browser history management
- Navigation error handling
"""

import asyncio
import pytest
from pytest_httpserver import HTTPServer

from browser_use.browser import BrowserSession
from browser_use.browser.profile import BrowserProfile


@pytest.fixture
def test_server(httpserver: HTTPServer):
	"""Create a test HTTP server with various navigation scenarios."""

	# Home page
	httpserver.expect_request('/').respond_with_data(
		'<html><head><title>Home Page</title></head><body><h1>Welcome</h1><a href="/page1">Link to Page 1</a></body></html>',
		content_type='text/html',
	)

	# Page 1 - Normal page
	httpserver.expect_request('/page1').respond_with_data(
		'<html><head><title>Page 1</title></head><body><h1>Page 1</h1><a href="/page2">Link to Page 2</a></body></html>',
		content_type='text/html',
	)

	# Page 2 - Page with redirect
	httpserver.expect_request('/page2').respond_with_data(
		'<html><head><title>Page 2</title><meta http-equiv="refresh" content="0; url=/page3"></head><body><h1>Redirecting...</h1></body></html>',
		content_type='text/html',
	)

	# Page 3 - Final destination
	httpserver.expect_request('/page3').respond_with_data(
		'<html><head><title>Page 3 - Final</title></head><body><h1>Final Page</h1></body></html>',
		content_type='text/html',
	)

	# Error page
	httpserver.expect_request('/error').respond_with_data(
		'<html><head><title>Error</title></head><body><h1>404 Not Found</h1></body></html>',
		content_type='text/html',
		status=404,
	)

	# Slow loading page
	httpserver.expect_request('/slow').respond_with_data(
		'<html><head><title>Slow Page</title></head><body><h1>Slow Loading Page</h1></body></html>',
		content_type='text/html',
		headers={'Cache-Control': 'no-cache'},
	)

	return httpserver


@pytest.mark.asyncio
async def test_basic_navigation():
	"""Test basic page navigation functionality."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Navigate to a simple page
		test_url = "data:text/html,<html><head><title>Test Page</title></head><body><h1>Test Content</h1></body></html>"
		page = await session.new_page(test_url)

		# Verify page loaded
		assert page is not None
		title = await page.title()
		assert title == "Test Page"

		# Verify we can get page content
		content = await page.content()
		assert "Test Content" in content

	finally:
		await session.kill()


@pytest.mark.asyncio
async def test_navigation_with_test_server(test_server):
	"""Test navigation using local test server."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Navigate to home page
		page = await session.new_page(test_server.url_for('/'))
		assert page is not None

		# Verify initial page
		title = await page.title()
		assert title == "Home Page"

		# Navigate to page 1
		await page.goto(test_server.url_for('/page1'))
		title = await page.title()
		assert title == "Page 1"

		# Verify we can find and click a link
		link_element = await page.wait_for_selector('a[href="/page2"]')
		assert link_element is not None

	finally:
		await session.kill()


@pytest.mark.asyncio
async def test_navigation_error_handling():
	"""Test navigation error handling for invalid URLs."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Try to navigate to invalid URL
		with pytest.raises(Exception):
			await session.new_page("invalid://url")

		# Try to navigate to non-existent page
		with pytest.raises(Exception):
			await session.new_page("http://localhost:99999/nonexistent")

	finally:
		await session.kill()


@pytest.mark.asyncio
async def test_multiple_page_navigation():
	"""Test navigation with multiple pages/tabs."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Create first page
		page1 = await session.new_page("data:text/html,<html><head><title>Page 1</title></head><body>Page 1</body></html>")
		assert page1 is not None

		# Create second page
		page2 = await session.new_page("data:text/html,<html><head><title>Page 2</title></head><body>Page 2</body></html>")
		assert page2 is not None

		# Verify both pages have different content
		title1 = await page1.title()
		title2 = await page2.title()
		assert title1 == "Page 1"
		assert title2 == "Page 2"
		assert title1 != title2

		# Verify session has multiple pages
		pages = session.get_pages()
		assert len(pages) >= 2

	finally:
		await session.kill()


@pytest.mark.asyncio
async def test_page_reload():
	"""Test page reload functionality."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Navigate to a page
		page = await session.new_page("data:text/html,<html><head><title>Reload Test</title></head><body>Content</body></html>")
		assert page is not None

		# Get initial content
		initial_content = await page.content()

		# Reload the page
		await page.reload()

		# Verify content is still there after reload
		reloaded_content = await page.content()
		assert "Reload Test" in reloaded_content
		assert "Content" in reloaded_content

	finally:
		await session.kill()


@pytest.mark.asyncio
async def test_navigation_timing():
	"""Test navigation timing and page load events."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Navigate to a simple page and measure timing
		start_time = asyncio.get_event_loop().time()
		page = await session.new_page("data:text/html,<html><head><title>Timing Test</title></head><body>Timing test content</body></html>")
		end_time = asyncio.get_event_loop().time()

		# Verify navigation completed in reasonable time (< 10 seconds)
		navigation_time = end_time - start_time
		assert navigation_time < 10.0
		assert page is not None

		# Verify page is fully loaded
		title = await page.title()
		assert title == "Timing Test"

	finally:
		await session.kill()


@pytest.mark.asyncio
async def test_back_forward_navigation():
	"""Test browser back and forward navigation."""
	session = BrowserSession(
		browser_profile=BrowserProfile(
			headless=True,
			keep_alive=True,
		)
	)

	try:
		await session.start()

		# Navigate to first page
		page = await session.new_page("data:text/html,<html><head><title>Page A</title></head><body>Page A content</body></html>")
		assert await page.title() == "Page A"

		# Navigate to second page
		await page.goto("data:text/html,<html><head><title>Page B</title></head><body>Page B content</body></html>")
		assert await page.title() == "Page B"

		# Navigate to third page
		await page.goto("data:text/html,<html><head><title>Page C</title></head><body>Page C content</body></html>")
		assert await page.title() == "Page C"

		# Go back to previous page
		await page.go_back()
		await asyncio.sleep(0.5)  # Wait for navigation to complete
		assert await page.title() == "Page B"

		# Go back again
		await page.go_back()
		await asyncio.sleep(0.5)
		assert await page.title() == "Page A"

		# Go forward
		await page.go_forward()
		await asyncio.sleep(0.5)
		assert await page.title() == "Page B"

	finally:
		await session.kill()