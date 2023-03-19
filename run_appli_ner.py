import streamlit as st 
import spacy
from spacy import displacy
import nltk
from nltk.tokenize import word_tokenize
import requests
import bs4
import pandas as pd
import textdistance
nltk.download('punkt')
nlp = spacy.load(R"output_clean/model-best")
def analyze_text(text):
	return nlp(text)

@st.cache
def load_cim_df():
    return pd.read_csv('cim_desc.csv', sep=',')

@st.cache
def load_vidal_df():
    return pd.read_csv('vidal.csv', sep=',')

@st.cache
def load_atc_df():
    return pd.read_csv('code_atc.csv', sep=',')

def get_atc_code(STRING):
    VIDAL = load_vidal_df()
    atc = load_atc_df()
    
    #On cherche la substance correspondant le plus au nom commercial
    previous_best = 0
    best_ix = 0
    for ix in VIDAL.index:
        dist = textdistance.jaro_winkler.normalized_similarity(STRING, VIDAL.at[ix,'nom_com_prep'])
        if dist > previous_best:
            previous_best = textdistance.jaro_winkler.normalized_similarity(STRING, VIDAL.at[ix,'nom_com_prep'])
            best_ix = ix
            
    res = VIDAL.at[best_ix, 'denomination_substance']
    
    #On cherche le code atc relié à la substance
    previous_best_code = 0
    best_ix_code = 0
    for ix_code in atc.index:
        dist_code = textdistance.jaro_winkler.normalized_similarity(res, atc.at[ix_code,'substance'])
        if dist_code > previous_best_code:
            previous_best_code = textdistance.jaro_winkler.normalized_similarity(res, atc.at[ix_code,'substance'])
            best_ix_code = ix_code
            
    res_ATC = atc.at[best_ix_code, 'atc']
    denom_ATC = atc.at[best_ix_code, 'substance']
    
    return res_ATC, denom_ATC

def main():
    st.title("Détection de code CIM et ATC à partir de texte brut (Prototype)")
    data_cim = load_cim_df()
    st.sidebar.warning("""
    **TODO NEXT :**    
    -    Optimiser le modèle NLP pour une meilleur détection des entités
    -    Ajouter une couche de sémantique (ex: ne pas détecter une entité si elle ne fait pas référence au patient, ou si il y a une négation devant signifiant son absence)
    -    Ajouter un correcteur orthographique pour nettoyer les entités détectées
    -    Etre indépendant du requêtage HTML sur le site aide au codage (ie. Construire notre propre moteur de recheche, ou API aideaucodage pour les pathologies)
    -    Optimiser la façon dont est détecté le code ATC des médicaments
    -    Intégrer la reconnaisance des codes CCAM, NGAP (actes professionnels), NABM (actes bio)
    -    Optimiser le temps d'exécution
        """)
    hide_explainations = st.checkbox("Masquer les explications")
    if hide_explainations == False:
        st.info("""
    On utilise les modèles créés à partir des RPU annotés pour détecter les entités dans du texte entrées par l'utilisateur et les standardiser en 
    les reliant au code CIM ou ATC qui leur est associé. 
    -    Si une pathologie est détectée, on lance une recherche sur le site aideaucodage et on récupère le premier résultat de la requête.
    -    Si l'entité est un médicament, on récupère dans un premier temps le nom du principe actif à l'aide d'une calcul de distance (jaro-winkler) 
    entre le nom de l'entité et une table de référence, puis on récupère le code ATC correspondant au principe actif (dans une table de référence)
        """)

    raw_text = st.text_area("Entrer une phrase à tester","cancer prostate au stade terminal, cancer des testicules. Traitement en cours: doliprane, lovenox")
    if st.button('Valider'):
        with st.spinner("Exécution du code en cours..."):
            docx = analyze_text(raw_text)
            html = displacy.render(docx,style="ent")
            #st.write(html,unsafe_allow_html=True) #Pour display les résultats
            for ent in docx.ents:
                if ent.label_ == 'MED_Molecule':
                    res_ATC, denom_ATC = get_atc_code(str(ent).upper())
                    st.markdown("**Entité reconnue:** "+str(ent)+" **--- Type: **Médicament** --- Code ATC détecté:** "+res_ATC+" - "+denom_ATC)
                    
                else:
                    query = 'https://www.aideaucodage.fr/cim-'
                    entity = ent.text
                    for mot in [entity]:
                        tokens = word_tokenize(mot, language='french')
                        for token in tokens:
                            query = query+token+'+'
                    query = query[:-1] #On retire le dernier '+'
                    
                    
                    response = requests.get(query)
                    soup = bs4.BeautifulSoup(response.text, 'html.parser')
                    em_box = soup.find_all("tr")
                    res = em_box[0].span.string #0 car on prend premier résultat
                    desc = data_cim.at[data_cim.loc[data_cim.libelle == res].index[0], 'description_longue']
                    st.markdown("**Entité reconnue:** "+str(ent)+" **--- Type: **Pathologie** --- Code CIM détecté:** "+res+" - "+desc)
            
if __name__ == '__main__':
	main()
