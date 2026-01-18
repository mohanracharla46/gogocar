"""
AWS SES email service for sending emails
"""
from typing import List, Optional, Dict
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

from app.core.config import settings
from app.core.logging_config import logger


class EmailService:
    """Service for sending emails via AWS SES"""
    
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.SES_REGION
        )
        self.from_email = settings.SES_FROM_EMAIL
        self.from_name = settings.SES_FROM_NAME
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email via AWS SES
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            destination = {
                'ToAddresses': [to_email]
            }
            
            if cc:
                destination['CcAddresses'] = cc
            if bcc:
                destination['BccAddresses'] = bcc
            
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'}
            }
            
            body = {
                'Text': {'Data': body_text, 'Charset': 'UTF-8'}
            }
            
            if body_html:
                body['Html'] = {'Data': body_html, 'Charset': 'UTF-8'}
            
            message['Body'] = body
            
            response = self.ses_client.send_email(
                Source=f"{self.from_name} <{self.from_email}>",
                Destination=destination,
                Message=message
            )
            
            logger.info(f"Email sent successfully to {to_email}. MessageId: {response['MessageId']}")
            return True
            
        except ClientError as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False
    
    def send_booking_confirmation(
        self,
        to_email: str,
        user_name: str,
        booking_id: str,
        car_name: str,
        car_brand: str,
        car_model: str,
        registration_number: Optional[str],
        start_date: str,
        end_date: str,
        pickup_location: Optional[str],
        drop_location: Optional[str],
        total_amount: float,
        advance_amount: float,
        payment_mode: Optional[str] = None,
        tracking_id: Optional[str] = None
    ) -> bool:
        """
        Send booking confirmation email with beautiful HTML template
        
        Args:
            to_email: Recipient email
            user_name: User's name
            booking_id: Booking ID
            car_name: Car name
            car_brand: Car brand
            car_model: Car model
            registration_number: Car registration number
            start_date: Start date
            end_date: End date
            pickup_location: Pickup location
            drop_location: Drop location
            total_amount: Total amount
            advance_amount: Advance amount paid
            payment_mode: Payment mode
            tracking_id: Payment tracking ID
            
        Returns:
            True if successful
        """
        subject = f"🎉 Booking Confirmed - Order #{booking_id}"
        
        # Format dates
        start_date_formatted = start_date
        end_date_formatted = end_date
        
        body_text = f"""
        Dear {user_name},
        
        Your booking has been confirmed!
        
        Booking ID: {booking_id}
        Car: {car_name}
Registration: {registration_number or 'N/A'}
Start Date: {start_date_formatted}
End Date: {end_date_formatted}
Pickup Location: {pickup_location or 'N/A'}
Drop Location: {drop_location or 'N/A'}
Total Amount: ₹{total_amount:,.0f}
Advance Paid: ₹{advance_amount:,.0f}
Payment Mode: {payment_mode or 'N/A'}
Transaction ID: {tracking_id or 'N/A'}
        
        Thank you for choosing GoGoCar!
        """
        
        body_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Booking Confirmed</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f5f5f5;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">🎉 Booking Confirmed!</h1>
                            <p style="margin: 10px 0 0 0; color: #e0e7ff; font-size: 16px;">Your car rental booking is confirmed</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <p style="margin: 0 0 20px 0; color: #1f2937; font-size: 16px; line-height: 1.6;">Dear <strong>{user_name}</strong>,</p>
                            <p style="margin: 0 0 30px 0; color: #4b5563; font-size: 15px; line-height: 1.6;">Thank you for your payment! Your booking has been successfully confirmed. Here are your booking details:</p>
                            
                            <!-- Booking Details Card -->
                            <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f9fafb; border-radius: 8px; margin-bottom: 30px; overflow: hidden;">
                                <tr>
                                    <td style="padding: 25px; border-bottom: 2px solid #e5e7eb;">
                                        <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                            <tr>
                                                <td style="padding: 8px 0;">
                                                    <span style="color: #6b7280; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Booking ID</span>
                                                    <div style="color: #1f2937; font-size: 20px; font-weight: 700; margin-top: 4px;">#{booking_id}</div>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 25px;">
                                        <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                            <tr>
                                                <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;">
                                                    <span style="color: #6b7280; font-size: 14px;">Car</span>
                                                    <div style="color: #1f2937; font-size: 16px; font-weight: 600; margin-top: 4px;">{car_brand} {car_model}</div>
                                                    {f'<div style="color: #6b7280; font-size: 13px; margin-top: 2px;">Reg: {registration_number}</div>' if registration_number else ''}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;">
                                                    <span style="color: #6b7280; font-size: 14px;">Pickup Date & Time</span>
                                                    <div style="color: #1f2937; font-size: 16px; font-weight: 600; margin-top: 4px;">{start_date_formatted}</div>
                                                    {f'<div style="color: #6b7280; font-size: 13px; margin-top: 2px;">📍 {pickup_location}</div>' if pickup_location else ''}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;">
                                                    <span style="color: #6b7280; font-size: 14px;">Return Date & Time</span>
                                                    <div style="color: #1f2937; font-size: 16px; font-weight: 600; margin-top: 4px;">{end_date_formatted}</div>
                                                    {f'<div style="color: #6b7280; font-size: 13px; margin-top: 2px;">📍 {drop_location}</div>' if drop_location else ''}
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;">
                                                    <span style="color: #6b7280; font-size: 14px;">Total Amount</span>
                                                    <div style="color: #1f2937; font-size: 20px; font-weight: 700; margin-top: 4px;">₹{total_amount:,.0f}</div>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;">
                                                    <span style="color: #6b7280; font-size: 14px;">Advance Paid</span>
                                                    <div style="color: #059669; font-size: 18px; font-weight: 600; margin-top: 4px;">₹{advance_amount:,.0f}</div>
                                                </td>
                                            </tr>
                                            {f'<tr><td style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;"><span style="color: #6b7280; font-size: 14px;">Payment Mode</span><div style="color: #1f2937; font-size: 15px; font-weight: 500; margin-top: 4px;">{payment_mode}</div></td></tr>' if payment_mode else ''}
                                            {f'<tr><td style="padding: 12px 0;"><span style="color: #6b7280; font-size: 14px;">Transaction ID</span><div style="color: #1f2937; font-size: 14px; font-weight: 500; margin-top: 4px; font-family: monospace;">{tracking_id}</div></td></tr>' if tracking_id else ''}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- Info Box -->
                            <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 4px; margin-bottom: 30px;">
                                <p style="margin: 0; color: #1e40af; font-size: 14px; line-height: 1.6;">
                                    <strong>📋 Important:</strong> Please arrive on time for pickup. Bring a valid driving license and ID proof. The remaining balance will be collected at the time of pickup.
                                </p>
                            </div>
                            
                            <!-- CTA Button -->
                            <table role="presentation" style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                                <tr>
                                    <td style="text-align: center; padding: 20px 0;">
                                        <a href="{settings.DOMAIN_URL or 'http://localhost:8000'}/orders/view" style="display: inline-block; background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 600; font-size: 15px;">View My Bookings</a>
                                    </td>
                                </tr>
                            </table>
                            
                            <p style="margin: 0; color: #4b5563; font-size: 14px; line-height: 1.6;">If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
                            
                            <p style="margin: 30px 0 0 0; color: #1f2937; font-size: 15px; line-height: 1.6;">
                                Best regards,<br>
                                <strong>The GoGoCar Team</strong>
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                            <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 13px;">© {datetime.now().year} GoGoCar. All rights reserved.</p>
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">This is an automated email. Please do not reply.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body_text, body_html)
    
    def send_kyc_approval(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send KYC approval email"""
        subject = "KYC Verification Approved"
        body_text = f"Dear {user_name}, your KYC documents have been approved. You can now book cars!"
        body_html = f"<p>Dear {user_name},</p><p>Your KYC documents have been approved. You can now book cars!</p>"
        return self.send_email(to_email, subject, body_text, body_html)
    
    def send_kyc_rejection(
        self,
        to_email: str,
        user_name: str,
        reason: str
    ) -> bool:
        """Send KYC rejection email"""
        subject = "KYC Verification Rejected"
        body_text = f"Dear {user_name}, your KYC documents have been rejected. Reason: {reason}"
        body_html = f"<p>Dear {user_name},</p><p>Your KYC documents have been rejected.</p><p><strong>Reason:</strong> {reason}</p>"
        return self.send_email(to_email, subject, body_text, body_html)
    
    def send_booking_status_update(
        self,
        to_email: str,
        user_name: str,
        booking_id: str,
        status: str
    ) -> bool:
        """Send booking status update email"""
        subject = f"Booking {status} - {booking_id}"
        body_text = f"Dear {user_name}, your booking {booking_id} status has been updated to {status}."
        body_html = f"<p>Dear {user_name},</p><p>Your booking <strong>{booking_id}</strong> status has been updated to <strong>{status}</strong>.</p>"
        return self.send_email(to_email, subject, body_text, body_html)


# Global instance
email_service = EmailService()

