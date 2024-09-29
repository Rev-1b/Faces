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
        video_stream = self.get_video_stream(self.youtube_url)

        print(f"Выбран поток с разрешением: {video_stream.resolution}")
        video_filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(self.output_dir, video_filename)
        video_stream.download(output_path=self.output_dir, filename=video_filename)

        if start_time is not None or end_time is not None:
            output_path = self.trim_video(output_path, start_time, end_time)

        print(f"\nЗагрузка видео {video_filename} завершена!")
        return Video(output_path, video_filename)

    def get_video_stream(self, youtube_url):
        yt = YouTube(youtube_url, 'MWEB', on_progress_callback=self.show_progress, use_oauth=True)
        streams = yt.streams.filter(adaptive=True, type="video", file_extension='mp4')

        # Фильтруем разрешения вручную
        valid_resolutions = ['1080p', '720p', '480p']
        video_stream = None

        # Проходим по разрешениям, начиная с самого высокого
        for res in valid_resolutions:
            video_stream = streams.filter(res=res).first()
            if video_stream:
                break

        if video_stream:
            return video_stream
        else:
            raise ValueError("Видео в нужном диапазоне разрешений не найдено")


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


class PreloadedVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, temp_dir):
        super().__init__(output_dir)
        self.temp_dir = temp_dir

    def download(self, start_time=None, end_time=None):
        # Проверяем, что папка с временными видео существует
        if not os.path.exists(self.temp_dir):
            raise FileNotFoundError(f"Папка {self.temp_dir} не найдена.")

        # Получаем список файлов в папке temp
        video_files = [f for f in os.listdir(self.temp_dir) if os.path.isfile(os.path.join(self.temp_dir, f))]

        # Если нет видеофайлов, бросаем исключение
        if not video_files:
            raise FileNotFoundError(f"В папке {self.temp_dir} нет видео.")

        video_file = video_files[0]
        video_path = os.path.join(self.temp_dir, video_file)

        # Генерируем новое имя файла с UUID
        new_filename = f"{uuid.uuid4()}.mp4"
        new_video_path = os.path.join(self.output_dir, new_filename)

        # Переименовываем и перемещаем видео в папку назначения
        os.rename(video_path, new_video_path)

        # Обрезаем видео, если указаны start_time и end_time
        if start_time is not None or end_time is not None:
            new_video_path = self.trim_video(new_video_path, start_time, end_time)

        self.video_filename = new_filename
        print(f"Видео {video_file} переименовано в {new_filename} и перемещено в {self.output_dir}")

        return Video(new_video_path, self.video_filename)

