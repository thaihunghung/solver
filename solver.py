import time
import random

class Solver:
    def __init__(self, playwright, proxy="", headless=True):
        self.playwright = playwright
        self.proxy = proxy
        self.headless = headless

        self.start_browser(self.playwright)
            
    def terminate(self):
        self.browser.close()

    def build_page_data(self):
        # this builds a custom page with the sitekey so we do not have to load the actual page, taking less bandwidth
        with open("utils/page.html") as f:
            self.page_data = f.read()
        stub = f"<div style='width: 42px; height: 45px;' class=\"cf-turnstile\" data-sitekey=\"{self.sitekey}\"></div>"
        self.page_data = self.page_data.replace("<!-- cf turnstile -->", stub)

    def get_mouse_path(self, x1, y1, x2, y2):
        # calculate the path to x2 and y2 from x1 and y1
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
                if elem.get_attribute("value"):
                    return elem.get_attribute("value")
            time.sleep(random.randint(2, 5) / random.randint(400, 600))
        return "failed"
            
    def solve_visible(self):
        # Tìm <div class="cf-turnstile">
        turnstile_div = self.page.query_selector(".cf-turnstile")
        while not turnstile_div:
            turnstile_div = self.page.query_selector(".cf-turnstile")
            time.sleep(0.1)
        box = turnstile_div.bounding_box()
        for _ in range(random.randint(5, 6)):
            x = box["x"] + random.randint(5, int(box["width"] - 5))
            y = box["y"] + random.randint(5, int(box["height"] - 5))
            self.move_to(x, y)
            self.current_x = x
            self.current_y = y
            time.sleep(random.uniform(0.3, 0.6))
            self.page.mouse.click(x, y)
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
                value = elem.get_attribute("value")
                if value:
                    return value
            time.sleep(random.uniform(0.3, 0.6))
        return "failed"

    def solve(self, url, sitekey, invisible=False):
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
        return output
    
    def start_browser(self, playwright):
        if self.proxy:
            self.browser = playwright.firefox.launch(headless=self.headless, proxy={
                "server": "http://" + self.proxy.split("@")[1],
                "username": self.proxy.split("@")[0].split(":")[0],
                "password": self.proxy.split("@")[0].split(":")[1]
            })
        else:
            self.browser = playwright.firefox.launch(headless=self.headless)
