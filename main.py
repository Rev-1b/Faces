import os
import tempfile
import uuid
import shutil
import cv2
import face_recognition
from pytubefix import YouTube
import pandas as pd


def _input(message):
    """
    Функция для ввода и валидации данных.
    """
    res = input(message)
    while res not in ['1', '2']:
        res = input('Ввод не верен, выбери 1 или 2: ')
    return res


def show_progress(stream, chunk, bytes_remaining):
    """
    Функция для отображения прогресса загрузки видео с YouTube.
    """
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    print(f"\rЗагрузка видео {bytes_downloaded}/{total_size} байт: {percentage_of_completion:.2f}%", end="", flush=True)


def download_video(url):
    """
    Функция для загрузки видео с YouTube.
    Возвращает путь к загруженному видеофайлу.
    """
    yt = YouTube(url, on_progress_callback=show_progress)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    stream.download(output_path=os.path.dirname(temp_file.name), filename=os.path.basename(temp_file.name))
    print("\nЗагрузка завершена!")
    return temp_file.name


def get_video(folder):
    """
    Функция для выбора типа видео и его получения, либо с YouTube, либо из локальной папки.
    Возвращает путь к видео и тип видео (обычное или дипфейк).
    """
    is_video_normal = {'1': True, '2': False}[_input('Выбери тип видео (1 - обычное, 2 - дипфейк): ')]
    is_youtube_video = {'1': True, '2': False}[
        _input('Выбери 1 для обработки видео с YouTube, 2 для обработки заранее загруженного видео: ')]

    if is_youtube_video:
        link = f"https://www.youtube.com/watch?v={input('Ссылка на видео: https://www.youtube.com/watch?v=')}"
        path_to_video = download_video(link)
    else:
        path_to_video = os.path.join(folder, input(f'Введи название видео в папке {folder}: '))
    return {'path': path_to_video, 'is_video_normal': is_video_normal}


def extract_faces_from_video(video_path, output_folder, temp_csv, is_normal):
    """
    Функция для извлечения лиц из видео и сохранения их во временной папке и временном CSV файле.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = pd.DataFrame(columns=["filename", "is_normal"])

    video_capture = cv2.VideoCapture(video_path)
    frame_number, face_count = 0, 0

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
            face_filename = os.path.join(output_folder, f"{uuid.uuid4()}.jpg")
            cv2.imwrite(face_filename, face_image)
            df = pd.concat([df, pd.DataFrame({"filename": [face_filename], "is_normal": [is_normal]})])
            face_count += 1

        frame_number += 1
        print(f"Обработано кадров: {frame_number}, Найдено лиц: {face_count}")

    df.to_csv(temp_csv, index=False)
    video_capture.release()
    print("Обработка видео завершена.")


def cleanup_faces(temp_csv_file, raw_faces_folder, permanent_csv_file, result_folder):
    """
    Функция для очистки временной папки с лицами, удаления записей из временного CSV и переноса изображений в результирующую папку.
    """

    # Загружаем данные из временного CSV файла
    df = pd.read_csv(temp_csv_file)

    # Фильтрация: оставляем только те файлы, которые существуют
    df = df[df['filename'].apply(lambda x: os.path.exists(os.path.join(raw_faces_folder, x)))]

    # Перемещаем оставшиеся файлы в папку result
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)

    for filename in df['filename']:
        shutil.move(os.path.join(raw_faces_folder, filename), os.path.join(result_folder, filename))

    # Обновляем основной CSV файл
    if os.path.exists(permanent_csv_file):
        df_permanent = pd.read_csv(permanent_csv_file)
        df_permanent = pd.concat([df_permanent, df], ignore_index=True)
    else:
        df_permanent = df

    # Сохраняем обновленный основной CSV файл
    df_permanent.to_csv(permanent_csv_file, index=False)

    # Удаляем временный CSV файл
    os.remove(temp_csv_file)
    print("Очистка и перенос файлов завершены.")


if __name__ == "__main__":
    video_folder = 'downloaded_video'
    raw_faces_folder = "raw_faces"
    result_folder = "result_faces"
    permanent_csv_file = "faces.csv"

    while True:
        # Создание временного CSV файла для каждого видео
        temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

        # Получение видео и обработка
        path, is_video_normal = get_video(video_folder).values()
        extract_faces_from_video(path, raw_faces_folder, temp_csv_file, is_video_normal)
        os.remove(path)

        # Ожидание удаления файлов вручную
        input("Удалите ненужные изображения из папки raw_faces и нажмите Enter для продолжения...")

        # Очистка временного CSV и перемещение оставшихся изображений в result_faces
        cleanup_faces(temp_csv_file, raw_faces_folder, permanent_csv_file, result_folder)
