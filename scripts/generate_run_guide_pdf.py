#!/usr/bin/env python3
"""
ZeroDayAI - Professional PDF Run Guide Generator
Generates docs/Zero_Day_NIDS_Complete_Run_Guide.pdf using ReportLab with custom styling.
"""
import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Palette Definition (SOC Dark / Cyan / Indigo / Slate / Crimson theme)
COLOR_PRIMARY = colors.HexColor("#0f172a")      # Deep Slate 900
COLOR_SECONDARY = colors.HexColor("#1e293b")    # Slate 800
COLOR_ACCENT = colors.HexColor("#0284c7")       # Cyan / Sky 600
COLOR_ACCENT_DARK = colors.HexColor("#0369a1")  # Sky 700
COLOR_SUCCESS = colors.HexColor("#10b981")      # Emerald 500
COLOR_WARNING = colors.HexColor("#f59e0b")      # Amber 500
COLOR_DANGER = colors.HexColor("#ef4444")       # Rose 500
COLOR_BG_LIGHT = colors.HexColor("#f8fafc")     # Slate 50
COLOR_BG_CODE = colors.HexColor("#0f172a")      # Code block background
COLOR_TEXT_MAIN = colors.HexColor("#1e293b")    # Slate 800
COLOR_TEXT_MUTED = colors.HexColor("#64748b")   # Slate 500
COLOR_CODE_TEXT = colors.HexColor("#38bdf8")    # Sky 400
COLOR_BORDER = colors.HexColor("#cbd5e1")       # Slate 300
COLOR_CARD_BORDER = colors.HexColor("#e2e8f0")  # Slate 200


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and render total page count."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress headers/footers on title cover page
            return

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_TEXT_MUTED)

        # Running Header
        self.drawString(
            54,
            11 * inch - 36,
            "Zero-Day NIDS (ZeroDayAI) — Complete Project Run Guide & Local Deployment Manual"
        )
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer
        self.line(54, 46, 8.5 * inch - 54, 46)
        self.drawString(
            54,
            32,
            "CONFIDENTIAL & PROPRIETARY — FOR SECURITY EVALUATION & OPERATIONAL USE"
        )
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 32, page_str)
        self.restoreState()


