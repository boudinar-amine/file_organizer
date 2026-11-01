# Local Intelligent PDF Organizer — MVP

A privacy-first desktop application that intelligently classifies and organizes PDF documents on your local Windows PC.

## Core Principles

- **Privacy First**: 100% offline. No documents are uploaded to any external server or cloud service.
- **File Safety**: Never overwrites existing files. Analysis mode is strictly read-only (dry-run). File movement requires explicit user confirmation.
- **Full Undo Support**: Every organization operation is recorded in a SQLite transaction log and can be reversed with a single click.

---

## Features

- **Folder Scanning**: Recursively discovers `.pdf` files while collecting file metadata (size, dates, page count).
- **Text & Metadata Extraction**: Uses PyMuPDF (`pymupdf`) with configurable page limits (default: 2 pages). Automatically extracts first-page titles when embedded PDF metadata is missing or generic.
- **Scanned PDF Detection**: Image-only / scanned PDFs ($< 30$ chars/page) are automatically flagged as `Scanned / OCR required` and routed to the manual review queue.
- **Bilingual (EN/FR) Multi-Domain Classification**:
  - Covers Public Health (WHO/OMS, Epidemiology, Pharmacovigilance, Vaccination), Administration (Invoices/Factures, Procurement/Marchés Publics, Contracts, HR), Research (Scientific Articles, Theses), Legal (Laws, Regulations, Decrees), Strategy (Strategic Plans, Roadmaps), Guides (Manuals, SOPs), Meetings (Minutes/PV, Presentations), Finance, and Personal.
  - Multi-zone weighted scoring (Filename 3.0×, Title 2.5×, Lead text 1.8×, Body 1.0×).
  - Organization normalization (`OMS` $\rightarrow$ `World Health Organization`, `Santé Publique France`, `ANSM`, `HAS`, `Inserm`, `CDC`, `FDA`, `EMA`, etc.).
- **User Profile & Knowledge Graph (Section 21)**:
  - **Work is a Context, not a Domain**: Supports multiple career stages, employers, roles, consulting, freelance, and academic activities.
  - **Three Fundamental Dimensions**:
    * **Context (Scope)**: Why do I have this document? (`Work`, `Learning`, `Training`, `Reference`, `Personal`).
    * **Relationship**: What connects me to it? (Employer, Organization, Project, Role, Career Stage/Dates).
    * **Content**: What is the document actually about? (Domain, Topic, Document Type).
  - **Local Offline CV/Résumé Importer**:
    * Automatically extracts candidate employers, job titles, employment dates, domains, skills, and education from `.pdf`, `.docx`, and `.txt` files.
    * 100% offline and local; privacy checkbox to securely delete source CV after extraction.
    * Candidate review interface to Accept, Edit, Delete, or Merge extracted items.
  - **Progressive Discovery from Documents**:
    * Automatically inspects scanned documents to detect recurring organizations, clients, or domains not yet in the profile and proposes one-click additions.
- **Pre-execution Interactive UI/UX Tree Preview**:
  - Replaces raw text/JSON dumps with a visual hierarchical folder tree (`Category` $\rightarrow$ `Subcategory` $\rightarrow$ `File`).
  - Real-time search filter by filename, category, or document type.
  - Document Inspector Card displaying `FROM -> TO` path mappings, confidence progress bar, extracted metadata signals (Title, Author, Year), evidence weights, and matched rule markers.
  - Direct execution button (`⚡ Confirm & Organize Now`) straight from the preview.
- **Multi-Activity Personalization (`👤 Domain Profile`)**:
  - Personalize the classifier with multiple career activities and domains:
    * **PhD Researcher in Explainable AI (XAI) / AI Engineer**: `Research` $\rightarrow$ `Explainable AI (XAI)`, `Conference Papers` (NeurIPS, ICML, CVPR), `Deep Learning`, `Theses` (keywords: `shap`, `interpretability`, `lime`, `counterfactual`, etc.).
    * **Data Scientist in Insurtech**: `Insurtech` $\rightarrow$ `Risk Modeling & Actuarial`, `Claims & Fraud Detection`, `Underwriting & Pricing` (keywords: `actuarial`, `sinistre`, `fraude à l'assurance`, `solvency ii`, etc.).
    * **Étude et Dév Ingénieur in Sécurité Sanitaire**: `Sécurité Sanitaire` $\rightarrow$ `Dispositifs Médicaux`, `Normes & Qualité (ISO/HACCP)`, `Veille Sanitaire` (keywords: `dispositifs médicaux`, `iso 13485`, `marquage ce`, `matériovigilance`, etc.).
  - Ability to customize, add, or remove domains via `ProfileDialog`.
- **Optional Local AI (Ollama)**:
  - Connects to a locally running Ollama instance (`http://localhost:11434`, e.g. `llama3.2`).
  - Automatically inspects installed models via `/api/tags`. If no models are downloaded yet, the app gracefully alerts you with the exact command (`ollama pull llama3.2`) and seamlessly uses the tailored Rule Engine without throwing 404 errors.
- **Confidence Scoring**: High ($\ge 85\%$), Medium ($65-84\%$), and Low ($< 65\%$, needs review).
- **Execution Modes**:
  - **Safe Test Mode (COPY)**: Copies files into organized structure while keeping original source files untouched.
  - **Relocation Mode (MOVE)**: Safely relocates files into organized structure.
- **Filename Conflict Prevention**: Never overwrites files. Configurable to either skip & flag or auto-rename with `(1)`.
- **One-Click Undo**: Restores moved files back to their exact original paths or removes copies.

---

## Installation & Running

### Requirements
- Windows 10 / 11
- Python 3.10+
- PySide6 & PyMuPDF

### Quick Launch
Inside `C:\Users\HP\Desktop\pdf_organizer`:
- **Double-click** `run_app.bat`

Or run via terminal:
```powershell
cd C:\Users\HP\Desktop\pdf_organizer
python main.py
```

---

## Automated Test Suite

Run all 62 unit and integration tests:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```
