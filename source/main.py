"""Application entry point."""

from ursina import Ursina

from game.app_controller import AppController


# Disable Ursina's editor overlay (FPS/entities/colliders, cog and red X).
app = Ursina(title="Bloxorz", development_mode=False, fullscreen=False)

app_controller = AppController()

app.run()
