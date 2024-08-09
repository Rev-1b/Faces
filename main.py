import os
import tempfile
import uuid

import cv2
import face_recognition
from pytubefix import YouTube
import pandas as pd


def _input(message):
    res = input(message)
    while res not in ['1', '2']:
        res = input('Ввод не верен, выбери 1 или 2: ')
    return res


def show_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    print(f"\rЗагрузка видео '{bytes_downloaded}'/'{total_size}': {percentage_of_completion:.2f}%", end="", flush=True)


def download_video(url):
    yt = YouTube(url, on_progress_callback=show_progress)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    stream.download(output_path=os.path.dirname(temp_file.name), filename=os.path.basename(temp_file.name))
    print("\nDownload completed!")
    return temp_file.name


def get_video(video_folder):
    is_video_normal = {'1': True, '2': False}[_input('Выбери тип видео (1 - обычное, 2 - дипфейк): ')]
    is_youtube_video = {'1': True, '2': False}[
        _input('Выбери 1 для обработки ютуб видео, 2 для обработки заранее загруженного видео: ')]

    if is_youtube_video:
        link = f"https://www.youtube.com/watch?v={input('Ссылка на видео: https://www.youtube.com/watch?v=')}"
        path_to_video = download_video(link)
    else:
        path_to_video = input(f'Введи название видео в папке {video_folder}:')
    return {'path': path_to_video, 'is_video_normal': is_video_normal}


def extract_faces_from_video(video_path, output_folder, csv_file, is_normal):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
    else:
        df = pd.DataFrame(columns=["filename", "is_normal"])

    video_capture = cv2.VideoCapture(video_path)
    frame_number = 0
    face_count = 0

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("No more frames to read, ending.")
            break

        rgb_frame = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)

        for face_location in face_locations:
            top, right, bottom, left = face_location
            face_image = frame[top:bottom, left:right]
            face_filename = os.path.join(output_folder, f"{uuid.uuid4()}.jpg")
            cv2.imwrite(face_filename, face_image)
            df = df.append({"filename": face_filename, "is_normal": is_normal}, ignore_index=True)
            face_count += 1

        frame_number += 1
        print(f"Processed frames: {frame_number}, Found faces: {face_count}")

    df.to_csv(csv_file, index=False)
    video_capture.release()
    print("Video processing complete")


if __name__ == "__main__":
    while True:
        video_folder = 'downloaded_video'
        output_folder = "raw_faces"
        csv_file = "faces.csv"

        path, is_video_normal = get_video(video_folder).values()
        extract_faces_from_video(path, output_folder, csv_file, is_video_normal)
        os.remove(path)
