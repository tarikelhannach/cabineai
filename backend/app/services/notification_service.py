# backend/app/services/notification_service.py - Servicio de Notificaciones

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from ..config import settings
from ..models import User

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Servicio de notificaciones para el Sistema Judicial Digital
    Soporta email, SMS y notificaciones in-app
    """
    
    def __init__(self):
        self.smtp_host = getattr(settings, 'smtp_host', None)
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', None)
        self.smtp_password = getattr(settings, 'smtp_password', None)
        self.smtp_tls = getattr(settings, 'smtp_tls', True)
    
    async def send_welcome_notification(
        self, 
        email: str, 
        name: str, 
        language: str = "ar"
    ) -> bool:
        """Enviar notificación de bienvenida"""
        try:
            subject = self._get_localized_text("welcome_subject", language)
            message = self._get_localized_text("welcome_message", language).format(name=name)
            
            return await self._send_email(email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending welcome notification: {e}")
            return False
    
    async def send_approval_required_notification(
        self, 
        email: str, 
        name: str
    ) -> bool:
        """Enviar notificación de aprobación requerida"""
        try:
            subject = "Aprobación de Cuenta Requerida - Sistema Judicial Digital"
            message = f"""
Estimado/a {name},

Su cuenta ha sido creada exitosamente en el Sistema Judicial Digital de Marruecos.

Sin embargo, debido a su rol seleccionado, su cuenta requiere aprobación administrativa antes de poder acceder al sistema.

Un administrador revisará su solicitud y se le notificará una vez que sea aprobada.

Gracias por su paciencia.

