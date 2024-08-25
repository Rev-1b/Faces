import os
import uuid

import click
from pytubefix import YouTube
from collections import namedtuple
from moviepy.video.io.VideoFileClip import VideoFileClip


Video = namedtuple('Video', ['path', 'name'])


class VideoDownloader:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def download(self):
        raise NotImplementedError("Этот метод должен быть реализован в дочернем классе.")

    @staticmethod
    def show_progress(stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        completion_percentage = bytes_downloaded / total_size * 100
        print(f"\rЗагрузка видео {bytes_downloaded}/{total_size} байт: {completion_percentage:.2f}%", end="",
              flush=True)

    def trim_video(self, video_path, start_time, end_time):
        with VideoFileClip(video_path) as video:
            trimmed_video = video.subclip(start_time, end_time)
            trimmed_filename = f"{uuid.uuid4()}.mp4"
            trimmed_path = os.path.join(self.output_dir, trimmed_filename)
            trimmed_video.write_videofile(trimmed_path, codec="libx264")
        os.remove(video_path)  # удаляем оригинальное видео
        return trimmed_path


class YouTubeVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, youtube_url, resolution='720p'):
        super().__init__(output_dir)
        self.youtube_url = youtube_url
        self.resolution = resolution

    def download(self, start_time=None, end_time=None):
        yt = YouTube(self.youtube_url, on_progress_callback=self.show_progress, use_oauth=True)
        video_stream = yt.streams.filter(adaptive=True, type="video", resolution=self.resolution,
                                         file_extension='mp4').first()

        if video_stream is None:
            print('Неподходящее разрешение, пробую другое')
            video_stream = yt.streams.filter(adaptive=True, type="video", resolution='480p',
                                             file_extension='mp4').first()

        if video_stream is None:
            raise ValueError("Не удалось найти видеопоток без звука на YouTube.")

        print(f"Выбран поток с разрешением: {video_stream.resolution}")
        video_filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(self.output_dir, video_filename)
        video_stream.download(output_path=self.output_dir, filename=video_filename)

        if start_time is not None or end_time is not None:
            output_path = self.trim_video(output_path, start_time, end_time)

        # further = click.prompt(
        #     'Продолжаем?',
        #     type=click.Choice(['Y', 'N'], case_sensitive=False),
        #     default='Y',
        #     show_default=True,
        #     show_choices=True
        # ) == 'Y'
        # if not further:
        #     raise Exception('Видео загружено, начинаем сначала')

        print("\nЗагрузка завершена!")
        return Video(output_path, video_filename)


class LocalVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, video_filename):
        super().__init__(output_dir)
        self.video_filename = video_filename
        if not os.path.splitext(self.video_filename)[1]:
            self.video_filename += '.mp4'

    def download(self, start_time=None, end_time=None):
        video_path = os.path.join(self.output_dir, self.video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео {self.video_filename} не найдено в папке {self.output_dir}.")

        video_path = self.handle_duplicate(video_path)

        if start_time is not None or end_time is not None:
            video_path = self.trim_video(video_path, start_time, end_time)
        return Video(video_path, self.video_filename)

    def handle_duplicate(self, video_path):
        filename, ext = os.path.splitext(video_path)
        original_path = None
        if filename.endswith(" (2)"):
            original_path = filename[:-4] + ext
            if os.path.exists(original_path):
                os.remove(original_path)
                print(f"Удалено оригинальное видео: {original_path}")
            os.rename(video_path, original_path)
            print(f"Переименовано видео: {self.video_filename}")
        return original_path if original_path else video_path

