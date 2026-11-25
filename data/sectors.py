"""Business-type taxonomy, intake questions and sector question sets (CyberShield SMB 2.0, Sprint 2).

CONTENT STATUS: DRAFT FOR TEAM REVIEW.
The sector questions were drafted so the adaptive pathway could be built and tested. Each one is
traced to published frameworks in its ``sources`` list (see FRAMEWORKS below). The team's
Research Lead should review the wording and confirm each reference before the usability sessions.

How far each reference has been checked (15 November 2026):
- NIST CSF 2.0: every subcategory identifier confirmed against NIST CSWP 29 (NIST_CSF_2.0.pdf).
  The short descriptions are close paraphrases in Australian spelling, not quotations.
- ASD Essential Eight: strategy names and the Maturity Level One wording confirmed against the
  Essential Eight maturity model, last updated November 2023.
- PCI DSS v4.0.1: every cited requirement number confirmed against the standard (PCI-DSS-v4_0_1.pdf).
- ACSC Small Business Cyber Security Guide: section headings checked against the January 2025 PDF.
- OAIC Guide to securing personal information: statements checked against the OAIC web page.
- Privacy Act 1988 (Cth): Part IIIC (ss 26WK, 26WL), s 6D and Australian Privacy Principles 11.1 and
  11.2 confirmed against Compilation No. 104 (Privacy_Act_1988.pdf).

"fit" is "direct" when the source asks for the same safeguard, and "related" when the source covers
the same aim but not this exact safeguard. Not every question has an Essential Eight source: the
Essential Eight covers eight technical strategies and does not address topics such as card handling.

Design rules that the rest of the code relies on:
- The business types are a small, fixed, predefined set (project delimitation).
- Sector questions are written in advance. Nothing here is generated per user.
- Sector questions are extra. They never replace or alter the 20 core questions, and they
  are scored separately from the core score.
- Every sector question carries a plain-English ``reason`` and at least two ``sources``.
"""

FRAMEWORKS = {
    "nist": {
        "name": "NIST Cybersecurity Framework 2.0",
        "short": "NIST CSF 2.0",
        "publisher": "National Institute of Standards and Technology, NIST CSWP 29 (2024)",
        "url": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
    },
    "e8": {
        "name": "Essential Eight maturity model",
        "short": "Essential Eight",
        "publisher": "Australian Signals Directorate (last updated November 2023)",
        "url": "https://www.cyber.gov.au/sites/default/files/2023-11/PROTECT%20-%20Essential%20Eight%20Maturity%20Model%20%28November%202023%29.pdf",
    },
    "acsc": {
        "name": "Small Business Cyber Security Guide",
        "short": "ACSC small business guide",
        "publisher": "Australian Cyber Security Centre, Australian Signals Directorate (January 2025)",
        "url": "https://www.cyber.gov.au/business-government/small-business-cyber-security/small-business-hub/small-business-cyber-security-guide",
    },
    "pci": {
        "name": "Payment Card Industry Data Security Standard v4.0.1",
        "short": "PCI DSS v4.0.1",
        "publisher": "PCI Security Standards Council",
        "url": "https://www.pcisecuritystandards.org/document_library/?category=pcidss",
    },
    "oaic": {
        "name": "Guide to securing personal information (Australian Privacy Principle 11)",
        "short": "OAIC guide, APP 11",
        "publisher": "Office of the Australian Information Commissioner",
        "url": "https://www.oaic.gov.au/privacy/guidance-and-advice/guide-to-securing-personal-information",
    },
    "ndb": {
        "name": "Privacy Act 1988 (Cth), Part IIIC: Notification of eligible data breaches",
        "short": "Privacy Act 1988",
        "publisher": "Commonwealth of Australia, Compilation No. 104 (4 June 2026)",
        "url": "https://www.legislation.gov.au/C2004A03712/latest/downloads",
    },
}

