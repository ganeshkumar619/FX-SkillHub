from django.core.management.base import BaseCommand
from django.conf import settings
from notifications.email_service import EmailNotificationService


class Command(BaseCommand):
    help = 'Safely diagnoses and tests the FX SkillHub SMTP connection and email delivery without exposing credentials.'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            type=str,
            default=None,
            help='Optional recipient email address (defaults to EMAIL_HOST_USER or DEFAULT_FROM_EMAIL)'
        )

    def handle(self, *args, **options):
        recipient = options.get('recipient')
        self.stdout.write(self.style.NOTICE('==================================================='))
        self.stdout.write(self.style.NOTICE(' [FX SKILLHUB EMAIL DELIVERY DIAGNOSTIC TEST]'))
        self.stdout.write(self.style.NOTICE('==================================================='))

        backend = getattr(settings, 'EMAIL_BACKEND', '')
        host = getattr(settings, 'EMAIL_HOST', '')
        port = getattr(settings, 'EMAIL_PORT', '')
        user = getattr(settings, 'EMAIL_HOST_USER', '')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)

        self.stdout.write(f"EMAIL_BACKEND:       {backend}")
        self.stdout.write(f"EMAIL_HOST:          {host}:{port}")
        self.stdout.write(f"EMAIL_USE_TLS:       {getattr(settings, 'EMAIL_USE_TLS', False)}")
        self.stdout.write(f"EMAIL_USE_SSL:       {getattr(settings, 'EMAIL_USE_SSL', False)}")
        self.stdout.write(f"EMAIL_HOST_USER:     {'[CONFIGURED]' if user else '[MISSING]'}")
        self.stdout.write(f"EMAIL_HOST_PASSWORD: {'[CONFIGURED]' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else '[MISSING]'}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL:  {from_email}")
        self.stdout.write(f"EMAIL_TIMEOUT:       {timeout}s")
        self.stdout.write('---------------------------------------------------')

        self.stdout.write('Executing SMTP connection, authentication & dispatch test...')
        report = EmailNotificationService.send_test_email(recipient=recipient)

        self.stdout.write(f"Target Recipient:    {report.get('recipient')}")
        self.stdout.write(f"Socket Connected:    {report.get('connected')}")
        self.stdout.write(f"Authenticated:       {report.get('authenticated')}")
        self.stdout.write(f"Email Dispatched:    {report.get('send_success')}")
        self.stdout.write(f"Total Latency:       {report.get('total_latency_ms')} ms")

        if report.get('send_success'):
            self.stdout.write(self.style.SUCCESS('\n>>> RESULT: SUCCESS! The email was successfully handed off to the SMTP server.'))
        else:
            self.stdout.write(self.style.ERROR('\n>>> RESULT: FAILED!'))
            self.stdout.write(self.style.ERROR(f"Failure Stage:   {report.get('error_stage')}"))
            self.stdout.write(self.style.ERROR(f"Exception Type:  {report.get('error_type')}"))
            self.stdout.write(self.style.ERROR(f"Error Message:   {report.get('error_message')}"))

            self.stdout.write(self.style.WARNING('\nTroubleshooting Guidance:'))
            if report.get('error_stage') == 'CONFIG':
                self.stdout.write(self.style.WARNING(
                    "• Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD to your environment (Render dashboard / .env)."
                ))
            elif 'auth' in str(report.get('error_type', '')).lower() or '535' in str(report.get('error_message', '')):
                self.stdout.write(self.style.WARNING(
                    "• Authentication failed: If using Gmail (smtp.gmail.com), ensure 2-Step Verification is ON and you are using a dedicated 16-character Google App Password without spaces."
                ))
            elif 'timeout' in str(report.get('error_type', '')).lower() or 'refused' in str(report.get('error_message', '')).lower():
                self.stdout.write(self.style.WARNING(
                    "• Connection failed: Outbound port 587 may be blocked or unreachable from this network environment."
                ))
