import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notification_service import NotificationService
from app.config import settings

async def test_email():
    print("📧 Testing Email Configuration...")
    print(f"Host: {settings.smtp_host}")
    print(f"Port: {settings.smtp_port}")
    print(f"User: {settings.smtp_user}")
    print(f"TLS: {settings.smtp_tls}")
    
    if not settings.smtp_host or not settings.smtp_user:
        print("❌ SMTP configuration missing in .env")
        return

    service = NotificationService()
    
    # Ask for recipient email
    recipient = input("\nEnter recipient email address: ")
    
    print(f"\nSending test email to {recipient}...")
    success = await service._send_email(
        recipient,
        "Test Email from CabineAI",
        "This is a test email to verify your SMTP configuration is working correctly.\n\nCabineAI Team"
    )
    
    if success:
        print("✅ Email sent successfully!")
    else:
        print("❌ Failed to send email. Check logs for details.")

if __name__ == "__main__":
    asyncio.run(test_email())