SECTORS = [
    {
        "id": "retail",
        "name": "Retail",
        "icon": "bi-bag-check",
        "description": "Shops, showrooms and online stores that sell products to customers.",
        "examples": "clothing shop, gift store, online store, newsagent",
        "questions": [
            {
                "id": "retail_pos_supported",
                "question": "Are your point-of-sale (POS) system and card terminals still supported by the supplier and kept up to date?",
                "help": "Supported equipment keeps receiving security fixes. Your POS or payment provider can confirm this.",
                "recommendation": "Ask your POS and payment providers whether your terminals and software are still supported, and turn on automatic updates where offered.",
                "priority": "High",
                "reason": "Retail businesses take most of their payments through POS equipment, which makes it a common target.",
                "sources": [
                    {"framework": "nist", "ref": "PR.PS-02, PR.PS-03", "note": "Software and hardware are maintained, replaced and removed commensurate with risk", "fit": "direct"},
                    {"framework": "e8", "ref": "Patch applications; Patch operating systems", "note": "Maturity Level One includes replacing operating systems that vendors no longer support", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Update your software", "note": "", "fit": "direct"},
                    {"framework": "pci", "ref": "Requirements 6.3.3 and 12.3.4", "note": "Security patches are installed; technologies in use are reviewed to confirm vendors still provide security fixes", "fit": "direct"},
                ],
            },
            {
                "id": "retail_terminal_checks",
                "question": "Do staff regularly check card terminals for signs of tampering, such as unfamiliar attachments or broken seals?",
                "help": "A quick look at the start of each day is enough for most small shops.",
                "recommendation": "Add a daily terminal check to opening tasks and tell staff who to call if something looks different.",
                "priority": "Medium",
                "reason": "Terminals on a shop counter can be reached by the public, so physical tampering is a realistic risk.",
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-06, DE.CM-02", "note": "Physical access to assets is managed; the physical environment is monitored", "fit": "direct"},
                    {"framework": "pci", "ref": "Requirements 9.5.1.2 and 9.5.1.3", "note": "Payment terminal surfaces are periodically inspected for tampering; staff are trained to notice it", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Keep your devices locked and physically secure", "note": "", "fit": "related"},
                ],
            },
            {
                "id": "retail_individual_logins",
                "question": "Does each staff member sign in to the POS or till with their own login or PIN?",
                "help": "Shared logins make it impossible to tell who did what, and they are rarely changed when someone leaves.",
                "recommendation": "Give each staff member their own POS login or PIN and remove it on their last day.",
                "priority": "High",
                "reason": "Shops often have casual and part-time staff sharing one till, so shared logins are common.",
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-01", "note": "Identities and credentials for authorised users, services and hardware are managed", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Manage shared accounts", "note": "", "fit": "direct"},
                    {"framework": "pci", "ref": "Requirements 8.2.1 and 8.2.2", "note": "All users are assigned a unique ID; shared IDs are used only by exception", "fit": "direct"},
                ],
            },
            {
                "id": "retail_card_data",
                "question": "Do you avoid writing down, photographing or emailing customers' card details?",
                "help": "Card details should only ever be entered into the payment terminal or payment page.",
                "recommendation": "Stop recording card details outside your payment system and securely destroy any that have been kept.",
                "priority": "Critical",
                "reason": "Retailers handle card payments every day, and stored card details are valuable to criminals.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-01", "note": "Data-at-rest is protected", "fit": "direct"},
                    {"framework": "pci", "ref": "Requirements 3.3.1 and 4.2.2", "note": "Sensitive authentication data is not stored after authorisation; card numbers sent by email or messaging must be protected with strong cryptography", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Protect your business data", "note": "", "fit": "related"},
                ],
            },
            {
                "id": "retail_selling_accounts",
                "question": "Are the accounts you sell or advertise through (online store, marketplace or social media) protected with multi-factor authentication?",
                "help": "These accounts can change prices, see orders and reach your customers.",
                "recommendation": "Turn on MFA for your online store, marketplace and social media admin accounts.",
                "priority": "High",
                "reason": "A hijacked store or social account can be used to scam your customers under your name.",
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-03", "note": "Users, services and hardware are authenticated", "fit": "direct"},
                    {"framework": "e8", "ref": "Multi-factor authentication", "note": "Maturity Level One: MFA for third-party online services that handle the organisation's sensitive data", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Turn on multi-factor authentication", "note": "", "fit": "direct"},
                ],
            },
        ],
    },
    {
        "id": "hospitality",
        "name": "Hospitality",
        "icon": "bi-cup-hot",
        "description": "Cafes, restaurants, bars, takeaway, catering and accommodation.",
        "examples": "cafe, restaurant, pub, motel, catering business",
        "questions": [
            {
                "id": "hospitality_platform_accounts",
                "question": "Are your booking, online ordering and delivery platform accounts protected with unique passwords and multi-factor authentication?",
                "help": "These accounts hold customer details and often control payouts to your bank account.",
                "recommendation": "Use a unique password and turn on MFA for every booking, ordering and delivery platform you use.",
                "priority": "High",
                "reason": "Hospitality businesses rely on third-party booking and delivery platforms, and a takeover can redirect payouts.",
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-01, PR.AA-03", "note": "Credentials are managed; users are authenticated", "fit": "direct"},
                    {"framework": "e8", "ref": "Multi-factor authentication", "note": "Maturity Level One: MFA for third-party online services that handle the organisation's sensitive data", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Turn on multi-factor authentication; Use strong passwords or passphrases", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "hospitality_staff_logins",
                "question": "Does each staff member have their own POS login or PIN, removed when they leave?",
                "help": "High staff turnover means old logins build up quickly.",
                "recommendation": "Give each worker their own POS login or PIN and remove it as part of their final shift.",
                "priority": "High",
                "reason": "Venues often have many casual staff and frequent turnover, which makes shared or leftover logins likely.",
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-01, PR.AA-05", "note": "Credentials are managed; access permissions are managed and enforced", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Manage shared accounts", "note": "", "fit": "direct"},
                    {"framework": "pci", "ref": "Requirements 8.2.1, 8.2.2 and 8.2.5", "note": "Unique IDs for all users; shared IDs only by exception; access for terminated users is revoked immediately", "fit": "direct"},
                ],
            },
            {
                "id": "hospitality_dedicated_devices",
                "question": "Are POS and ordering tablets used for business only, with no personal email, browsing or app installs?",
                "help": "Personal use is a common way for malware to reach a payment device.",
                "recommendation": "Restrict POS and ordering devices to business apps only and keep them signed out of personal accounts.",
                "priority": "Medium",
                "reason": "Shared tablets at the counter or in the kitchen are often used casually by many people.",
                "sources": [
                    {"framework": "nist", "ref": "PR.PS-01, PR.PS-05", "note": "Configuration management is applied; installation and execution of unauthorised software are prevented", "fit": "direct"},
                    {"framework": "e8", "ref": "Application control", "note": "A simplified small-business form of restricting devices to approved applications", "fit": "related"},
                ],
            },
            {
                "id": "hospitality_outage_plan",
                "question": "Could you keep taking orders and payments if your POS or internet went down during service?",
                "help": "A simple written fallback, such as manual dockets and an offline payment option, is enough.",
                "recommendation": "Write a short outage plan covering manual orders and an offline or backup payment method, and show it to shift leaders.",
                "priority": "Medium",
                "reason": "An outage during a busy service stops trade immediately, so recovery planning matters more here.",
                "sources": [
                    {"framework": "nist", "ref": "PR.IR-03, ID.IM-04, RC.RP-01", "note": "Resilience mechanisms; response and other plans are established; recovery plans are executed", "fit": "direct"},
                    {"framework": "acsc", "ref": "Prepare your staff: Make an emergency plan", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "hospitality_card_details",
                "question": "Do you avoid taking card details on paper, by email or by text for bookings and phone orders?",
                "help": "Use your payment provider's secure link or terminal instead.",
                "recommendation": "Take booking deposits and phone orders through a secure payment link or terminal, never on paper or by message.",
                "priority": "Critical",
                "reason": "Bookings, deposits and phone orders create pressure to take card details informally.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-01, PR.DS-02", "note": "Data-at-rest and data-in-transit are protected", "fit": "direct"},
                    {"framework": "pci", "ref": "Requirements 3.3.1 and 4.2.2", "note": "Sensitive authentication data is not stored after authorisation; card numbers sent by email or messaging must be protected with strong cryptography", "fit": "direct"},
                    {"framework": "oaic", "ref": "Email security", "note": "The guide states that email is not a secure form of communication", "fit": "related"},
                ],
            },
        ],
    },
    {
        "id": "trades",
        "name": "Trades and on-site services",
        "icon": "bi-tools",
        "description": "Building, electrical, plumbing, repairs, cleaning and other work done at customer sites.",
        "examples": "electrician, plumber, builder, landscaper, cleaner",
        "questions": [
            {
                "id": "trades_device_wipe",
                "question": "Can phones and tablets used on the job be locked or wiped remotely if they are lost or stolen?",
                "help": "Both iPhone and Android include a free find-and-erase feature.",
                "recommendation": "Turn on the built-in find, lock and erase feature on every work phone and tablet.",
                "priority": "High",
                "reason": "Devices used on sites and in vehicles are far more likely to be lost or stolen than office equipment.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-01", "note": "Data-at-rest is protected", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Keep your devices locked and physically secure", "note": "The guide covers locking devices; remote erase extends the same aim", "fit": "related"},
                ],
            },
            {
                "id": "trades_invoice_scams",
                "question": "Do your customers know how you send invoices and that you will never change bank details by email?",
                "help": "A line on quotes and invoices is enough.",
                "recommendation": "Add a standing note to quotes and invoices explaining how you send bills and that bank details never change by email.",
                "priority": "High",
                "reason": "Trades are paid by invoice, and criminals send fake invoices with changed bank details in a business's name.",
                "sources": [
                    {"framework": "acsc", "ref": "Threats to small businesses: Email attacks, ways to mitigate", "note": "A formal process for payment requests and bank-detail changes", "fit": "direct"},
                    {"framework": "nist", "ref": "PR.AT (category)", "note": "Awareness and training. No subcategory covers warning customers directly; this is the nearest fit", "fit": "related"},
                ],
            },
            {
                "id": "trades_job_apps",
                "question": "Are your job management, quoting and accounting apps protected with multi-factor authentication?",
                "help": "These apps hold customer details, addresses and payment information.",
                "recommendation": "Turn on MFA for your job management, quoting and accounting apps.",
                "priority": "High",
                "reason": "Mobile businesses run almost entirely from cloud apps, so those logins are the main way in.",
                "sources": [
                    {"framework": "nist", "ref": "PR.AA-03", "note": "Users, services and hardware are authenticated", "fit": "direct"},
                    {"framework": "e8", "ref": "Multi-factor authentication", "note": "Maturity Level One: MFA for third-party online services that handle the organisation's sensitive data", "fit": "direct"},
                    {"framework": "acsc", "ref": "Secure your accounts: Turn on multi-factor authentication", "note": "", "fit": "direct"},
                ],
            },
            {
                "id": "trades_public_wifi",
                "question": "When working away from base, do you use your phone's hotspot or mobile data instead of public Wi-Fi for business tasks?",
                "help": "Public Wi-Fi in cafes, suppliers or customer sites cannot be trusted with banking or invoicing.",
                "recommendation": "Use mobile data or a phone hotspot for banking, invoicing and email when on the road.",
                "priority": "Medium",
                "reason": "On-site work means connecting from many places you do not control.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-02, PR.IR-01", "note": "Data-in-transit is protected; networks are protected from unauthorised access and usage", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Secure your network and external services", "note": "The guide covers securing your own network; it does not address public Wi-Fi", "fit": "related"},
                ],
            },
            {
                "id": "trades_site_access",
                "question": "Are customer site details such as alarm codes, key safe codes and access instructions kept in a protected app rather than texts, notes or paper?",
                "help": "Your job management app or a password manager is a safer place.",
                "recommendation": "Move access codes and site instructions into a protected app and delete them from messages and notes when the job ends.",
                "priority": "High",
                "reason": "Trades are trusted with access to homes and premises, so this information is unusually sensitive.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-01, PR.AA-05", "note": "Data-at-rest is protected; access permissions are managed and enforced", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Protect your business data", "note": "", "fit": "direct"},
                    {"framework": "oaic", "ref": "Access security", "note": "Personal information is only accessed by authorised persons", "fit": "related"},
                ],
            },
        ],
    },
    {
        "id": "professional",
        "name": "Professional services",
        "icon": "bi-briefcase",
        "description": "Office-based advice and services such as accounting, legal, consulting and design.",
        "examples": "accountant, bookkeeper, law practice, consultant, architect",
        "questions": [
            {
                "id": "professional_client_storage",
                "question": "Are client files kept in a business system with access controls, rather than personal email, personal cloud storage or USB drives?",
                "help": "A business-grade document system lets you control and remove access.",
                "recommendation": "Move client files into a business document system and stop using personal accounts and USB drives for client work.",
                "priority": "High",
                "reason": "Professional firms hold confidential client records, which is the main thing an attacker would be after.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-01, PR.AA-05", "note": "Data-at-rest is protected; access permissions are managed and enforced", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your business data; Secure your accounts: Implement access controls", "note": "", "fit": "direct"},
                    {"framework": "oaic", "ref": "APP 11.1 (Privacy Act 1988, Schedule 1)", "note": "Take reasonable steps to protect personal information from misuse, interference and loss, and from unauthorised access, modification or disclosure", "fit": "direct"},
                ],
            },
            {
                "id": "professional_secure_sharing",
                "question": "Do you send sensitive documents through a secure portal or protected link instead of ordinary email attachments?",
                "help": "Many accounting and document tools include a client portal.",
                "recommendation": "Use a client portal or protected sharing link for financial, legal and identity documents.",
                "priority": "High",
                "reason": "This work involves exchanging identity, financial and legal documents with clients all the time.",
                "sources": [
                    {"framework": "nist", "ref": "PR.DS-02", "note": "Data-in-transit is protected", "fit": "direct"},
                    {"framework": "oaic", "ref": "Email security", "note": "The guide states that email is not a secure form of communication", "fit": "direct"},
                ],
            },
            {
                "id": "professional_breach_plan",
                "question": "Do you know whether the Notifiable Data Breaches scheme applies to your business, and who would tell affected clients after a breach?",
                "help": "The Office of the Australian Information Commissioner explains who is covered.",
                "recommendation": "Check whether the Notifiable Data Breaches scheme covers your business and write down who would notify clients and the regulator.",
                "priority": "High",
                "reason": "Firms handling personal and financial records are more likely to have legal notification duties.",
                "sources": [
                    {"framework": "nist", "ref": "GV.OC-03, RS.CO-02", "note": "Legal and regulatory requirements are understood and managed; stakeholders are notified of incidents", "fit": "direct"},
                    {"framework": "ndb", "ref": "Part IIIC, ss 26WK and 26WL; s 6D", "note": "An entity gives a statement to the Commissioner and notifies affected individuals of an eligible data breach; s 6D sets the $3,000,000 small business test and its exceptions", "fit": "direct"},
                    {"framework": "acsc", "ref": "Prepare your staff: Make an emergency plan; Protect your business data", "note": "", "fit": "related"},
                ],
            },
            {
                "id": "professional_identity_checks",
                "question": "Do staff confirm a person's identity through a known contact before sharing client information or acting on changed instructions?",
                "help": "Call back on a number you already hold, not one given in the request.",
                "recommendation": "Require a call-back to a known number before releasing client information or acting on changed instructions.",
                "priority": "High",
                "reason": "Criminals impersonate clients and partners to obtain records or redirect funds.",
                "sources": [
                    {"framework": "oaic", "ref": "Individuals accessing and correcting their own personal information", "note": "Identify clients before disclosing their personal information", "fit": "direct"},
                    {"framework": "acsc", "ref": "Threats to small businesses: Email attacks, ways to mitigate", "note": "Call the sender using contact details from a trusted source", "fit": "direct"},
                    {"framework": "nist", "ref": "PR.AT-01", "note": "Personnel are provided with awareness and training", "fit": "related"},
                ],
            },
            {
                "id": "professional_retention",
                "question": "Do you delete or securely archive client information once you no longer need to keep it?",
                "help": "Keeping less means less can be exposed.",
                "recommendation": "Set a retention period for client records and delete or archive files that have passed it.",
                "priority": "Medium",
                "reason": "Client files build up over years, and old records are still exposed if a system is breached.",
                "sources": [
                    {"framework": "nist", "ref": "ID.AM-08", "note": "Systems, hardware, software, services and data are managed throughout their life cycles", "fit": "direct"},
                    {"framework": "oaic", "ref": "APP 11.2 (Privacy Act 1988, Schedule 1)", "note": "Take reasonable steps to destroy or de-identify personal information that is no longer needed", "fit": "direct"},
                    {"framework": "acsc", "ref": "Protect your devices and information: Protect your business data", "note": "", "fit": "related"},
                ],
            },
        ],
    },
]

