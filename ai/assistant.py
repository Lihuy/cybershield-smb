"""A transparent rule-based assistant for common small-business cyber questions."""

DISCLAIMER = (
    "CyberShield SMB provides general educational information only and does not replace "
    "professional cybersecurity, legal, or incident-response advice."
)

_RESPONSES = {
    "mfa": (
        "Multi-factor authentication (MFA) is an extra security check after your password. "
        "For example, you might approve a prompt on your phone or enter a code from an authenticator app. "
        "If someone steals your password, MFA makes it much harder for them to access your account."
    ),
    "multi factor": (
        "Multi-factor authentication (MFA) is an extra security check after your password. "
        "For example, you might approve a prompt on your phone or enter a code from an authenticator app. "
        "If someone steals your password, MFA makes it much harder for them to access your account."
    ),
    "two factor": (
        "Two-factor authentication (2FA) is a type of MFA. It adds a second proof of identity after your password, "
        "such as a phone prompt or code, to help protect your account."
    ),
    "phish": (
        "Phishing is a fake email, text, or website designed to trick you into sharing information, paying a false invoice, "
        "or opening harmful files. Pause before clicking, check the sender carefully, and verify unusual requests using a known phone number."
    ),
    "backup": (
        "Backups are separate copies of your important business information. They are essential because they can help you recover after "
        "ransomware, accidental deletion, theft, or equipment failure. Keep at least one encrypted copy separate from your main network and test restoring it."
    ),
    "firewall": (
        "A firewall is a security control that filters network traffic. It helps block unwanted connections to your devices and network. "
        "Your internet router and each business computer should have a firewall enabled and protected with strong administrator passwords."
    ),
    "vpn": (
        "A virtual private network (VPN) creates an encrypted connection between your device and a trusted network or service. "
        "It can help protect work traffic on public Wi-Fi, but it does not replace MFA, updates, backups, or good password practices."
    ),
    "risk": (
        "Cyber risk is the chance that a digital threat could disrupt your business, expose information, or cause financial loss. "
        "You reduce it by improving practical controls such as MFA, secure backups, regular updates, safe email habits, and limited access."
    ),
    "password": (
        "Use a long, unique password for every business account. A password manager can create and remember them safely. "
        "Avoid reusing passwords because one leaked password could otherwise unlock several services."
    ),
    "ransomware": (
        "Ransomware is harmful software that locks or encrypts files and demands payment. "
        "Reduce the impact with tested offline or cloud-separated backups, software updates, endpoint protection, MFA, and phishing awareness."
    ),
    "incident": (
        "If you suspect a cyber incident, disconnect the affected device from the network if safe to do so, preserve evidence, tell the right person, "
        "reset exposed passwords from a clean device, and seek qualified help when needed. Do not rush to delete evidence or pay a demand."
    ),
}


def answer_question(question):
    """Return a concise, simple-language answer without presenting as generative AI."""
    cleaned = (question or "").strip().lower()
    if not cleaned:
        response = "Ask me about MFA, phishing, backups, firewalls, VPNs, passwords, ransomware, or cyber risk."
    else:
        response = next((text for keyword, text in _RESPONSES.items() if keyword in cleaned), None)
        if response is None:
            response = (
                "I can help explain common small-business cybersecurity topics in plain English. "
                "Try asking about MFA, phishing, backups, passwords, firewalls, VPNs, ransomware, or cyber risk."
            )
    return f"{response}\n\n{DISCLAIMER}"
