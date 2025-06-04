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

    def solve_visible(self, timeout=30):
        print(f"Starting solve_visible... URL: {self.page.url}")
        start_time = time.time()

        # Try to find the Shadow host or iframe directly
        iframe = None
        while not iframe and time.time() - start_time < timeout:
            # First try direct iframe selector
            iframe = self.page.query_selector("iframe[src*='challenges.cloudflare.com']")
            if not iframe:
                # Try accessing via Shadow DOM
                iframe = self.page.evaluate_handle("""
                    () => {
                        const host = document.querySelector('cf-turnstile, [data-cf-challenge], div#challenge');
                        if (host && host.shadowRoot) {
                            return host.shadowRoot.querySelector('iframe');
                        }
                        return document.querySelector('iframe');
                    }
                """)
            time.sleep(0.1)
        if not iframe:
            print("Error: Iframe not found in Shadow DOM or main DOM")
            return "failed"

        # Wait for iframe bounding box
        while not iframe.bounding_box() and time.time() - start_time < timeout:
            time.sleep(0.1)
        if not iframe.bounding_box():
            print("Error: Iframe bounding box not available")
            return "failed"

        # Calculate coordinates for iframe
        try:
            box = iframe.bounding_box()
            x = box["x"] + random.randint(5, 12)
            y = box["y"] + random.randint(5, 12)
            self.move_to(x, y)
            self.current_x = x
            self.current_y = y
        except Exception as e:
            print(f"Error accessing iframe bounding box: {e}")
            return "failed"

        # Access iframe content
        framepage = iframe.content_frame()
        if not framepage:
            print("Error: Could not access iframe content")
            return "failed"

        # Wait for checkbox
        checkbox = None
        while not checkbox and time.time() - start_time < timeout:
            checkbox = framepage.query_selector("input[type=checkbox]")
            time.sleep(0.1)
        if not checkbox:
            print("Error: Checkbox not found in iframe")
            return "failed"

        # Calculate checkbox coordinates
        try:
            box = checkbox.bounding_box()
            if not box:
                print("Error: Checkbox bounding box not available")
                return "failed"
            width = box["width"]
            height = box["height"]
            x = box["x"] + width / 5 + random.randint(int(width / 5), int(width - width / 5))
            y = box["y"] + height / 5 + random.randint(int(height / 5), int(height - height / 5))
            self.move_to(x, y)
            self.current_x = x
            self.current_y = y