# Each option awards points to one or more business types. The classifier adds the points up,
# so the reasoning behind every result can be shown to the user.
INTAKE_QUESTIONS = [
    {
        "id": "activity",
        "short": "Main activity",
        "question": "What does your business mainly do?",
        "options": [
            {"id": "sell", "label": "Sells products to customers, in a shop or online", "points": {"retail": 3}},
            {"id": "food", "label": "Serves food, drink or accommodation", "points": {"hospitality": 3}},
            {"id": "onsite", "label": "Does trade or service work at customer sites", "points": {"trades": 3}},
            {"id": "advice", "label": "Provides office-based professional services or advice", "points": {"professional": 3}},
            {"id": "other", "label": "Something else, or not sure", "points": {}},
        ],
    },
    {
        "id": "workplace",
        "short": "Where staff work",
        "question": "Where do most of your people do their work?",
        "options": [
            {"id": "shop", "label": "In a shop or showroom", "points": {"retail": 2}},
            {"id": "venue", "label": "In a kitchen, venue or front of house", "points": {"hospitality": 2}},
            {"id": "sites", "label": "At customer sites or on the road", "points": {"trades": 2}},
            {"id": "office", "label": "At desks, in an office or at home", "points": {"professional": 2}},
            {"id": "mixed", "label": "A mix of these", "points": {}},
        ],
    },
    {
        "id": "payment",
        "short": "How customers pay",
        "question": "How do customers usually pay you?",
        "options": [
            {"id": "counter", "label": "At a counter or card terminal", "points": {"retail": 1, "hospitality": 1}},
            {"id": "online", "label": "Through an online store, booking or ordering site", "points": {"retail": 1, "hospitality": 1}},
            {"id": "invoice", "label": "By invoice or bank transfer", "points": {"trades": 1, "professional": 1}},
            {"id": "mixed", "label": "A mix of these", "points": {}},
        ],
    },
    {
        "id": "information",
        "short": "Most sensitive information",
        "question": "What is the most sensitive information your business handles?",
        "options": [
            {"id": "cards", "label": "Customer payment card details", "points": {"retail": 1, "hospitality": 1}},
            {"id": "bookings", "label": "Bookings, rosters and supplier accounts", "points": {"hospitality": 1}},
            {"id": "access", "label": "Job details, addresses and site access information", "points": {"trades": 2}},
            {"id": "records", "label": "Client records, financial or legal documents", "points": {"professional": 2}},
            {"id": "unsure", "label": "Not sure", "points": {}},
        ],
    },
]

SECTOR_IDS = [sector["id"] for sector in SECTORS]


def get_sector(sector_id):
    """Return the sector definition for an id, or None if the id is not one of the fixed set."""
    for sector in SECTORS:
        if sector["id"] == sector_id:
            return sector
    return None
