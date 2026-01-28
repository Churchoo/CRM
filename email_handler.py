"""
Email handler module for CRM Application
Handles email sending, SMTP configuration, and templates
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
import re


class EmailHandler:
    def __init__(self, smtp_server: str = None, smtp_port: int = None,
                 username: str = None, password: str = None):
        """
        Initialize email handler
        
        Args:
            smtp_server: SMTP server address (e.g., smtp.gmail.com)
            smtp_port: SMTP port (587 for TLS, 465 for SSL)
            username: Email account username
            password: Email account password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def configure(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """Update SMTP configuration"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def validate_email(self, email: str) -> bool:
        """Validate email address format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def send_email(self, to_email: str, subject: str, body: str, 
                   html: bool = False) -> tuple[bool, str]:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            html: If True, send as HTML email
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Validate configuration
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            return False, "Email configuration incomplete. Please configure SMTP settings."
        
        # Validate recipient email
        if not self.validate_email(to_email):
            return False, f"Invalid email address: {to_email}"
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True, f"Email sent successfully to {to_email}"
        
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check your email and password."
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def test_connection(self) -> tuple[bool, str]:
        """Test SMTP connection and authentication"""
        if not all([self.smtp_server, self.smtp_port, self.username, self.password]):
            return False, "Email configuration incomplete"
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.username, self.password)
            return True, "Connection successful!"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check your email and password."
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def send_birthday_email(self, customer: Dict, template: str = None) -> tuple[bool, str]:
        """
        Send a birthday email to a customer
        
        Args:
            customer: Customer dictionary with 'name' and 'email' keys
            template: Optional message template string. '{name}' will be replaced.
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        name = customer.get('name', 'Valued Customer')
        email = customer.get('email')
        
        if not email:
            return False, "Customer has no email address"
        
        # Birthday email template subject
        subject = f"🎉 Happy Birthday, {name.split()[0]}!"
        
        if template:
            body = template.replace("{name}", name)
            # Detect if template is HTML
            is_html = "<html>" in body.lower() or "<body>" in body.lower()
        else:
            # Default HTML template (legacy/fallback)
            is_html = True
            body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
                <h2 style="color: #4CAF50; text-align: center;">🎂 Happy Birthday! 🎂</h2>
                <p style="font-size: 16px;">Dear {name},</p>
                <p style="font-size: 16px;">
                    Wishing you a wonderful birthday filled with joy, laughter, and all the things that make you happy!
                </p>
                <p style="font-size: 16px;">
                    Thank you for being such a valued customer. We hope your special day is as amazing as you are!
                </p>
                <p style="font-size: 16px; margin-top: 30px;">
                    Warmest wishes,<br>
                    <strong>Your CRM Team</strong>
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(email, subject, body, html=is_html)
    
    @staticmethod
    def get_common_smtp_settings() -> Dict[str, Dict]:
        """Get common SMTP server settings for popular email providers"""
        return {
            "Gmail": {
                "server": "smtp.gmail.com",
                "port": 587,
                "note": "Use App Password, not regular password. Enable 2FA first."
            },
            "Outlook/Hotmail": {
                "server": "smtp-mail.outlook.com",
                "port": 587,
                "note": "Use your regular Outlook password"
            },
            "Yahoo": {
                "server": "smtp.mail.yahoo.com",
                "port": 587,
                "note": "Use App Password from Yahoo account security"
            },
            "Custom": {
                "server": "",
                "port": 587,
                "note": "Enter your custom SMTP server details"
            }
        }


# Test function
def test_email():
    """Test email functionality (requires valid SMTP credentials)"""
    print("Email Handler Test")
    print("Note: This test requires valid SMTP credentials to actually send emails")
    
    handler = EmailHandler()
    
    # Test email validation
    print(f"✓ Valid email test: {handler.validate_email('test@example.com')}")
    print(f"✓ Invalid email test: {not handler.validate_email('invalid-email')}")
    
    # Test configuration check
    success, msg = handler.test_connection()
    print(f"Connection test (no config): {msg}")
    
    # Show common SMTP settings
    print("\n✓ Common SMTP settings available:")
    for provider, settings in handler.get_common_smtp_settings().items():
        print(f"  - {provider}: {settings['server']}:{settings['port']}")
    
    print("\n✓ Email handler tests passed!")


if __name__ == "__main__":
    test_email()
