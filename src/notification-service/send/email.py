import smtplib, os, json, sys
from email.message import EmailMessage

def notification(logger, message):
    try:
        # Parse message
        message_data = json.loads(message)
        mp3_fid = message_data.get("mp3_fid")
        receiver_address = message_data.get("username")
        
        logger.info("Processing notification request", extra={
            'mp3_id': mp3_fid,
            'recipient': receiver_address
        })
        
        # Get email configuration
        sender_address = os.environ.get("FROM_ADDRESS")
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        
        if not sender_address or not smtp_user or not smtp_password:
            logger.error("Missing email configuration", extra={
                'has_address': bool(sender_address),
                'has_smtp_user': bool(smtp_user),
                'has_smtp_password': bool(smtp_password),
            })
            raise ValueError("Email configuration is incomplete")
        
        # Create email message
        logger.debug("Creating email message")
        msg = EmailMessage()
        msg.set_content(f"mp3 file_id: {mp3_fid} is now ready!")
        msg["Subject"] = "MP3 Download"
        msg["From"] = sender_address
        msg["To"] = receiver_address
        
        # Connect to SMTP server
        logger.info("Connecting to SMTP server", extra={'server': "192.168.0.119"})
        session = smtplib.SMTP("192.168.0.119", 25)
        
        # Log in to SMTP server
        logger.debug("Logging in to SMTP server", extra={'user': smtp_user})
        session.login(smtp_user, smtp_password)
        
        # Send email
        logger.info("Sending email", extra={
            'from': sender_address,
            'to': receiver_address,
            'mp3_id': mp3_fid
        })
        session.send_message(msg, sender_address, receiver_address)
        
        # Close connection
        session.quit()
        
        logger.info("Email sent successfully", extra={
            'mp3_id': mp3_fid,
            'recipient': receiver_address
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid message format: {str(e)}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending notification: {str(e)}")
        raise