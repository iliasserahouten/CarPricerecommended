import streamlit as st
import pandas as pd
import joblib
import base64
from sklearn.metrics.pairwise import euclidean_distances
import numpy as np
import traceback

# Charger le modèle sauvegardé
model = joblib.load('best_model_pipeline.pkl')

def add_bg_from_local(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def normalize_features(df, features):
    result = df.copy()
    for feature in features:
        max_value = df[feature].max()
        min_value = df[feature].min()
        if max_value != min_value:
            result[feature] = (df[feature] - min_value) / (max_value - min_value)
        else:
            result[feature] = 0
    return result

def calculate_similarity_score(input_car, candidate_car, features_weights):
    score = 0
    for feature, weight in features_weights.items():
        if feature in ['Year', 'Mileage', 'Price']:
            # Pour ces caractéristiques, on calcule la différence relative
            max_val = max(input_car[feature], candidate_car[feature])
            min_val = min(input_car[feature], candidate_car[feature])
            if max_val != 0:
                similarity = min_val / max_val
            else:
                similarity = 1
            score += weight * similarity
        else:
            # Pour les autres caractéristiques, on vérifie l'égalité
            score += weight * (input_car[feature] == candidate_car[feature])
    return score

# Mapper les colonnes catégoriques avec gestion des valeurs manquantes
def preprocess_input(data):
    mappings = {
        'Emission_class': {'Euro 6': 1, 'Euro 6d-TEMP': 2, 'Euro 6d': 3, 'Euro 5': 0},
        'Doors': {'4/5 doors': 1, '2/3 doors': 0},
        'Drive_type': {'4x2': 0, '4x4': 1},
        'Fuel': {'Diesel': 0, 'Petrol': 1, 'Electric': 3, 'Hybrid': 2},
        'Transmission': {'Automatic': 0, 'Manual': 1}
    }

    # Créer une copie pour éviter les modifications sur place
    processed_data = data.copy()
    
    for column, mapping in mappings.items():
        if column in processed_data:
            # Remplacer les valeurs manquantes par une valeur par défaut avant le mapping
            processed_data[column] = processed_data[column].fillna(list(mapping.keys())[0])
            processed_data[column] = processed_data[column].map(mapping)
            # Si des valeurs n'ont pas été mappées, les remplacer par 0
            processed_data[column] = processed_data[column].fillna(0)
    
    # Convertir les colonnes numériques en float et remplacer les NaN par 0
    numeric_columns = ['Mileage', 'Power', 'Seats', 'CO2_emissions', 'Engine_capacity', 'Year']
    for col in numeric_columns:
        if col in processed_data:
            processed_data[col] = pd.to_numeric(processed_data[col], errors='coerce').fillna(0)
    
    return processed_data

# Charger les données existantes pour la recommandation avec gestion du cache
@st.cache_data
def load_existing_data(file_path):
    data = pd.read_csv(file_path)
    # Assurer que toutes les colonnes numériques sont du bon type
    numeric_columns = ['Mileage', 'Power', 'Seats', 'CO2_emissions', 'Engine_capacity', 'Year']
    for col in numeric_columns:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
    return data

# Ajouter l'image d'arrière-plan
add_bg_from_local("close-up-hand-holding-car-keys.jpg")

# Interface utilisateur avec Streamlit
st.title("Prédiction du Prix de Voitures")

# Entrée des caractéristiques
st.header("Entrez les caractéristiques de la voiture :")

Mileage = st.number_input("Kilométrage (Mileage)", min_value=0, step=1000)
Power = st.number_input("Puissance (Power en chevaux)", min_value=0, step=10)
Transmission = st.selectbox("Transmission", options=['Automatic', 'Manual'])
Fuel = st.selectbox("Type de carburant", options=['Diesel', 'Petrol', 'Electric', 'Hybrid'])
Drive_type = st.selectbox("Type de transmission", options=['4x2', '4x4'])
Doors = st.selectbox("Nombre de portes", options=['4/5 doors', '2/3 doors'])
Seats = st.selectbox("Nombre de sièges", options=[2, 3, 4, 5, 6, 7])
CO2_emissions = st.number_input("Émissions de CO2 (en g/km)", min_value=0, step=1)
Engine_capacity = st.number_input("Cylindrée (Engine capacity en litres)", min_value=0.0, step=0.1)
Emission_class = st.selectbox("Classe d'émission", options=['Euro 6', 'Euro 6d-TEMP', 'Euro 6d', 'Euro 5'])
Year = st.number_input("Année de fabrication", min_value=2011, max_value=2024, step=1)
Make = st.selectbox(
    "Marque de la voiture (Make)", 
    options=['Abarth', 'Alfa Romeo','Aston Martin', 'Audi', 'BMW', 'Bentley','Chevrolet', 'Citroën', 'Cupra', 'DR Automobiles', 'DS Automobiles','Dacia','Ferrari', 'Fiat', 'Ford', 'Honda', 'Hyundai', 'Jaguar','Jeep','Kia', 'Lamborghini', 'Lancia', 'Land Rover', 'Lexus','Lynk & Co', 'MG','MINI', 'Maserati', 'Mazda', 'Mercedes-Benz','Mitsubishi', 'Nissan', 'Opel', 'Peugeot', 'Polestar', 'Porsche','Renault', 'Seat', 'Smart', 'SsangYong', 'Subaru', 'Suzuki','Tesla', 'Toyota', 'Volkswagen', 'Volvo', 'Škoda'],
    index=3
)
Body = st.selectbox(
    "Type de carrosserie (Body)", 
    options=['SUV / offroad', 'Hatchback', 'Station Wagon', 'Sedans / saloons','MPV/VAN', 'MPV', 'Pick-up', 'Cargo VAN', 'Coupe'],
    index=0
)

Interior_material = st.selectbox(
    "Matériau de l'intérieur", 
    options=['Part leather interior','Cloth interior', 'Full leather interior','Other interior material', 'Velour interior'],
    index=2
)

# Bouton pour effectuer la prédiction
if st.button("Prédire le Prix"):
    # Préparer les données
    input_data = pd.DataFrame([{
        'Mileage': Mileage,
        'Power': Power,
        'Transmission': Transmission,
        'Fuel': Fuel,
        'Drive_type': Drive_type,
        'Doors': Doors,
        'Seats': Seats,
        'CO2_emissions': CO2_emissions,
        'Engine_capacity': Engine_capacity,
        'Emission_class': Emission_class,
        'Year': Year,
        'Make': Make,
        'Body': Body,
        'Interior_material': Interior_material
    }])

    # Prétraitement des données
    input_data = preprocess_input(input_data)

    # Sauvegarder dans session_state
    st.session_state.input_data = input_data

    try:
        # Effectuer la prédiction
        prediction = model.predict(input_data)
        # Afficher le résultat
        st.success(f"Prix prédit : {prediction[0]:,.2f} €")
    except Exception as e:
        st.error(f"Erreur lors de la prédiction : {str(e)}")

# Modification de la partie recommandation
if st.button("Recommander des Voitures Similaires"):
    if 'input_data' not in st.session_state:
        st.error("Veuillez d'abord entrer les informations de la voiture et effectuer une prédiction.")
    else:
        try:
            # Charger les données existantes
            existing_data = load_existing_data("recommandation.csv")
            
            # Récupérer la marque de la voiture prédite
            selected_make = st.session_state.input_data['Make'].iloc[0]
            
            # Filtrer d'abord par marque
            existing_data_filtered = existing_data[existing_data['Make'] == selected_make].copy()
            
            if existing_data_filtered.empty:
                st.warning(f"Aucune voiture similaire trouvée pour la marque {selected_make}")
            else:
                # Définir les poids des caractéristiques pour la similarité
                features_weights = {
                    'Year': 0.15,
                    'Mileage': 0.15,
                    'Power': 0.1,
                    'Engine_capacity': 0.1,
                    'Fuel': 0.1,
                    'Transmission': 0.1,
                    'Body': 0.1,
                    'Drive_type': 0.1,
                    'Interior_material': 0.05,
                    'Emission_class': 0.05
                }
                
                # Prétraiter les données d'entrée
                input_processed = preprocess_input(st.session_state.input_data)
                existing_processed = preprocess_input(existing_data_filtered)
                
                # Prédire le prix pour la voiture d'entrée
                predicted_price = model.predict(input_processed)[0]
                
                # Calculer les scores de similarité
                similarity_scores = []
                for idx, row in existing_processed.iterrows():
                    score = calculate_similarity_score(
                        input_processed.iloc[0],
                        row,
                        features_weights
                    )
                    
                    # Ajouter une pénalité basée sur la différence de prix
                    price_diff = abs(existing_data_filtered.loc[idx, 'price'] - predicted_price)
                    price_penalty = min(price_diff / predicted_price, 1)  # Normaliser la pénalité
                    final_score = score * (1 - 0.2 * price_penalty)  # Le prix compte pour 20% du score final
                    
                    similarity_scores.append((idx, final_score))
                
                # Trier par score de similarité
                similarity_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Sélectionner les 5 meilleures recommandations
                st.subheader(f"Voitures similaires {selected_make} :")
                
                # Afficher les recommandations avec plus de détails
                for idx, score in similarity_scores[:5]:
                    car = existing_data_filtered.loc[idx]
                    st.markdown(
                        f"""
                        [**{car['Make']} {car.get('Model', '')}**](https://carvago.com{car['Link']})  
                        Prix: {car['price']:,.2f}€ | Année: {int(car['Year'])} | Kilométrage: {car['Mileage']:,}km  
                        Moteur: {car['Engine_capacity']}L, {car['Power']}ch | {car['Fuel']} | {car['Transmission']}  
                        Similarité: {score:.2%}
                        """
                    )
                    st.markdown("---")
                    
        except Exception as e:
            st.error(f"Erreur lors de la recommandation : {str(e)}")
            st.error(f"Détails : {traceback.format_exc()}")