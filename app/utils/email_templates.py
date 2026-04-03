"""
Templates de email personalizados para Bazaar
"""

BAZAAR_PRIMARY_COLOR = '#E6A500'
BAZAAR_LOGO_URL = 'https://bazaar-app-bucket.s3.amazonaws.com/logo.png'  


def get_verification_email_html(username: str, verification_link: str) -> str:
    """Template para verificación de email"""
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
    .cta-button {{
      display: inline-block;
      background-color: {BAZAAR_PRIMARY_COLOR};
      color: #000000;
      padding: 14px 40px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: bold;
      font-size: 16px;
      margin: 20px 0;
      transition: background-color 0.3s ease;
    }}
    .cta-button:hover {{
      background-color: #d4900a;
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
      <div class="greeting">¡Hola {username}!</div>
      
      <div class="message">
        <p>Gracias por registrarte en <strong>Bazaar</strong>.</p>
        <p>Verifica tu correo para activar tu cuenta y comenzar a usar todas nuestras funcionalidades.</p>
      </div>
      
      <a href="{verification_link}" class="cta-button">Verificar Cuenta</a>
      
      <div class="expiration">
        ⏱️ Este enlace expira en 24 horas
      </div>
      
      <div class="security-note">
        <strong>¿No solicitaste este correo?</strong><br>
        Si no creaste esta cuenta, simplemente ignora este mensaje. Tu seguridad es importante para nosotros.
      </div>
    </div>
    
    <div class="footer">
      <p>&copy; 2026 Bazaar. Todos los derechos reservados.</p>
      <p>¿Preguntas? Contáctanos en support@bazaar.app</p>
    </div>
  </div>
</body>
</html>
"""


def get_reset_password_email_html(username: str, reset_link: str) -> str:
    """Template para reseteo de contraseña"""
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
    .cta-button {{
      display: inline-block;
      background-color: {BAZAAR_PRIMARY_COLOR};
      color: #000000;
      padding: 14px 40px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: bold;
      font-size: 16px;
      margin: 20px 0;
      transition: background-color 0.3s ease;
    }}
    .cta-button:hover {{
      background-color: #d4900a;
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
      <div class="greeting">Hola {username},</div>
      
      <div class="message">
        <p>Recibimos una solicitud para restablecer tu contraseña.</p>
        <p>Haz clic en el botón de abajo para crear una nueva contraseña.</p>
      </div>
      
      <a href="{reset_link}" class="cta-button">Restablecer Contraseña</a>
      
      <div class="expiration">
        ⏱️ Este enlace expira en 24 horas
      </div>
      
      <div class="security-note">
        <strong>⚠️ Por seguridad:</strong><br>
        Si tú no solicitaste esto, ignora este correo. Tu cuenta permanecerá segura.
      </div>
    </div>
    
    <div class="footer">
      <p>&copy; 2026 Bazaar. Todos los derechos reservados.</p>
      <p>¿Preguntas? Contáctanos en support@bazaar.app</p>
    </div>
  </div>
</body>
</html>
"""


def get_welcome_email_html(username: str) -> str:
    """Template de bienvenida (opcional)"""
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
      <div class="greeting">¡Bienvenido {username}!</div>
      
      <div class="message">
        <p>Tu cuenta está verificada y lista para usar.</p>
        <p>Estamos emocionados de tenerte en la comunidad Bazaar.</p>
      </div>
      
      <div class="features">
        <div class="feature-item">Acceso ilimitado a todas las funcionalidades</div>
        <div class="feature-item">Soporte al cliente 24/7</div>
        <div class="feature-item">Sincronización en tiempo real</div>
        <div class="feature-item">Seguridad de nivel empresarial</div>
      </div>
    </div>
    
    <div class="footer">
      <p>&copy; 2026 Bazaar. Todos los derechos reservados.</p>
      <p>¿Preguntas? Contáctanos en support@bazaar.app</p>
    </div>
  </div>
</body>
</html>
"""
