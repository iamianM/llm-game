"""Shared HTML primitives for static review reports."""

from __future__ import annotations

import html
from collections.abc import Iterable

CSS = """
body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:#f7f4ef;color:#27231f}
main{max-width:1100px;margin:0 auto;padding:32px}
a{color:#7a2d12} code{font-size:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.card,.turn{background:#fff;border:1px solid #d8d0c2;border-radius:8px;padding:16px;margin:12px 0}
.turn summary{cursor:pointer;font-size:22px;font-weight:700}
.meta{color:#655d52;font-size:14px}.success{color:#17633a}.miss{color:#9b2d20}
.pill{display:inline-block;border:1px solid #d8d0c2;border-radius:999px;padding:4px 10px;margin:2px;background:#fff}
.math{border-left:4px solid #17633a}.pull-attempt{border-left:4px solid #d8793f}.interruption{border-left:4px solid #6b3fa0}.memory{border-left:4px solid #7a2d12}
table{border-collapse:collapse;width:100%;background:#fff}th,td{border:1px solid #d8d0c2;padding:8px;text-align:left}
.bar{height:14px;background:#d8793f;display:inline-block;vertical-align:middle}
"""


def page(title: str, body: str) -> str:
    """Wrap body HTML in a self-contained document."""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{CSS}</style></head>"
        f"<body><main><h1>{escape(title)}</h1>{body}</main></body></html>"
    )


def index_page(links: Iterable[tuple[str, str]]) -> str:
    """Render packet index links."""
    items = "".join(
        f"<div class='card'><a href='{escape(href)}'>{escape(label)}</a></div>"
        for label, href in links
    )
    return page("Review Packet", f"<div class='grid'>{items}</div>")


def table_page(title: str, headers: list[str], rows: list[list[str]]) -> str:
    """Render a simple table page."""
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return page(title, f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")


def escape(value: object) -> str:
    """HTML-escape any value."""
    return html.escape(str(value), quote=True)
