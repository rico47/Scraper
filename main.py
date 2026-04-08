import asyncio
import os
import json
from typing import List, Optional
from playwright.async_api import async_playwright
import google.generativeai as genai
from openai import OpenAI
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# Konfiguracja
load_dotenv()
BASE_DIR = os.getcwd()
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")

DEFAULT_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {"active": "Domyślny", "projects": {}}
    return {"active": "Domyślny", "projects": {}}

def save_projects(data: dict):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class AdvancedWebAgent:
    async def get_content(self, context, url: str, is_twitter: bool = False):
        page = await context.new_page()
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pl-PL,pl;q=0.9"
        })
        try:
            print(f"Scrapowanie: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if is_twitter or "x.com" in url or "twitter.com" in url:
                try: await page.wait_for_selector('[data-testid="tweetText"]', timeout=15000)
                except: pass
                await page.evaluate("window.scrollBy(0, 1500)")
                await asyncio.sleep(3)
                tweets = await page.query_selector_all('[data-testid="tweetText"]')
                texts = [await t.inner_text() for t in tweets]
                content = "\n--- TWEET ---\n".join(texts)
            else:
                await page.evaluate("""() => {
                    const toRemove = ['script', 'style', 'nav', 'footer', 'header', 'noscript', 'iframe', 'ads'];
                    toRemove.forEach(tag => document.querySelectorAll(tag).forEach(el => el.remove()));
                }""")
                content = await page.inner_text('body')
            await page.close()
            return f"\nŹRÓDŁO: {url}\nTREŚĆ:\n{' '.join(content.split())[:12000]}" 
        except Exception as e:
            await page.close()
            return f"Błąd na stronie {url}: {str(e)}"

    async def run_pipeline(self, provider: str, api_key: str, urls: List[str], user_task: str, report_format: str, is_twitter: bool, headless: bool):
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=headless, args=["--disable-blink-features=AutomationControlled"])
            tasks = [self.get_content(context, url, is_twitter) for url in urls if url.strip()]
            results = await asyncio.gather(*tasks)
            all_text = "\n".join(results)
            await context.close()
        prompt = f"PRZEDMIOT ANALIZY:\n{all_text}\n\nCEL: {user_task}\nFORMAT: {report_format}\n\nOdpowiedz po polsku."
        try:
            if provider == "gemini":
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                return model.generate_content(prompt).text
            else:
                client = OpenAI(api_key=api_key, base_url=None if provider == "openai_api" else api_key)
                model_name = "gpt-4o" if provider == "openai_api" else "local-model"
                resp = client.chat.completions.create(model=model_name, messages=[{"role": "user", "content": prompt}], temperature=0.2)
                return resp.choices[0].message.content
        except Exception as e: return f"Błąd LLM: {str(e)}"

agent = AdvancedWebAgent()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = load_projects()
    active_name = data.get("active", "Domyślny")
    p = data["projects"].get(active_name, {})
    return templates.TemplateResponse(request=request, name="index.html", context={
        "report": None, "projects": data["projects"], "active_project": active_name,
        "api_key": p.get("api_key", DEFAULT_GEMINI_KEY),
        "provider": p.get("provider", "gemini"),
        "urls": p.get("urls", ""),
        "task": p.get("task", ""),
        "format": p.get("format", "Tabela z kluczowymi informacjami."),
        "is_twitter": p.get("is_twitter", False)
    })

@app.post("/save_project")
async def save_project(
    name: str = Form(...), provider: str = Form(...), api_key: str = Form(...),
    urls: str = Form(...), task: str = Form(...), format: str = Form(...),
    is_twitter: bool = Form(False)
):
    data = load_projects()
    data["projects"][name] = {
        "provider": provider, "api_key": api_key, "urls": urls,
        "task": task, "format": format, "is_twitter": is_twitter
    }
    data["active"] = name
    save_projects(data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/load/{name}")
async def load_project(name: str):
    data = load_projects()
    if name in data["projects"]:
        data["active"] = name
        save_projects(data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{name}")
async def delete_project(name: str):
    data = load_projects()
    if name in data["projects"]:
        del data["projects"][name]
        if data["active"] == name:
            data["active"] = list(data["projects"].keys())[0] if data["projects"] else "Domyślny"
        save_projects(data)
    return RedirectResponse(url="/", status_code=303)

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request, provider: str = Form(...), api_key: str = Form(...),
    urls: str = Form(...), task: str = Form(...), format: str = Form(...),
    is_twitter: bool = Form(False), show_browser: bool = Form(False),
    project_name: str = Form("Domyślny")
):
    # Automatyczny zapis przy analizie do aktualnego projektu
    data = load_projects()
    current_vals = {"provider": provider, "api_key": api_key, "urls": urls, "task": task, "format": format, "is_twitter": is_twitter}
    data["projects"][project_name] = current_vals
    data["active"] = project_name
    save_projects(data)

    url_list = [u.strip() for u in urls.split('\n') if u.strip()]
    final_key = api_key if api_key.strip() else (DEFAULT_GEMINI_KEY if provider == "gemini" else DEFAULT_OPENAI_KEY)
    
    report = await agent.run_pipeline(provider, final_key, url_list, task, format, is_twitter, not show_browser)
    
    return templates.TemplateResponse(request=request, name="index.html", context={
        "report": report, "projects": data["projects"], "active_project": project_name, **current_vals
    })

if __name__ == "__main__":
    if not os.path.exists(USER_DATA_DIR): os.makedirs(USER_DATA_DIR)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
