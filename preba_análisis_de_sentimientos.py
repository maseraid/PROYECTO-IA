from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer, util
import torch

# 1. Cargar modelos preentrenados
emotion_model_name = "j-hartmann/emotion-english-distilroberta-base"  # Modelo de emociones (inglés)
semantic_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Modelo para inferencia semántica
tokenizer = AutoTokenizer.from_pretrained(emotion_model_name)
emotion_model = AutoModelForSequenceClassification.from_pretrained(emotion_model_name)
semantic_model = SentenceTransformer(semantic_model_name)

# 2. Definir emociones, sentimientos y patrones contextuales
emotions = ["Ira", "Asco", "Miedo", "Tristeza", "Felicidad", "Sorpresa"]

sentimientos_nivel1 = [
    "Irritado", "Frustrado", "Distante", "Crítico", "Hostil", "Enfurecido", "Agresivo", 
    "Decepcionado", "Horrible", "Repugnante", "Odioso", "Culpable", 
    "Inseguro", "Ansioso", "Asustado", "Espantado", "Aterrorizado",
    "Abandonado", "Desesperado", "Deprimido", "Aislado", "Melancólico", 
    "Optimista", "Orgulloso", "Interesado", "Eufórico", "Alegre", 
    "Conmocionado", "Asombrado", "Confundido"
]

sentimientos_nivel2 = [
    "Irritativo", "Provocado", "Molesto", "Exasperado", "Desconfiado", "Cínico", "Sarcástico", "Moralista",
    "Provocador", "Hiriente", "Odioso", "Furioso", "Amenazante", "Dominante", 
    "Descontento", "Insatisfecho", "Avergonzado", "Deshonrado", "Revoltoso", "Repulsivo", 
    "Vengativo", "Resentido", "Arrepentido", "Remordido", "Vulnerable", "Rechazado", 
    "Preocupado", "Nervioso", "Temoroso", "Intimidador", "Sobrecogido", "Alarmado", 
    "Horrorizado", "Atemorizado", "Ignorado", "Desamparado", "Indefenso", "Derrotado", 
    "Agotado", "Sin esperanza", "Solo", "Distante", "Nostálgico", "Desolado", 
    "Esperanzado", "Confiado", "Respetado", "Seguro", "Curioso", "Inspirado", 
    "Energizado", "Exaltado", "Divertido", "Contento", "Desconectado", "Aturdido", 
    "Impresionado", "Fascinado", "Desorientado", "Estupefacto"
]

# 3. Función para escalar intensidades a Likert (1-7)
def scale_to_likert(value, min_val=0.2, max_val=1.0):
    """Escala un valor flotante a la escala Likert de 1 a 7."""
    scaled_value = int(round((value - min_val) / (max_val - min_val) * 6 + 1))
    return min(max(scaled_value, 1), 7)

# 4. Función para analizar emociones principales
def analyze_emotions(text):
    """Detecta emociones principales con el modelo preentrenado."""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    outputs = emotion_model(**inputs)
    probabilities = torch.softmax(outputs.logits, dim=-1).detach().numpy()[0]
    return {emotions[i]: scale_to_likert(probabilities[i]) for i in range(len(probabilities)) if probabilities[i] > 0.2}

# 5. Función para inferir sentimientos implícitos mediante embeddings
def infer_implicit_sentiments(text, sentiments):
    """Usa embeddings para inferir sentimientos implícitos en el texto."""
    detected_sentiments = {}
    text_embedding = semantic_model.encode(text, convert_to_tensor=True)
    for sentiment in sentiments:
        sentiment_embedding = semantic_model.encode(sentiment, convert_to_tensor=True)
        similarity = util.pytorch_cos_sim(text_embedding, sentiment_embedding).item()
        if similarity > 0.5:  # Umbral ajustable
            detected_sentiments[sentiment] = scale_to_likert(similarity)
    return detected_sentiments

# 6. Programa principal
def main():
    print("Bienvenido al análisis emocional.")
    
    while True:
        user_input = input("Por favor, escribe cualquier cosa: ").strip()
        
        # Analizar emociones principales
        explicit_emotions = analyze_emotions(user_input)
        
        # Inferir sentimientos implícitos de Nivel 1 y Nivel 2
        implicit_sentiments_n1 = infer_implicit_sentiments(user_input, sentimientos_nivel1)
        implicit_sentiments_n2 = infer_implicit_sentiments(user_input, sentimientos_nivel2)
        
        # Verificar si se detectaron emociones o sentimientos
        if not explicit_emotions and not implicit_sentiments_n1 and not implicit_sentiments_n2:
            print("\nNo se detectaron emociones o sentimientos en tu texto.")
            print("Por favor, escribe cómo te sientes o cómo te ha ido en el día.\n")
            continue
        
        # Mostrar resultados
        print("\nResultados del análisis emocional:")
        
        if explicit_emotions:
            print("\nEmociones principales detectadas:")
            for emotion, intensity in explicit_emotions.items():
                print(f"- {emotion}: Intensidad {intensity}")
        
        if implicit_sentiments_n1:
            print("\nSentimientos de Nivel 1 detectados:")
            for sentiment, intensity in implicit_sentiments_n1.items():
                print(f"- {sentiment}: Intensidad {intensity}")
        
        if implicit_sentiments_n2:
            print("\nSentimientos de Nivel 2 detectados:")
            for sentiment, intensity in implicit_sentiments_n2.items():
                print(f"- {sentiment}: Intensidad {intensity}")
        
        break

if __name__ == "__main__":
    main()
