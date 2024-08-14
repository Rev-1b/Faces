import os
import platform
import shutil
import tempfile
import uuid

import cv2
import face_recognition
import pandas as pd
from pytubefix import YouTube


def _input(message):
    """
    Функция для ввода и валидации данных.
    """
    user_input = input(message)
    while user_input not in ['1', '2']:
        user_input = input('Ввод не верен, выбери 1 или 2: ')
    return user_input


def show_progress(stream, chunk, bytes_remaining):
    """
    Функция для отображения прогресса загрузки видео с YouTube.
    """
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    completion_percentage = bytes_downloaded / total_size * 100
    print(f"\rЗагрузка видео {bytes_downloaded}/{total_size} байт: {completion_percentage:.2f}%", end="", flush=True)


def download_video(youtube_url, resolution='480p'):
    """
    Функция для загрузки только видео с YouTube (без звука).
    Возвращает путь к загруженному видео файлу.
    """
    yt = YouTube(youtube_url, on_progress_callback=show_progress)

    # Ищем адаптивный видеопоток без аудио, с заданным разрешением
    video_stream = yt.streams.filter(adaptive=True, type="video", resolution=resolution, file_extension='mp4').first()

    if video_stream is None:
        # Пробуем выбрать адаптивный поток с другим доступным разрешением
        print('Неподходящее разрешение, пробую другое')
        video_stream = yt.streams.filter(adaptive=True, type="video", resolution='360p', file_extension='mp4').first()

    if video_stream is None:
        raise ValueError("Не удалось найти видеопоток без звука на YouTube.")

    print(f"Выбран поток с разрешением: {video_stream.resolution}")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    video_stream.download(output_path=os.path.dirname(temp_file.name), filename=os.path.basename(temp_file.name))
    print("\nЗагрузка завершена!")
    return temp_file.name


def get_video(video_dir):
    """
    Функция для выбора типа видео и его получения, либо с YouTube, либо из локальной папки.
    Возвращает путь к видео и тип видео (обычное или дипфейк).
    """
    is_normal_video = {'1': True, '2': False}[_input('Выбери тип видео (1 - обычное, 2 - дипфейк): ')]
    is_youtube_video = {'1': True, '2': False}[
        _input('Выбери 1 для обработки видео с YouTube, 2 для обработки заранее загруженного видео: ')]

    if is_youtube_video:
        youtube_link = input('Ссылка на видео: ')
        # youtube_link = 'https://youtu.be/Z54FdjHqPgM?si=WttLybEL3ac0kUls'
        d_video_path = download_video(youtube_link)
    else:
        video_filename = input(f'Введи название видео в папке {video_dir}: ')
        d_video_path = os.path.join(video_dir, video_filename)
    return {'path': d_video_path, 'is_video_normal': is_normal_video}


def extract_faces_from_video(video_file, output_dir, temp_csv_path, is_normal_video):
    """
    Функция для извлечения лиц из видео и сохранения их во временной папке и временном CSV файле.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    faces_df = pd.DataFrame(columns=["filename", "is_normal"])

    video_capture = cv2.VideoCapture(video_file)
    frame_count, total_faces = 0, 0

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Все кадры обработаны, завершаем.")
            break

        rgb_frame = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)

        for face_location in face_locations:
            top, right, bottom, left = face_location
            face_image = frame[top:bottom, left:right]
            face_filename = f"{uuid.uuid4()}.jpg"
            cv2.imwrite(os.path.join(output_dir, face_filename), face_image)
            faces_df = pd.concat(
                [faces_df, pd.DataFrame({"filename": [face_filename], "is_normal": [is_normal_video]})])
            total_faces += 1

        frame_count += 1
        print(f"Обработано кадров: {frame_count}, Найдено лиц: {total_faces}")

    faces_df.to_csv(temp_csv_path, index=False)
    video_capture.release()
    print("Обработка видео завершена.")


def cleanup_faces(temp_csv, raw_faces_dir, final_csv, result_dir):
    """
    Функция для очистки временной папки с лицами, удаления записей из временного CSV и
    переноса изображений в результирующую папку.
    """
    # Загружаем данные из временного CSV файла
    temp_faces_df = pd.read_csv(temp_csv)

    # Фильтрация: оставляем только те файлы, которые существуют
    temp_faces_df = temp_faces_df[
        temp_faces_df['filename'].apply(lambda x: os.path.exists(os.path.join(raw_faces_dir, x)))]

    # Перемещаем оставшиеся файлы в папку result
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    for face_file in temp_faces_df['filename']:
        shutil.move(os.path.join(raw_faces_dir, face_file), os.path.join(result_dir, face_file))

    # Обновляем основной CSV файл
    if os.path.exists(final_csv):
        permanent_faces_df = pd.read_csv(final_csv)
        permanent_faces_df = pd.concat([permanent_faces_df, temp_faces_df], ignore_index=True)
    else:
        permanent_faces_df = temp_faces_df

    # Сохраняем обновленный основной CSV файл
    permanent_faces_df.to_csv(final_csv, index=False)

    # Удаляем временный CSV файл
    os.remove(temp_csv)
    print("Очистка и перенос файлов завершены.")


def open_folder(path):
    """
    Функция для открытия проводника в указанной папке.
    """
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":  # macOS
        os.system(f"open {path}")
    elif platform.system() == "Linux":
        os.system(f"xdg-open {path}")
    else:
        print(f"Операционная система {platform.system()} не поддерживается.")


if __name__ == "__main__":
    video_directory = 'downloaded_video'
    raw_faces_directory = "raw_faces"
    result_faces_directory = "result_faces"
    permanent_csv_file = "faces.csv"

    while True:
        # Создание временного CSV файла для каждого видео
        temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

        # Получение видео и обработка
        try:
            video_path, is_video_normal = get_video(video_directory).values()
            extract_faces_from_video(video_path, raw_faces_directory, temp_csv_file, is_video_normal)
            os.remove(video_path)

            open_folder(raw_faces_directory)

            # Ожидание удаления файлов вручную
            input("Удалите ненужные изображения из папки raw_faces и нажмите Enter для продолжения...")

            # Очистка временного CSV и перемещение оставшихся изображений в result_faces
            cleanup_faces(temp_csv_file, raw_faces_directory, permanent_csv_file, result_faces_directory)
        except Exception as err:
            print(err)
        finally:
            print('Начинаем сначала')
