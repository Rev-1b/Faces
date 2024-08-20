import os
import uuid

from pytubefix import YouTube
from collections import namedtuple


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


class YouTubeVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, youtube_url, resolution='720p'):
        super().__init__(output_dir)
        self.youtube_url = youtube_url
        self.resolution = resolution

    def download(self):
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
        print("\nЗагрузка завершена!")
        return Video(output_path, video_filename)


class LocalVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, video_filename):
        super().__init__(output_dir)
        self.video_filename = video_filename

    def download(self):
        video_path = os.path.join(self.output_dir, self.video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео {self.video_filename} не найдено в папке {self.output_dir}.")
        return Video(video_path, self.video_filename)
