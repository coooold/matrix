"""Capture the pinned OMEGA browser reference without changing its files."""
import argparse
from functools import partial
import http.server
import json
import hashlib
import urllib.request
from pathlib import Path
import subprocess
import threading
from playwright.sync_api import sync_playwright

PIN = 'a4e2a52e3b5ce1c2f0f0161c8dea624bd553c7f0'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--output', type=Path, default=Path('artifacts/reference'))
    parser.add_argument('--chromium', default='/usr/bin/chromium')
    args = parser.parse_args()
    if subprocess.check_output(['git', '-C', str(args.checkout), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        parser.error('reference checkout must match the pinned SHA')
    if subprocess.check_output(['git', '-C', str(args.checkout), 'status', '--porcelain'], text=True).strip():
        parser.error('reference checkout must be unchanged')
    args.output.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(args.checkout.resolve())))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = {'reference_commit': PIN, 'viewport': [1920, 1080], 'scale': 1,
              'sandbox': 'container-isolated headless Chromium', 'page_errors': [], 'failed_requests': [], 'scenarios': {}, 'verified_resources': []}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.chromium, headless=True)
            report['browser'] = browser.version
            context = browser.new_context(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1)
            # Chromium may not inherit the container's custom root store. Fetch
            # external assets through Python's verified system-CA HTTPS transport.
            def verified_asset(route):
                try:
                    request = urllib.request.Request(route.request.url, headers={'User-Agent': route.request.headers.get('user-agent', '')})
                    with urllib.request.urlopen(request, timeout=20) as response:
                        body = response.read()
                        headers = {k: v for k, v in response.headers.items() if k.lower() not in ('content-length', 'transfer-encoding', 'content-encoding')}
                        route.fulfill(status=response.status, headers=headers, body=body)
                        report['verified_resources'].append({'url': route.request.url, 'sha256': hashlib.sha256(body).hexdigest(), 'tls': 'system CA verified'})
                except Exception as error:
                    report['failed_requests'].append({'url': route.request.url, 'error': str(error)})
                    route.abort()
            context.route('https://**/*', verified_asset)
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
            page.on('requestfailed', lambda request: report['failed_requests'].append({'url': request.url, 'error': request.failure}))
            page.goto(f'http://127.0.0.1:{server.server_port}', wait_until='load')
            page.screenshot(path=str(args.output / '01-lock.png'))
            page.locator('#input-password').fill('reference-only')
            page.locator('#input-password').press('Enter')
            page.locator('#desktop').wait_for(state='visible', timeout=15000)
            page.screenshot(path=str(args.output / '02-desktop.png'))
            def launch(app):
                if not page.locator('#start-menu').is_visible():
                    page.locator('#start-btn').click()
                page.locator(f'#start-menu [data-app="{app}"]').click()
                page.locator(f'#win-{app}').wait_for(state='visible')
                page.wait_for_timeout(350)
            page.locator('#start-btn').click()
            page.screenshot(path=str(args.output / '03-menu.png'))
            launch('calculator')
            launch('notes')
            page.screenshot(path=str(args.output / '04-overlap.png'))
            page.locator('#win-notes .minimize').click()
            page.wait_for_timeout(400)
            page.screenshot(path=str(args.output / '05-minimize.png'))
            page.locator('#taskbar-notes').click()
            page.wait_for_timeout(400)
            header = page.locator('#win-notes .window-header').bounding_box()
            page.mouse.move(header['x'] + 80, header['y'] + 15)
            page.mouse.down()
            page.mouse.move(3, 200, steps=20)
            page.mouse.up()
            page.screenshot(path=str(args.output / '06-snap.png'))
            report['scenarios']['left_snap'] = page.locator('#win-notes').evaluate('(el) => ({left:el.style.left,width:el.style.width})')
            page.locator('.notification-btn').click()
            page.screenshot(path=str(args.output / '07-notifications.png'))
            launch('files')
            page.screenshot(path=str(args.output / '08-files.png'))
            launch('settings')
            page.screenshot(path=str(args.output / '09-settings.png'))
            report['scenarios']['windows'] = page.locator('.os-window').count()
            context.tracing.stop(path=str(args.output / 'trace.zip'))
            browser.close()
    finally:
        server.shutdown()
        (args.output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
