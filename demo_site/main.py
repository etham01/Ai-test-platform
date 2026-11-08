from __future__ import annotations

import secrets
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from demo_site.data import (
    NEXT_ORDER_ID,
    ORDERS,
    PRODUCTS,
    PRODUCTS_BY_ID,
    SESSIONS,
    USERS,
)

BASE_DIR = Path(__file__).resolve().parent
COOKIE_NAME = "demo_session"

app = FastAPI(title="DemoShop", description="SmartTest local demo site")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _session(request: Request) -> tuple[str | None, dict]:
    sid = request.cookies.get(COOKIE_NAME)
    if not sid:
        return None, {}
    return sid, SESSIONS.get(sid, {})


def _save_session(response: RedirectResponse, sid: str | None, session: dict) -> None:
    if sid is None:
        sid = secrets.token_urlsafe(24)
        response.set_cookie(
            COOKIE_NAME,
            sid,
            httponly=True,
            samesite="lax",
            max_age=3600,
        )
    SESSIONS[sid] = session


def _context(request: Request, **extra) -> dict:
    _, session = _session(request)
    cart = session.get("cart", {})
    return {
        "request": request,
        "user": session.get("user"),
        "cart_count": sum(int(value) for value in cart.values()),
        **extra,
    }


def _safe_next(value: str | None) -> str:
    if not value:
        return "/products"
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/products"
    return value


def _cart_details(session: dict) -> tuple[list[dict], float]:
    items: list[dict] = []
    total = 0.0
    for raw_id, quantity in session.get("cart", {}).items():
        product = PRODUCTS_BY_ID.get(int(raw_id))
        if not product:
            continue
        qty = int(quantity)
        subtotal = round(product["price"] * qty, 2)
        total += subtotal
        items.append({**product, "quantity": qty, "subtotal": subtotal})
    return items, round(total, 2)


def _render(request: Request, name: str, *, status_code: int = 200, **extra):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=_context(request, **extra),
        status_code=status_code,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "DemoShop"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _render(request, "home.html", featured=PRODUCTS[:3])


@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    return _render(request, "about.html")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/products"):
    return _render(request, "login.html", next_url=_safe_next(next), error=None)


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/products"),
):
    user = USERS.get(username.strip())
    if user is None or user["password"] != password:
        return _render(
            request,
            "login.html",
            status_code=400,
            next_url=_safe_next(next),
            error="用户名或密码不正确，请使用 demo / demo123。",
        )

    sid, session = _session(request)
    session["user"] = {"username": username.strip(), "display_name": user["display_name"]}
    response = RedirectResponse(_safe_next(next), status_code=303)
    _save_session(response, sid, session)
    return response


@app.get("/logout")
def logout(request: Request):
    sid, session = _session(request)
    if sid:
        SESSIONS.pop(sid, None)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.get("/products", response_class=HTMLResponse)
def products(request: Request):
    return _render(request, "products.html", products=PRODUCTS)


@app.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(request: Request, product_id: int):
    product = PRODUCTS_BY_ID.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return _render(request, "product_detail.html", product=product)


@app.post("/cart/add")
def add_to_cart(
    request: Request,
    product_id: int = Form(...),
    quantity: int = Form(1),
):
    if product_id not in PRODUCTS_BY_ID:
        raise HTTPException(status_code=404, detail="商品不存在")
    sid, session = _session(request)
    cart = session.setdefault("cart", {})
    current = int(cart.get(str(product_id), 0))
    cart[str(product_id)] = max(1, min(99, current + max(1, min(99, quantity))))
    response = RedirectResponse("/cart", status_code=303)
    _save_session(response, sid, session)
    return response


@app.post("/cart/remove")
def remove_from_cart(request: Request, product_id: int = Form(...)):
    sid, session = _session(request)
    session.get("cart", {}).pop(str(product_id), None)
    response = RedirectResponse("/cart", status_code=303)
    _save_session(response, sid, session)
    return response


@app.get("/cart", response_class=HTMLResponse)
def cart(request: Request):
    _, session = _session(request)
    items, total = _cart_details(session)
    return _render(request, "cart.html", items=items, total=total)


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request):
    _, session = _session(request)
    if not session.get("user"):
        return RedirectResponse("/login?next=/checkout", status_code=303)
    items, total = _cart_details(session)
    return _render(request, "checkout.html", items=items, total=total, error=None)


@app.post("/checkout", response_class=HTMLResponse)
def checkout_submit(
    request: Request,
    full_name: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
):
    global NEXT_ORDER_ID
    sid, session = _session(request)
    if not session.get("user"):
        return RedirectResponse("/login?next=/checkout", status_code=303)
    items, total = _cart_details(session)
    if not items:
        return RedirectResponse("/cart", status_code=303)

    order_id = NEXT_ORDER_ID
    NEXT_ORDER_ID += 1
    ORDERS[order_id] = {
        "id": order_id,
        "user": session["user"]["username"],
        "items": items,
        "total": total,
        "full_name": full_name.strip(),
        "address": address.strip(),
        "phone": phone.strip(),
    }
    session["cart"] = {}
    response = RedirectResponse(f"/order/{order_id}", status_code=303)
    _save_session(response, sid, session)
    return response


@app.get("/order/{order_id}", response_class=HTMLResponse)
def order_detail(request: Request, order_id: int):
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return _render(request, "order.html", order=order)
