from fastapi import FastAPI, File, UploadFile, HTTPException, Header, Depends, Response
from cbfa import ClassBased 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
import os, shutil
import uuid
import subprocess
from loguru import logger
import sys
import time
import base64
import datetime
import asyncio
import subprocess


# создание объекта FastAPI app
app = FastAPI()
# точка входа в приложение
action_cls_wraper = ClassBased(app=app)


class Payload:
    def __init__(self, status, result=None):
        self.status = status
        self.result = result or {}

    def get_status(self):
        return self.status

    def get_result(self):
        return self.result

class PhotoResponseHandler:
    @staticmethod
    def handle_response(payload: Payload):
        """
        Static method to handle the response based on the payload status.
        """
        status = payload.get_status()

        if status == 'SUCCESS RESTORED':
            return Response(
                content=payload.get_result(),
                media_type='image/png'
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail='Unknown Payload Status'
            )


class AuthService:
    def __init__(self, firebase_app: firebase_admin.App = None):
        self.firebase_app = firebase_app

    def validate_token(self, token: HTTPAuthorizationCredentials = None):
        if not token:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is missing"
            )
    
        try:
            decoded_token = auth.verify_id_token(token.credentials)
            return decoded_token
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials"
            )

class PhotoServiceWithAuth:
    #проверяет есть ли такой пользователь
    # запуск реставрации
    # отдает результат в payload
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    
    def create_tmp_dir(self, base_path) -> str:
        unique_id = uuid.uuid4()
        directory_path = os.path.join(base_path, str(unique_id))
        
        try:
            os.makedirs(directory_path)
            print(f"Директория создана: {directory_path}")
            return directory_path
        except OSError as error:
            print(f"Ошибка при создании директории: {error}")
            return None

    def delete_directory(self, path):
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Директория '{path}' успешно удалена.")
        else:
            print(f"Директория '{path}' не найдена.")

    async def start_restoration(
            self,
            image_save_path: str,
            photo_name:str
    ):
        process = await asyncio.create_subprocess_shell(
            f'''python run.py --input_folder {image_save_path} --output_folder {image_save_path} --GPU -1 --with_scratch''',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        print('good output', stdout)
        print('error', stderr)
        if stderr:
            raise Exception(str(stderr))
        
        with open(f'{image_save_path}/final_output/{photo_name}', 'rb') as f:
            restored_photo = f.read()

        self.delete_directory(image_save_path)

        return restored_photo

    async def restore_process(self, photo_file: UploadFile, token: str):
        if user := self.auth_service.validate_token(token=token):
            logger.info(f'this user {user}, send request')
        # restored_photo = await  moak_process(photo_file)
        # создать уникальную папку
        photo_save_path = self.create_tmp_dir('./')
        # сохранить в нее полученное фото
        photo_unic_name = f'{uuid.uuid4()}.png'
        with open(f'{photo_save_path}/{photo_unic_name}', 'wb') as f:
            photo_file = await photo_file.read()
            f.write(photo_file)
        # передать в наш скрипт путь для того что бы он искал этой папке
        # получить по указанному пути файл 
        # удалить его папку 
        if restored_photo := await  self.start_restoration(
            photo_save_path,
            photo_unic_name
        ):
            return Payload('SUCCESS RESTORED', result=restored_photo)
        else:
            return Payload('ERROR', result=restored_photo)


photo_service = PhotoServiceWithAuth(
    auth_service=AuthService( 
        firebase_admin.initialize_app(
            credentials.Certificate(
                "src/testfastapi-e24b4-firebase-adminsdk-r1194-fa7344e2ff.json"
            )
        )
    )
)

@action_cls_wraper(
    '/process_photo'
)
class PhotoActions:
    # класс action который принимает реализует методы принимающие
    # запросы пользователей со стороны клиента
    # передает эти запросы в область домена (PhotoServiceWithAuth) для 
    # для старта процесса обработки запросов
    # получает результат обработки и отправляен его в область ответчика
    # (PhotoResponseHandler)
    
    async def get(user_agent: str = Header(None)):
        return 'hi'

    async def post(
            file: UploadFile = File(...),
            token: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ):
        restoration_result = await photo_service.restore_process(
            photo_file=file, token=token
        )

        return PhotoResponseHandler.handle_response(
            payload=restoration_result
        )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)