Sistema Judicial Digital - Marruecos
            """
            
            return await self._send_email(email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending approval notification: {e}")
            return False
    
    async def send_password_change_notification(
        self, 
        email: str, 
        name: str, 
        language: str = "ar"
    ) -> bool:
        """Enviar notificación de cambio de contraseña"""
        try:
            subject = self._get_localized_text("password_change_subject", language)
            message = self._get_localized_text("password_change_message", language).format(
                name=name,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            return await self._send_email(email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending password change notification: {e}")
            return False
    
    async def send_case_update_notification(
        self, 
        user_email: str, 
        case_number: str, 
        update_type: str,
        language: str = "ar"
    ) -> bool:
        """Enviar notificación de actualización de caso"""
        try:
            subject = self._get_localized_text("case_update_subject", language)
            message = self._get_localized_text("case_update_message", language).format(
                case_number=case_number,
                update_type=update_type
            )
            
            return await self._send_email(user_email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending case update notification: {e}")
            return False
    
    async def send_document_ready_notification(
        self, 
        user_email: str, 
        document_name: str,
        language: str = "ar"
    ) -> bool:
        """Enviar notificación de documento procesado"""
        try:
            subject = self._get_localized_text("document_ready_subject", language)
            message = self._get_localized_text("document_ready_message", language).format(
                document_name=document_name
            )
            
            return await self._send_email(user_email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending document ready notification: {e}")
            return False
    
    async def send_signature_required_notification(
        self, 
        user_email: str, 
        document_name: str,
        language: str = "ar"
    ) -> bool:
        """Enviar notificación de firma requerida"""
        try:
            subject = self._get_localized_text("signature_required_subject", language)
            message = self._get_localized_text("signature_required_message", language).format(
                document_name=document_name
            )
            
            return await self._send_email(user_email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending signature required notification: {e}")
            return False

    async def send_user_invitation(
        self, 
        email: str, 
        password: str,
        language: str = "ar"
    ) -> bool:
        """Enviar invitación a nuevo usuario"""
        try:
            subject = self._get_localized_text("invitation_subject", language)
            message = self._get_localized_text("invitation_message", language).format(
                email=email,
                password=password
            )
            
            return await self._send_email(email, subject, message)
            
        except Exception as e:
            logger.error(f"Error sending invitation: {e}")
            return False
    
    async def create_in_app_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        related_resource_type: Optional[str] = None,
        related_resource_id: Optional[int] = None
    ) -> bool:
        """Crear notificación in-app"""
        try:
            from ..database import SessionLocal
            
            db = SessionLocal()
            try:
                notification = Notification(
                    recipient_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    related_resource_type=related_resource_type,
                    related_resource_id=related_resource_id,
                    is_read=False,
                    is_sent=False
                )
                
                db.add(notification)
                db.commit()
                
                logger.info(f"In-app notification created for user {user_id}")
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error creating in-app notification: {e}")
            return False
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        message: str
    ) -> bool:
        """Enviar email usando SMTP"""
        try:
            if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
                logger.warning("SMTP not configured, skipping email send")
                return False
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Agregar cuerpo del mensaje
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # Enviar email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    def _get_localized_text(self, key: str, language: str) -> str:
        """Obtener texto localizado"""
        texts = {
            "es": {
                "welcome_subject": "Bienvenido al Sistema Judicial Digital - Marruecos",
                "welcome_message": "Estimado/a {name},\n\nBienvenido al Sistema Judicial Digital del Reino de Marruecos.\n\nSu cuenta ha sido creada exitosamente y ahora puede acceder al sistema.\n\nGracias.\n\nSistema Judicial Digital - Marruecos",
                "password_change_subject": "Contraseña modificada",
                "password_change_message": "Estimado/a {name},\n\nSu contraseña ha sido modificada exitosamente el {timestamp}.\n\nSi no realizó este cambio, por favor contáctenos inmediatamente.\n\nSistema Judicial Digital - Marruecos",
                "case_update_subject": "Actualización de caso",
                "case_update_message": "El caso {case_number} ha sido actualizado.\n\nTipo de actualización: {update_type}\n\nPor favor inicie sesión para ver los detalles.\n\nSistema Judicial Digital - Marruecos",
                "document_ready_subject": "Documento listo",
                "document_ready_message": "El documento '{document_name}' ha sido procesado exitosamente y está listo para revisión.\n\nSistema Judicial Digital - Marruecos",
                "signature_required_subject": "Firma requerida",
                "signature_required_message": "El documento '{document_name}' requiere firma.\n\nPor favor inicie sesión para completar la firma.\n\nSistema Judicial Digital - Marruecos",
                "invitation_subject": "Invitación a CabineAI - Sistema Judicial Digital",
                "invitation_message": "Estimado/a,\n\nHa sido invitado a unirse a CabineAI.\n\nSus credenciales temporales son:\nEmail: {email}\nContraseña: {password}\n\nPor favor inicie sesión y cambie su contraseña inmediatamente.\n\nSistema Judicial Digital - Marruecos"
            },
            "ar": {
                "welcome_subject": "مرحباً بك في النظام القضائي الرقمي - المغرب",
                "welcome_message": "عزيزي/عزيزة {name}،\n\nمرحباً بك في النظام القضائي الرقمي للمملكة المغربية.\n\nتم إنشاء حسابك بنجاح ويمكنك الآن الوصول إلى النظام.\n\nشكراً لك.\n\nالنظام القضائي الرقمي - المغرب",
                "password_change_subject": "تم تغيير كلمة المرور",
                "password_change_message": "عزيزي/عزيزة {name}،\n\nتم تغيير كلمة المرور الخاصة بحسابك بنجاح في {timestamp}.\n\nإذا لم تقم بهذا التغيير، يرجى الاتصال بنا فوراً.\n\nالنظام القضائي الرقمي - المغرب",
                "case_update_subject": "تحديث حالة القضية",
                "case_update_message": "تم تحديث القضية رقم {case_number}.\n\nنوع التحديث: {update_type}\n\nيرجى تسجيل الدخول للاطلاع على التفاصيل.\n\nالنظام القضائي الرقمي - المغرب",
                "document_ready_subject": "الوثيقة جاهزة",
                "document_ready_message": "تم معالجة الوثيقة '{document_name}' بنجاح وهي جاهزة للمراجعة.\n\nالنظام القضائي الرقمي - المغرب",
                "signature_required_subject": "توقيع مطلوب",
                "signature_required_message": "يتطلب توقيع الوثيقة '{document_name}'.\n\nيرجى تسجيل الدخول لإكمال التوقيع.\n\nالنظام القضائي الرقمي - المغرب",
                "invitation_subject": "دعوة للانضمام إلى CabineAI",
                "invitation_message": "مرحباً،\n\nلقد تمت دعوتك للانضمام إلى CabineAI.\n\nبيانات الاعتماد المؤقتة الخاصة بك هي:\nالبريد الإلكتروني: {email}\nكلمة المرور: {password}\n\nيرجى تسجيل الدخول وتغيير كلمة المرور الخاصة بك على الفور.\n\nالنظام القضائي الرقمي - المغرب"
            },
            "fr": {
                "welcome_subject": "Bienvenue dans le Système Judiciaire Numérique - Maroc",
                "welcome_message": "Cher/Chère {name},\n\nBienvenue dans le Système Judiciaire Numérique du Royaume du Maroc.\n\nVotre compte a été créé avec succès et vous pouvez maintenant accéder au système.\n\nMerci.\n\nSystème Judiciaire Numérique - Maroc",
                "password_change_subject": "Mot de passe modifié",
                "password_change_message": "Cher/Chère {name},\n\nVotre mot de passe a été modifié avec succès le {timestamp}.\n\nSi vous n'avez pas effectué cette modification, veuillez nous contacter immédiatement.\n\nSystème Judiciaire Numérique - Maroc",
                "case_update_subject": "Mise à jour du dossier",
                "case_update_message": "Le dossier {case_number} a été mis à jour.\n\nType de mise à jour: {update_type}\n\nVeuillez vous connecter pour voir les détails.\n\nSystème Judiciaire Numérique - Maroc",
                "document_ready_subject": "Document prêt",
                "document_ready_message": "Le document '{document_name}' a été traité avec succès et est prêt pour révision.\n\nSystème Judiciaire Numérique - Maroc",
                "signature_required_subject": "Signature requise",
                "signature_required_message": "Le document '{document_name}' nécessite une signature.\n\nVeuillez vous connecter pour compléter la signature.\n\nSystème Judiciaire Numérique - Maroc",
                "invitation_subject": "Invitation à rejoindre CabineAI",
                "invitation_message": "Bonjour,\n\nVous avez été invité à rejoindre CabineAI.\n\nVos identifiants temporaires sont :\nEmail : {email}\nMot de passe : {password}\n\nVeuillez vous connecter et changer votre mot de passe immédiatement.\n\nSystème Judiciaire Numérique - Maroc"
            }
        }
        
        return texts.get(language, texts["ar"]).get(key, f"[{key}]")
