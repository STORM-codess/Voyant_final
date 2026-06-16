import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from app.config import settings

SMTP_FROM = f"Voyant <{settings.SMTP_EMAIL}>"

# Frontend base URL for links in emails. Falls back to localhost for dev;
# set FRONTEND_URL in the environment for production.
FRONTEND_URL = getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173"


async def send_trip_invite(
    to_email: str,
    inviter_name: str,
    trip_name: str,
    trip_id: str
):
    """Send trip invite email to new member"""
    trip_link = f"{FRONTEND_URL}/trip/{trip_id}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #6366f1;">You've been invited! 🌍</h2>
        <p><strong>{inviter_name}</strong> has invited you to join <strong>{trip_name}</strong> on Voyant.</p>
        <p>Voyant helps groups plan trips together — fill in your preferences, vote on destinations, and let AI handle the rest.</p>
        <div style="margin: 30px 0;">
            <a href="{trip_link}"
               style="background-color: #6366f1; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                View Trip
            </a>
        </div>
        <p style="color: #888; font-size: 14px;">
            If you don't have an account yet, you'll be prompted to create one.
        </p>
    </div>
    """
    try:
        await _send_email(
            subject=f"You're invited to join {trip_name} on Voyant!",
            to_email=to_email,
            html=html
        )
        print(f"✅ Invite email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        return False


async def send_final_plan(
    members: list,
    trip_name: str,
    final_plan: list
):
    """Send final trip plan to all members"""

    # build plan html
    plan_html = ""
    for decision in final_plan:
        plan_html += f"""
        <div style="margin: 16px 0; padding: 16px; background: #f9fafb; border-radius: 8px;">
            <h3 style="color: #6366f1; margin: 0 0 8px 0;">{decision['title']}</h3>
            <p style="margin: 0; font-size: 18px; font-weight: bold;">{decision['winner']}</p>
            {f'<p style="color: #888; font-size: 12px;">Selected randomly due to tie</p>' if decision.get('is_random_winner') else ''}
        </div>
        """

    for member_email in members:
        try:
            await _send_email(
                subject=f"Your trip plan for {trip_name} is ready! 🎉",
                to_email=member_email,
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #6366f1;">Your Trip Plan is Ready! 🌍</h2>
                    <p>The group has voted and your trip plan for <strong>{trip_name}</strong> is finalized.</p>
                    <div style="margin: 24px 0;">
                        {plan_html}
                    </div>
                    <p style="color: #888; font-size: 14px;">
                        Enjoy your trip! Planned with Voyant 🚀
                    </p>
                </div>
                """
            )
            print(f"✅ Final plan sent to {member_email}")
        except Exception as e:
            print(f"❌ Email failed for {member_email}: {str(e)}")


async def _send_email(subject: str, to_email: str, html: str):
    return await asyncio.to_thread(_send_email_sync, subject, to_email, html)


def _send_email_sync(subject: str, to_email: str, html: str):
    message = EmailMessage()
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(
        "This email contains HTML content. Please view it in an email client that supports HTML."
    )
    message.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        server.send_message(message)