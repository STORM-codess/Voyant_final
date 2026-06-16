import asyncio
import os
import httpx
from app.config import settings

# Transactional email via Resend's HTTP API (https://resend.com).
# We use HTTP (port 443) instead of SMTP because most cloud hosts (Render
# free tier included) block outbound SMTP ports — HTTP email always works.
#
# Required env var: RESEND_API_KEY
# Optional env var: EMAIL_FROM  (defaults to Resend's shared onboarding sender)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
# Until you verify your own domain in Resend, use their sandbox sender.
# Once you verify a domain, set EMAIL_FROM="Voyant <hello@yourdomain.com>".
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Voyant <onboarding@resend.dev>")

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
        <h2 style="color: #2F5D50;">You've been invited!</h2>
        <p><strong>{inviter_name}</strong> has invited you to join <strong>{trip_name}</strong> on Voyant.</p>
        <p>Voyant helps groups plan trips together — fill in your preferences, vote on destinations, and let AI handle the rest.</p>
        <div style="margin: 30px 0;">
            <a href="{trip_link}"
               style="background-color: #E0A458; color: white; padding: 12px 24px;
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
        print(f"Invite email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Email failed: {str(e)}")
        return False


async def send_final_plan(
    members: list,
    trip_name: str,
    final_plan: list
):
    """Send final trip plan to all members"""

    plan_html = ""
    for decision in final_plan:
        plan_html += f"""
        <div style="margin: 16px 0; padding: 16px; background: #f9fafb; border-radius: 8px;">
            <h3 style="color: #2F5D50; margin: 0 0 8px 0;">{decision['title']}</h3>
            <p style="margin: 0; font-size: 18px; font-weight: bold;">{decision['winner']}</p>
            {f'<p style="color: #888; font-size: 12px;">Selected randomly due to tie</p>' if decision.get('is_random_winner') else ''}
        </div>
        """

    for member_email in members:
        try:
            await _send_email(
                subject=f"Your trip plan for {trip_name} is ready!",
                to_email=member_email,
                html=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #2F5D50;">Your Trip Plan is Ready!</h2>
                    <p>The group has voted and your trip plan for <strong>{trip_name}</strong> is finalized.</p>
                    <div style="margin: 24px 0;">
                        {plan_html}
                    </div>
                    <p style="color: #888; font-size: 14px;">
                        Enjoy your trip! Planned with Voyant
                    </p>
                </div>
                """
            )
            print(f"Final plan sent to {member_email}")
        except Exception as e:
            print(f"Email failed for {member_email}: {str(e)}")


async def _send_email(subject: str, to_email: str, html: str):
    """POST the email to Resend's HTTP API. Raises on non-2xx so callers'
    try/except can log a failure."""
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not set")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": subject,
                "html": html,
            },
        )
    if resp.status_code >= 300:
        raise RuntimeError(f"Resend API {resp.status_code}: {resp.text}")
    return resp.json()
