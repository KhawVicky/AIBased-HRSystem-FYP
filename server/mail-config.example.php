<?php
// Shows the settings needed for SMTP or HTTPS email providers.

return [
    // Use "resend" or "sendgrid" in hosted environments when SMTP is unavailable.
    "provider" => "smtp",
    "enabled" => true,
    "host" => "smtp.gmail.com",
    "port" => 587,
    "username" => "your-email@gmail.com",
    "password" => "your-app-password",
    "encryption" => "tls",
    "from_email" => "your-email@gmail.com",
    "from_name" => "UWC Recruitment",
    "verify_peer" => true,
    // HTTPS mail settings are normally supplied through environment variables:
    // MAIL_PROVIDER=resend, RESEND_API_KEY, RESEND_FROM_EMAIL, RESEND_FROM_NAME.
    // MAIL_PROVIDER=sendgrid, SENDGRID_API_KEY, SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME.
];
