import random
import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from account.serializers import UserRegistrationSerializer,UserLoginSerializer,UserProfileSerializer,UserChangePasswordSerializer,SendPasswordResetEmailSerializer,UserPasswordResetSerializer,SendOTPSerializer,VerifyOTPSerializer,PlanSerializer
from django.contrib.auth import authenticate
from account.renderers import UserRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.utils import timezone
from account.models import User, Plan
from account.utils import Util

# Get logger for this module
logger = logging.getLogger('account')

# Generate Token Manually
def get_tokens_for_user(user):
  refresh = RefreshToken.for_user(user)
  return {
      'refresh': str(refresh),
      'access': str(refresh.access_token),
  }

class UserRegistrationView(APIView):
  renderer_classes = [UserRenderer]
  def post(self, request, format=None):
    try:
      serializer = UserRegistrationSerializer(data=request.data, context={'request': request})
      serializer.is_valid(raise_exception=True)
      user = serializer.save()
      token = get_tokens_for_user(user)
      logger.info(f"New user registered: {user.email}")
      return Response({'token':token, 'msg':'Registration Successful'}, status=status.HTTP_201_CREATED)
    except Exception as e:
      logger.error(f"Registration failed: {str(e)}", exc_info=True)
      raise
  
class SendOTPView(APIView):
    renderer_classes = [UserRenderer]
    def post(self, request):
        try:
            serializer = SendOTPSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']
            otp = random.randint(100000, 999999)
            request.session['otp'] = otp
            request.session['otp_email'] = email
            request.session['otp_expires_at'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

            # HTML email for OTP
            html_body = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ text-align: center; padding: 20px 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 10px; }}
                    .otp-box {{
                        background: #7c3aed;
                        color: white;
                        font-size: 32px;
                        font-weight: bold;
                        padding: 20px;
                        text-align: center;
                        border-radius: 8px;
                        margin: 20px 0;
                        letter-spacing: 8px;
                    }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                    .warning {{ color: #666; font-size: 14px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="color: #7c3aed;">📧 BillEazzy</h1>
                    </div>
                    <div class="content">
                        <p>Hello,</p>
                        <p>Your verification code for BillEazzy account is:</p>
                        <div class="otp-box">{otp}</div>
                        <p class="warning">
                            ⏰ This OTP is valid for <strong>10 minutes</strong> only.
                        </p>
                        <p class="warning">
                            If you didn't request this code, please ignore this email.
                        </p>
                    </div>
                    <div class="footer">
                        <p>Thanks,<br><strong>BillEazzy Team</strong></p>
                    </div>
                </div>
            </body>
            </html>
            '''
            
            data = {
              'subject':'Verify Your Account - BillEazzy',
              'html_body':html_body,
              'to_email':email
            }
            Util.send_email(data)
            logger.info(f"OTP sent to {email}")
            return Response({"msg": "OTP sent successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error sending OTP: {str(e)}", exc_info=True)
            raise


class VerifyOtpView(APIView):
    renderer_classes = [UserRenderer]
    def post(self, request):
        try:
            serializer = VerifyOTPSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            # Retrieve session data
            session_otp = request.session.get('otp')
            session_email = request.session.get('otp_email')
            session_otp_expires_at = request.session.get('otp_expires_at')
            
            if not all([session_otp, session_email, session_otp_expires_at]):
              logger.warning(f"OTP verification failed for {email}: Session expired")
              return Response({'msg': 'OTP not found or session expired'}, status=status.HTTP_400_BAD_REQUEST)

            # Parse session_otp_expires_at back to datetime
            session_otp_expires_at = make_aware(datetime.strptime(session_otp_expires_at, '%Y-%m-%d %H:%M:%S'))

            if email != session_email:
              logger.warning(f"OTP verification failed: Email mismatch for {email}")
              return Response({'msg': 'Email mismatch'}, status=status.HTTP_400_BAD_REQUEST)
            
            if timezone.now() - timedelta(minutes=10) > session_otp_expires_at:
                logger.warning(f"OTP expired for {email}")
                return Response({'msg': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
            if str(session_otp) == str(otp):
                try:
                    request.session.flush()  # Clear the session after verification
                    logger.info(f"OTP verified successfully for {email}")
                    return Response({'msg': 'OTP verified successfully'}, status=status.HTTP_200_OK)

                except User.DoesNotExist:
                    logger.error(f"User not found during OTP verification: {email}")
                    return Response({'msg': 'Unexpected error occurs please try after some time'}, status=status.HTTP_404_NOT_FOUND)
            else:
                logger.warning(f"Invalid OTP for {email}")
                return Response({'msg': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error verifying OTP: {str(e)}", exc_info=True)
            raise
    

class UserLoginView(APIView):
  renderer_classes = [UserRenderer]
  def post(self, request, format=None):
    try:
      serializer = UserLoginSerializer(data=request.data)
      serializer.is_valid(raise_exception=True)
      email = serializer.data.get('email')
      password = serializer.data.get('password')
      user = authenticate(email=email, password=password)
      if user is not None:
        token = get_tokens_for_user(user)
        logger.info(f"User logged in: {email}")
        return Response({'token':token, 'msg':'Login Success'}, status=status.HTTP_200_OK)
      else:
        logger.warning(f"Failed login attempt for: {email}")
        return Response({'errors':{'non_field_errors':['Email or Password is not Valid']}}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
      logger.error(f"Login error: {str(e)}", exc_info=True)
      raise


class UserProfileView(APIView):
  renderer_classes = [UserRenderer]
  permission_classes = [IsAuthenticated]
  def get(self, request, format=None):
    try:
      serializer = UserProfileSerializer(request.user)
      logger.info(f"Profile viewed by user: {request.user.email}")
      return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
      logger.error(f"Error fetching profile for {request.user.email}: {str(e)}", exc_info=True)
      raise
  
  def put(self, request, format=None):
    try:
      serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
      if serializer.is_valid():
        serializer.save()
        logger.info(f"Profile updated by user: {request.user.email}")
        return Response(serializer.data, status=status.HTTP_200_OK)
      logger.warning(f"Profile update failed for {request.user.email}: {serializer.errors}")
      return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
      logger.error(f"Error updating profile for {request.user.email}: {str(e)}", exc_info=True)
      raise
  

class UserChangePasswordView(APIView):
  renderer_classes = [UserRenderer]
  permission_classes = [IsAuthenticated]
  def post(self, request, format=None):
    try:
      serializer = UserChangePasswordSerializer(data=request.data, context={'user':request.user})
      serializer.is_valid(raise_exception=True)
      logger.info(f"Password changed for user: {request.user.email}")
      return Response({'msg':'Password Changed Successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
      logger.error(f"Error changing password for {request.user.email}: {str(e)}", exc_info=True)
      raise
  

class SendPasswordResetEmailView(APIView):
  renderer_classes = [UserRenderer]
  def post(self, request, format=None):
    try:
      serializer = SendPasswordResetEmailSerializer(data=request.data)
      serializer.is_valid(raise_exception=True)
      email = request.data.get('email', 'unknown')
      logger.info(f"Password reset email sent to: {email}")
      return Response({'msg':'Password Reset link send. Please check your Email'}, status=status.HTTP_200_OK)
    except Exception as e:
      logger.error(f"Error sending password reset email: {str(e)}", exc_info=True)
      raise
  

class UserPasswordResetView(APIView):
  renderer_classes = [UserRenderer]
  def post(self, request, uid, token, format=None):
    try:
      serializer = UserPasswordResetSerializer(data=request.data, context={'uid':uid, 'token':token})
      serializer.is_valid(raise_exception=True)
      logger.info(f"Password reset completed for uid: {uid}")
      return Response({'msg':'Password Reset Successfully'}, status=status.HTTP_200_OK)
    except Exception as e:
      logger.error(f"Error resetting password for uid {uid}: {str(e)}", exc_info=True)
      raise


class GetPlansView(APIView):
  """
  GET: List all active plans for user selection (excludes custom plans)
  """
  renderer_classes = [UserRenderer]
  def get(self, request, format=None):
    try:
      plans = Plan.objects.filter(is_active=True, is_custom=False).order_by('price')
      serializer = PlanSerializer(plans, many=True)
      logger.info(f"Plans list fetched successfully, {len(plans)} plans available")
      return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
      logger.error(f"Error fetching plans: {str(e)}", exc_info=True)
      raise