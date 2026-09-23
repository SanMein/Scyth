# utils/containers.py — билдеры Components V2
import discord


def build_container(
    text: str,
    thumb_url: str | None = None,
    accent_color: int = 0x9B59B6,
    extra_items: list | None = None,
) -> discord.ui.LayoutView:
    """
    Собирает LayoutView с одним Section (TextDisplay + Thumbnail)
    и опциональными доп. элементами.

    ВАЖНО: LayoutView одноразовый. Для каждой отправки создавай новый экземпляр.
    """
    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(accent_color=discord.Colour(accent_color))

    if thumb_url:
        section = discord.ui.Section(
            discord.ui.TextDisplay(text),
            accessory=discord.ui.Thumbnail(thumb_url),
        )
    else:
        section = discord.ui.Section(discord.ui.TextDisplay(text))

    container.add_item(section)

    if extra_items:
        for item in extra_items:
            container.add_item(item)

    view.add_item(container)
    return view