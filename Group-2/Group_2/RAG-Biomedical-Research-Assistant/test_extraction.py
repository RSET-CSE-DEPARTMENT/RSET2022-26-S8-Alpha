import ollama

# -------------------------
# PROMPTS
# -------------------------

SYSTEM_PROMPT = (
    "You are an expert medical assistant specialised in clinical and biomedical question answering. "
    "Answer questions accurately using ONLY the context provided. "
    "Do NOT use any outside knowledge. "
    "If the context does not contain enough information to answer, say so clearly."
)

USER_TEMPLATE = (
    "Use the following context to answer the question below in 2–3 clear, complete sentences.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)

# -------------------------
# CHANGE MODEL NAME HERE
# -------------------------

MODEL_NAME = "qwen2"   # Changed from mistral to llama3

# -------------------------
# INPUT
# -------------------------

context = """
metimes leading to death.\nNeurological manifestations of malaria, often associated with _Plasmodium falciparum_, include seizures,\n[psychosis, agitation, altered extrapyramidal signs, cerebellar ataxia, impaired consciousness, and coma .](javascript:void(0))\nThe WHO defines cerebral malaria as a condition where the patient has at least one hour of coma after the\nresolution of a seizure or hypoglycemia, with asexual forms of _Plasmodium falciparum_ on peripheral blood\n[smears, and no better explanation for the coma . It is also defined by a Glasgow Coma Scale (GCS) score](javascript:void(0))\n[below 11 . Many clinicians would make a diagnosis of cerebral malaria in patients with any neurological](javascript:void(0))\nmanifestation. The mortality rate of cerebral malaria ranges from 10% to 20%, with some sources citing rates\nas high as 30%. Additionally, up to 25% of children with cerebral malaria experience long-term motor,\n[cognitive, and/or behavioral impairments, with 10% developing epilepsy .](javascript:void(0))', 'source': 'Delayed_Onset_White_Matter_Lesions_on_Brain_MRI_in.pdf', 'section': 'General'}, {'rank': 2, 'score': 1.5963313579559326, 'text': 'A 50-year-old man presented to the Emergency Department (ED) in 2024 with fever, malaise, and severe\nheadaches for three to four days, following his return from Jamaica two weeks prior. He reported that these\nsymptoms felt very similar to his previous malaria infection. He had a confirmed non-cerebral malaria\ninfection in 2006, during which he had no neurological manifestations. He had no other significant past\nmedical history. The patient, a businessman, traveled frequently between Los Angeles and Jamaica. In 2021,\nhe had an ED visit for headaches, during which a brain MRI was negative (Figure _(javascript:void(0))_ ).', 'source': 'Delayed_Onset_White_Matter_Lesions_on_Brain_MRI_in.pdf', 'section': 'General'}, {'rank': 3, 'score': 1.5499839782714844, 'text': 'Malaria is a life-threatening tropical disease and remains\none of the most important global health problems .\nAccording to the World Health Organization (WHO),\n249 million people contracted malaria in 2022 and an\nestimated 608,000 died from it, 76% of whom were children under the age of five . Malaria can affect any\norgan system, with involvement of the central nervous\nsystem (CNS) being the most feared . Cerebral malaria\nhas a mortality rate of 15–20%, and even long-term survivors often suffer from neurocognitive sequelae . The\ndiagnostic patterns range from diffuse encephalopathy\nwith subsequent seizures to coma. Other organ dysfunctions such as kidney and liver failure usually occur in\nadults, while isolated cerebral malaria is more common\nin children. In endemic areas, almost half of children\nadmitted to hospitals present with neurological symptoms . The aetiopathogenesis of cerebral malaria is not\nfully understood . It is a multifactorial process triggered by sequestration and adhesion of red blood cells,\nan immunologic response and loss of blood–brain barrier\nintegrity .\nPost malaria neurologic syndrome (PMNS) was first\ndescribed in 1996 in patients suffering from acute confusion, psychosis or seizures within two days to two months\nafter recovery from cerebral malaria . The exact incidence is unknown due to misdiagnosis and underreporting, and there is no general definition of PMNS. In the\nlargest prospective study conducted to date in Vietnam,\nthe risk of developing PM', 'source': 'Anti_septin_complex_positive_autoimmune_encephalit.pdf', 'section': 'General'}, {'rank': 4, 'score': 1.5153032541275024, 'text': 'We report on the case of a 54-year-old German male\nwho was on a business trip to Chad for two weeks. In the\nsecond week of his stay abroad, symptoms began with\n\nnausea, vomiting and diarrhoea and led to an immediate\nreturn to his home country. After his arrival in Germany,\nthe neurocognitive symptoms (misbehaviour, headaches)\nworsened. The patient was admitted to our infectious\ndiseases ward one week after the onset of symptoms.\nWe saw an awake, cognitively impaired patient (Glasgow coma scale [GCS] 13) with stable vital signs and no\nliver or renal dysfunction. Severe thrombocytopenia (32\nGpt/L) was conspicuous. The patient’s condition deteriorated rapidly and somnolence (GCS 8) developed within\n24 h, requiring intensive cardio-circulatory monitoring.\n_Plasmodium falciparum_ was detected in blood smears\nwith a parasite density of 14%. Antiprotozoal therapy\nwith artesunate (2.4 mg per kg body weight IV) was initiated. After 24 h, the parasite density had decreased to\nless than 1% and oral follow-up therapy with artemether/\nlumefantrine was completed. In the further course of the\ndisease, no more malaria parasites could be detected.\nDue to the severe cerebral form of falciparum malaria, a\ncranial MRI examination was performed, which revealed\nunremarkable findings. The electroencephalographic\nexamination showed no abnormalities, and electroneurography revealed a discrete peripheral polyneuropathy.\nThe patient was discharged as cured on day eight.\nTwenty-five days after discharge', 'source': 'Anti_septin_complex_positive_autoimmune_encephalit.pdf', 'section': 'General'}, {'rank': 5, 'score': 0.4309564232826233, 'text': 'Malaria infections present a significant healthcare challenge, especially within endemic areas such as subSaharan Africa, South and Southeast Asia, the Middle East, Latin America, and the Western Pacific. The\nCenters for Disease Control and Prevention (CDC) and the World Health Organization (WHO) classify\nmalaria as a life-threatening disease caused by parasites of the genus _Plasmodium_, transmitted to humans\nvia infected female _Anopheles_ mosquitoes. The most threatening species are _Plasmodium falciparum_ and\n_Plasmodium vivax_ . In 2020, the WHO reported an estimated 241 million malaria cases and 627,000 malaria\n[deaths globally . The United States is not an endemic area and, therefore, malaria may be less well](javascript:void(0))\nunderstood in the United States. However, 68 cases of imported malaria were reported in the United States\n[in 2023 . In the context of the United States, imported malaria is defined as malaria that is acquired](javascript:void(0))\n[outside of the United States, with travel to an endemic region within two years of diagnosis .](javascript:void(0))\n\nUncomplicated malaria is characterized by non-specific findings such as fever, chills, headaches, myalgia,\n[abdominal pain, diarrhea, and cough . Complicated malaria can present with more severe symptoms and](javascript:void(0))\noutcomes, including anemia, respiratory distress, and multi-organ failure, sometimes leading to death.\nNeurological manifestations of malaria, often associated with _Plasmodiu', 'source': 'Delayed_Onset_White_Matter_Lesions_on_Brain_MRI_in.pdf', 'section': 'General'}]
"""
question = "What are the symptoms of malaria in patients?"

# -------------------------
# GENERATION
# -------------------------

prompt = USER_TEMPLATE.format(context=context, question=question)

response = ollama.chat(
    model=MODEL_NAME,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ],
    options={
        "temperature": 0.2,
        "num_predict": 200
    }
)

answer = response["message"]["content"]

print("\nModel:", MODEL_NAME)
print("\nAnswer:\n")
print(answer)
