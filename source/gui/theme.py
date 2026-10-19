"""Màu sắc và các thành phần giao diện dùng chung."""

from ursina import Button, Entity, Text, color


BG = color.rgb32(13, 17, 32)
PANEL = color.rgb32(25, 31, 51)
ACCENT = color.rgb32(139, 116, 255)
TEXT = color.rgb32(232, 238, 255)
MUTED = color.rgb32(151, 164, 192)
GOLD = color.rgb32(255, 190, 90)
ERROR = color.rgb32(255, 130, 140)


def panel(
    parent,
    x,
    y,
    width,
    height,
    tint=PANEL,
    z=0.1,
):
    return Entity(
        parent=parent,
        model="quad",
        position=(x, y, z),
        scale=(width, height),
        color=tint,
    )


def label(
    parent,
    text,
    x,
    y,
    size=1,
    tint=TEXT,
):
    return Text(
        parent=parent,
        text=text,
        position=(x, y, -0.1),
        scale=size,
        color=tint,
    )


def button(
    parent,
    text,
    x,
    y,
    action,
    width=.20,
    height=.055,
    tint=PANEL,
):
    result = Button(
        parent=parent,
        text=text,
        position=(x, y, -.15),
        scale=(width, height),
        color=tint,
        highlight_color=ACCENT,
        pressed_color=GOLD,
        on_click=action,
    )

    result.text_entity.color = TEXT
    return result