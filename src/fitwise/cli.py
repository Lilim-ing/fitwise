"""CLI."""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import sizing
from .answer import answer as answer_fn
from .knowledge import KnowledgeBase

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

app = typer.Typer(add_completion=False, help="fitwise · 内衣尺码与穿着知识助手")
console = Console()

_KB: KnowledgeBase | None = None


def kb() -> KnowledgeBase:
    global _KB
    if _KB is None:
        _KB = KnowledgeBase()
    return _KB


@app.command()
def ask(
    question: str = typer.Argument(..., help="问题"),
    underbust: float = typer.Option(0, help="下胸围 cm"),
    bust: float = typer.Option(0, help="上胸围 cm"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """问一个尺码或穿着问题。"""
    result = answer_fn(
        question,
        kb(),
        underbust=underbust or None,
        bust=bust or None,
    )
    if json_out:
        console.print_json(json.dumps(result, ensure_ascii=False))
        return
    style = "red" if result["refused"] else "green"
    console.print(Panel(result["answer"], border_style=style, title="回答" if result["ok"] else "拒答"))
    if result["citations"]:
        table = Table(show_header=True, header_style="bold", title="引用")
        for col in ("id", "标题", "来源", "相关度"):
            table.add_column(col)
        for c in result["citations"]:
            table.add_row(c["id"], c["title"], c["source"], f"{c['score']:.3f}")
        console.print(table)


@app.command()
def size(
    underbust: float = typer.Option(..., help="下胸围 cm"),
    bust: float = typer.Option(..., help="上胸围 cm"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """按测量值算尺码。"""
    result = sizing.compute(underbust, bust)
    if json_out:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
        return
    if not result.ok:
        console.print(f"[red]无法计算[/red] {'；'.join(result.notes)}")
        raise typer.Exit(code=2)
    table = Table(show_header=False, header_style="bold")
    table.add_row("推荐尺码", f"[bold]{result.size}[/bold]")
    table.add_row("围差", f"{result.diff_cm} cm")
    table.add_row("姐妹尺码", " / ".join(result.sister_sizes) or "—")
    table.add_row("置信度", result.confidence)
    console.print(table)
    for note in result.notes:
        console.print(f"[yellow]{note}[/yellow]")


@app.command()
def search(
    query: str = typer.Argument(...),
    k: int = typer.Option(3, help="返回条数"),
) -> None:
    """检索知识库。"""
    hits = kb().search(query, k=k)
    if not hits:
        console.print("[yellow]没有命中[/yellow]")
        raise typer.Exit(code=1)
    table = Table(show_header=True, header_style="bold")
    for col in ("id", "标题", "相关度", "内容"):
        table.add_column(col, overflow="fold")
    for h in hits:
        table.add_row(h.id, h.title, f"{h.score:.3f}", h.content[:40] + "…")
    console.print(table)


if __name__ == "__main__":
    app()
