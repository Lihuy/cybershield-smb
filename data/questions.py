"""Cybersecurity self-assessment questions used by the Flask application."""

ASSESSMENT_CATEGORIES = [
    {
        "id": "identity",
        "name": "Identity & Access",
        "short_name": "Identity",
        "icon": "bi-person-lock",
        "description": "How your business protects accounts and who can use them.",
        "questions": [
            {
                "id": "mfa",
                "question": "Do staff use multi-factor authentication (MFA) on important business accounts?",
                "help": "MFA asks for a second proof, such as a phone prompt, after a password.",
                "recommendation": "Enable MFA on email, banking, accounting, cloud storage, and administrator accounts.",
                "priority": "Critical",
            },
            {
                "id": "unique_passwords",
                "question": "Does every staff member use a unique, strong password for each business account?",
                "help": "A password manager makes strong, unique passwords much easier to manage.",
                "recommendation": "Adopt a password manager and require long, unique passwords for every business service.",
                "priority": "High",
            },
            {
                "id": "least_privilege",
                "question": "Do staff have access only to the systems and data they need for their role?",
                "help": "Limiting access reduces the impact of a compromised account.",
                "recommendation": "Review user permissions and remove administrator access that is not essential.",
                "priority": "High",
            },
            {
                "id": "account_review",
                "question": "Are accounts promptly removed or disabled when a worker leaves the business?",
                "help": "Old accounts can give former staff or attackers a way back in.",
                "recommendation": "Add account removal to your employee offboarding checklist and review inactive accounts monthly.",
                "priority": "Medium",
            },
        ],
    },
    {
        "id": "device",
        "name": "Device Security",
        "short_name": "Device",
        "icon": "bi-laptop",
        "description": "How laptops, desktops, phones, and tablets are kept secure.",
        "questions": [
            {
                "id": "automatic_updates",
                "question": "Are operating systems and business software set to install security updates promptly?",
                "help": "Updates close weaknesses that criminals routinely exploit.",
                "recommendation": "Turn on automatic updates and set a regular check for devices that need manual updates.",
                "priority": "High",
            },
            {
                "id": "endpoint_protection",
                "question": "Does every business device have active antivirus or endpoint protection?",
                "help": "Endpoint protection helps detect harmful software and suspicious activity.",
                "recommendation": "Install and monitor reputable endpoint protection on every company-owned device.",
                "priority": "High",
            },
            {
                "id": "screen_lock",
                "question": "Do business devices automatically lock when left unattended?",
                "help": "A short screen-lock timer protects data in shared or public spaces.",
                "recommendation": "Require a PIN or password and enable automatic screen locking after a short period of inactivity.",
                "priority": "Medium",
            },
            {
                "id": "disk_encryption",
                "question": "Is full-disk encryption enabled on laptops that hold business information?",
                "help": "Encryption protects files if a laptop is lost or stolen.",
                "recommendation": "Enable BitLocker, FileVault, or your device platform's full-disk encryption on all laptops.",
                "priority": "Medium",
            },
        ],
    },
    {
        "id": "network",
        "name": "Network Security",
        "short_name": "Network",
        "icon": "bi-router",
        "description": "How your internet connection, Wi-Fi, and network equipment are protected.",
        "questions": [
            {
                "id": "firewall",
                "question": "Is a firewall enabled on your business network and on staff computers?",
                "help": "A firewall controls unwanted connections to and from your systems.",
                "recommendation": "Confirm your router firewall and device firewalls are enabled and protected with strong administrator passwords.",
                "priority": "Critical",
            },
            {
                "id": "secure_wifi",
                "question": "Is your business Wi-Fi protected with WPA2/WPA3 and a strong, unique password?",
                "help": "Old Wi-Fi security and shared default passwords are easier to break into.",
                "recommendation": "Use WPA2 or WPA3, change the router's default credentials, and use a unique Wi-Fi passphrase.",
                "priority": "High",
            },
            {
                "id": "guest_network",
                "question": "Do guests and personal devices use a separate Wi-Fi network from business systems?",
                "help": "Network separation prevents a visitor's device from reaching sensitive systems.",
                "recommendation": "Create a separate guest Wi-Fi network that cannot access business computers, printers, or file storage.",
                "priority": "Medium",
            },
        ],
    },
    {
        "id": "email",
        "name": "Email Security",
        "short_name": "Email",
        "icon": "bi-envelope-check",
        "description": "How your business reduces phishing, invoice fraud, and email account takeover.",
        "questions": [
            {
                "id": "email_mfa",
                "question": "Is MFA enabled on all business email accounts?",
                "help": "Email is often the key to password resets and sensitive business communications.",
                "recommendation": "Make MFA mandatory for every business email account, including shared or administrator mailboxes.",
                "priority": "Critical",
            },
            {
                "id": "email_filtering",
                "question": "Does your email service use spam and phishing filtering?",
                "help": "Filtering catches many malicious messages before staff see them.",
                "recommendation": "Enable your email provider's anti-phishing and spam controls and review quarantine reports regularly.",
                "priority": "High",
            },
            {
                "id": "payment_verification",
                "question": "Do staff verify unusual payment or bank-detail changes through a second channel?",
                "help": "A phone call to a known number can stop many business email compromise scams.",
                "recommendation": "Create a two-person or out-of-band verification step for new payees and changed bank details.",
                "priority": "High",
            },
        ],
    },
    {
        "id": "backup",
        "name": "Backup & Recovery",
        "short_name": "Backup",
        "icon": "bi-cloud-arrow-up",
        "description": "How your business keeps important information recoverable after an incident.",
        "questions": [
            {
                "id": "regular_backups",
                "question": "Are important business files backed up automatically and regularly?",
                "help": "Regular backups help your business recover from ransomware, mistakes, and hardware failure.",
                "recommendation": "Set up automatic backups for essential files, accounting data, customer records, and key systems.",
                "priority": "Critical",
            },
            {
                "id": "offsite_backup",
                "question": "Is at least one backup kept separate from your main computers or network?",
                "help": "A separate copy is less likely to be affected by ransomware or a local disaster.",
                "recommendation": "Keep an encrypted cloud or offline backup separate from the main business network.",
                "priority": "Critical",
            },
            {
                "id": "restore_testing",
                "question": "Have you tested restoring a file or system from backup in the last 12 months?",
                "help": "A backup only helps if it can be restored when needed.",
                "recommendation": "Schedule a simple restore test at least twice a year and record the result.",
                "priority": "High",
            },
        ],
    },
    {
        "id": "awareness",
        "name": "Employee Awareness",
        "short_name": "Employees",
        "icon": "bi-people",
        "description": "How your people recognise and report common cyber threats.",
        "questions": [
            {
                "id": "security_training",
                "question": "Do staff receive regular, practical cybersecurity awareness training?",
                "help": "Short, recurring training is more effective than a single annual session.",
                "recommendation": "Run brief cybersecurity awareness sessions at least twice a year, focusing on real business risks.",
                "priority": "High",
            },
            {
                "id": "phishing_reporting",
                "question": "Do staff know how to report a suspicious email, link, or text message?",
                "help": "Fast reporting helps stop an attack before it spreads.",
                "recommendation": "Publish a simple reporting process and encourage staff to report suspicious messages without blame.",
                "priority": "Medium",
            },
            {
                "id": "incident_process",
                "question": "Does the business have a simple plan for responding to a cyber incident?",
                "help": "Knowing who to call and what to do reduces confusion during an incident.",
                "recommendation": "Write a one-page incident response checklist covering isolation, reporting, contacts, and recovery.",
                "priority": "Medium",
            },
        ],
    },
]


def all_questions():
    """Return every question in assessment order."""
    return [question for category in ASSESSMENT_CATEGORIES for question in category["questions"]]