def create_styles():
    """Builds custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=COLOR_PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=10,
    ))

    styles.add(ParagraphStyle(
        name="DocSubTitle",
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=COLOR_ACCENT_DARK,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))

    styles.add(ParagraphStyle(
        name="SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=COLOR_PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="SubSectionHeading",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=COLOR_ACCENT_DARK,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="SubSubSectionHeading",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=COLOR_SECONDARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    ))

    styles.add(ParagraphStyle(
        name="BodyCustom",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=COLOR_TEXT_MAIN,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
    ))

    styles.add(ParagraphStyle(
        name="BodyCustomBold",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13.5,
        textColor=COLOR_TEXT_MAIN,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="BulletCustom",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT_MAIN,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    ))

    styles.add(ParagraphStyle(
        name="CodeBlockText",
        fontName="Courier-Bold",
        fontSize=8,
        leading=10.5,
        textColor=COLOR_CODE_TEXT,
    ))

    styles.add(ParagraphStyle(
        name="TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name="TableCell",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT_MAIN,
    ))

    styles.add(ParagraphStyle(
        name="TableCellMono",
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=COLOR_PRIMARY,
    ))

    styles.add(ParagraphStyle(
        name="CalloutText",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=COLOR_TEXT_MAIN,
    ))

    styles.add(ParagraphStyle(
        name="TOCItem",
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=COLOR_PRIMARY,
    ))

    return styles


def make_code_box(code_str, styles):
    """Wraps code text inside a styled dark-mode code container table."""
    p = Paragraph(code_str.replace("\n", "<br/>").replace(" ", "&nbsp;"), styles["CodeBlockText"])
    t = Table([[p]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_CODE),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_CODE_TEXT),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_SECONDARY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def make_callout(title, text, callout_type, styles):
    """Creates a stylized notification callout banner."""
    if callout_type == "IMPORTANT":
        bar_color = COLOR_ACCENT
        title_color = COLOR_ACCENT_DARK
        title_prefix = "<b>[IMPORTANT]</b> "
    elif callout_type == "WARNING":
        bar_color = COLOR_WARNING
        title_color = COLOR_WARNING
        title_prefix = "<b>[WARNING]</b> "
    elif callout_type == "NOTE":
        bar_color = COLOR_SUCCESS
        title_color = COLOR_SUCCESS
        title_prefix = "<b>[NOTE]</b> "
    else:
        bar_color = COLOR_SECONDARY
        title_color = COLOR_SECONDARY
        title_prefix = ""

    content = f"<font color='{title_color.hexval()}'>{title_prefix}{title}</font><br/><br/>{text}"
    p = Paragraph(content, styles["CalloutText"])
    t = Table([[p]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 7),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('LINELEFT', (0, 0), (-1, -1), 3.5, bar_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def build_pdf(output_pdf_path):
    """Assembles all sections into a comprehensive PDF document."""
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = create_styles()
    story = []

    # =========================================================================
    # COVER / TITLE PAGE
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("ZERO-DAY NETWORK INTRUSION DETECTION SYSTEM", styles["DocTitle"]))
    story.append(Paragraph("ZeroDayAI — Complete Project Run Guide & Local Deployment Manual", styles["DocSubTitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_ACCENT, spaceAfter=20))

    meta_table_data = [
        [
            Paragraph("<b>Document Version:</b> 1.0.0", styles["TableCell"]),
            Paragraph("<b>Operating System:</b> Windows 10/11 (64-bit)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Python Environment:</b> backend/.venv (3.10+)", styles["TableCell"]),
            Paragraph("<b>Node.js Runtime:</b> Node 18+ LTS / npm 9+", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Database Engine:</b> MongoDB 6.0+ / 7.0+", styles["TableCell"]),
            Paragraph("<b>Deployment Scope:</b> Local Dev & SOC Testing", styles["TableCell"]),
        ],
        [
            Paragraph("<b>Release Date:</b> 2026-09-09", styles["TableCell"]),
            Paragraph("<b>Classification:</b> Operational Technical Standard", styles["TableCell"]),
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[3.5 * inch, 3.5 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 18))

    story.append(make_callout(
        "Purpose of This Run Guide",
        "This manual provides complete, verified, deterministic instructions for setting up and running the Zero-Day Network Intrusion Detection System from scratch on a fresh machine. Every command listed has been verified against the actual application codebase. All Python operations strictly require <b>backend/.venv</b>.",
        "IMPORTANT",
        styles
    ))
    story.append(Spacer(1, 20))

    # Architecture Overview Box
    story.append(Paragraph("System Architecture Flow", styles["SubSectionHeading"]))
    arch_flow = (
        "Network Traffic Ingestion (Live Sniffing / PCAP Replay)\n"
        "  │\n"
        "  ▼\n"
        "Packet Dissection & Flow Aggregation (Scapy + Custom Flow Engine)\n"
        "  │\n"
        "  ▼\n"
        "42-Feature Extraction & StandardScaler Preprocessing\n"
        "  │\n"
        "  ├─► Isolation Forest (Tree-based Outlier Isolation)\n"
        "  ├─► Dense Autoencoder (Reconstruction Error MSE)\n"
        "  ├─► LSTM Autoencoder (Temporal Sequential Pattern Analysis)\n"
        "  └─► Random Forest (Supervised Flow Classification Baseline)\n"
        "  │\n"
        "  ▼\n"
        "Ensemble Risk Scoring Engine (Normalized Calibrated Risk Score 0-100)\n"
        "  │\n"
        "  ▼\n"
        "Severity Classification & XAI (SHAP & Feature Attribution Summaries)\n"
        "  │\n"
        "  ▼\n"
        "Security Alert Engine (Deduplication, Cooldown, Dispatch)\n"
        "  │\n"
        "  ▼\n"
        "MongoDB Persistence (users, logs, detections, alerts, events, audit)\n"
        "  │\n"
        "  ▼\n"
        "FastAPI REST Core ──► React SOC Monitoring Console (http://localhost:5173)"
    )
    story.append(make_code_box(arch_flow, styles))
    story.append(PageBreak())

    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    story.append(Paragraph("Table of Contents", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=12))

    toc_items = [
        ("1. Prerequisites & System Requirements", "Page 3"),
        ("2. Project Directory Structure", "Page 3"),
        ("3. Python Virtual Environment Policy", "Page 4"),
        ("4. Database Setup (MongoDB)", "Page 4"),
        ("5. Environment Variables Configuration", "Page 6"),
        ("6. Backend Setup & Installation", "Page 7"),
        ("7. Database Seeding & RBAC User Management", "Page 7"),
        ("8. Backend Server Startup & URLs", "Page 8"),
        ("9. Frontend Setup, Installation & Startup", "Page 8"),
        ("10. Quick Start Guide (Zero to Running)", "Page 10"),
        ("11. End-to-End Operational Workflow", "Page 10"),
        ("12. Real-Time Monitoring & Live Sniffing", "Page 11"),
        ("13. PCAP Ingestion & Replay Testing", "Page 11"),
        ("14. SOC Dashboard Telemetry & Analytics", "Page 12"),
        ("15. Security Incident Alert Management", "Page 12"),
        ("16. Detection History & Zero-Day Analytics", "Page 13"),
        ("17. AI Ensemble Model Registry", "Page 13"),
        ("18. System Health Diagnostics", "Page 14"),
        ("19. User Management (Admin Console)", "Page 14"),
        ("20. Verification & Test Commands", "Page 15"),
        ("21. Comprehensive Troubleshooting Manual (20 Scenarios)", "Page 16"),
        ("22. Common Windows Administration Commands", "Page 17"),
        ("23. Daily Operations: Startup & Orderly Shutdown", "Page 17"),
        ("24. Security Best Practices & Production Hardening", "Page 18"),
        ("25. Known Limitations & Operational Boundaries", "Page 18"),
    ]

    toc_table_data = []
    for title, pg in toc_items:
        toc_table_data.append([
            Paragraph(f"<b>{title}</b>", styles["TOCItem"]),
            Paragraph(f"<b>{pg}</b>", ParagraphStyle(name="TOCPg", parent=styles["TOCItem"], alignment=TA_RIGHT, textColor=COLOR_ACCENT_DARK))
        ])

    toc_table = Table(toc_table_data, colWidths=[5.8 * inch, 1.2 * inch])
    toc_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, COLOR_CARD_BORDER),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 1: PREREQUISITES & SYSTEM REQUIREMENTS
    # =========================================================================
    story.append(Paragraph("1. Prerequisites & System Requirements", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Ensure that the host machine satisfies all required runtime dependencies before proceeding with installation. "
        "The project has been fully validated on Microsoft Windows 10/11 64-bit environments.",
        styles["BodyCustom"]
    ))

    prereq_table_data = [
        [
            Paragraph("Software Component", styles["TableHeader"]),
            Paragraph("Minimum Version", styles["TableHeader"]),
            Paragraph("Verified Version", styles["TableHeader"]),
            Paragraph("Verification Command", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>Operating System</b>", styles["TableCell"]),
            Paragraph("Windows 10 64-bit", styles["TableCell"]),
            Paragraph("Windows 11 Pro 64-bit", styles["TableCell"]),
            Paragraph("cmd /c ver", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>Python</b>", styles["TableCell"]),
            Paragraph("3.10.x", styles["TableCell"]),
            Paragraph("3.14.3 / 3.11.x", styles["TableCell"]),
            Paragraph("python --version", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>Node.js</b>", styles["TableCell"]),
            Paragraph("18.x LTS", styles["TableCell"]),
            Paragraph("24.14.0", styles["TableCell"]),
            Paragraph("node --version", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>npm</b>", styles["TableCell"]),
            Paragraph("9.x", styles["TableCell"]),
            Paragraph("10.9.0", styles["TableCell"]),
            Paragraph("npm --version", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>MongoDB Server</b>", styles["TableCell"]),
            Paragraph("6.0+ / Atlas", styles["TableCell"]),
            Paragraph("7.0.12 / Atlas M0+", styles["TableCell"]),
            Paragraph("mongosh --version", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>Git</b>", styles["TableCell"]),
            Paragraph("2.30+", styles["TableCell"]),
            Paragraph("2.45.0", styles["TableCell"]),
            Paragraph("git --version", styles["TableCellMono"]),
        ],
    ]
    prereq_table = Table(prereq_table_data, colWidths=[1.7 * inch, 1.3 * inch, 1.5 * inch, 2.5 * inch])
    prereq_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(prereq_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Verification Commands (PowerShell / CMD)", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "python --version\n"
        "node --version\n"
        "npm --version\n"
        "git --version",
        styles
    ))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 2: PROJECT DIRECTORY STRUCTURE
    # =========================================================================
    story.append(Paragraph("2. Project Directory Structure", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The application maintains strict architectural separation between frontend UI code, backend FastAPI services, pre-trained machine learning weights, and operational scripts.",
        styles["BodyCustom"]
    ))

    dir_tree = (
        "ZERO/\n"
        "├── backend/                  # FastAPI Python backend service\n"
        "│   ├── .env                  # Active backend environment variables\n"
        "│   ├── .env.example          # Backend environment template\n"
        "│   ├── .venv/                # Mandatory isolated Python virtual environment\n"
        "│   ├── requirements.txt      # Pinned Python package dependencies\n"
        "│   ├── app/                  # Application core, API, ML, and database modules\n"
        "│   └── tests/                # 210 Pytest automated test suites\n"
        "├── frontend/                 # React 19 + Vite SOC Monitoring Dashboard\n"
        "│   ├── .env                  # Active frontend configuration\n"
        "│   ├── .env.example          # Frontend environment template\n"
        "│   ├── package.json          # Node dependencies & test scripts\n"
        "│   ├── src/                  # React components, pages, hooks, and context\n"
        "│   └── dist/                 # Production compiled frontend bundle\n"
        "├── data/                     # Cleaned CSV datasets and PCAP capture files\n"
        "├── ml_models/                # Serialized AI models, scalers, and explainers\n"
        "├── scripts/                  # Automated setup, startup, and test scripts\n"
        "└── docs/                     # Technical specifications and PDF Run Guide"
    )
    story.append(make_code_box(dir_tree, styles))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: PYTHON VIRTUAL ENVIRONMENT POLICY
    # =========================================================================
    story.append(Paragraph("3. Python Virtual Environment Policy", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))

    story.append(make_callout(
        "Mandatory Runtime Constraint",
        "ALL Python operations, model loading, user seeding, server startup, and test suites MUST be executed using the isolated virtual environment: <b>backend/.venv</b>.<br/><br/>"
        "<b>DO NOT install Python packages globally.</b> Global packages can lead to dependency conflicts and non-deterministic behavior.",
        "IMPORTANT",
        styles
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Commands for Virtual Environment Management", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# 1. Create virtual environment on fresh machine (from project root):\n"
        "cd backend\n"
        "python -m venv .venv\n\n"
        "# 2. Activate virtual environment on Windows (PowerShell):\n"
        ".\\.venv\\Scripts\\Activate.ps1\n\n"
        "# 2b. Activate virtual environment on Windows (Command Prompt):\n"
        ".venv\\Scripts\\activate.bat\n\n"
        "# 3. Alternative: Direct Python execution without shell activation:\n"
        ".\\backend\\.venv\\Scripts\\python.exe <script_path.py>",
        styles
    ))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 4: MONGODB SETUP & VERIFICATION
    # =========================================================================
    story.append(Paragraph("4. Database Setup (MongoDB)", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "ZeroDayAI connects asynchronously to MongoDB to persist security events, network flows, AI detections, deduplicated alerts, and user accounts. "
        "The target database name is <b>zero_day_detection</b> across 6 indexed collections.",
        styles["BodyCustom"]
    ))

    story.append(Paragraph("6 Core Database Collections", styles["SubSectionHeading"]))
    story.append(Paragraph("• <b>users:</b> RBAC user accounts, salted bcrypt password hashes, and active status.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>network_logs:</b> Ingested raw network flow features, IPs, ports, and packet metrics.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>detection_results:</b> AI model scores, anomaly flags, severity ratings, and latencies.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>alerts:</b> Deduplicated security incidents, triage states, and XAI feature attributions.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>system_events:</b> Lifecycle events, monitoring state transitions, and system errors.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>audit_logs:</b> Tamper-evident record of logins, user creations, and alert triage.", styles["BulletCustom"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Starting Local MongoDB (Windows Service)", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Check status of MongoDB Windows Service:\n"
        "Get-Service -Name MongoDB\n\n"
        "# Start MongoDB Service (Requires Administrator PowerShell):\n"
        "Start-Service -Name MongoDB\n\n"
        "# Alternative CMD command:\n"
        "net start MongoDB",
        styles
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Verifying MongoDB Connection with Diagnostic Tool", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Run direct database verification test:\n"
        ".\\backend\\.venv\\Scripts\\python.exe scripts/test_mongo_verification.py",
        styles
    ))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 5: ENVIRONMENT VARIABLES CONFIGURATION
    # =========================================================================
    story.append(Paragraph("5. Environment Variables Configuration", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Both backend and frontend services rely on environment files. Template configurations are provided in <code>.env.example</code>.",
        styles["BodyCustom"]
    ))

    story.append(Paragraph("Creating Environment Files", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Create backend .env (from project root):\n"
        "Copy-Item backend\\.env.example backend\\.env\n\n"
        "# Create frontend .env:\n"
        "Copy-Item frontend\\.env.example frontend\\.env",
        styles
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Backend Environment Variables (`backend/.env`)", styles["SubSectionHeading"]))

    env_table_data = [
        [
            Paragraph("Variable", styles["TableHeader"]),
            Paragraph("Req", styles["TableHeader"]),
            Paragraph("Default / Example", styles["TableHeader"]),
            Paragraph("Purpose & Description", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>ENVIRONMENT</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("development", styles["TableCellMono"]),
            Paragraph("Runtime mode: development | production | testing", styles["TableCell"]),
        ],
        [
            Paragraph("<b>API_PORT</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("8000", styles["TableCellMono"]),
            Paragraph("FastAPI HTTP listening port", styles["TableCell"]),
        ],
        [
            Paragraph("<b>FRONTEND_URL</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("http://localhost:5173", styles["TableCellMono"]),
            Paragraph("Target client URL for CORS origin validation", styles["TableCell"]),
        ],
        [
            Paragraph("<b>CORS_ORIGINS</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("http://localhost:5173,http://localhost:3000", styles["TableCellMono"]),
            Paragraph("Comma-separated list of trusted client origins", styles["TableCell"]),
        ],
        [
            Paragraph("<b>MONGODB_URI</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("mongodb://localhost:27017", styles["TableCellMono"]),
            Paragraph("MongoDB connection string (local or Atlas URI)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>MONGODB_DATABASE</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("zero_day_detection", styles["TableCellMono"]),
            Paragraph("Target database name for all security collections", styles["TableCell"]),
        ],
        [
            Paragraph("<b>JWT_SECRET_KEY</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("dev-insecure-secret-key-...", styles["TableCellMono"]),
            Paragraph("Secret for JWT signature (must change in prod)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>MODEL_DIRECTORY</b>", styles["TableCell"]),
            Paragraph("Yes", styles["TableCell"]),
            Paragraph("./ml_models/trained", styles["TableCellMono"]),
            Paragraph("Path to serialized AI model weights (.joblib, .pt)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>DEFAULT_ANOMALY_THRESHOLD</b>", styles["TableCell"]),
            Paragraph("No", styles["TableCell"]),
            Paragraph("0.65", styles["TableCellMono"]),
            Paragraph("Decision boundary for anomaly classification", styles["TableCell"]),
        ],
    ]
    env_table = Table(env_table_data, colWidths=[1.8 * inch, 0.4 * inch, 2.0 * inch, 2.8 * inch])
    env_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(env_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Frontend Environment Variables (`frontend/.env`)", styles["SubSectionHeading"]))
    story.append(Paragraph("• <b>VITE_API_BASE_URL:</b> <code>http://localhost:8000</code> (FastAPI API gateway)", styles["BulletCustom"]))
    story.append(Paragraph("• <b>VITE_POLLING_INTERVAL_MS:</b> <code>5000</code> (Telemetry refresh interval in milliseconds)", styles["BulletCustom"]))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 6: BACKEND SETUP & INSTALLATION
    # =========================================================================
    story.append(Paragraph("6. Backend Setup & Installation", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Follow these exact sequential steps to configure the backend on a fresh machine:",
        styles["BodyCustom"]
    ))

    story.append(make_code_box(
        "# Step 1: Navigate to backend folder (from project root)\n"
        "cd backend\n\n"
        "# Step 2: Create Python virtual environment\n"
        "python -m venv .venv\n\n"
        "# Step 3: Activate virtual environment (PowerShell)\n"
        ".\\.venv\\Scripts\\Activate.ps1\n\n"
        "# Step 4: Upgrade pip\n"
        ".\\.venv\\Scripts\\python.exe -m pip install --upgrade pip\n\n"
        "# Step 5: Install all backend dependencies\n"
        ".\\.venv\\Scripts\\pip.exe install -r requirements.txt\n\n"
        "# Step 6: Install reportlab for PDF generation\n"
        ".\\.venv\\Scripts\\pip.exe install reportlab\n\n"
        "# Step 7: Create environment file\n"
        "Copy-Item .env.example .env\n\n"
        "# (Alternative: run one-click setup script from project root: scripts\\setup_env.bat)",
        styles
    ))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 7: USER SEEDING & RBAC
    # =========================================================================
    story.append(Paragraph("7. Database Seeding & RBAC User Management", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "ZeroDayAI enforces Role-Based Access Control (RBAC). Initial development users for each role tier are provisioned using the seeding script. "
        "Passwords are salted and hashed with <b>bcrypt</b>.",
        styles["BodyCustom"]
    ))

    rbac_table_data = [
        [
            Paragraph("Role", styles["TableHeader"]),
            Paragraph("Default Username", styles["TableHeader"]),
            Paragraph("Default Email", styles["TableHeader"]),
            Paragraph("Permissions Scope", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>ADMIN</b>", styles["TableCell"]),
            Paragraph("admin", styles["TableCellMono"]),
            Paragraph("admin@zeroday.local", styles["TableCellMono"]),
            Paragraph("Full administrative access: User Management (/users), Alert Triage, System Config.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>ANALYST</b>", styles["TableCell"]),
            Paragraph("analyst", styles["TableCellMono"]),
            Paragraph("analyst@zeroday.local", styles["TableCellMono"]),
            Paragraph("Security Operations: Alert Triage (Acknowledge, Resolve, Dismiss), Live Monitoring.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>VIEWER</b>", styles["TableCell"]),
            Paragraph("viewer", styles["TableCellMono"]),
            Paragraph("viewer@zeroday.local", styles["TableCellMono"]),
            Paragraph("Read-only access: SOC Dashboard, Detection History, AI Models, System Health.", styles["TableCell"]),
        ],
    ]
    rbac_table = Table(rbac_table_data, colWidths=[1.1 * inch, 1.4 * inch, 1.8 * inch, 2.7 * inch])
    rbac_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(rbac_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Exact User Seeding Command", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Seed development users non-interactively (from project root):\n"
        ".\\backend\\.venv\\Scripts\\python.exe scripts/seed_users.py --non-interactive\n\n"
        "# To update passwords of existing accounts:\n"
        ".\\backend\\.venv\\Scripts\\python.exe scripts/seed_users.py --update-passwords --non-interactive",
        styles
    ))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 8: BACKEND STARTUP & URLS
    # =========================================================================
    story.append(Paragraph("8. Backend Server Startup & URLs", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Start the FastAPI ASGI server with auto-reload enabled using Uvicorn inside the virtual environment.",
        styles["BodyCustom"]
    ))

    story.append(Paragraph("Exact Backend Startup Command", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# From project root:\n"
        ".\\backend\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload\n\n"
        "# (Alternative batch script: scripts\\start_backend.bat)",
        styles
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Expected Terminal Startup Output", styles["SubSectionHeading"]))
    startup_out = (
        "======================================================\n"
        "ZERO-DAY NIDS BACKEND\n"
        "======================================================\n"
        "[OK] Configuration loaded\n"
        "[OK] MongoDB connected successfully\n"
        "[OK] Database: zero_day_detection\n"
        "[OK] Connection type: Standalone\n"
        "[OK] MongoDB ping: 2.1 ms\n"
        "[OK] ML models available (4/4 loaded)\n"
        "[OK] Security headers & rate limiting active\n"
        "[OK] Monitoring subsystem ready\n"
        "[OK] API ready\n"
        "======================================================\n"
        "Server running on http://0.0.0.0:8000"
    )
    story.append(make_code_box(startup_out, styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Verified Backend URLs", styles["SubSectionHeading"]))
    story.append(Paragraph("• <b>API Base URL:</b> <code>http://localhost:8000</code>", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Interactive Swagger UI:</b> <code>http://localhost:8000/docs</code>", styles["BulletCustom"]))
    story.append(Paragraph("• <b>ReDoc API Documentation:</b> <code>http://localhost:8000/redoc</code>", styles["BulletCustom"]))
    story.append(Paragraph("• <b>OpenAPI JSON Schema:</b> <code>http://localhost:8000/openapi.json</code>", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Health Status Probe:</b> <code>http://localhost:8000/api/v1/health</code>", styles["BulletCustom"]))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 9: FRONTEND SETUP & STARTUP
    # =========================================================================
    story.append(Paragraph("9. Frontend Setup, Installation & Startup", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The React 19 SOC Operations Center is served via Vite.",
        styles["BodyCustom"]
    ))

    story.append(Paragraph("Exact Frontend Setup & Startup Commands", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Step 1: Open a new terminal and navigate to frontend directory\n"
        "cd C:\\Users\\Win\\Desktop\\ZERO\\frontend\n\n"
        "# Step 2: Install node dependencies\n"
        "npm install\n\n"
        "# Step 3: Configure environment file\n"
        "Copy-Item .env.example .env\n\n"
        "# Step 4: Start development server\n"
        "npm run dev\n\n"
        "# (Alternative batch script: scripts\\start_frontend.bat)",
        styles
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Browser Access", styles["SubSectionHeading"]))
    story.append(Paragraph("Open your web browser and navigate to: <b>http://localhost:5173</b>", styles["BodyCustomBold"]))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 10: QUICK START GUIDE
    # =========================================================================
    story.append(Paragraph("10. Quick Start Guide (Zero to Running)", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "For an operator on an already-configured machine, use this 3-terminal sequence to launch the full platform in under 30 seconds:",
        styles["BodyCustom"]
    ))

    quick_start = (
        "┌────────────────────────────────────────────────────────────────────────┐\n"
        "│ TERMINAL 1 — MongoDB Database Service (Admin Shell)                    │\n"
        "│   Start-Service -Name MongoDB                                          │\n"
        "├────────────────────────────────────────────────────────────────────────┤\n"
        "│ TERMINAL 2 — Backend FastAPI ASGI Server                               │\n"
        "│   cd C:\\Users\\Win\\Desktop\\ZERO                                         │\n"
        "│   .\\backend\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app   │\n"
        "│                                      --host 0.0.0.0 --port 8000 --reload│\n"
        "├────────────────────────────────────────────────────────────────────────┤\n"
        "│ TERMINAL 3 — Frontend React 19 SOC Dashboard                           │\n"
        "│   cd C:\\Users\\Win\\Desktop\\ZERO\\frontend                                 │\n"
        "│   npm run dev                                                          │\n"
        "├────────────────────────────────────────────────────────────────────────┤\n"
        "│ BROWSER ACCESS:                                                        │\n"
        "│   URL: http://localhost:5173                                           │\n"
        "│   Login Credentials: admin / Admin12345!                               │\n"
        "└────────────────────────────────────────────────────────────────────────┘"
    )
    story.append(make_code_box(quick_start, styles))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 11: END-TO-END OPERATIONAL WORKFLOW
    # =========================================================================
    story.append(Paragraph("11. End-to-End Operational Workflow", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The diagram below outlines the standard operational lifecycle from login to incident triage:",
        styles["BodyCustom"]
    ))

    workflow_text = (
        "1. Authenticate at /login (ADMIN, ANALYST, or VIEWER role)\n"
        "      │\n"
        "2. Review SOC Dashboard (/dashboard) for network risk gauge and active alerts\n"
        "      │\n"
        "3. Ingest Network Traffic via Live Sniffing or PCAP Replay (/monitoring)\n"
        "      │\n"
        "4. AI Pipeline extracts 42 features -> Normalizes -> Inferences 4 Models\n"
        "      │\n"
        "5. Ensemble Engine computes unified Risk Score (0-100) & Severity Rating\n"
        "      │\n"
        "6. XAI Engine computes SHAP feature importance for high-risk anomalies\n"
        "      │\n"
        "7. Alert Engine deduplicates events and publishes incidents to /alerts\n"
        "      │\n"
        "8. Security Analyst investigates forensic details & triages alert (Acknowledge/Resolve)\n"
        "      │\n"
        "9. Administrator provisions new analysts or manages role permissions (/users)"
    )
    story.append(make_code_box(workflow_text, styles))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 12: REAL-TIME MONITORING & LIVE SNIFFING
    # =========================================================================
    story.append(Paragraph("12. Real-Time Monitoring & Live Sniffing", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The <b>Monitoring</b> module (<code>/monitoring</code>) provides continuous packet capture, bidirectional flow aggregation, and real-time inference.",
        styles["BodyCustom"]
    ))
    story.append(Paragraph("• <b>Select Source:</b> Choose between <i>Live Interface Sniffing</i> and <i>PCAP File Replay</i>.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Packet Filters:</b> Apply standard BPF syntax (e.g., <code>tcp or udp</code>, <code>port 80 or port 443</code>).", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Telemetry Stream:</b> Observe live counters for Packets Captured, Packet Rate (pkts/sec), Aggregated Flows, Detections, and Triggered Alerts.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Graceful Stop:</b> Click <i>Stop Monitoring</i> to flush in-flight flow buffers cleanly to MongoDB.", styles["BulletCustom"]))
    story.append(Spacer(1, 8))

    story.append(make_callout(
        "Windows Packet Capture Driver Requirement",
        "Live network capture on Windows requires the <b>Npcap</b> driver installed with administrative privileges. If Npcap is unavailable on your test machine, use <b>PCAP Ingestion Mode</b> for offline evaluation.",
        "NOTE",
        styles
    ))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 13: PCAP INGESTION & REPLAY TESTING
    # =========================================================================
    story.append(Paragraph("13. PCAP Ingestion & Replay Testing", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "PCAP replay allows reproducible evaluation of AI models against standard cyber benchmark traffic traces.",
        styles["BodyCustom"]
    ))
    story.append(Paragraph("1. Place <code>.pcap</code> or <code>.pcapng</code> files into: <code>C:\\Users\\Win\\Desktop\\ZERO\\data\\sample\\</code>", styles["BulletCustom"]))
    story.append(Paragraph("2. Navigate to <b>Monitoring</b> (<code>/monitoring</code>) and select <b>PCAP File Ingestion</b>.", styles["BulletCustom"]))
    story.append(Paragraph("3. Select target capture file from the dropdown and configure replay speed.", styles["BulletCustom"]))
    story.append(Paragraph("4. Click <b>Start PCAP Replay</b> to stream flows into the detection engine.", styles["BulletCustom"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Generating a Synthetic Test PCAP File", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Generate sample network traffic capture file:\n"
        ".\\backend\\.venv\\Scripts\\python.exe scripts/create_sample_pcap.py",
        styles
    ))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 14: SOC DASHBOARD TELEMETRY
    # =========================================================================
    story.append(Paragraph("14. SOC Dashboard Telemetry & Analytics", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The <b>Dashboard</b> (<code>/dashboard</code>) provides real-time situational awareness across all detection metrics:",
        styles["BodyCustom"]
    ))
    story.append(Paragraph("• <b>Total Detections:</b> Total volume of network flows evaluated by the AI ensemble.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Anomalies Identified:</b> Number of flows exceeding the calibrated anomaly threshold.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Open Security Alerts:</b> Unresolved incident tickets requiring analyst attention.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Critical Alerts:</b> High-severity incidents with risk score >= 75.0.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Average Risk Score:</b> Global weighted risk gauge across recent traffic.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Severity Distribution:</b> Categorized breakdown of Low, Medium, High, and Critical events.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Model Readiness Status:</b> Individual health indicators for all 4 AI engines.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Recent Alerts Stream:</b> Live table of incoming security alerts with instant triage links.", styles["BulletCustom"]))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 15: ALERT MANAGEMENT & TRIAGE
    # =========================================================================
    story.append(Paragraph("15. Security Incident Alert Management", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The <b>Alerts</b> console (<code>/alerts</code>) supports end-to-end incident response workflows.",
        styles["BodyCustom"]
    ))

    alert_tiers_data = [
        [
            Paragraph("Severity Tier", styles["TableHeader"]),
            Paragraph("Risk Score Range", styles["TableHeader"]),
            Paragraph("Alert Generation", styles["TableHeader"]),
            Paragraph("XAI Explanation", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>LOW</b>", styles["TableCell"]),
            Paragraph("0.00 – 24.99", styles["TableCellMono"]),
            Paragraph("Logged in detection history", styles["TableCell"]),
            Paragraph("Disabled (Noise reduction)", styles["TableCell"]),
        ],
        [
            Paragraph("<b>MEDIUM</b>", styles["TableCell"]),
            Paragraph("25.00 – 49.99", styles["TableCellMono"]),
            Paragraph("Filterable detection record", styles["TableCell"]),
            Paragraph("Optional on demand", styles["TableCell"]),
        ],
        [
            Paragraph("<b>HIGH</b>", styles["TableCell"]),
            Paragraph("50.00 – 74.99", styles["TableCellMono"]),
            Paragraph("<b>Raises Incident Ticket</b>", styles["TableCell"]),
            Paragraph("<b>Enabled (Top 10 Features)</b>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>CRITICAL</b>", styles["TableCell"]),
            Paragraph("75.00 – 100.00", styles["TableCellMono"]),
            Paragraph("<b>Immediate Priority Ticket</b>", styles["TableCell"]),
            Paragraph("<b>Enabled (Full SHAP Breakdown)</b>", styles["TableCell"]),
        ],
    ]
    alert_table = Table(alert_tiers_data, colWidths=[1.3 * inch, 1.5 * inch, 2.0 * inch, 2.2 * inch])
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(alert_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Alert Detail Forensics (`/alerts/:alertId`)", styles["SubSectionHeading"]))
    story.append(Paragraph("• <b>Network Socket Info:</b> Source IP/Port, Destination IP/Port, Protocol, and Flow Duration.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Multi-Model Consensus:</b> Individual anomaly scores from Isolation Forest, Autoencoder, LSTM, and Random Forest.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>XAI Feature Attribution:</b> Ranked bar chart of network features driving the risk assessment.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Triage Actions:</b> Acknowledge, Resolve, or Dismiss with analyst notes.", styles["BulletCustom"]))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 16: DETECTION HISTORY & ZERO-DAY ANALYTICS
    # =========================================================================
    story.append(Paragraph("16. Detection History & Zero-Day Analytics", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The <b>Detections</b> module (<code>/detections</code>) logs every flow processed by the ML inference engine.",
        styles["BodyCustom"]
    ))

    story.append(make_callout(
        "Scientific Context: Zero-Day Proxy Definition",
        "Evaluation against <i>unseen attacks</i> is conducted using held-out attack category splits (e.g., training exclusively on normal traffic and known exploit classes, then testing against held-out classes such as PortScan, DoS, or Botnet).<br/><br/>"
        "This serves as a valid <b>zero-day proxy metric</b>, but does <b>NOT</b> constitute mathematical proof of detecting all real-world zero-day exploits.",
        "NOTE",
        styles
    ))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 17: AI ENSEMBLE MODEL REGISTRY
    # =========================================================================
    story.append(Paragraph("17. AI Ensemble Model Registry", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The <b>Models</b> console (<code>/models</code>) inspects the weights, thresholds, and performance metrics of the 4 ensemble models:",
        styles["BodyCustom"]
    ))

    models_data = [
        [
            Paragraph("Model Engine", styles["TableHeader"]),
            Paragraph("Paradigm", styles["TableHeader"]),
            Paragraph("Core Strength / Detection Focus", styles["TableHeader"]),
            Paragraph("Weight", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>Isolation Forest</b>", styles["TableCell"]),
            Paragraph("Unsupervised", styles["TableCell"]),
            Paragraph("Fast isolation of sparse outliers in high-dimensional flow space.", styles["TableCell"]),
            Paragraph("25%", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>Dense Autoencoder</b>", styles["TableCell"]),
            Paragraph("Unsupervised DL", styles["TableCell"]),
            Paragraph("Reconstruction error (MSE) on non-linear manifold representations.", styles["TableCell"]),
            Paragraph("25%", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>LSTM Autoencoder</b>", styles["TableCell"]),
            Paragraph("Sequential DL", styles["TableCell"]),
            Paragraph("Recurrent temporal analysis across sliding windows of consecutive packets.", styles["TableCell"]),
            Paragraph("25%", styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>Random Forest</b>", styles["TableCell"]),
            Paragraph("Supervised", styles["TableCell"]),
            Paragraph("High-precision classification baseline for known exploit signatures.", styles["TableCell"]),
            Paragraph("25%", styles["TableCellMono"]),
        ],
    ]
    models_table = Table(models_data, colWidths=[1.5 * inch, 1.2 * inch, 3.5 * inch, 0.8 * inch])
    models_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(models_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 18: SYSTEM HEALTH DIAGNOSTICS
    # =========================================================================
    story.append(Paragraph("18. System Health Diagnostics", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "The <b>System Health</b> page (<code>/health</code>) performs live probes across all platform dependencies:",
        styles["BodyCustom"]
    ))
    story.append(Paragraph("• <b>FastAPI Server:</b> Online status, process uptime, and request latency.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>MongoDB Database:</b> Connection state (<code>CONNECTED</code>), ping latency (&lt;5 ms), server topology (Standalone/ReplicaSet), and pool usage.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>ML Models Loader:</b> Status of all 4 pre-trained models in memory (<code>4/4 Loaded</code>).", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Monitoring Engine:</b> Status of packet capture workers and buffer capacity.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Memory & CPU Telemetry:</b> Host RAM utilization and execution thread count.", styles["BulletCustom"]))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 19: USER MANAGEMENT (ADMIN CONSOLE)
    # =========================================================================
    story.append(Paragraph("19. User Management (Admin Console)", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Accessible exclusively to users with the <b>ADMIN</b> role via <code>/users</code>.",
        styles["BodyCustom"]
    ))
    story.append(Paragraph("• <b>Account Registry:</b> View all provisioned users, assigned roles, and creation timestamps.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Provision New User:</b> Create analyst accounts with secure passwords and RBAC role assignments.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Active / Inactive Toggle:</b> Instantly revoke platform access for deactivated users.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Audit Trail:</b> All user creations and role changes are recorded in <code>audit_logs</code>.", styles["BulletCustom"]))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 20: VERIFICATION & TEST COMMANDS
    # =========================================================================
    story.append(Paragraph("20. Verification, Quality Assurance & Test Commands", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Run the automated test suites using <code>backend/.venv</code> to verify system integrity before deployment:",
        styles["BodyCustom"]
    ))

    story.append(Paragraph("1. Backend Pytest Suite (210 Tests)", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Run complete backend test suite (from project root):\n"
        ".\\backend\\.venv\\Scripts\\python.exe -m pytest backend/tests -v\n\n"
        "# (Alternative batch script: scripts\\test_backend.bat)",
        styles
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2. Frontend Vitest Suite (16 Tests)", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Run frontend unit and integration tests:\n"
        "cd frontend\n"
        "npm run test",
        styles
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. Frontend Linting & Production Build", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Run Oxlint static analysis:\n"
        "cd frontend\n"
        "npm run lint\n\n"
        "# Build production bundle:\n"
        "npm run build",
        styles
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4. End-to-End System Integration Test", styles["SubSectionHeading"]))
    story.append(make_code_box(
        "# Run full E2E pipeline verification test:\n"
        ".\\backend\\.venv\\Scripts\\python.exe scripts/test_phase17_e2e.py",
        styles
    ))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 21: TROUBLESHOOTING MANUAL (20 SCENARIOS)
    # =========================================================================
    story.append(Paragraph("21. Comprehensive Troubleshooting Manual", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "This section documents the 20 most frequent operational issues, their root causes, and exact recovery commands:",
        styles["BodyCustom"]
    ))

    troubleshoot_data = [
        [
            Paragraph("Problem / Symptom", styles["TableHeader"]),
            Paragraph("Root Cause", styles["TableHeader"]),
            Paragraph("Exact Resolution & Recovery Command", styles["TableHeader"]),
        ],
        [
            Paragraph("<b>1. MongoDB Offline</b>", styles["TableCell"]),
            Paragraph("MongoDB service is stopped.", styles["TableCell"]),
            Paragraph("Start service: <code>Start-Service MongoDB</code> in Admin PowerShell.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>2. MongoDB Conn Refused</b>", styles["TableCell"]),
            Paragraph("Port 27017 unreachable or blocked.", styles["TableCell"]),
            Paragraph("Verify mongod.cfg bindIp is 127.0.0.1 and port is 27017.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>3. Backend Fails to Start</b>", styles["TableCell"]),
            Paragraph("Global Python invoked instead of venv.", styles["TableCell"]),
            Paragraph("Use: <code>.\\backend\\.venv\\Scripts\\python.exe -m uvicorn ...</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>4. Missing Python Module</b>", styles["TableCell"]),
            Paragraph("Incomplete pip dependency install.", styles["TableCell"]),
            Paragraph("Run: <code>.\\backend\\.venv\\Scripts\\pip.exe install -r backend/requirements.txt</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>5. Wrong IDE Interpreter</b>", styles["TableCell"]),
            Paragraph("VS Code pointing to global Python.", styles["TableCell"]),
            Paragraph("Set interpreter in VS Code to <code>.\\backend\\.venv\\Scripts\\python.exe</code>.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>6. PowerShell Script Blocked</b>", styles["TableCell"]),
            Paragraph("Execution policy restricted.", styles["TableCell"]),
            Paragraph("Run: <code>Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>7. Frontend Won't Start</b>", styles["TableCell"]),
            Paragraph("Missing node_modules directory.", styles["TableCell"]),
            Paragraph("Run: <code>cd frontend && npm install && npm run dev</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>8. npm Peer Conflict</b>", styles["TableCell"]),
            Paragraph("Conflicting package metadata.", styles["TableCell"]),
            Paragraph("Run: <code>npm install --legacy-peer-deps</code> in frontend directory.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>9. CORS Error in Browser</b>", styles["TableCell"]),
            Paragraph("Frontend port missing from CORS_ORIGINS.", styles["TableCell"]),
            Paragraph("Add <code>http://localhost:5173</code> to CORS_ORIGINS in <code>backend/.env</code>.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>10. Login Failure (401)</b>", styles["TableCell"]),
            Paragraph("Database not seeded with users.", styles["TableCell"]),
            Paragraph("Run: <code>.\\backend\\.venv\\Scripts\\python.exe scripts/seed_users.py --non-interactive</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>11. Service Conn Error</b>", styles["TableCell"]),
            Paragraph("FastAPI backend not running on port 8000.", styles["TableCell"]),
            Paragraph("Start backend: <code>.\\backend\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --port 8000</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>12. User Mgmt 403 Forbidden</b>", styles["TableCell"]),
            Paragraph("Logged in as ANALYST or VIEWER.", styles["TableCell"]),
            Paragraph("Log in with ADMIN account (<code>admin</code> / <code>Admin12345!</code>).", styles["TableCell"]),
        ],
        [
            Paragraph("<b>13. Monitoring Inactive</b>", styles["TableCell"]),
            Paragraph("Missing Npcap driver on Windows.", styles["TableCell"]),
            Paragraph("Install Npcap driver or switch to PCAP Ingestion Mode.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>14. 0 Packets Captured</b>", styles["TableCell"]),
            Paragraph("Wrong capture adapter or restrictive filter.", styles["TableCell"]),
            Paragraph("Set filter to empty or choose correct active network adapter.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>15. PCAP Path Rejected</b>", styles["TableCell"]),
            Paragraph("PCAP file outside data/ directory.", styles["TableCell"]),
            Paragraph("Place PCAP file in <code>data/sample/</code> directory.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>16. ML Models 0/4 Loaded</b>", styles["TableCell"]),
            Paragraph("Missing serialized .joblib / .pt files.", styles["TableCell"]),
            Paragraph("Run model training/evaluation: <code>.\\backend\\.venv\\Scripts\\python.exe scripts/evaluate_models.py</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>17. Port 8000/5173 in Use</b>", styles["TableCell"]),
            Paragraph("Orphan process occupying port.", styles["TableCell"]),
            Paragraph("Kill process: <code>Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>18. Missing Env Variable</b>", styles["TableCell"]),
            Paragraph("Missing backend/.env file.", styles["TableCell"]),
            Paragraph("Copy template: <code>Copy-Item backend\\.env.example backend\\.env</code>", styles["TableCell"]),
        ],
        [
            Paragraph("<b>19. JWT Token Expired (401)</b>", styles["TableCell"]),
            Paragraph("Session exceeded 60 min lifetime.", styles["TableCell"]),
            Paragraph("Log out and log back in to obtain a fresh access token.", styles["TableCell"]),
        ],
        [
            Paragraph("<b>20. 429 Too Many Requests</b>", styles["TableCell"]),
            Paragraph("Rate limit threshold exceeded.", styles["TableCell"]),
            Paragraph("Wait 60s or increase <code>API_RATE_LIMIT_DEFAULT_PER_MINUTE</code> in <code>.env</code>.", styles["TableCell"]),
        ],
    ]
    troubleshoot_table = Table(troubleshoot_data, colWidths=[1.8 * inch, 1.8 * inch, 3.4 * inch])
    troubleshoot_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(troubleshoot_table)
    story.append(PageBreak())

    # =========================================================================
    # SECTION 22: COMMON WINDOWS ADMINISTRATION COMMANDS
    # =========================================================================
    story.append(Paragraph("22. Common Windows Administration Commands", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph(
        "Quick reference for Windows PowerShell and Command Prompt operations:",
        styles["BodyCustom"]
    ))

    win_cmds = [
        ("Activate venv (PowerShell)", ".\\backend\\.venv\\Scripts\\Activate.ps1"),
        ("Activate venv (Command Prompt)", "backend\\.venv\\Scripts\\activate.bat"),
        ("Check Port 8000 (Backend)", "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue"),
        ("Check Port 5173 (Frontend)", "Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue"),
        ("Kill Process on Port 8000", "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force"),
        ("Check MongoDB Service", "Get-Service -Name MongoDB"),
        ("Start MongoDB Service", "Start-Service -Name MongoDB"),
        ("Stop MongoDB Service", "Stop-Service -Name MongoDB"),
    ]

    win_table_data = [[Paragraph("Operation", styles["TableHeader"]), Paragraph("PowerShell Command", styles["TableHeader"])]]
    for op, cmd in win_cmds:
        win_table_data.append([
            Paragraph(f"<b>{op}</b>", styles["TableCell"]),
            Paragraph(cmd, styles["TableCellMono"])
        ])

    win_table = Table(win_table_data, colWidths=[2.5 * inch, 4.5 * inch])
    win_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARY),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_LIGHT]),
    ]))
    story.append(win_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 23: DAILY OPERATIONS
    # =========================================================================
    story.append(Paragraph("23. Daily Operations: Startup & Orderly Shutdown", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))

    story.append(Paragraph("Daily Startup Sequence (5 Steps)", styles["SubSectionHeading"]))
    story.append(Paragraph("1. Start MongoDB: <code>Start-Service -Name MongoDB</code>", styles["BulletCustom"]))
    story.append(Paragraph("2. Start Backend: <code>.\\backend\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --port 8000 --reload</code>", styles["BulletCustom"]))
    story.append(Paragraph("3. Start Frontend: <code>cd frontend && npm run dev</code>", styles["BulletCustom"]))
    story.append(Paragraph("4. Open Browser: Navigate to <code>http://localhost:5173</code>", styles["BulletCustom"]))
    story.append(Paragraph("5. Authenticate: Log in with your assigned RBAC credentials.", styles["BulletCustom"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Orderly Shutdown Sequence", styles["SubSectionHeading"]))
    story.append(Paragraph("1. <b>Stop Live Monitoring:</b> If active, click <i>Stop Monitoring</i> in the UI (<code>/monitoring</code>) to flush flow buffers.", styles["BulletCustom"]))
    story.append(Paragraph("2. <b>Stop Frontend Server:</b> Press <code>Ctrl + C</code> in the Vite terminal.", styles["BulletCustom"]))
    story.append(Paragraph("3. <b>Stop Backend Server:</b> Press <code>Ctrl + C</code> in the FastAPI terminal. The lifespan context manager will gracefully close the MongoDB connection pool.", styles["BulletCustom"]))
    story.append(Paragraph("4. <b>(Optional) Stop MongoDB:</b> <code>Stop-Service -Name MongoDB</code> if host shutdown is desired.", styles["BulletCustom"]))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 24: SECURITY NOTES & PRODUCTION HARDENING
    # =========================================================================
    story.append(Paragraph("24. Security Best Practices & Production Hardening", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph("• <b>Rotate JWT Secret Key:</b> Generate a cryptographically random string (>= 32 chars) in production.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Enforce HTTPS / TLS:</b> Enable <code>STRICT_TRANSPORT_SECURITY_ENABLED=True</code> behind an SSL reverse proxy.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Protect Credentials:</b> Never commit <code>.env</code> files to Git repositories.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Disable Debug Mode:</b> Set <code>DEBUG=False</code> and <code>ENVIRONMENT=production</code> in production.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Restrict CORS:</b> Whitelist only trusted enterprise origins.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Isolate Virtual Environment:</b> Strictly contain all dependencies inside <code>backend/.venv</code>.", styles["BulletCustom"]))
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 25: KNOWN LIMITATIONS & OPERATIONAL BOUNDARIES
    # =========================================================================
    story.append(Paragraph("25. Known Limitations & Operational Boundaries", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=8))
    story.append(Paragraph("• <b>Live Capture Permissions:</b> Live packet capture on Windows requires Npcap with administrative privileges.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Zero-Day Proxy Representation:</b> Unseen attack detection scores represent an experimental zero-day proxy metric, not a mathematical guarantee of detecting every real-world zero-day exploit.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Memory Buffering Bounds:</b> In-memory flow aggregation is bounded at 10,000 flows to prevent memory exhaustion.", styles["BulletCustom"]))
    story.append(Paragraph("• <b>Single-Node Architecture:</b> Default setup is optimized for local evaluation. Enterprise multi-gigabit setups require Kafka message queuing and distributed GPU inference workers.", styles["BulletCustom"]))
    story.append(Spacer(1, 20))

    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_ACCENT, spaceAfter=10))
    story.append(Paragraph(
        "<b>End of Zero-Day NIDS Run Guide</b> — Developed for Enterprise Cyber Defense & Zero-Day Threat Mitigation.",
        ParagraphStyle(name="DocEnd", parent=styles["BodyCustom"], alignment=TA_CENTER, textColor=COLOR_TEXT_MUTED)
    ))

    # Build Document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Generated professional PDF at: {output_pdf_path}")


if __name__ == "__main__":
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "Zero_Day_NIDS_Complete_Run_Guide.pdf"))
    build_pdf(output_path)
