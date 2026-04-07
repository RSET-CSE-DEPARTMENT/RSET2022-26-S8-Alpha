import sys
from flan_generator import get_final_rag_answer

def run_manual_context_test(query: str, manual_context: str):
    print(f"\n🚀 Starting Manual Context RAG Test")
    print(f"🔍 Query: {query}")
    print(f"📏 Context Length: {len(manual_context)} characters")
    print("=" * 80)

    # =====================================================
    # 1. Package Manual Context
    # =====================================================
    # We wrap your string into a list of dicts to match the 
    # expected input of your flan_generator.py entry point.
    simulated_results = [
        {
            "rank": 1,
            "score": 0.0,
            "section": "Manual Input",
            "source": "manual_test_string",
            "text": manual_context
        }
    ]

    # =====================================================
    # 2. Generation Step
    # =====================================================
    print("\n🧠 GENERATION STEP: Flan-T5 Large Scientific Synthesis")
    print("-" * 80)

    # This will now trigger your sifter/distillation logic on the big string
    final_answer = get_final_rag_answer(
        user_query=query,
        retrieved_results=simulated_results
    )

    # =====================================================
    # 3. Display Results
    # =====================================================
    print(f"\n✅ FINAL ANSWER:")
    print("-" * 80)
    print(final_answer)
    print("\n" + "=" * 80)
    print(f"✅ Manual Test Complete.")

