"""
Authentication utilities
"""
import boto3
from typing import Dict
from sqlalchemy.orm import Session
from app.db.models import UserProfile
from app.core.config import settings
from app.core.logging_config import logger


def create_user_if_not_exists(token_data: Dict, db: Session) -> UserProfile:
    """
    Create user if not exists in database
    
    Args:
        token_data: Token data from Cognito
        db: Database session
        
    Returns:
        UserProfile instance
    """
    try:
        # Check if user exists
        user = db.query(UserProfile).filter(
            UserProfile.username == token_data.get("username")
        ).first()
        
        if user:
            return user
        
        # Get user attributes from Cognito
        cognito_client = boto3.client(
            "cognito-idp",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        
        try:
            cognito_user = cognito_client.admin_get_user(
                UserPoolId=settings.USERPOOL_ID,
                Username=token_data.get("username")
            )
            
            # Extract user attributes
            user_attrs = {attr["Name"]: attr["Value"] for attr in cognito_user.get("UserAttributes", [])}
            
            # Create user
            new_user = UserProfile(
                username=token_data.get("username"),
                email=user_attrs.get("email", token_data.get("email", "")),
                firstname=user_attrs.get("given_name", ""),
                lastname=user_attrs.get("family_name", ""),
                isadmin=False
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            logger.info(f"User created: {new_user.username}")
            return new_user
            
        except cognito_client.exceptions.UserNotFoundException:
            logger.error(f"User not found in Cognito: {token_data.get('username')}")
            raise
        except Exception as e:
            logger.error(f"Error getting user from Cognito: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise

