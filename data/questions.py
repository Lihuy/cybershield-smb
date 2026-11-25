"""Cybersecurity self-assessment questions used by the Flask application.

Each question keeps its v1.0 wording, priority and recommendation unchanged. CyberShield SMB 2.0
adds traceability fields only; they are shown to the user but never used in scoring:
- ``reason``: why a small business is asked this, in plain English.
- ``csf_functions``: the NIST CSF 2.0 function(s) the safeguard belongs to.
- ``sources``: published guidance the question is based on, in the same format as the sector
  questions (see ``data/sectors.py`` for the framework list and how each reference was checked).
  NIST CSF 2.0 identifiers and Essential Eight Maturity Level One wording were checked against
  the PDFs on 23 November 2026; ACSC headings against the January 2025 Small Business Cyber
  Security Guide. "direct" means the source asks for the same safeguard; "related" means it
  covers the same aim without naming this exact safeguard.

The Essential Eight appears only where one of its eight strategies fits. Wi-Fi, firewalls,
encryption, screen locks, email filtering, training and incident planning are outside it.
"""

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
                "reason": "Stolen or guessed passwords are the most common way into small business accounts, and MFA stops most of these attempts.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-03", "note": "Users, services and hardware are authenticated", "fit": "direct"},
                    {"framework": "e8", "ref": "Multi-factor authentication", "note": "Maturity Level One requires MFA for online services that hold the organisation's sensitive data", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Turn on multi-factor authentication", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "unique_passwords",
                "question": "Does every staff member use a unique, strong password for each business account?",
                "help": "A password manager makes strong, unique passwords much easier to manage.",
                "recommendation": "Adopt a password manager and require long, unique passwords for every business service.",
                "priority": "High",
                "reason": "A password reused across services means one breached website can unlock the business's other accounts.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-01", "note": "Identities and credentials for authorised users are managed by the organisation", "fit": "related"},
                    {"framework": "acsc", "ref": "Secure your accounts: Use strong passwords or passphrases", "note": "Includes using a password manager", "fit": "direct"},
                ],
            },
            {
                "id": "least_privilege",
                "question": "Do staff have access only to the systems and data they need for their role?",
                "help": "Limiting access reduces the impact of a compromised account.",
                "recommendation": "Review user permissions and remove administrator access that is not essential.",
                "priority": "High",
                "reason": "If an account with wide access is taken over, the attacker gets that same wide access.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-05", "note": "Access permissions are managed and reviewed using least privilege and separation of duties", "fit": "direct"},
                    {"framework": "e8", "ref": "Restrict administrative privileges", "note": "Maturity Level One requires privileged access to be validated and kept to dedicated accounts", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Implement access controls", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "account_review",
                "question": "Are accounts promptly removed or disabled when a worker leaves the business?",
                "help": "Old accounts can give former staff or attackers a way back in.",
                "recommendation": "Add account removal to your employee offboarding checklist and review inactive accounts monthly.",
                "priority": "Medium",
                "reason": "Accounts left open after someone leaves are an easy way back in for the former worker or an attacker.",
                "csf_functions": ["GOVERN", "PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-01", "note": "Identities and credentials for authorised users are managed by the organisation", "fit": "direct"},
                    {"framework": "nist", "ref": "GV.RR-04", "note": "Cybersecurity is included in human resources practices, such as offboarding", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Manage shared accounts", "note": "Covers changing access when staff leave", "fit": "related"},
                ],
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
                "reason": "Criminals routinely use known weaknesses that an available update would have closed.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.PS-02", "note": "Software is maintained, replaced and removed commensurate with risk", "fit": "direct"},
                    {"framework": "e8", "ref": "Patch applications; Patch operating systems", "note": "Maturity Level One sets time limits for applying patches and replacing unsupported software", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Update your software", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "endpoint_protection",
                "question": "Does every business device have active antivirus or endpoint protection?",
                "help": "Endpoint protection helps detect harmful software and suspicious activity.",
                "recommendation": "Install and monitor reputable endpoint protection on every company-owned device.",
                "priority": "High",
                "reason": "Harmful software usually arrives through everyday devices, so each one needs something watching for it.",
                "csf_functions": ["PROTECT", "DETECT"],
                "sources": [
                    {"framework": "nist", "ref": "DE.CM-09", "note": "Computing hardware, software and their data are monitored to find potentially adverse events", "fit": "direct"},
                    {"framework": "e8", "ref": "Application control", "note": "Covers the same aim, stopping malicious programs from running, by a stricter method", "fit": "related"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Use security software", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "screen_lock",
                "question": "Do business devices automatically lock when left unattended?",
                "help": "A short screen-lock timer protects data in shared or public spaces.",
                "recommendation": "Require a PIN or password and enable automatic screen locking after a short period of inactivity.",
                "priority": "Medium",
                "reason": "An unlocked device left in a shop, café or car gives anyone nearby access to business accounts.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-03", "note": "Users, services and hardware are authenticated", "fit": "related"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Keep your devices locked and physically secure", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "disk_encryption",
                "question": "Is full-disk encryption enabled on laptops that hold business information?",
                "help": "Encryption protects files if a laptop is lost or stolen.",
                "recommendation": "Enable BitLocker, FileVault, or your device platform's full-disk encryption on all laptops.",
                "priority": "Medium",
                "reason": "Laptops are often lost or stolen, and encryption keeps the files on them unreadable.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-01", "note": "The confidentiality, integrity and availability of data at rest are protected", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Keep your devices locked and physically secure", "note": "Covers the same aim of protecting lost or stolen devices; encryption is not named", "fit": "related"},
                ],
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
                "reason": "A firewall blocks unwanted connections before they reach business computers.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.IR-01", "note": "Networks and environments are protected from unauthorised logical access and usage", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Secure your network and external services", "note": "The guide covers network security but does not name firewalls", "fit": "related"},
                ],
            },
            {
                "id": "secure_wifi",
                "question": "Is your business Wi-Fi protected with WPA2/WPA3 and a strong, unique password?",
                "help": "Old Wi-Fi security and shared default passwords are easier to break into.",
                "recommendation": "Use WPA2 or WPA3, change the router's default credentials, and use a unique Wi-Fi passphrase.",
                "priority": "High",
                "reason": "Weak Wi-Fi security or a default router password lets people nearby join the business network.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.IR-01", "note": "Networks and environments are protected from unauthorised logical access and usage", "fit": "direct"},
                    {"framework": "nist", "ref": "PR.PS-01", "note": "Configuration management practices are established and applied, such as changing default settings", "fit": "related"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Secure your network and external services", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "guest_network",
                "question": "Do guests and personal devices use a separate Wi-Fi network from business systems?",
                "help": "Network separation prevents a visitor's device from reaching sensitive systems.",
                "recommendation": "Create a separate guest Wi-Fi network that cannot access business computers, printers, or file storage.",
                "priority": "Medium",
                "reason": "A visitor's infected phone or laptop should not be able to reach business systems.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.IR-01", "note": "Networks and environments are protected from unauthorised logical access and usage", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Secure your network and external services", "note": "", "fit": "direct"},
                ],
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
                "reason": "Email is used to reset other passwords, so a taken-over mailbox often leads to every other account.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-03", "note": "Users, services and hardware are authenticated", "fit": "direct"},
                    {"framework": "e8", "ref": "Multi-factor authentication", "note": "Maturity Level One requires MFA for online services that hold the organisation's sensitive data", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Turn on multi-factor authentication", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "email_filtering",
                "question": "Does your email service use spam and phishing filtering?",
                "help": "Filtering catches many malicious messages before staff see them.",
                "recommendation": "Enable your email provider's anti-phishing and spam controls and review quarantine reports regularly.",
                "priority": "High",
                "reason": "Most attacks on small businesses start with a scam email, and filtering removes many before staff see them.",
                "csf_functions": ["PROTECT", "DETECT"],
                "sources": [
                    {"framework": "nist", "ref": "DE.CM-01", "note": "Networks and network services are monitored to find potentially adverse events", "fit": "related"},
                    {"framework": "acsc", "ref": "Threats to small businesses: Scam messages, ways to mitigate", "note": "", "fit": "direct"},
                    {"framework": "oaic", "ref": "Email security", "note": "", "fit": "related"},
                ],
            },
            {
                "id": "payment_verification",
                "question": "Do staff verify unusual payment or bank-detail changes through a second channel?",
                "help": "A phone call to a known number can stop many business email compromise scams.",
                "recommendation": "Create a two-person or out-of-band verification step for new payees and changed bank details.",
                "priority": "High",
                "reason": "Fake invoices and changed bank details are among the costliest scams reported by Australian businesses.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "acsc", "ref": "Threats to small businesses: Email attacks, ways to mitigate", "note": "Recommends checking payment and bank-detail requests through a known contact", "fit": "direct"},
                    {"framework": "nist", "ref": "PR.AT-01", "note": "Personnel are given awareness and training to perform tasks with cybersecurity risks in mind", "fit": "related"},
                ],
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
                "reason": "Backups are what let a business recover from ransomware, mistakes and hardware failure.",
                "csf_functions": ["PROTECT", "RECOVER"],
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-11", "note": "Backups of data are created, protected, maintained and tested", "fit": "direct"},
                    {"framework": "e8", "ref": "Regular backups", "note": "Maturity Level One requires backups to be performed and retained according to business criticality", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Back up your information", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "offsite_backup",
                "question": "Is at least one backup kept separate from your main computers or network?",
                "help": "A separate copy is less likely to be affected by ransomware or a local disaster.",
                "recommendation": "Keep an encrypted cloud or offline backup separate from the main business network.",
                "priority": "Critical",
                "reason": "Ransomware often encrypts or deletes backups it can reach, so one copy needs to be kept apart.",
                "csf_functions": ["PROTECT", "RECOVER"],
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-11", "note": "Backups of data are created, protected, maintained and tested", "fit": "direct"},
                    {"framework": "e8", "ref": "Regular backups", "note": "Maturity Level One requires backups to be kept in a secure and resilient manner and protected from deletion", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Back up your information", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "restore_testing",
                "question": "Have you tested restoring a file or system from backup in the last 12 months?",
                "help": "A backup only helps if it can be restored when needed.",
                "recommendation": "Schedule a simple restore test at least twice a year and record the result.",
                "priority": "High",
                "reason": "A backup that has never been restored may fail when it is needed.",
                "csf_functions": ["RECOVER"],
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-11", "note": "Backups of data are created, protected, maintained and tested", "fit": "direct"},
                    {"framework": "nist", "ref": "RC.RP-03", "note": "The integrity of backups is verified before using them for restoration", "fit": "direct"},
                    {"framework": "e8", "ref": "Regular backups", "note": "Maturity Level One requires restoration from backups to be tested", "fit": "direct"},
                ],
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
                "reason": "Most incidents begin with someone being tricked, so staff are the first line of defence.",
                "csf_functions": ["PROTECT"],
                "sources": [
                    {"framework": "nist", "ref": "PR.AT-01", "note": "Personnel are given awareness and training to perform tasks with cybersecurity risks in mind", "fit": "direct"},
                    {"framework": "acsc", "ref": "Prepare your staff: Educate employees", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "phishing_reporting",
                "question": "Do staff know how to report a suspicious email, link, or text message?",
                "help": "Fast reporting helps stop an attack before it spreads.",
                "recommendation": "Publish a simple reporting process and encourage staff to report suspicious messages without blame.",
                "priority": "Medium",
                "reason": "A quick report from one person can stop the same scam reaching everyone else.",
                "csf_functions": ["DETECT", "RESPOND"],
                "sources": [
                    {"framework": "nist", "ref": "DE.AE-06", "note": "Information on adverse events is provided to authorised staff and tools", "fit": "direct"},
                    {"framework": "nist", "ref": "RS.MA-02", "note": "Incident reports are triaged and validated", "fit": "related"},
                    {"framework": "acsc", "ref": "Prepare your staff: Educate employees", "note": "Includes reporting suspicious messages", "fit": "direct"},
                ],
            },
            {
                "id": "incident_process",
                "question": "Does the business have a simple plan for responding to a cyber incident?",
                "help": "Knowing who to call and what to do reduces confusion during an incident.",
                "recommendation": "Write a one-page incident response checklist covering isolation, reporting, contacts, and recovery.",
                "priority": "Medium",
                "reason": "Knowing who to call and what to do first limits the damage and the time a business is closed.",
                "csf_functions": ["RESPOND", "RECOVER"],
                "sources": [
                    {"framework": "nist", "ref": "ID.IM-04", "note": "Incident response plans are established, communicated, maintained and improved", "fit": "direct"},
                    {"framework": "nist", "ref": "RS.MA-01", "note": "The incident response plan is executed once an incident is declared", "fit": "direct"},
                    {"framework": "acsc", "ref": "Prepare your staff: Make an emergency plan", "note": "", "fit": "direct"},
                    {"framework": "ndb", "ref": "Part IIIC: Notification of eligible data breaches", "note": "A plan should cover when a breach must be reported", "fit": "related"},
                ],
            },
        ],
    },
]


def all_questions():
    """Return every question in assessment order."""
    return [question for category in ASSESSMENT_CATEGORIES for question in category["questions"]]
