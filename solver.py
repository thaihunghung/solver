import time
import random

class Solver:
    def __init__(self, playwright, proxy="", headless=True):
        print("Solver.__init__ start")  # LOG DEBUG
        self.playwright = playwright
        self.proxy = proxy
        self.headless = headless

        self.start_browser(self.playwright)
        print("Solver.__init__ end")  # LOG DEBUG

    def terminate(self):
        print("Terminating browser...")  # LOG DEBUG
        self.browser.close()

    def build_page_data(self):
        print("Building page data...")  # LOG DEBUG
        with open("utils/page.html") as f:
            self.page_data = f.read()
        stub = f'<div class="cf-turnstile" data-sitekey="{self.sitekey}"></div>'
        self.page_data = self.page_data.replace("<!-- cf turnstile -->", stub)

    def get_mouse_path(self, x1, y1, x2, y2):
        path = []
        x = x1
        y = y1
        while abs(x - x2) > 3 or abs(y - y2) > 3:
            diff = abs(x - x2) + abs(y - y2)
            speed = random.randint(1, 2)
            if diff < 20:
                speed = random.randint(1, 3)
            else:
                speed *= diff / 45

            if abs(x - x2) > 3:
                if x < x2:
                    x += speed
                elif x > x2:
                    x -= speed
            if abs(y - y2) > 3:
                if y < y2:
                    y += speed
                elif y > y2:
                    y -= speed
            path.append((x, y))

        return path

    def move_to(self, x, y):
        for path in self.get_mouse_path(self.current_x, self.current_y, x, y):
            self.page.mouse.move(path[0], path[1])
            if random.randint(0, 100) > 15:
                time.sleep(random.randint(1, 5) / random.randint(400, 600))

    def solve_invisible(self):
        iterations = 0
        while iterations < 10:
            self.random_x = random.randint(0, self.window_width)
            self.random_y = random.randint(0, self.window_height)
            iterations += 1

            self.move_to(self.random_x, self.random_y)
            self.current_x = self.random_x
            self.current_y = self.random_y
            elem = self.page.query_selector("[name=cf-turnstile-response]")
            if elem:
                val = elem.get_attribute("value")
                if val:
                    print(f"solve_invisible got token: {val}")  # LOG DEBUG
                    return val
            time.sleep(random.randint(2, 5) / random.randint(400, 600))
        print("solve_invisible failed")  # LOG DEBUG
        return "failed"

    def solve_visible(self, timeout=15):
        start_time = time.time()
    
        # Wait for iframe element to appear with correct handle type
        iframe_handle = self.page.evaluate_handle("""
            () => {
                const host = document.querySelector('cf-turnstile, [data-cf-challenge], div#challenge');
                if (host && host.shadowRoot) {
                    return host.shadowRoot.querySelector('iframe');
                }
                return document.querySelector('iframe');
            }
        """)
        iframe = iframe_handle.as_element()
        if not iframe:
            raise Exception("Iframe element not found")
    
        # Wait until iframe has bounding box (visible in viewport)
        while not iframe.bounding_box() and time.time() - start_time < timeout:
            time.sleep(0.2)
    
        if not iframe.bounding_box():
            raise TimeoutError("Timeout waiting for iframe to become visible")
    
        # Wait for challenge response textarea to appear inside iframe
        iframe_content = iframe.content_frame()
        if not iframe_content:
            raise Exception("Unable to get iframe content frame")
    
        textarea = iframe_content.query_selector('textarea[name="cf-turnstile-response"]')
        if not textarea:
            # wait some more or raise error
            start_wait = time.time()
            while not textarea and time.time() - start_wait < timeout:
                time.sleep(0.2)
                textarea = iframe_content.query_selector('textarea[name="cf-turnstile-response"]')
            if not textarea:
                raise TimeoutError("Textarea for response not found inside iframe")
    
        # Evaluate function inside iframe to solve the challenge
        token = self.page.evaluate("""() => {
            // Your solving logic here, e.g. trigger events or extract value
            const textarea = document.querySelector('textarea[name="cf-turnstile-response"]');
            return textarea ? textarea.value : '';
        }""", force_expr=True)
    
        return token


    def solve(self, url, sitekey, invisible=False):
        print(f"Starting solve for {url} with sitekey {sitekey} invisible={invisible}")  # LOG DEBUG
        self.url = url + "/" if not url.endswith("/") else url
        self.sitekey = sitekey
        self.invisible = invisible
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

        self.build_page_data()

        self.page.route(self.url, lambda route: route.fulfill(body=self.page_data, status=200))
        self.page.goto(self.url)
        output = "failed"
        self.current_x = 0
        self.current_y = 0

        self.window_width = self.page.evaluate("window.innerWidth")
        self.window_height = self.page.evaluate("window.innerHeight")
        if self.invisible:
            output = self.solve_invisible()
        else:
            output = self.solve_visible()

        self.context.close()
        print(f"Solve finished with output: {output}")  # LOG DEBUG
        return output

    def start_browser(self, playwright):
        print(f"start_browser called with proxy: {self.proxy} headless: {self.headless}")  # LOG DEBUG
        try:
            if self.proxy:
                self.browser = playwright.firefox.launch(
                    headless=self.headless,
                    proxy={
                        "server": "http://" + self.proxy.split("@")[1],
                        "username": self.proxy.split("@")[0].split(":")[0],
                        "password": self.proxy.split("@")[0].split(":")[1]
                    }
                )
            else:
                self.browser = playwright.firefox.launch(headless=self.headless)
            print("Browser started successfully")  # LOG DEBUG
        except Exception as e:
            print("Error launching browser:", e)  # LOG DEBUG
            raise e
