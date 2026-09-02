"""Helpers for rendering embed-like bot messages as Components V2 panels."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Optional

import discord

__all__ = (
    "Panel",
    "PanelLayoutView",
    "cv2_send",
    "embed_to_view",
    "embeds_to_view",
    "panel_with_actions",
    "send_panel",
    "sync_panel_message",
)

_MAX_TEXT_DISPLAY = 3800


def _asset_url(value: Any) -> Optional[str]:
    url = getattr(value, "url", None)
    return str(url) if url else None


def _append_text_chunks(container_children: list[discord.ui.Item], lines: Iterable[str]) -> None:
    current = ""
    for raw_line in lines:
        line = str(raw_line)
        candidate = line if not current else f"{current}\n\n{line}"
        if len(candidate) > _MAX_TEXT_DISPLAY and current:
            container_children.append(discord.ui.TextDisplay(current))
            current = line
        else:
            current = candidate

    if current:
        container_children.append(discord.ui.TextDisplay(current))


def _add_embed_parts(container_children: list[discord.ui.Item], embed: discord.Embed) -> None:
    author_name = getattr(embed.author, "name", None)
    if author_name:
        container_children.append(discord.ui.TextDisplay(f"> {author_name}"))

    if embed.title:
        title = f"## {embed.title}"
        if embed.url:
            title = f"## [{embed.title}]({embed.url})"
        container_children.append(discord.ui.TextDisplay(title))

    if author_name or embed.title:
        container_children.append(discord.ui.Separator(visible=False))

    if embed.description:
        container_children.append(discord.ui.TextDisplay(embed.description))

    media_urls: list[str] = []
    thumb_url = _asset_url(embed.thumbnail)
    image_url = _asset_url(embed.image)
    if thumb_url:
        media_urls.append(thumb_url)
    if image_url:
        media_urls.append(image_url)
    if media_urls:
        container_children.append(discord.ui.MediaGallery(*(discord.MediaGalleryItem(url) for url in media_urls)))

    if embed.fields:
        if embed.description or embed.title or author_name or media_urls:
            container_children.append(discord.ui.Separator())
        _append_text_chunks(container_children, (f"**{field.name}**\n{field.value}" for field in embed.fields))

    footer_text = getattr(embed.footer, "text", None)
    if footer_text:
        container_children.append(discord.ui.Separator())
        container_children.append(discord.ui.TextDisplay(f"-# {footer_text}"))


def _append_view_links(container_children: list[discord.ui.Item], source: Optional[discord.ui.View]) -> None:
    if source is None:
        return

    links: list[str] = []
    for child in list(getattr(source, "children", ())):
        if isinstance(child, discord.ui.Button) and child.url:
            label = child.label or "Open"
            links.append(f"[{label}]({child.url})")

    if links:
        container_children.append(discord.ui.Separator())
        container_children.append(discord.ui.TextDisplay(" | ".join(links)))


def embeds_to_view(
    embeds: Optional[Sequence[discord.Embed]],
    view: Optional[discord.ui.View] = None,
    *,
    timeout: Optional[float] = None,
) -> discord.ui.LayoutView:
    children: list[discord.ui.Item] = []
    for index, embed in enumerate(embeds or []):
        if index:
            children.append(discord.ui.Separator())
        _add_embed_parts(children, embed)

    _append_view_links(children, view)

    if not children:
        children.append(discord.ui.TextDisplay("\u200b"))

    layout = discord.ui.LayoutView(timeout=timeout if timeout is not None else getattr(view, "timeout", 180))
    layout.add_item(discord.ui.Container(*children))
    return layout


def _has_interactive_children(source: Optional[discord.ui.View]) -> bool:
    if source is None:
        return False
    for child in list(getattr(source, "children", ())):
        if isinstance(child, discord.ui.Button) and not child.url:
            return True
        if isinstance(child, (discord.ui.Select, discord.ui.UserSelect, discord.ui.RoleSelect, discord.ui.ChannelSelect, discord.ui.MentionableSelect)):
            return True
    return False


class PanelLayoutView(discord.ui.LayoutView):
    """LayoutView that merges an embed panel with interactive controls."""

    def __init__(
        self,
        embed: Optional[discord.Embed],
        controls: Optional[discord.ui.View] = None,
        *,
        timeout: Optional[float] = None,
    ) -> None:
        resolved_timeout = timeout if timeout is not None else getattr(controls, "timeout", 180)
        super().__init__(timeout=resolved_timeout)
        self.controls = controls

        children: list[discord.ui.Item] = []
        if embed is not None:
            panel = embeds_to_view([embed])
            children.extend(list(panel.children[0].children))
        elif not controls or not controls.children:
            children.append(discord.ui.TextDisplay("\u200b"))

        if controls and controls.children:
            interactive = list(controls.children)
            if interactive:
                children.append(discord.ui.Separator())
                for index in range(0, len(interactive), 5):
                    for item in interactive[index : index + 5]:
                        item._view = None
                    children.append(discord.ui.ActionRow(*interactive[index : index + 5]))

        self.add_item(discord.ui.Container(*children))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.controls and hasattr(self.controls, "interaction_check"):
            return await self.controls.interaction_check(interaction)
        return True

    async def on_timeout(self) -> None:
        if self.controls and hasattr(self.controls, "on_timeout"):
            await self.controls.on_timeout()


def panel_with_actions(
    embed: Optional[discord.Embed],
    controls: Optional[discord.ui.View] = None,
    *,
    timeout: Optional[float] = None,
) -> PanelLayoutView:
    return PanelLayoutView(embed, controls, timeout=timeout)


def embed_to_view(
    embed: Optional[discord.Embed],
    view: Optional[discord.ui.View] = None,
    *,
    timeout: Optional[float] = None,
) -> discord.ui.LayoutView:
    if view is not None and embed is not None:
        view.panel_embed = embed
    if _has_interactive_children(view):
        return panel_with_actions(embed, view, timeout=timeout)
    return embeds_to_view([embed] if embed is not None else [], view=view, timeout=timeout)


async def send_panel(
    ctx,
    embed: discord.Embed,
    controls: discord.ui.View,
    **kwargs,
) -> discord.Message:
    controls.panel_embed = embed
    message = await ctx.send(view=panel_with_actions(embed, controls), **kwargs)
    controls.message = message
    return message


async def sync_panel_message(
    controls: discord.ui.View,
    *,
    embed: Optional[discord.Embed] = None,
    disable: bool = True,
    skip_labels: tuple[str, ...] = (),
) -> None:
    if disable:
        for item in controls.children:
            label = getattr(item, "label", None)
            if label in skip_labels:
                continue
            item.disabled = True

    message = getattr(controls, "message", None)
    panel_embed = embed or getattr(controls, "panel_embed", None)
    if not message or not panel_embed:
        return

    try:
        await message.edit(view=panel_with_actions(panel_embed, controls))
    except Exception:
        pass


class Panel:
    """Embed-compatible wrapper that outputs a Components V2 LayoutView."""

    def __init__(self, *, title: Optional[str] = None, description: Optional[str] = None, color: Any = None) -> None:
        self.title = title
        self.description = description
        self.color = color
        self._author_name: Optional[str] = None
        self._footer_text: Optional[str] = None
        self._fields: list[tuple[str, str, bool]] = []

    def set_author(self, *, name: str, icon_url: Optional[str] = None) -> "Panel":
        self._author_name = name
        return self

    def set_footer(self, *, text: str, icon_url: Optional[str] = None) -> "Panel":
        self._footer_text = text
        return self

    def add_field(self, *, name: str, value: str, inline: bool = False) -> "Panel":
        self._fields.append((name, value, inline))
        return self

    def set_thumbnail(self, *, url: str) -> "Panel":
        return self

    def set_image(self, *, url: str) -> "Panel":
        return self

    def to_view(self, timeout: Optional[float] = None) -> discord.ui.LayoutView:
        children: list[discord.ui.Item] = []

        if self._author_name:
            children.append(discord.ui.TextDisplay(f"> {self._author_name}"))
        if self.title:
            children.append(discord.ui.TextDisplay(f"## {self.title}"))
        if self._author_name or self.title:
            children.append(discord.ui.Separator(visible=False))
        if self.description:
            children.append(discord.ui.TextDisplay(self.description))
        if self._fields:
            if self.description or self.title or self._author_name:
                children.append(discord.ui.Separator())
            _append_text_chunks(children, (f"**{name}**\n{value}" for name, value, _ in self._fields))
        if self._footer_text:
            children.append(discord.ui.Separator())
            children.append(discord.ui.TextDisplay(f"-# {self._footer_text}"))
        if not children:
            children.append(discord.ui.TextDisplay("\u200b"))

        view = discord.ui.LayoutView(timeout=timeout)
        view.add_item(discord.ui.Container(*children))
        return view

    async def send(self, ctx, content: Optional[str] = None, **kwargs) -> Optional[discord.Message]:
        kwargs.pop("embed", None)
        return await ctx.send(content=content, view=self.to_view(), **kwargs)

    async def reply(
        self,
        ctx,
        content: Optional[str] = None,
        mention_author: bool = False,
        **kwargs,
    ) -> Optional[discord.Message]:
        kwargs.pop("embed", None)
        return await ctx.reply(content=content, view=self.to_view(), mention_author=mention_author, **kwargs)

    async def edit(self, message: discord.Message, content: Optional[str] = None, **kwargs) -> discord.Message:
        kwargs.pop("embed", None)
        return await message.edit(content=content, view=self.to_view(), **kwargs)


async def cv2_send(
    ctx,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    color: Any = None,
    fields: Optional[list[tuple[str, str]]] = None,
    footer: Optional[str] = None,
    author: Optional[str] = None,
    mention_author: bool = False,
    reply: bool = False,
    content: Optional[str] = None,
    **kwargs,
) -> Optional[discord.Message]:
    panel = Panel(title=title, description=description, color=color)
    if author:
        panel.set_author(name=author)
    if footer:
        panel.set_footer(text=footer)
    for name, value in fields or []:
        panel.add_field(name=name, value=value)

    if reply:
        return await panel.reply(ctx, content=content, mention_author=mention_author, **kwargs)
    return await panel.send(ctx, content=content, **kwargs)