if __name__ == "__main__":
    # 1. Define your Query
    test_query = "what is the symptoms of malria in patients"

    # 2. Paste your 4000+ character context string here
    # Use triple quotes for multi-line strings
    test_context = """
    [{'rank': 1, 'score': -0.517379641532898, 'text': 'Malaria infections present a significant healthcare challenge, especially within endemic areas such as subSaharan Africa, South and Southeast Asia, the Middle East, Latin America, and the Western Pacific. The\nCenters for Disease Control and Prevention (CDC) and the World Health Organization (WHO) classify\nmalaria as a life-threatening disease caused by parasites of the genus _Plasmodium_, transmitted to humans\nvia infected female _Anopheles_ mosquitoes. The most threatening species are _Plasmodium falciparum_ and\n_Plasmodium vivax_ . In 2020, the WHO reported an estimated 241 million malaria cases and 627,000 malaria\n[deaths globally . The United States is not an endemic area and, therefore, malaria may be less well](javascript:void(0))\nunderstood in the United States. However, 68 cases of imported malaria were reported in the United States\n[in 2023 . In the context of the United States, imported malaria is defined as malaria that is acquired](javascript:void(0))\n[outside of the United States, with travel to an endemic region within two years of diagnosis .](javascript:void(0))\n\nUncomplicated malaria is characterized by non-specific findings such as fever, chills, headaches, myalgia,\n[abdominal pain, diarrhea, and cough . Complicated malaria can present with more severe symptoms and](javascript:void(0))\noutcomes, including anemia, respiratory distress, and multi-organ failure, sometimes leading to death.\nNeurological manifestations of malaria, often associated with _Plasmodiu', 'source': 'Delayed_Onset_White_Matter_Lesions_on_Brain_MRI_in.pdf', 'section': 'General'}, {'rank': 2, 'score': -0.792472779750824, 'text': 'A 9-year-old male patient from a malaria-endemic area, with no relevant past medical\nhistory, presented with a persistent febrile syndrome of six days’ duration. Fever was\nobjectively documented, with evening spikes reaching a maximum recorded temperature\nof 38.8 _[◦]_ C, and was associated with chills, holocranial headache, and asthenia. There were\nno accompanying respiratory, urinary, or gastrointestinal symptoms. The patient reported\nno recent travel and no family history of malaria. He had routine exposure to mosquitoes\nin his area of residence and did not regularly use a bed net.\nUpon admission, he was hemodynamically stable, with a blood pressure of\n94/51 mmHg, heart rate of 96 bpm, respiratory rate of 20 breaths per minute, and oxygen\nsaturation of 95% on room air. Physical examinations showed preserved general condition,\n\n[https://doi.org/10.3390/children13010145](https://doi.org/10.3390/children13010145)\n\n_Children_ **2026**, _13_, 145 3 of 11\n\nnormocolored mucosae, absence of jaundice, normal vesicular breath sounds without\nadditional noises, a soft and non-tender abdomen, and a neurological exam without focal\ndeficits or meningeal signs, or clinical evidence of cerebral malaria. No clinical criteria for\nsevere malaria were identified.\nNo clinical criteria for severe malaria were identified. Initial laboratory studies (Table 1)\nshowed no evidence of severe anemia, significant thrombocytopenia, hepatocellular injury,\nor renal dysfunction. Anthropometric evaluation re', 'source': 'Pediatric_Mixed__i_Plasmodium_vivax__i___i_P__falc.pdf', 'section': 'General'}, {'rank': 3, 'score': -1.728276014328003, 'text': 'We report on the case of a 54-year-old German male\nwho was on a business trip to Chad for two weeks. In the\nsecond week of his stay abroad, symptoms began with\n\nnausea, vomiting and diarrhoea and led to an immediate\nreturn to his home country. After his arrival in Germany,\nthe neurocognitive symptoms (misbehaviour, headaches)\nworsened. The patient was admitted to our infectious\ndiseases ward one week after the onset of symptoms.\nWe saw an awake, cognitively impaired patient (Glasgow coma scale [GCS] 13) with stable vital signs and no\nliver or renal dysfunction. Severe thrombocytopenia (32\nGpt/L) was conspicuous. The patient’s condition deteriorated rapidly and somnolence (GCS 8) developed within\n24 h, requiring intensive cardio-circulatory monitoring.\n_Plasmodium falciparum_ was detected in blood smears\nwith a parasite density of 14%. Antiprotozoal therapy\nwith artesunate (2.4 mg per kg body weight IV) was initiated. After 24 h, the parasite density had decreased to\nless than 1% and oral follow-up therapy with artemether/\nlumefantrine was completed. In the further course of the\ndisease, no more malaria parasites could be detected.\nDue to the severe cerebral form of falciparum malaria, a\ncranial MRI examination was performed, which revealed\nunremarkable findings. The electroencephalographic\nexamination showed no abnormalities, and electroneurography revealed a discrete peripheral polyneuropathy.\nThe patient was discharged as cured on day eight.\nTwenty-five days after discharge', 'source': 'Anti_septin_complex_positive_autoimmune_encephalit.pdf', 'section': 'General'}, {'rank': 4, 'score': -1.9954980611801147, 'text': 'show a steady rise in malaria\ncases since 2021, with 161 753 cases in 2021, increasing\nto 176 522 in 2022, 227 564 in 2023, and 255 500 in\n2024.  This upward trend highlights the urgent need for\nsustained and adaptive control strategies.\nIndia’s malaria control gains have been driven primarily\nby the National Vector-\xadBorne Disease Control Program,\nimplemented by state governments with support from the\ncentral government under the National Health Mission. \nSustained domestic investments have strengthened surveillance, early diagnosis, complete treatment and integrated\nvector management, contributing to a steady decline in\nmalaria cases and deaths since 2000. These efforts have\nbeen augmented by international partnerships, notably\nthe Global Fund to Fight AIDS, Tuberculosis and Malaria\n(GFATM). GFATM has supported India’s malaria control\nefforts since 2005. Through successive grant cycles,\nit has supported the Intensified Malaria Elimination\nProject (IMEP) in high-\xadendemic districts by providing\nlong-\xadlasting insecticidal nets (LLINs), rapid diagnostic\ntests (RDTs), artemisinin-\xadbased combination therapies,\ninjectable artesunate and other essential commodities, in\naddition to funding human resources, capacity building,\ninformation–education–communication activities and\nprogramme mobility. While IMEP-\xadI (2018–2021) targeted\nseven northeastern states and Madhya Pradesh, IMEP-\xadII\n(2021–2024), invested US$46.31 million, expanded to\n3 more states, Odisha, Jharkhand and Chhattisgarh,', 'source': 'Multicentric_longitudinal_study_on_malaria_burden_.pdf', 'section': 'General'}, {'rank': 5, 'score': -2.2538743019104004, 'text': 'logical complications.  While neuropsychiatric manifestations such as seizures,\ndelirium, and coma are well recognized in\nacute cerebral malaria, delayed neuropsychiatric syndromes within 2 months after\nclinically proven recovered malaria and\nparasite clearance, collectively termed\npost-malaria neurological syndrome\n(PMNS), are less common and thought to\nbe immune-mediated.  It occurs typically\nbetween 4 and 30 days after parasite clearance. A wide range of neuropsychiatric\nand neurological symptoms, including\nconfusion, psychosis, ataxia, seizures,\ncatatonia, myoclonus, mood disturbances, and movement abnormalities, characterizes it.  Unlike acute cerebral malaria,\nPMNS presents with a symptom-free\ninterval following malaria treatment, normal neuroimaging, and negative parasitemia, making it diagnostically challenging\nand often mistaken for functional or\n\nprimary psychiatric illness.  Recognition\nof PMNS is clinically crucial in endemic\nregions, as its manifestations are typically\ntransient and reversible with symptomatic treatment and supportive care, and\ndo not require prolonged psychiatric or\nantipsychotic therapy.  Awareness of\nthis syndrome is essential to distinguish\nit from drug-induced effects, relapse of\ninfection, or new-onset psychiatric disorders. We present three women with\nfalciparum malaria who subsequently\ndeveloped distinct, short-lived neuropsychiatric syndromes—complex motor\ntics, catatonia, and obsessive-compulsive\nsymptoms—despite adequate treatment\nand ', 'source': 'A_Case_Series_of_Transient_Neuropsychiatric_Manife.pdf', 'section': 'General'}]
    """

    run_manual_context_test(test_query, test_context)