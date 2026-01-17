from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings

class Util:
  @staticmethod
  def send_email(data):
    # Check if HTML content is provided
    if 'html_body' in data:
      # Use plain text fallback if provided, otherwise use a simple text version
      plain_text = data.get('body', 'Please view this email in an HTML-supported email client.')
      email = EmailMultiAlternatives(
        subject=data['subject'],
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[data['to_email']]
      )
      email.attach_alternative(data['html_body'], "text/html")
      email.send()
    else:
      email = EmailMessage(
        subject=data['subject'],
        body=data['body'],
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[data['to_email']]
      )
      email.send()