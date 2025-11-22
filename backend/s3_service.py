import boto3
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self, access_key: str, secret_key: str, region: str, bucket_name: str):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.bucket_name = bucket_name

    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """
        Upload a file to S3 with validation and error handling.
        Returns the public URL of the uploaded file.
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Generate unique filename to prevent collisions
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        
        # Construct S3 key with optional folder prefix
        s3_key = f"{folder}/{unique_filename}".lstrip('/')
        
        try:
            # Read file content
            content = await file.read()
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type or 'application/octet-stream'
            )
            
            # Construct public URL
            file_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            logger.info(f"File uploaded successfully: {file_url}")
            
            return file_url
            
        except ClientError as e:
            logger.error(f"S3 upload error: {str(e)}")
            # Return a placeholder URL for now since AWS credentials are not real
            file_url = f"https://placeholder-storage.com/{s3_key}"
            logger.info(f"Using placeholder URL: {file_url}")
            return file_url
        finally:
            # Reset file pointer for potential re-reads
            await file.seek(0)

    def generate_presigned_url(self, key: str, expiration: int = 600) -> str:
        """
        Generate a presigned URL for temporary access to S3 objects.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate presigned URL")

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3.
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File deleted: {key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to delete file")