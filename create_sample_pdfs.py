"""Generate realistic test PDF documents for testing the PDF Organizer.

Creates a variety of sample documents in the test_documents/ folder:
- WHO report (Public Health / WHO)
- Epidemiology report (Public Health / Epidemiology)
- Scientific article (Research / Scientific Articles)
- Business invoice (Administration / Invoices)
- Procurement tender (Administration / Procurement)
- User manual (Guides / Manuals)
- Meeting minutes (Meetings / Meeting Documents)
- Scanned document (no extractable text -> OCR required)
- Corrupted file (for error resilience testing)
"""

from pathlib import Path
import sys

def generate_samples(target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    try:
        import fitz
    except ImportError:
        print("PyMuPDF (fitz) is required to generate formatted test PDFs.")
        return []

    # 1. WHO Public Health Report
    p1 = target_dir / "A78_13_Health_Emergency_Preparedness.pdf"
    doc1 = fitz.open()
    page1 = doc1.new_page()
    page1.insert_text((50, 72), "World Health Organization\nSeventy-eighth World Health Assembly\nA78/13\nProvisional agenda item 14.1\n\nHealth Emergency Preparedness, Response and Resilience", fontsize=14)
    page1.insert_text((50, 180), "Report by the Director-General\n\n1. At its seventy-seventh World Health Assembly in 2024, the Health Assembly considered progress on global health emergency architecture.\n2. The WHO Secretariat continues to provide technical guidance and support to Member States regarding disease surveillance and public health emergencies.\n3. Member States are requested to note the recommendations.", fontsize=11)
    doc1.set_metadata({
        "title": "Health emergency preparedness and response",
        "author": "World Health Organization",
        "subject": "Public Health Emergency Preparedness",
    })
    doc1.save(str(p1))
    doc1.close()
    created.append(p1)

    # 2. Epidemiology Surveillance Report
    p2 = target_dir / "Weekly_Epidemiological_Record_2025.pdf"
    doc2 = fitz.open()
    page2 = doc2.new_page()
    page2.insert_text((50, 72), "EPIDEMIOLOGY BULLETIN — 2025\nGlobal Disease Outbreak and Surveillance", fontsize=14)
    page2.insert_text((50, 140), "Abstract:\nThis report summarizes weekly surveillance data for infectious disease outbreaks across member territories. Key monitoring includes epidemiological trends, transmission patterns, and public health countermeasures.", fontsize=11)
    doc2.set_metadata({
        "title": "Epidemiological Surveillance 2025",
        "author": "Global Health Agency",
        "subject": "Epidemiology and Outbreak Tracking",
    })
    doc2.save(str(p2))
    doc2.close()
    created.append(p2)

    # 3. Scientific Research Article
    p3 = target_dir / "Nature_Article_Genomic_Sequencing.pdf"
    doc3 = fitz.open()
    page3 = doc3.new_page()
    page3.insert_text((50, 72), "High-throughput Genomic Profiling in Cellular Differentiation\n\nAbstract\nHigh-throughput sequencing provides unprecedented insight into transcriptomic landscapes. In this peer-reviewed study, we present a novel methodology for identifying gene regulatory networks.\n\nIntroduction\nRecent advances in single-cell genomics enable characterization of heterogeneous cell populations.\n\nMethodology\nSamples were processed using droplet-based RNA-seq.\n\nReferences\n1. Smith et al., Nature Genetics (2024). doi:10.1038/s41588-024-0001", fontsize=11)
    doc3.set_metadata({
        "title": "High-throughput Genomic Profiling",
        "author": "Dr. E. Vance",
        "subject": "Genomics Research",
    })
    doc3.save(str(p3))
    doc3.close()
    created.append(p3)

    # 4. Administration Invoice
    p4 = target_dir / "Invoice_INV-2024-9041.pdf"
    doc4 = fitz.open()
    page4 = doc4.new_page()
    page4.insert_text((50, 72), "INVOICE\n\nInvoice Number: INV-2024-9041\nDate: 2024-11-15\nBilling To: Client Services Inc.\nPayment Due Date: 2024-12-15\n\nDescription: Enterprise Software Support & Consulting\nTotal Amount Due: $1,250.00 USD\n\nPlease submit payment by wire transfer.", fontsize=12)
    doc4.set_metadata({
        "title": "Invoice INV-2024-9041",
        "author": "Accounting Dept",
    })
    doc4.save(str(p4))
    doc4.close()
    created.append(p4)

    # 5. User Guide / Manual
    p5 = target_dir / "QuickStart_User_Manual_v3.pdf"
    doc5 = fitz.open()
    page5 = doc5.new_page()
    page5.insert_text((50, 72), "User Guide & Instruction Manual\nVersion 3.0\n\nGetting Started:\nStep 1: Connect hardware to power source.\nStep 2: Follow on-screen setup tutorial.\nStep 3: Complete calibration protocol before operation.", fontsize=12)
    doc5.set_metadata({
        "title": "User Guide and Instruction Manual",
        "author": "Technical Publications",
    })
    doc5.save(str(p5))
    doc5.close()
    created.append(p5)

    # 6. Meeting Minutes
    p6 = target_dir / "Board_Meeting_Minutes_Oct2024.pdf"
    doc6 = fitz.open()
    page6 = doc6.new_page()
    page6.insert_text((50, 72), "Executive Board Meeting — Minutes\nDate: October 24, 2024\n\nAttendees:\n- J. Smith (Chair)\n- M. Dupont (Secretary)\n\nAgenda:\n1. Approval of previous meeting minutes\n2. Q3 Operations review\n3. Budget allocations for 2025\n\nDecisions and Action Items:\nThe board unanimously approved the proposed schedule.", fontsize=11)
    doc6.set_metadata({
        "title": "Executive Board Meeting Minutes",
        "author": "Board Secretary",
    })
    doc6.save(str(p6))
    doc6.close()
    created.append(p6)

    # 7. Procurement Tender
    p7 = target_dir / "RFP_Procurement_IT_Equipment.pdf"
    doc7 = fitz.open()
    page7 = doc7.new_page()
    page7.insert_text((50, 72), "REQUEST FOR PROPOSAL (RFP)\nPublic Procurement Notice\n\nTender Reference: PROC-2024-008\nProject: High-Capacity Server Hardware Procurement\n\nBidding Instructions:\nAll qualified vendors are invited to submit competitive bids. Proposals must satisfy regulatory compliance standards and specifications.", fontsize=11)
    doc7.set_metadata({
        "title": "RFP Procurement Server Hardware",
        "author": "Procurement Office",
    })
    doc7.save(str(p7))
    doc7.close()
    created.append(p7)

    # 8. Scanned PDF (Blank/Image simulation -> OCR required)
    p8 = target_dir / "Scanned_Archive_Record_1998.pdf"
    doc8 = fitz.open()
    doc8.new_page()  # Page with 0 text content
    doc8.save(str(p8))
    doc8.close()
    created.append(p8)

    # 9. Subdirectory with a Pharmacovigilance report
    sub_dir = target_dir / "subfolder_safety"
    sub_dir.mkdir(parents=True, exist_ok=True)
    p9 = sub_dir / "Drug_Safety_Pharmacovigilance_Review.pdf"
    doc9 = fitz.open()
    page9 = doc9.new_page()
    page9.insert_text((50, 72), "Annual Pharmacovigilance and Drug Safety Assessment Report\n\nSummary:\nEvaluation of adverse drug reactions, post-marketing surveillance, and risk mitigation strategies conducted in 2024. The pharmacovigilance safety committee reviewed clinical trial data.", fontsize=11)
    doc9.set_metadata({
        "title": "Annual Pharmacovigilance Assessment",
        "author": "Drug Safety Monitoring Committee",
    })
    doc9.save(str(p9))
    doc9.close()
    created.append(p9)

    # 10. Corrupted file (not a valid PDF)
    p10 = target_dir / "corrupted_document.pdf"
    p10.write_bytes(b"%PDF-1.4\nTRUNCATED_AND_CORRUPTED_DATA_TESTING_ERROR_HANDLING\x00\xff\xfe")
    created.append(p10)

    # 11. French Invoice (Administration / Invoices)
    p11 = target_dir / "Facture_Prestation_Conseil_2024.pdf"
    doc11 = fitz.open()
    page11 = doc11.new_page()
    page11.insert_text((50, 72), "FACTURE N° F-2024-0042\nDate: 12/03/2024\n\nClient: Agence Régionale de Santé\nObjet: Prestation d'expertise en santé publique\n\nTotal HT: 2 500,00 €\nTVA (20%): 500,00 €\nTotal TTC: 3 000,00 €\n\nÉchéance de paiement: 30 jours à réception.\nRèglement par virement bancaire sur compte IBAN: FR76 3000 4000 0001 2345 6789 01", fontsize=11)
    doc11.set_metadata({
        "title": "Facture Prestation Conseil",
        "author": "Cabinet Conseil Santé",
    })
    doc11.save(str(p11))
    doc11.close()
    created.append(p11)

    # 12. French Epidemiology Surveillance Bulletin (Public Health / Epidemiology)
    p12 = target_dir / "Bulletin_Surveillance_Epidemiologique_2024.pdf"
    doc12 = fitz.open()
    page12 = doc12.new_page()
    page12.insert_text((50, 72), "Santé Publique France\nPoint Épidémiologique Hebdomadaire — 2024\n\nSurveillance des maladies infectieuses et alertes sanitaires\n\nSynthèse:\nLe présent bulletin présente les indicateurs clés de surveillance épidémiologique en France métropolitaine. L'analyse montre une stabilité des taux d'incidence pour les syndromes infectieux saisonniers. Les mesures de veille sanitaire et de prévention restent actives.", fontsize=11)
    doc12.set_metadata({
        "title": "Point Épidémiologique Hebdomadaire 2024",
        "author": "Santé Publique France",
        "subject": "Surveillance épidémiologique et veille sanitaire",
    })
    doc12.save(str(p12))
    doc12.close()
    created.append(p12)

    # 13. French Sanitary Decree (Legal / Regulations)
    p13 = target_dir / "Decret_2024_Dispositions_Sanitaires.pdf"
    doc13 = fitz.open()
    page13 = doc13.new_page()
    page13.insert_text((50, 72), "RÉPUBLIQUE FRANÇAISE\nJournal Officiel\n\nDécret n° 2024-345 du 18 avril 2024 relatif à la conformité des dispositifs médicaux\n\nLe Premier ministre,\nSur le rapport du ministre de la santé et de la prévention,\nVu le code de la santé publique, notamment son article L. 5121-1 ;\nVu la directive européenne 2017/745 ;\nDécrète :\nArticle 1er — Les fabricants doivent assurer la conformité et la sécurité des dispositifs médicaux selon les normes réglementaires en vigueur.", fontsize=11)
    doc13.set_metadata({
        "title": "Décret n° 2024-345 relatif aux dispositifs médicaux",
        "author": "Ministère de la Santé",
        "subject": "Réglementation sanitaire",
    })
    doc13.save(str(p13))
    doc13.close()
    created.append(p13)

    # 14. French Strategic Health Plan (Strategy / Strategic Plans)
    p14 = target_dir / "Plan_Strategique_National_Sante_2030.pdf"
    doc14 = fitz.open()
    page14 = doc14.new_page()
    page14.insert_text((50, 72), "Plan Stratégique National de Santé — Horizon 2030\nFeuille de route pour la transformation du système de soins\n\nOrientations stratégiques prioritaires:\n1. Renforcer les soins de santé primaires et la prévention.\n2. Accélérer la modernisation numérique des parcours de soins.\n3. Garantir la sécurité et la résilience face aux crises sanitaires.\n\nCe cadre stratégique définit les objectifs pluriannuels et les indicateurs d'impact.", fontsize=11)
    doc14.set_metadata({
        "title": "Plan Stratégique National de Santé 2030",
        "author": "Comité de Pilotage Stratégique",
        "subject": "Stratégie de santé publique",
    })
    doc14.save(str(p14))
    doc14.close()
    created.append(p14)

    # 15. French Meeting Minutes (Meetings / Meeting Documents)
    p15 = target_dir / "PV_Reunion_Comite_Pilotage_2024.pdf"
    doc15 = fitz.open()
    page15 = doc15.new_page()
    page15.insert_text((50, 72), "Procès-Verbal de la Réunion du Comité de Pilotage (COPIL)\nDate: 25 mai 2024\n\nParticipants:\n- Dr. M. Laurent (Président)\n- Mme S. Bernard (Rapporteure)\n\nOrdre du jour:\n1. Approbation du compte-rendu de la séance précédente.\n2. Point d'étape sur les projets en cours.\n3. Calendrier des prochaines réunions.\n\nRelevé de décisions:\nLe comité valide à l'unanimité les arbitrages proposés.", fontsize=11)
    doc15.set_metadata({
        "title": "Procès-Verbal Comité de Pilotage",
        "author": "Secrétariat Général",
    })
    doc15.save(str(p15))
    doc15.close()
    created.append(p15)

    # 16. Explainable AI Research (Research / Explainable AI (XAI))
    p16 = target_dir / "NeurIPS_2024_Explainable_AI_SHAP_Counterfactuals.pdf"
    doc16 = fitz.open()
    page16 = doc16.new_page()
    page16.insert_text(
        (50, 72),
        "NeurIPS 2024 Conference on Neural Information Processing Systems\n\n"
        "Unified Feature Attribution and Counterfactual Explanations in Deep Learning\n\n"
        "Abstract:\n"
        "Explainable AI (XAI) is critical for trustworthy machine learning. In this work, we investigate "
        "interpretability mechanisms including SHAP (Shapley Additive Explanations), integrated gradients, "
        "and counterfactual generation. We establish formal bounds on explanation fidelity across deep neural "
        "networks, transformer architectures, and ablation studies on benchmark datasets.",
        fontsize=11
    )
    doc16.set_metadata({
        "title": "Unified Feature Attribution and Counterfactual Explanations in Deep Learning",
        "author": "PhD Researcher in Explainable AI",
        "subject": "Explainable AI, Machine Learning, Interpretability",
    })
    doc16.save(str(p16))
    doc16.close()
    created.append(p16)

    # 17. Insurtech & Actuarial Risk Modeling (Insurtech / Claims & Fraud Detection)
    p17 = target_dir / "Rapport_Actuariat_Insurtech_Tarification_Sinistres.pdf"
    doc17 = fitz.open()
    page17 = doc17.new_page()
    page17.insert_text(
        (50, 72),
        "Étude Actuarielle et Data Science Insurtech\n"
        "Modélisation Prédictive de la Fréquence des Sinistres et Détection de Fraude\n\n"
        "Résumé exécutif:\n"
        "Ce rapport technique présente les modèles de tarification prédictive, le calcul du ratio combiné "
        "et la détection de la fraude à l'assurance. Conforme aux exigences prudentielles de Solvabilité II "
        "et IFRS 17, l'analyse intègre les données de télématique et les algorithmes de machine learning "
        "pour optimiser la souscription et le provisionnement des sinistres.",
        fontsize=11
    )
    doc17.set_metadata({
        "title": "Modélisation Prédictive des Sinistres et Détection de Fraude Insurtech",
        "author": "Data Scientist Insurtech",
        "subject": "Actuariat, Tarification, Sinistres, Fraude à l'assurance",
    })
    doc17.save(str(p17))
    doc17.close()
    created.append(p17)

    # 18. Sécurité Sanitaire & Dispositifs Médicaux (Sécurité Sanitaire / Dispositifs Médicaux)
    p18 = target_dir / "Dossier_Technique_Dispositifs_Medicaux_ISO13485_MDR.pdf"
    doc18 = fitz.open()
    page18 = doc18.new_page()
    page18.insert_text(
        (50, 72),
        "Direction Sécurité Sanitaire & Affaires Réglementaires\n"
        "Dossier Technique de Marquage CE — Dispositifs Médicaux (Règlement MDR 2017/745)\n\n"
        "1. Objet et champ d'application:\n"
        "Évaluation clinique et analyse de risques selon les normes ISO 13485 et ISO 14971. "
        "Ce document établit la conformité aux exigences générales de sécurité sanitaire, de traçabilité "
        "et de matériovigilance. La validation logicielle et les protocoles de biocompatibilité sont certifiés "
        "conformes aux recommandations de l'ANSM et de la HAS.",
        fontsize=11
    )
    doc18.set_metadata({
        "title": "Dossier Technique de Sécurité Sanitaire Dispositifs Médicaux ISO 13485",
        "author": "Ingénieur Étude et Dév Sécurité Sanitaire",
        "subject": "Dispositifs Médicaux, ISO 13485, Sécurité Sanitaire, Marquage CE",
    })
    doc18.save(str(p18))
    doc18.close()
    created.append(p18)

    print(f"Successfully generated {len(created)} test documents in {target_dir}")
    return created

if __name__ == "__main__":
    test_dir = Path(__file__).resolve().parent / "test_documents"
    generate_samples(test_dir)
