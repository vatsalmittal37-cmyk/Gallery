import os
from pathlib import Path
from PIL import Image

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image as KivyImage
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

def get_android_pictures_dir():
    """Resolves correct Android storage permissions and path."""
    if platform == "android":
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.READ_MEDIA_IMAGES, Permission.READ_EXTERNAL_STORAGE])
        from android.storage import primary_external_storage_path
        return os.path.join(primary_external_storage_path(), "Pictures")
    else:
        # Desktop fallback during testing
        return str(Path.home() / "Pictures")


class GalleryGridScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        # Header
        self.header = Label(
            text="Photos",
            size_hint_y=None,
            height=60,
            color=(0, 0, 0, 1),
            bold=True,
            font_size='20sp'
        )
        self.layout.add_widget(self.header)

        # Scrollable Thumbnail Grid
        self.scroll = ScrollView()
        self.grid = GridLayout(cols=3, spacing=5, padding=5, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)

        self.layout.add_widget(self.scroll)
        self.add_widget(self.layout)

    def load_gallery(self, media_paths):
        self.header.text = f"Photos ({len(media_paths)})"
        self.grid.clear_widgets()

        # Load thumbnails asynchronously so the app UI opens instantly
        Clock.schedule_once(lambda dt: self._load_batch(media_paths, 0), 0.1)

    def _load_batch(self, paths, index):
        if index >= len(paths):
            return

        batch_size = 6
        end_idx = min(index + batch_size, len(paths))

        for i in range(index, end_idx):
            path = paths[i]
            btn = Button(
                size_hint_y=None,
                height=Window.width / 3 - 10,
                background_normal=path,
                background_down=path
            )
            btn.bind(on_release=lambda instance, idx=i: self.open_single_view(idx))
            self.grid.add_widget(btn)

        Clock.schedule_once(lambda dt: self._load_batch(paths, end_idx), 0.05)

    def open_single_view(self, index):
        app = App.get_running_app()
        app.sm.transition = SlideTransition(direction='left')
        app.single_screen.set_image(index)
        app.sm.current = 'single_view'


class SingleViewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_index = 0

        self.layout = BoxLayout(orientation='vertical')

        # Top Bar
        top_bar = BoxLayout(size_hint_y=None, height=50)
        btn_back = Button(text="❮ Back", size_hint_x=0.3)
        btn_back.bind(on_release=self.go_back)
        
        self.info_label = Label(text="", color=(1, 1, 1, 1))

        top_bar.add_widget(btn_back)
        top_bar.add_widget(self.info_label)
        self.layout.add_widget(top_bar)

        # Full Image Preview
        self.image_widget = KivyImage(allow_stretch=True, keep_ratio=True)
        self.layout.add_widget(self.image_widget)

        self.add_widget(self.layout)

    def set_image(self, index):
        app = App.get_running_app()
        self.current_index = index
        path = app.media_paths[index]

        self.image_widget.source = path
        self.info_label.text = f"{index + 1} of {len(app.media_paths)}"

    def on_touch_down(self, touch):
        self.touch_x = touch.x
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if hasattr(self, 'touch_x'):
            delta = touch.x - self.touch_x
            app = App.get_running_app()

            # Swipe Left -> Next
            if delta < -100 and self.current_index < len(app.media_paths) - 1:
                app.sm.transition = SlideTransition(direction='left')
                self.set_image(self.current_index + 1)
            # Swipe Right -> Previous
            elif delta > 100 and self.current_index > 0:
                app.sm.transition = SlideTransition(direction='right')
                self.set_image(self.current_index - 1)

        return super().on_touch_up(touch)

    def go_back(self, instance):
        app = App.get_running_app()
        app.sm.transition = SlideTransition(direction='right')
        app.sm.current = 'grid_view'


class AndroidGalleryApp(App):
    def build(self):
        Window.clearcolor = (0.97, 0.98, 0.98, 1)

        self.media_paths = []
        self.sm = ScreenManager()

        self.grid_screen = GalleryGridScreen(name='grid_view')
        self.single_screen = SingleViewScreen(name='single_view')

        self.sm.add_widget(self.grid_screen)
        self.sm.add_widget(self.single_screen)

        self.scan_media()

        return self.sm

    def scan_media(self):
        folder = get_android_pictures_dir()
        found = []

        if os.path.exists(folder):
            for root_dir, _, filenames in os.walk(folder):
                for f in filenames:
                    if f.lower().endswith(IMAGE_EXTENSIONS):
                        found.append(os.path.join(root_dir, f))

        self.media_paths = sorted(found)
        self.grid_screen.load_gallery(self.media_paths)


if __name__ == '__main__':
    AndroidGalleryApp().run()
