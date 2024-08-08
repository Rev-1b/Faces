import os
import tempfile
import uuid

import cv2
import face_recognition
from pytubefix import YouTube


def show_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    print(f"\rЗагрузка видео '{bytes_downloaded}'/'{total_size}': {percentage_of_completion:.2f}%", end="", flush=True)


def download_video(url):
    yt = YouTube(url, on_progress_callback=show_progress)
    stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
    # if not stream:
    #     raise ValueError(f"No video stream available with resolution {resolution}")
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    stream.download(output_path=os.path.dirname(temp_file.name), filename=os.path.basename(temp_file.name))
    print("\nDownload completed!")
    return temp_file.name


def get_video(video_folder):
    choice = input('Выбери 1 для обработки ютуб видео, 2 для обработки заранее загруженного видео:')
    if choice == '1':
        link = f"https://www.youtube.com/watch?v={input('Ссылка на видео: https://www.youtube.com/watch?v=')}"
        path_to_video = download_video(link)
    else:
        path_to_video = input(f'Введи название видео в папке {video_folder}:')
    return path_to_video


def extract_faces_from_video(video_path, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

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
            face_count += 1

        frame_number += 1
        print(f"Processed frames: {frame_number}, Found faces: {face_count}")

    video_capture.release()
    print("Video processing complete")


if __name__ == "__main__":
    while True:
        video_folder = 'downloaded_video'
        output_folder = "raw_faces"
        video_path = get_video(video_folder)
        extract_faces_from_video(video_path, output_folder)
        os.remove(video_path)
