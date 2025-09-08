import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    def upload_file(self, file_obj, object_name):
        """
        Sube un archivo a un bucket de S3.
        :param file_obj: Objeto de archivo para subir.
        :param object_name: Nombre del objeto S3.
        :return: URL del archivo subido o None si falla.
        """
        try:
            self.s3_client.upload_fileobj(file_obj, self.bucket_name, object_name)
            file_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"
            return file_url
        except NoCredentialsError:
            logger.error("Credenciales de AWS no encontradas.")
            return None
        except ClientError as e:
            logger.error(f"Error al subir archivo a S3: {e}")
            return None

    def delete_file(self, object_name):
        """
        Elimina un archivo de un bucket de S3.
        :param object_name: Nombre del objeto S3 a eliminar.
        :return: True si se eliminó, False en caso contrario.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            logger.error(f"Error al eliminar archivo de S3: {e}")
            return False

s3_service = S3Service() 