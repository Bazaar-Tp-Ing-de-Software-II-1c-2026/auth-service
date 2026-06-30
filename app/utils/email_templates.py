"""
Custom email templates for Bazaar
"""

BAZAAR_PRIMARY_COLOR = "#E6A500"
BAZAAR_LOGO_URL = "https://bazaar-app-bucket.s3.amazonaws.com/logo.png"


def get_verification_email_html(username: str, verification_code: str) -> str:
    """Template for email verification with code"""
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
      line-height: 1.6;
      color: #333;
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    .header {{
      background-color: #121212;
      padding: 30px 20px;
      text-align: center;
      border-bottom: 4px solid {BAZAAR_PRIMARY_COLOR};
    }}
    .logo {{
      max-width: 100px;
      height: auto;
      margin-bottom: 15px;
    }}
    .content {{
      padding: 40px 30px;
      text-align: center;
    }}
    .greeting {{
      font-size: 24px;
      font-weight: bold;
      color: #121212;
      margin-bottom: 20px;
    }}
    .message {{
      font-size: 16px;
      color: #555;
      margin-bottom: 30px;
      line-height: 1.8;
    }}
    .code-box {{
      background-color: #f9f9f9;
      border: 2px solid {BAZAAR_PRIMARY_COLOR};
      border-radius: 8px;
      padding: 20px;
      margin: 30px 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 15px;
    }}
    .code-text {{
      font-size: 28px;
      font-weight: bold;
      color: {BAZAAR_PRIMARY_COLOR};
      letter-spacing: 2px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    }}
    .copy-icon {{
      cursor: pointer;
      font-size: 20px;
      color: {BAZAAR_PRIMARY_COLOR};
    }}
    .footer {{
      background-color: #f8f8f8;
      padding: 20px;
      text-align: center;
      font-size: 12px;
      color: #999;
      border-top: 1px solid #e0e0e0;
    }}
    .expiration {{
      color: #e74c3c;
      font-size: 14px;
      margin-top: 20px;
      font-weight: bold;
    }}
    .security-note {{
      background-color: #f0f0f0;
      padding: 15px;
      border-radius: 4px;
      font-size: 13px;
      color: #666;
      margin-top: 25px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="{BAZAAR_LOGO_URL}" alt="Bazaar Logo" class="logo" />
      <h1 style="color: {BAZAAR_PRIMARY_COLOR}; margin: 10px 0;">Bazaar</h1>
    </div>
    
    <div class="content">
      <div class="greeting">Hi {username}!</div>
      
      <div class="message">
        <p>Thank you for signing up for <strong>Bazaar</strong>.</p>
        <p>Use the code below to verify your email and activate your account.</p>
      </div>
      
      <div class="code-box">
        <span class="code-text">{verification_code}</span>
        <span class="copy-icon">📋</span>
      </div>
      
      <div class="expiration">
        ⏱️ This code expires in 1 hour
      </div>
      
      <div class="security-note">
        <strong>Didn't request this email?</strong><br>
        If you didn't create this account, simply ignore this message. Your security is important to us.
      </div>
    </div>
    
    <div class="footer">
      <p>&copy; 2026 Bazaar. All rights reserved.</p>
      <p>Questions? Contact us at support@bazaar.app</p>
    </div>
  </div>
</body>
</html>
"""


def get_reset_password_email_html(username: str, reset_code: str) -> str:
    """Template for password reset with code"""
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
      line-height: 1.6;
      color: #333;
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    .header {{
      background-color: #121212;
      padding: 30px 20px;
      text-align: center;
      border-bottom: 4px solid {BAZAAR_PRIMARY_COLOR};
    }}
    .logo {{
      max-width: 100px;
      height: auto;
      margin-bottom: 15px;
    }}
    .content {{
      padding: 40px 30px;
      text-align: center;
    }}
    .greeting {{
      font-size: 24px;
      font-weight: bold;
      color: #121212;
      margin-bottom: 20px;
    }}
    .message {{
      font-size: 16px;
      color: #555;
      margin-bottom: 30px;
      line-height: 1.8;
    }}
    .code-box {{
      background-color: #f9f9f9;
      border: 2px solid {BAZAAR_PRIMARY_COLOR};
      border-radius: 8px;
      padding: 20px;
      margin: 30px 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 15px;
    }}
    .code-text {{
      font-size: 28px;
      font-weight: bold;
      color: {BAZAAR_PRIMARY_COLOR};
      letter-spacing: 2px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    }}
    .copy-icon {{
      cursor: pointer;
      font-size: 20px;
      color: {BAZAAR_PRIMARY_COLOR};
    }}
    .footer {{
      background-color: #f8f8f8;
      padding: 20px;
      text-align: center;
      font-size: 12px;
      color: #999;
      border-top: 1px solid #e0e0e0;
    }}
    .expiration {{
      color: #e74c3c;
      font-size: 14px;
      margin-top: 20px;
      font-weight: bold;
    }}
    .security-note {{
      background-color: #fff3cd;
      padding: 15px;
      border-radius: 4px;
      font-size: 13px;
      color: #856404;
      margin-top: 25px;
      border-left: 4px solid {BAZAAR_PRIMARY_COLOR};
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="{BAZAAR_LOGO_URL}" alt="Bazaar Logo" class="logo" />
      <h1 style="color: {BAZAAR_PRIMARY_COLOR}; margin: 10px 0;">Bazaar</h1>
    </div>
    
    <div class="content">
      <div class="greeting">Hi {username},</div>
      
      <div class="message">
        <p>We received a request to reset your password.</p>
        <p>Use the code below to set up a new password.</p>
      </div>
      
      <div class="code-box">
        <span class="code-text">{reset_code}</span>
        <span class="copy-icon">📋</span>
      </div>
      
      <div class="expiration">
        ⏱️ This code expires in 1 hour
      </div>
      
      <div class="security-note">
        <strong>⚠️ For security:</strong><br>
        If you didn't request this, please ignore this email. Your account will remain secure.
      </div>
    </div>
    
    <div class="footer">
      <p>&copy; 2026 Bazaar. All rights reserved.</p>
      <p>Questions? Contact us at support@bazaar.app</p>
    </div>
  </div>
</body>
</html>
"""


def get_welcome_email_html(username: str) -> str:
    """Welcome template (optional)"""
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
      line-height: 1.6;
      color: #333;
      margin: 0;
      padding: 0;
      background-color: #f5f5f5;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    .header {{
      background-color: #121212;
      padding: 30px 20px;
      text-align: center;
      border-bottom: 4px solid {BAZAAR_PRIMARY_COLOR};
    }}
    .logo {{
      max-width: 100px;
      height: auto;
      margin-bottom: 15px;
    }}
    .content {{
      padding: 40px 30px;
      text-align: center;
    }}
    .greeting {{
      font-size: 24px;
      font-weight: bold;
      color: #121212;
      margin-bottom: 20px;
    }}
    .message {{
      font-size: 16px;
      color: #555;
      margin-bottom: 30px;
      line-height: 1.8;
    }}
    .features {{
      text-align: left;
      background-color: #f8f8f8;
      padding: 20px;
      border-radius: 6px;
      margin: 20px 0;
    }}
    .feature-item {{
      padding: 10px 0;
      color: #555;
    }}
    .feature-item:before {{
      content: "✓ ";
      color: {BAZAAR_PRIMARY_COLOR};
      font-weight: bold;
      margin-right: 10px;
    }}
    .footer {{
      background-color: #f8f8f8;
      padding: 20px;
      text-align: center;
      font-size: 12px;
      color: #999;
      border-top: 1px solid #e0e0e0;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="{BAZAAR_LOGO_URL}" alt="Bazaar Logo" class="logo" />
      <h1 style="color: {BAZAAR_PRIMARY_COLOR}; margin: 10px 0;">Bazaar</h1>
    </div>
    
    <div class="content">
      <div class="greeting">Welcome {username}!</div>
      
      <div class="message">
        <p>Your account is verified and ready to go.</p>
        <p>We are thrilled to have you in the Bazaar community.</p>
      </div>
      
      <div class="features">
        <div class="feature-item">Unlimited access to all features</div>
        <div class="feature-item">24/7 customer support</div>
        <div class="feature-item">Real-time synchronization</div>
        <div class="feature-item">Enterprise-grade security</div>
      </div>
    </div>
    
    <div class="footer">
      <p>&copy; 2026 Bazaar. All rights reserved.</p>
      <p>Questions? Contact us at support@bazaar.app</p>
    </div>
  </div>
</body>
</html>
"""